---
name: analyze-call-audio
description: Investigate recorded telephone or voice-agent QA incidents by combining native audio understanding with call metadata, tester reports, and expected behavior. Use when Codex must determine what was audibly said or played, distinguish ASR, VAD, classifier, state-machine, TTS, routing, downstream telephony, tester-execution, or observability failures, conduct follow-up questioning of an audio-capable OpenAI model, preserve an auditable evidence trail, or produce a call-level forensic findings report from WAV audio and optional JSON metadata.
---

# Analyze Call Audio

Use native audio understanding for forensic analysis. Never substitute a local
speech-to-text model for listening when the disputed fact is acoustic.

## Invocation and authorization

This skill is explicit-invocation-only. Use it only when the developer invokes
`$analyze-call-audio`.

That invocation authorizes the OpenAI API calls needed to complete the requested
call-audio investigation, including the initial native-audio analysis and
focused follow-up turns for the selected evidence. Do not ask for separate API
authorization before individual calls. Do not make a dry run a prerequisite.
The authorization is limited to the evidence and investigation requested in the
invoking task.

## Core rules

1. Keep audible facts, metadata facts, tester claims, and inference separate.
2. Treat the recording as authoritative only for what it contains. It cannot
   prove events after capture stopped.
3. Never infer a completed PSTN/PBX handoff from a bot route decision alone.
4. Do not call a failure resolved when two evidence sources conflict.
5. Preserve the source hashes, rendered prompt, request audit, raw response,
   conversation history, and model name.
6. Set `store` to `false`. Never print or persist the API key.
7. Use `gpt-audio-1.5` through Chat Completions with native audio input and text
   output for bounded WAV files unless the user selects another native-audio
   model.

Read [references/evidence-model.md](references/evidence-model.md) before
classifying failures or synthesizing the final report.

## Workflow

### 1. Create a manifest

Copy [assets/case-manifest.example.json](assets/case-manifest.example.json) and
fill in one QA attempt. Use a separate case for each call attempt. Do not put
conclusions in the manifest.

Required fields are `schema_version`, `case_id`, `audio_path`,
`reported_failure`, and `expected_behavior`. `metadata_path`, `context`, and
`questions` are optional.

### 2. Prepare an immutable evidence bundle

Run:

```bash
PYENV_VERSION=pvb-orchestrator python \
  .agents/skills/analyze-call-audio/scripts/audio_forensics.py \
  prepare MANIFEST CASE_DIR
```

This validates PCM WAV structure, verifies JSON metadata, calculates SHA-256
hashes, records media properties, and writes `CASE_DIR/case.json`. It never
modifies the source audio or metadata.

Inspect `case.json`. Correct the source manifest and prepare a new case directory
if anything is wrong; do not hand-edit the prepared bundle.

### 3. Run native-audio analysis

Use the repository's `pvb-orchestrator` pyenv environment. It contains the
official `openai` SDK declared in `scripts/requirements.txt`. Check readiness
with `PYENV_VERSION=pvb-orchestrator python -c "import openai"`; do not inspect
the API-key environment variable.

Run the native-audio analysis directly:

```bash
PYENV_VERSION=pvb-orchestrator python \
  .agents/skills/analyze-call-audio/scripts/audio_forensics.py \
  analyze CASE_DIR
```

The command sends the original WAV as `input_audio`, supplies the model with the
tester report and metadata as explicitly non-authoritative evidence, and writes
the sanitized request audit plus raw response under `CASE_DIR/turns/`.

Use `--dry-run` only to troubleshoot request construction. It is optional and
must not delay normal analysis.

### 4. Interrogate uncertain findings

Use focused follow-ups instead of rerunning a broad initial prompt:

```bash
PYENV_VERSION=pvb-orchestrator python \
  .agents/skills/analyze-call-audio/scripts/audio_forensics.py \
  follow-up CASE_DIR \
  "At the final voicemail prompt, does the caller audibly say No or now? Explain the acoustic evidence and uncertainty."
```

Good follow-ups ask one falsifiable question. Ask for the exact audible phrase,
speaker, approximate offset, competing interpretation, and confidence. Do not
ask the model to merely endorse the tester or metadata.

For high-consequence ambiguous utterances, use at least two independently
worded turns. The explicit skill invocation authorizes these follow-up API
calls. Agreement between prompts is supporting evidence, not ground truth.

### 5. Render and synthesize

Render the auditable case ledger:

```bash
PYENV_VERSION=pvb-orchestrator python \
  .agents/skills/analyze-call-audio/scripts/audio_forensics.py \
  render CASE_DIR OUTPUT.md
```

Then inspect the raw model responses and metadata yourself. Apply the evidence
model and write the final findings. Include:

- the reported failure;
- the audible sequence and critical utterance;
- metadata sequence and terminal state;
- agreement or contradiction among sources;
- the narrowest verified failure layer;
- confidence and evidence basis;
- precise developer follow-up when unresolved.

Never present model prose as direct observation by Codex. Attribute it as
native-audio model analysis and state how it was corroborated.

## Operational safeguards

- The script refuses changed source hashes, non-PCM WAVs, missing inputs,
  malformed responses, and accidental initial-analysis overwrite.
- API calls use the official Python SDK's automatic `OPENAI_API_KEY` discovery.
  The skill and script must never read, print, log, persist, or accept the key.
- Add the global `--debug` option before the subcommand for diagnostics; secrets
  and base64 audio remain redacted.
- Keep case bundles outside the skill directory. They are task evidence, not
  reusable skill resources.
