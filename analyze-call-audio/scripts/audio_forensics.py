#!/usr/bin/env python3
"""Prepare, query, and render auditable native-audio call investigations."""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib
import json
import logging
import re
import sys
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "gpt-audio-1.5"
DEFAULT_MAX_COMPLETION_TOKENS = 4096
DEFAULT_TIMEOUT_SECONDS = 180.0
DEFAULT_MAX_RETRIES = 2
MAX_METADATA_BYTES = 2_000_000
SCHEMA_VERSION = 1
CASE_FILENAME = "case.json"
CONVERSATION_FILENAME = "conversation.json"
SYSTEM_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "assets" / "analysis-system-prompt.txt"
)
LOGGER = logging.getLogger("audio_forensics")
MAX_API_ERROR_MESSAGE_LENGTH = 500


class ForensicsError(RuntimeError):
    """Represent a safe, user-facing forensic workflow error."""


@dataclass(frozen=True)
class SourceEvidence:
    """Describe a source artifact without copying it.

    :param path: Absolute source path.
    :type path: pathlib.Path
    :param sha256: SHA-256 digest of the source bytes.
    :type sha256: str
    :param byte_count: Source size in bytes.
    :type byte_count: int
    """

    path: Path
    sha256: str
    byte_count: int

    def as_json(self) -> dict[str, Any]:
        """Return a JSON-compatible representation.

        :return: Serialized source evidence.
        :rtype: dict[str, Any]
        """

        return {
            "path": str(self.path),
            "sha256": self.sha256,
            "bytes": self.byte_count,
        }


