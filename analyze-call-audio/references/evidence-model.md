# Call-audio forensic evidence model

## Contents

- Evidence hierarchy
- Failure-layer taxonomy
- Resolution standards
- Report requirements

## Evidence hierarchy

Keep four parallel accounts until reconciliation:

1. **Audio:** what the recording audibly contains, including caller speech,
   played bot audio, silence, clipping, and recording termination.
2. **Metadata:** timestamps, ASR events, generated text, state transitions,
   route decisions, terminal status, and identifiers.
3. **Tester report:** what the caller intended, perceived, and recorded.
4. **Inference:** the proposed causal explanation.

Audio outranks ASR for the words audibly spoken. Metadata outranks recollection
for internal events it directly records. Tester observation may outrank bot
metadata for downstream behavior audible or experienced after the bot's own
event stream, but it requires telephony logs when the recording does not cover
that interval.

No single source is globally authoritative. Explicitly record contradictions.

## Failure-layer taxonomy

Choose the narrowest supported layer. Use multiple layers only when evidence
shows multiple independent faults.

| Layer | Verifiable evidence |
| --- | --- |
| No system failure / QA execution variance | Audio shows the tester did not perform the instructed response and the system behaved correctly for the actual input. |
| Recording or media capture | Speech or playback is absent, clipped, corrupt, or inconsistent with event timing in the captured WAV. |
| ASR | Audio clearly contains one phrase while finalized ASR records a materially different phrase. |
| VAD / endpointing / turn detection | Speech is audibly present but not finalized, is split or truncated incorrectly, or silence is treated as speech/a completed turn. |
| Intent or topic classification | The caller's complete request is captured correctly but assigned behavior for the wrong topic or policy class. |
| Readback verification | A correction, rejection, restatement, or ambiguous reply is treated as confirmation. |
| Voicemail-offer verification | A rejection or ambiguous reply is treated as voicemail acceptance. |
| Policy or prime-directive enforcement | An uncertain state reaches a non-fail-safe route even though the ambiguity is represented correctly upstream. |
| Retry / silence / state machine | Required reprompt, retry exhaustion, terminal fallback, or state transition does not occur. |
| LLM response generation | Recorded generated text itself violates the required policy or chooses an unsupported action. |
| TTS or playback | Generated text exists, but the corresponding prompt is missing, partial, or materially different in audible playback. |
| Bot route commit | The announced route and committed route differ, or the committed route violates a resolved decision. |
| Handoff / transport | The bot records a route attempt, but signaling or connection setup fails before reaching the configured endpoint. |
| Downstream PBX / endpoint | The handoff reaches the configured endpoint, but that endpoint answers incorrectly, times out, or forwards elsewhere. |
| Observability / metadata | The audible interaction or downstream logs prove an event that metadata omits or records incorrectly. |
| Indeterminate | Available evidence narrows the problem but cannot distinguish two or more layers. |

Do not label an ASR error solely because text looks implausible. Confirm the
spoken audio. Do not label a downstream routing failure solely because the
tester reports voicemail when the bot metadata says operator.

## Resolution standards

Use one of these dispositions:

- **Verified failure:** Direct evidence identifies a specific failing layer and
  rules out the material alternatives.
- **Verified behavior, unresolved cause:** The bad outcome is established, but
  two or more system layers remain plausible.
- **Partially supported:** Some reported behavior is confirmed, but the claimed
  final outcome or cause is outside the evidence.
- **Contradicted report:** Audio and metadata jointly demonstrate that the
  reported failure did not occur as stated.
- **Invalid QA execution:** Audio shows the required test action was not
  performed, so the attempt cannot measure the intended behavior.
- **No failure:** The actual input and resulting behavior satisfy the stated
  requirement.

For legal- or safety-sensitive routing, uncertainty is not evidence that the
system behaved safely. Record it as unresolved and identify the exact logs or
artifacts needed.

## Report requirements

For every attempt, report:

1. case identifier and source file links;
2. tester claim and expected behavior;
3. critical audible sequence, with approximate offsets when supported;
4. critical metadata events and terminal state;
5. contradictions and evidence boundaries;
6. disposition and narrowest supported failure layer;
7. confidence with reasons;
8. exact developer follow-up when unresolved.

Attribute native-audio model findings as model analysis. Corroborate them with
metadata, repeated targeted prompts, waveform timing, or human review before
using them as the sole basis for a high-consequence conclusion.
