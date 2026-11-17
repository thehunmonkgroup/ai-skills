"""Test deterministic preparation and auditing for call-audio forensics."""

from __future__ import annotations

import json
import sys
import wave
from pathlib import Path
from typing import Any

import pytest

SCRIPT_DIRECTORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIRECTORY))

from audio_forensics import (  # noqa: E402
    CaseBundle,
    ForensicsError,
    ForensicsWorkflow,
    NativeAudioClient,
)


class DiagnosticError(RuntimeError):
    """Provide structured SDK-like fields for diagnostic tests."""

    def __init__(self, message: str, code: str, param: str) -> None:
        """Initialize the test error.

        :param message: Error message.
        :type message: str
        :param code: API error code.
        :type code: str
        :param param: Invalid request parameter.
        :type param: str
        """

        super().__init__(message)
        self.message = message
        self.code = code
        self.param = param


class TestForensicsWorkflow:
    """Exercise the workflow without making external API requests."""

    def test_prepare_and_dry_run_redacts_audio(self, tmp_path: Path) -> None:
        """Verify preparation and a secret-free, audio-redacted dry run.

        :param tmp_path: Pytest temporary directory.
        :type tmp_path: pathlib.Path
        :return: None.
        :rtype: None
        """

        manifest_path, case_directory = self._create_case_sources(tmp_path)
        workflow = ForensicsWorkflow()
        workflow.case_bundle.prepare(manifest_path, case_directory)
        audit_path = workflow.analyze(
            case_directory,
            "gpt-audio-1.5",
            1024,
            30.0,
            0,
            True,
        )
        audit = self._read_json(audit_path)
        audio_part = audit["messages"][1]["content"][1]
        assert audio_part["input_audio"]["redacted"] is True
        assert "data" not in audio_part["input_audio"]
        assert audit["modalities"] == ["text"]
        assert "audio" not in audit
        assert audit["store"] is False
        assert "metadata" not in audit
        assert not (case_directory / "conversation.json").exists()

    def test_changed_audio_is_rejected(self, tmp_path: Path) -> None:
        """Verify that prepared source hashes are enforced.

        :param tmp_path: Pytest temporary directory.
        :type tmp_path: pathlib.Path
        :return: None.
        :rtype: None
        """

        manifest_path, case_directory = self._create_case_sources(tmp_path)
        case_bundle = CaseBundle()
        case_bundle.prepare(manifest_path, case_directory)
        manifest = self._read_json(manifest_path)
        audio_path = Path(manifest["audio_path"])
        audio_path.write_bytes(audio_path.read_bytes() + b"changed")
        with pytest.raises(ForensicsError, match="Source changed"):
            case_bundle.load(case_directory)

    def test_follow_up_dry_run_preserves_conversation_order(
        self, tmp_path: Path
    ) -> None:
        """Verify follow-up turns include the original audio and prior answer.

        :param tmp_path: Pytest temporary directory.
        :type tmp_path: pathlib.Path
        :return: None.
        :rtype: None
        """

        manifest_path, case_directory = self._create_case_sources(tmp_path)
        workflow = ForensicsWorkflow()
        case_path = workflow.case_bundle.prepare(manifest_path, case_directory)
        prepared_case = self._read_json(case_path)
        conversation = {
            "schema_version": 1,
            "case_id": prepared_case["case_id"],
            "model": "gpt-audio-1.5",
            "audio_sha256": prepared_case["sources"]["audio"]["sha256"],
            "turns": [
                {
                    "index": 1,
                    "user_text": "Initial forensic analysis",
                    "assistant_text": "Initial answer",
                    "response_file": "turns/turn-001-raw-response.json",
                }
            ],
        }
        (case_directory / "conversation.json").write_text(
            f"{json.dumps(conversation)}\n", encoding="utf-8"
        )
        audit_path = workflow.follow_up(
            case_directory,
            "Did the caller say no?",
            None,
            1024,
            30.0,
            0,
            True,
        )
        audit = self._read_json(audit_path)
        assert [message["role"] for message in audit["messages"]] == [
            "system",
            "user",
            "assistant",
            "user",
        ]
        assert audit["messages"][-1]["content"] == "Did the caller say no?"

    def test_render_requires_new_output(self, tmp_path: Path) -> None:
        """Verify the renderer creates a ledger and refuses overwrite.

        :param tmp_path: Pytest temporary directory.
        :type tmp_path: pathlib.Path
        :return: None.
        :rtype: None
        """

        manifest_path, case_directory = self._create_case_sources(tmp_path)
        workflow = ForensicsWorkflow()
        workflow.case_bundle.prepare(manifest_path, case_directory)
        output_path = tmp_path / "ledger.md"
        workflow.render(case_directory, output_path)
        ledger = output_path.read_text(encoding="utf-8")
        assert "Call-audio evidence ledger" in ledger
        assert "No completed model analysis is present" in ledger
        with pytest.raises(ForensicsError, match="Refusing to overwrite"):
            workflow.render(case_directory, output_path)

    def test_extracts_text_and_audio_transcript_fallback(self) -> None:
        """Verify supported native-audio response shapes.

        :return: None.
        :rtype: None
        """

        workflow = ForensicsWorkflow()
        text_response = {"choices": [{"message": {"content": "Finding"}}]}
        audio_response = {
            "choices": [
                {"message": {"content": None, "audio": {"transcript": "Spoken"}}}
            ]
        }
        assert workflow._extract_assistant_text(text_response) == "Finding"
        assert workflow._extract_assistant_text(audio_response) == "Spoken"

    def test_api_error_diagnostics_are_redacted(self) -> None:
        """Verify safe API diagnostics retain useful structured fields.

        :return: None.
        :rtype: None
        """

        error = DiagnosticError(
            "request failed for sk-secret " + ("A" * 200),
            "invalid_value",
            "modalities",
        )
        client = NativeAudioClient(30.0, 0)
        diagnostic = client._format_api_error(error)
        assert "code=invalid_value" in diagnostic
        assert "param=modalities" in diagnostic
        assert "sk-secret" not in diagnostic
        assert "A" * 128 not in diagnostic

    def _create_case_sources(self, tmp_path: Path) -> tuple[Path, Path]:
        audio_path = tmp_path / "call.wav"
        with wave.open(str(audio_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16_000)
            wav_file.writeframes(b"\x00\x00" * 16_000)
        metadata_path = tmp_path / "call.json"
        metadata_path.write_text(
            json.dumps({"call_uuid": "test", "result": {"route": "operator"}}),
            encoding="utf-8",
        )
        manifest_path = tmp_path / "manifest.json"
        manifest = {
            "schema_version": 1,
            "case_id": "tester-001",
            "audio_path": str(audio_path),
            "metadata_path": str(metadata_path),
            "reported_failure": "Tester reported silence.",
            "expected_behavior": "Route uncertainty to an operator.",
            "context": {"tester": "Example"},
            "questions": ["What happened?"],
        }
        manifest_path.write_text(
            f"{json.dumps(manifest, indent=2)}\n", encoding="utf-8"
        )
        return manifest_path, tmp_path / "case"

    def _read_json(self, path: Path) -> dict[str, Any]:
        value = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(value, dict)
        return value