class CaseBundle:
    """Create and verify immutable call-evidence bundles."""

    def prepare(self, manifest_path: Path, case_directory: Path) -> Path:
        """Prepare a case bundle from a source manifest.

        :param manifest_path: Path to the case manifest JSON.
        :type manifest_path: pathlib.Path
        :param case_directory: New directory for the prepared case.
        :type case_directory: pathlib.Path
        :return: Path to the prepared case file.
        :rtype: pathlib.Path
        :raises ForensicsError: If sources or manifest fields are invalid.
        """

        manifest = self._read_json_object(manifest_path)
        self._validate_manifest(manifest)
        audio_path = self._resolve_source_path(manifest["audio_path"], "audio_path")
        metadata_path = self._optional_source_path(manifest.get("metadata_path"))
        audio_evidence = self._inspect_source(audio_path)
        media = self._inspect_wav(audio_path)
        metadata_evidence: SourceEvidence | None = None
        if metadata_path is not None:
            self._validate_metadata(metadata_path)
            metadata_evidence = self._inspect_source(metadata_path)
        if case_directory.exists():
            raise ForensicsError(
                f"Case directory already exists; refusing overwrite: {case_directory}"
            )
        case_directory.mkdir(parents=True)
        prepared_case = {
            "schema_version": SCHEMA_VERSION,
            "case_id": manifest["case_id"],
            "reported_failure": manifest["reported_failure"],
            "expected_behavior": manifest["expected_behavior"],
            "context": manifest.get("context", {}),
            "questions": manifest.get("questions", []),
            "sources": {
                "audio": audio_evidence.as_json(),
                "metadata": (
                    metadata_evidence.as_json()
                    if metadata_evidence is not None
                    else None
                ),
            },
            "media": media,
        }
        case_path = case_directory / CASE_FILENAME
        self._write_json(case_path, prepared_case)
        LOGGER.info("Prepared evidence bundle at %s", case_path)
        return case_path

    def load(self, case_directory: Path) -> dict[str, Any]:
        """Load and verify a prepared case.

        :param case_directory: Prepared case directory.
        :type case_directory: pathlib.Path
        :return: Prepared case data.
        :rtype: dict[str, Any]
        :raises ForensicsError: If the case or its sources changed.
        """

        case_path = case_directory / CASE_FILENAME
        prepared_case = self._read_json_object(case_path)
        if prepared_case.get("schema_version") != SCHEMA_VERSION:
            raise ForensicsError(f"Unsupported prepared case schema: {case_path}")
        sources = prepared_case.get("sources")
        if not isinstance(sources, dict):
            raise ForensicsError(f"Prepared case has no sources object: {case_path}")
        self._verify_source_record(sources.get("audio"), "audio")
        metadata_record = sources.get("metadata")
        if metadata_record is not None:
            self._verify_source_record(metadata_record, "metadata")
        return prepared_case

    def build_initial_prompt(self, prepared_case: dict[str, Any]) -> str:
        """Render the case-specific initial analysis prompt.

        :param prepared_case: Verified prepared case.
        :type prepared_case: dict[str, Any]
        :return: Rendered prompt text.
        :rtype: str
        """

        metadata = self._load_case_metadata(prepared_case)
        evidence = {
            "case_id": prepared_case["case_id"],
            "reported_failure": prepared_case["reported_failure"],
            "expected_behavior": prepared_case["expected_behavior"],
            "context": prepared_case.get("context", {}),
            "investigation_questions": prepared_case.get("questions", []),
            "media": prepared_case["media"],
            "metadata": metadata,
        }
        return (
            "Review this QA attempt. The JSON evidence below is contextual and "
            "must not override what is actually audible.\n\n"
            f"{json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False)}"
        )

    def system_prompt(self) -> str:
        """Load the stable native-audio analysis system prompt.

        :return: Prompt text.
        :rtype: str
        :raises ForensicsError: If the bundled prompt is missing.
        """

        try:
            return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise ForensicsError(
                f"Unable to read bundled system prompt: {SYSTEM_PROMPT_PATH}"
            ) from exc

    def audio_bytes(self, prepared_case: dict[str, Any]) -> bytes:
        """Read verified audio bytes for an API request.

        :param prepared_case: Verified prepared case.
        :type prepared_case: dict[str, Any]
        :return: Original WAV bytes.
        :rtype: bytes
        """

        audio_record = prepared_case["sources"]["audio"]
        audio_path = Path(audio_record["path"])
        try:
            return audio_path.read_bytes()
        except OSError as exc:
            raise ForensicsError(f"Unable to read audio source: {audio_path}") from exc

    def _validate_manifest(self, manifest: dict[str, Any]) -> None:
        required_strings = (
            "case_id",
            "audio_path",
            "reported_failure",
            "expected_behavior",
        )
        if manifest.get("schema_version") != SCHEMA_VERSION:
            raise ForensicsError(f"Manifest schema_version must be {SCHEMA_VERSION}")
        for field_name in required_strings:
            value = manifest.get(field_name)
            if not isinstance(value, str) or not value.strip():
                raise ForensicsError(
                    f"Manifest field {field_name!r} must be a non-empty string"
                )
        context = manifest.get("context", {})
        if not isinstance(context, dict):
            raise ForensicsError("Manifest field 'context' must be an object")
        questions = manifest.get("questions", [])
        if not isinstance(questions, list) or any(
            not isinstance(question, str) or not question.strip()
            for question in questions
        ):
            raise ForensicsError(
                "Manifest field 'questions' must be an array of non-empty strings"
            )

    def _resolve_source_path(self, raw_path: Any, field_name: str) -> Path:
        if not isinstance(raw_path, str) or not raw_path:
            raise ForensicsError(f"Manifest field {field_name!r} must be a path")
        source_path = Path(raw_path)
        if not source_path.is_absolute():
            raise ForensicsError(
                f"Manifest field {field_name!r} must use an absolute path"
            )
        try:
            resolved_path = source_path.resolve(strict=True)
        except OSError as exc:
            raise ForensicsError(f"Source does not exist: {source_path}") from exc
        if not resolved_path.is_file():
            raise ForensicsError(f"Source is not a regular file: {resolved_path}")
        return resolved_path

    def _optional_source_path(self, raw_path: Any) -> Path | None:
        if raw_path in (None, ""):
            return None
        return self._resolve_source_path(raw_path, "metadata_path")

    def _inspect_source(self, source_path: Path) -> SourceEvidence:
        byte_count = source_path.stat().st_size
        digest = hashlib.sha256()
        try:
            with source_path.open("rb") as source_file:
                for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError as exc:
            raise ForensicsError(f"Unable to hash source: {source_path}") from exc
        return SourceEvidence(source_path, digest.hexdigest(), byte_count)

    def _inspect_wav(self, audio_path: Path) -> dict[str, Any]:
        if audio_path.suffix.lower() != ".wav":
            raise ForensicsError("This skill currently accepts WAV audio only")
        try:
            with wave.open(str(audio_path), "rb") as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()
                frame_count = wav_file.getnframes()
                compression = wav_file.getcomptype()
        except (OSError, EOFError, wave.Error) as exc:
            raise ForensicsError(f"Invalid WAV source: {audio_path}") from exc
        if compression != "NONE" or sample_width != 2:
            raise ForensicsError("WAV must contain uncompressed 16-bit PCM audio")
        if channels < 1 or frame_rate < 1 or frame_count < 1:
            raise ForensicsError("WAV has invalid channel, sample-rate, or frame data")
        return {
            "format": "wav",
            "encoding": "pcm_s16le",
            "channels": channels,
            "sample_rate_hz": frame_rate,
            "frames": frame_count,
            "duration_seconds": round(frame_count / frame_rate, 6),
        }

    def _validate_metadata(self, metadata_path: Path) -> None:
        if metadata_path.stat().st_size > MAX_METADATA_BYTES:
            raise ForensicsError(
                f"Metadata exceeds {MAX_METADATA_BYTES} bytes: {metadata_path}"
            )
        self._read_json_object(metadata_path)

    def _load_case_metadata(
        self, prepared_case: dict[str, Any]
    ) -> dict[str, Any] | None:
        metadata_record = prepared_case["sources"].get("metadata")
        if metadata_record is None:
            return None
        return self._read_json_object(Path(metadata_record["path"]))

    def _verify_source_record(self, record: Any, label: str) -> None:
        if not isinstance(record, dict):
            raise ForensicsError(f"Prepared case has invalid {label} source record")
        raw_path = record.get("path")
        expected_digest = record.get("sha256")
        expected_bytes = record.get("bytes")
        if (
            not isinstance(raw_path, str)
            or not isinstance(expected_digest, str)
            or not isinstance(expected_bytes, int)
        ):
            raise ForensicsError(f"Prepared case has malformed {label} source record")
        source_path = self._resolve_source_path(raw_path, f"sources.{label}.path")
        actual = self._inspect_source(source_path)
        if actual.sha256 != expected_digest or actual.byte_count != expected_bytes:
            raise ForensicsError(
                f"Source changed after preparation; create a new bundle: {source_path}"
            )

    def _read_json_object(self, path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ForensicsError(f"Unable to read JSON file: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ForensicsError(f"Malformed JSON file: {path}: {exc}") from exc
        if not isinstance(value, dict):
            raise ForensicsError(f"JSON root must be an object: {path}")
        return value

    def _write_json(self, path: Path, value: dict[str, Any]) -> None:
        try:
            path.write_text(
                f"{json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)}\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise ForensicsError(f"Unable to write JSON file: {path}") from exc


class NativeAudioClient:
    """Call an OpenAI native-audio model through the official Python SDK."""

    def __init__(self, timeout_seconds: float, max_retries: int) -> None:
        """Initialize SDK request settings without accessing credentials.

        :param timeout_seconds: API request timeout.
        :type timeout_seconds: float
        :param max_retries: SDK retry count.
        :type max_retries: int
        """

        self.timeout_seconds: float = timeout_seconds
        self.max_retries: int = max_retries

    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Submit a Chat Completions payload using SDK-managed credentials.

        :param payload: Chat Completions request body.
        :type payload: dict[str, Any]
        :return: JSON-compatible raw API response.
        :rtype: dict[str, Any]
        :raises ForensicsError: If the SDK is unavailable or the request fails.
        """

        try:
            openai_module = importlib.import_module("openai")
        except ImportError as exc:
            raise ForensicsError(
                "The official OpenAI Python SDK is required for API calls; "
                + "install the 'openai' package in the active Python environment"
            ) from exc
        client_class = getattr(openai_module, "OpenAI", None)
        if client_class is None:
            raise ForensicsError("Installed OpenAI SDK does not provide OpenAI()")
        try:
            client = client_class(
                timeout=self.timeout_seconds,
                max_retries=self.max_retries,
            )
            response = client.chat.completions.create(**payload)
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            status_text = f", HTTP {status_code}" if status_code is not None else ""
            diagnostic_text = self._format_api_error(exc)
            raise ForensicsError(
                f"OpenAI SDK request failed ({type(exc).__name__}{status_text}); "
                + f"{diagnostic_text}; no credential value was read or logged "
                + "by this script"
            ) from None
        model_dump = getattr(response, "model_dump", None)
        if not callable(model_dump):
            raise ForensicsError("OpenAI SDK returned an unsupported response object")
        raw_response = model_dump(mode="json")
        if not isinstance(raw_response, dict):
            raise ForensicsError("OpenAI SDK response did not serialize to an object")
        return raw_response

    def _format_api_error(self, exception: Exception) -> str:
        """Return safe structured API diagnostics without request content.

        :param exception: Exception raised by the OpenAI SDK.
        :type exception: Exception
        :return: Redacted diagnostic fields.
        :rtype: str
        """

        fields: list[str] = []
        for name in ("code", "param", "request_id", "message"):
            value = getattr(exception, name, None)
            if not isinstance(value, str) or not value.strip():
                continue
            sanitized_value = self._sanitize_error_value(value)
            fields.append(f"{name}={sanitized_value}")
        return ", ".join(fields) if fields else "no safe API diagnostic available"

    def _sanitize_error_value(self, value: str) -> str:
        """Redact secrets and long encoded values from one diagnostic field.

        :param value: API diagnostic value.
        :type value: str
        :return: Safe single-line diagnostic value.
        :rtype: str
        """

        single_line = " ".join(value.split())
        without_keys = re.sub(r"sk-[A-Za-z0-9_-]+", "[redacted-key]", single_line)
        without_encoded_values = re.sub(
            r"[A-Za-z0-9+/=_-]{128,}",
            "[redacted-long-value]",
            without_keys,
        )
        return without_encoded_values[:MAX_API_ERROR_MESSAGE_LENGTH]


class ForensicsWorkflow:
    """Orchestrate preparation, model turns, and evidence-ledger rendering."""

    def __init__(self, case_bundle: CaseBundle | None = None) -> None:
        """Initialize the workflow.

        :param case_bundle: Optional case-bundle implementation for testing.
        :type case_bundle: CaseBundle | None
        """

        self.case_bundle: CaseBundle = case_bundle or CaseBundle()

    def analyze(
        self,
        case_directory: Path,
        model: str,
        max_completion_tokens: int,
        timeout_seconds: float,
        max_retries: int,
        dry_run: bool,
    ) -> Path:
        """Run or preview the initial native-audio analysis turn.

        :param case_directory: Prepared case directory.
        :type case_directory: pathlib.Path
        :param model: Native-audio Chat Completions model.
        :type model: str
        :param max_completion_tokens: Maximum response tokens.
        :type max_completion_tokens: int
        :param timeout_seconds: API timeout.
        :type timeout_seconds: float
        :param max_retries: SDK retry count.
        :type max_retries: int
        :param dry_run: Write only a sanitized request audit.
        :type dry_run: bool
        :return: Path to the audit or assistant response.
        :rtype: pathlib.Path
        """

        prepared_case = self.case_bundle.load(case_directory)
        conversation_path = case_directory / CONVERSATION_FILENAME
        if conversation_path.exists():
            raise ForensicsError(
                "Initial analysis already exists; use the follow-up command"
            )
        initial_prompt = self.case_bundle.build_initial_prompt(prepared_case)
        audio_bytes = self.case_bundle.audio_bytes(prepared_case)
        payload = self._build_payload(
            prepared_case,
            model,
            max_completion_tokens,
            initial_prompt,
            audio_bytes,
            [],
            None,
        )
        return self._execute_turn(
            case_directory,
            prepared_case,
            model,
            timeout_seconds,
            max_retries,
            payload,
            "Initial forensic analysis",
            dry_run,
        )

    def follow_up(
        self,
        case_directory: Path,
        question: str,
        model: str | None,
        max_completion_tokens: int,
        timeout_seconds: float,
        max_retries: int,
        dry_run: bool,
    ) -> Path:
        """Ask a focused question in an existing native-audio conversation.

        :param case_directory: Prepared case directory.
        :type case_directory: pathlib.Path
        :param question: Focused forensic question.
        :type question: str
        :param model: Optional model override.
        :type model: str | None
        :param max_completion_tokens: Maximum response tokens.
        :type max_completion_tokens: int
        :param timeout_seconds: API timeout.
        :type timeout_seconds: float
        :param max_retries: SDK retry count.
        :type max_retries: int
        :param dry_run: Write only a sanitized request audit.
        :type dry_run: bool
        :return: Path to the audit or assistant response.
        :rtype: pathlib.Path
        """

        if not question.strip():
            raise ForensicsError("Follow-up question must not be empty")
        prepared_case = self.case_bundle.load(case_directory)
        conversation = self._load_conversation(case_directory)
        conversation_model = conversation.get("model")
        if not isinstance(conversation_model, str):
            raise ForensicsError("Conversation has no valid model")
        selected_model = model or conversation_model
        if selected_model != conversation_model:
            raise ForensicsError(
                "Model changes require a separate prepared case for independent review"
            )
        initial_prompt = self.case_bundle.build_initial_prompt(prepared_case)
        audio_bytes = self.case_bundle.audio_bytes(prepared_case)
        turns = conversation.get("turns")
        if not isinstance(turns, list) or not turns:
            raise ForensicsError("Conversation has no completed initial turn")
        payload = self._build_payload(
            prepared_case,
            selected_model,
            max_completion_tokens,
            initial_prompt,
            audio_bytes,
            turns,
            question.strip(),
        )
        return self._execute_turn(
            case_directory,
            prepared_case,
            selected_model,
            timeout_seconds,
            max_retries,
            payload,
            question.strip(),
            dry_run,
        )

    def render(self, case_directory: Path, output_path: Path) -> Path:
        """Render an auditable Markdown evidence ledger.

        :param case_directory: Prepared case directory.
        :type case_directory: pathlib.Path
        :param output_path: New Markdown output path.
        :type output_path: pathlib.Path
        :return: Output path.
        :rtype: pathlib.Path
        """

        if output_path.exists():
            raise ForensicsError(f"Refusing to overwrite output: {output_path}")
        prepared_case = self.case_bundle.load(case_directory)
        conversation_path = case_directory / CONVERSATION_FILENAME
        conversation = (
            self._read_json_object(conversation_path)
            if conversation_path.exists()
            else {"turns": []}
        )
        audio = prepared_case["sources"]["audio"]
        metadata = prepared_case["sources"].get("metadata")
        media = prepared_case["media"]
        lines = [
            f"# Call-audio evidence ledger: {prepared_case['case_id']}",
            "",
            "## Source evidence",
            "",
            f"- **Audio:** [WAV](<{audio['path']}>)",
            f"- **Audio SHA-256:** `{audio['sha256']}`",
            (
                f"- **Media:** {media['duration_seconds']:.3f} seconds, "
                f"{media['sample_rate_hz']} Hz, {media['channels']} channel(s), "
                f"{media['encoding']}"
            ),
        ]
        if isinstance(metadata, dict):
            lines.extend(
                [
                    f"- **Metadata:** [JSON](<{metadata['path']}>)",
                    f"- **Metadata SHA-256:** `{metadata['sha256']}`",
                ]
            )
        else:
            lines.append("- **Metadata:** None supplied")
        lines.extend(
            [
                "",
                "## QA account",
                "",
                f"- **Reported failure:** {prepared_case['reported_failure']}",
                f"- **Expected behavior:** {prepared_case['expected_behavior']}",
                "- **Context:**",
                "",
                "```json",
                json.dumps(
                    prepared_case.get("context", {}),
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                ),
                "```",
                "",
                "## Native-audio model turns",
                "",
            ]
        )
        turns = conversation.get("turns", [])
        if not isinstance(turns, list) or not turns:
            lines.append("No completed model analysis is present.")
        else:
            for turn in turns:
                if not isinstance(turn, dict):
                    continue
                lines.extend(
                    [
                        f"### Turn {turn.get('index', '?')}",
                        "",
                        f"- **Model:** `{conversation.get('model', 'unknown')}`",
                        f"- **Question:** {turn.get('user_text', '')}",
                        (
                            f"- **Raw response:** "
                            f"[{turn.get('response_file', '')}]"
                            f"(<{case_directory / str(turn.get('response_file', ''))}>)"
                        ),
                        "",
                        str(turn.get("assistant_text", "")),
                        "",
                    ]
                )
        lines.extend(
            [
                "## Required human/agent synthesis",
                "",
                (
                    "This ledger preserves model analysis but does not itself "
                    + "establish the final diagnosis. Reconcile audible findings "
                    + "with metadata and tester claims using the skill's evidence "
                    + "model. Resolve material contradictions with targeted "
                    + "follow-ups, telephony logs, or human listening before "
                    + "making high-consequence conclusions."
                ),
                "",
            ]
        )
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("\n".join(lines), encoding="utf-8")
        except OSError as exc:
            raise ForensicsError(f"Unable to write report: {output_path}") from exc
        LOGGER.info("Rendered evidence ledger at %s", output_path)
        return output_path

    def _build_payload(
        self,
        prepared_case: dict[str, Any],
        model: str,
        max_completion_tokens: int,
        initial_prompt: str,
        audio_bytes: bytes,
        prior_turns: list[Any],
        follow_up_question: str | None,
    ) -> dict[str, Any]:
        audio_data = base64.b64encode(audio_bytes).decode("ascii")
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.case_bundle.system_prompt()},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": initial_prompt},
                    {
                        "type": "input_audio",
                        "input_audio": {"data": audio_data, "format": "wav"},
                    },
                ],
            },
        ]
        for turn in prior_turns:
            if not isinstance(turn, dict):
                raise ForensicsError("Conversation contains a malformed turn")
            user_text = turn.get("user_text")
            assistant_text = turn.get("assistant_text")
            if not isinstance(user_text, str) or not isinstance(assistant_text, str):
                raise ForensicsError("Conversation turn is missing text")
            if turn.get("index") != 1:
                messages.append({"role": "user", "content": user_text})
            messages.append({"role": "assistant", "content": assistant_text})
        if follow_up_question is not None:
            messages.append({"role": "user", "content": follow_up_question})
        return {
            "model": model,
            "modalities": ["text"],
            "messages": messages,
            "max_completion_tokens": max_completion_tokens,
            "store": False,
        }

    def _execute_turn(
        self,
        case_directory: Path,
        prepared_case: dict[str, Any],
        model: str,
        timeout_seconds: float,
        max_retries: int,
        payload: dict[str, Any],
        user_text: str,
        dry_run: bool,
    ) -> Path:
        turns_directory = case_directory / "turns"
        turns_directory.mkdir(exist_ok=True)
        conversation_path = case_directory / CONVERSATION_FILENAME
        conversation = (
            self._read_json_object(conversation_path)
            if conversation_path.exists()
            else {
                "schema_version": SCHEMA_VERSION,
                "case_id": prepared_case["case_id"],
                "model": model,
                "audio_sha256": prepared_case["sources"]["audio"]["sha256"],
                "turns": [],
            }
        )
        turns = conversation.get("turns")
        if not isinstance(turns, list):
            raise ForensicsError("Conversation turns are malformed")
        turn_index = len(turns) + 1
        stem = f"turn-{turn_index:03d}"
        audit_path = turns_directory / f"{stem}-request-audit.json"
        response_path = turns_directory / f"{stem}-raw-response.json"
        assistant_path = turns_directory / f"{stem}-assistant.md"
        sanitized_payload = self._sanitize_payload(payload, prepared_case)
        self._write_json(audit_path, sanitized_payload)
        if dry_run:
            LOGGER.info("Dry run complete; no API call made: %s", audit_path)
            return audit_path
        if response_path.exists() or assistant_path.exists():
            raise ForensicsError(f"Refusing to overwrite turn {turn_index}")
        client = NativeAudioClient(timeout_seconds, max_retries)
        raw_response = client.complete(payload)
        assistant_text = self._extract_assistant_text(raw_response)
        self._write_json(response_path, raw_response)
        try:
            assistant_path.write_text(f"{assistant_text.rstrip()}\n", encoding="utf-8")
        except OSError as exc:
            raise ForensicsError(
                f"Unable to write assistant response: {assistant_path}"
            ) from exc
        usage = raw_response.get("usage")
        turns.append(
            {
                "index": turn_index,
                "user_text": user_text,
                "assistant_text": assistant_text,
                "request_audit_file": str(audit_path.relative_to(case_directory)),
                "response_file": str(response_path.relative_to(case_directory)),
                "assistant_file": str(assistant_path.relative_to(case_directory)),
                "response_id": raw_response.get("id"),
                "usage": usage if isinstance(usage, dict) else None,
            }
        )
        self._write_json(conversation_path, conversation)
        LOGGER.info("Completed native-audio model turn %d", turn_index)
        return assistant_path

    def _sanitize_payload(
        self, payload: dict[str, Any], prepared_case: dict[str, Any]
    ) -> dict[str, Any]:
        sanitized = json.loads(json.dumps(payload))
        messages = sanitized.get("messages", [])
        for message in messages:
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict) or part.get("type") != "input_audio":
                    continue
                part["input_audio"] = {
                    "format": "wav",
                    "redacted": True,
                    "source_sha256": prepared_case["sources"]["audio"]["sha256"],
                    "source_bytes": prepared_case["sources"]["audio"]["bytes"],
                }
        return sanitized

    def _extract_assistant_text(self, raw_response: dict[str, Any]) -> str:
        choices = raw_response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ForensicsError("OpenAI response contains no choices")
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise ForensicsError("OpenAI response choice is malformed")
        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise ForensicsError("OpenAI response contains no assistant message")
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            text_parts = [
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and isinstance(part.get("text"), str)
            ]
            joined_text = "\n".join(part for part in text_parts if part.strip())
            if joined_text:
                return joined_text
        audio = message.get("audio")
        if isinstance(audio, dict):
            transcript = audio.get("transcript")
            if isinstance(transcript, str) and transcript.strip():
                return transcript
        raise ForensicsError("OpenAI response contains no usable assistant text")

    def _load_conversation(self, case_directory: Path) -> dict[str, Any]:
        conversation_path = case_directory / CONVERSATION_FILENAME
        if not conversation_path.exists():
            raise ForensicsError("No completed analysis; run analyze first")
        return self._read_json_object(conversation_path)

    def _read_json_object(self, path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ForensicsError(f"Unable to read JSON file: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ForensicsError(f"Malformed JSON file: {path}: {exc}") from exc
        if not isinstance(value, dict):
            raise ForensicsError(f"JSON root must be an object: {path}")
        return value

    def _write_json(self, path: Path, value: dict[str, Any]) -> None:
        try:
            path.write_text(
                f"{json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)}\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise ForensicsError(f"Unable to write JSON file: {path}") from exc


class CommandLine:
    """Parse command-line arguments and invoke the forensic workflow."""

    def build_parser(self) -> argparse.ArgumentParser:
        """Build the command-line parser.

        :return: Configured parser.
        :rtype: argparse.ArgumentParser
        """

        parser = argparse.ArgumentParser(
            description="Prepare and analyze recorded calls with native audio models"
        )
        parser.add_argument(
            "--debug", action="store_true", help="Enable detailed diagnostic logging"
        )
        subparsers = parser.add_subparsers(dest="command", required=True)

        prepare_parser = subparsers.add_parser(
            "prepare", help="Prepare an immutable evidence bundle"
        )
        prepare_parser.add_argument("manifest", type=Path, help="Case manifest JSON")
        prepare_parser.add_argument(
            "case_directory", type=Path, help="New case directory"
        )

        analyze_parser = subparsers.add_parser(
            "analyze", help="Run the initial native-audio analysis"
        )
        analyze_parser.add_argument(
            "case_directory", type=Path, help="Prepared case directory"
        )
        self._add_model_arguments(analyze_parser, include_optional_model=False)

        follow_up_parser = subparsers.add_parser(
            "follow-up", help="Ask a focused question about a completed analysis"
        )
        follow_up_parser.add_argument(
            "case_directory", type=Path, help="Prepared case directory"
        )
        follow_up_parser.add_argument("question", help="Focused forensic question")
        self._add_model_arguments(follow_up_parser, include_optional_model=True)

        render_parser = subparsers.add_parser(
            "render", help="Render a Markdown evidence ledger"
        )
        render_parser.add_argument(
            "case_directory", type=Path, help="Prepared case directory"
        )
        render_parser.add_argument("output", type=Path, help="New Markdown output path")
        return parser

    def run(self, arguments: argparse.Namespace) -> int:
        """Run the requested command.

        :param arguments: Parsed command-line arguments.
        :type arguments: argparse.Namespace
        :return: Process exit code.
        :rtype: int
        """

        workflow = ForensicsWorkflow()
        if arguments.command in {"analyze", "follow-up"}:
            self._validate_model_arguments(arguments)
        if arguments.command == "prepare":
            result = workflow.case_bundle.prepare(
                arguments.manifest, arguments.case_directory
            )
        elif arguments.command == "analyze":
            result = workflow.analyze(
                arguments.case_directory,
                arguments.model,
                arguments.max_completion_tokens,
                arguments.timeout,
                arguments.max_retries,
                arguments.dry_run,
            )
        elif arguments.command == "follow-up":
            result = workflow.follow_up(
                arguments.case_directory,
                arguments.question,
                arguments.model,
                arguments.max_completion_tokens,
                arguments.timeout,
                arguments.max_retries,
                arguments.dry_run,
            )
        elif arguments.command == "render":
            result = workflow.render(arguments.case_directory, arguments.output)
        else:
            raise ForensicsError(f"Unsupported command: {arguments.command}")
        print(result)
        return 0

    def _validate_model_arguments(self, arguments: argparse.Namespace) -> None:
        """Validate shared model-request arguments.

        :param arguments: Parsed command-line arguments.
        :type arguments: argparse.Namespace
        :return: None.
        :rtype: None
        :raises ForensicsError: If a numeric request setting is invalid.
        """

        if arguments.max_completion_tokens < 1:
            raise ForensicsError("--max-completion-tokens must be positive")
        if arguments.timeout <= 0:
            raise ForensicsError("--timeout must be positive")
        if arguments.max_retries < 0:
            raise ForensicsError("--max-retries must not be negative")

    def _add_model_arguments(
        self, parser: argparse.ArgumentParser, include_optional_model: bool
    ) -> None:
        model_default = None if include_optional_model else DEFAULT_MODEL
        model_help = (
            "Model override; must match the existing conversation"
            if include_optional_model
            else "Native-audio model (default: %(default)s)"
        )
        parser.add_argument("--model", default=model_default, help=model_help)
        parser.add_argument(
            "--max-completion-tokens",
            type=int,
            default=DEFAULT_MAX_COMPLETION_TOKENS,
            help="Maximum response tokens (default: %(default)s)",
        )
        parser.add_argument(
            "--timeout",
            type=float,
            default=DEFAULT_TIMEOUT_SECONDS,
            help="SDK timeout in seconds (default: %(default)s)",
        )
        parser.add_argument(
            "--max-retries",
            type=int,
            default=DEFAULT_MAX_RETRIES,
            help="SDK retry count (default: %(default)s)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Write a redacted request audit without calling the API",
        )


def configure_logging(debug: bool) -> None:
    """Configure diagnostics while suppressing SDK transport detail.

    :param debug: Whether to enable skill-level debug logging.
    :type debug: bool
    :return: None.
    :rtype: None
    """

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def main() -> int:
    """Run the audio-forensics command-line application.

    :return: Process exit code.
    :rtype: int
    """

    command_line = CommandLine()
    parser = command_line.build_parser()
    arguments = parser.parse_args()
    configure_logging(arguments.debug)
    try:
        return command_line.run(arguments)
    except ForensicsError as exc:
        LOGGER.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
