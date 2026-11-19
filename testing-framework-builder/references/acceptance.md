# End-to-end acceptance

Choose checks for the capabilities implemented. Use a small local fixture set
with known outcomes and a fake system/provider where appropriate. Keep test
artifacts separate from authoritative cases and historical evidence. Identify
any authorized live validation separately from local simulation.

These are outcome checks, not a requirement to automate or test a matrix of
browsers. Verify data transformations and storage/error handling with focused
checks appropriate to the implementation. Browser testing and direct file://
delivery checks are only required when requested by the developer.

| Capability | Observable acceptance evidence |
| --- | --- |
| Case authority | Stable IDs survive recategorization or wording edits; revisions change; duplicate IDs and broken evidence references fail validation. |
| Uncertainty | Unsupported expectations remain unresolved; automated/assistant review never appears as human approval. |
| Review exchange | A valid Markdown/XLSX export imports with identities intact; stale, unknown, duplicate, and conflicting edits are rejected or explicitly reconciled. Accepted feedback creates a traceable revision. |
| In-page review | Enter dispositions, corrections, and notes beside cases; navigation/filtering retains edits. Untouched cases remain distinct from completed reviews, and source data stays unchanged. |
| Draft persistence | Storage writes/reads preserve draft state, and save status reflects completed writes. |
| Storage failure | Simulate unavailable storage and failed writes; drafts stay editable and exportable in memory, with truthful status. Cleared storage can be recovered from a draft export. |
| Draft isolation and conflicts | Different projects/revisions/sessions cannot silently share drafts. Stale imports and simultaneous tab edits are detected without overwriting either version. |
| Draft portability | Export includes the latest edits even before autosave completes; import into empty draft state preserves all fields and identities. Malformed/incompatible imports leave existing work intact. Downloads do not erase drafts. |
| Production fidelity | Representative application inputs/configuration match the adapter; relevant overrides are captured. No live provider is required to verify construction. |
| Frozen execution | Subsequent source/config changes do not silently mutate an existing run. Selection and scheduling can be reconstructed. Secrets are absent. |
| Recovery | Interrupt after some completed and partial work; resume preserves successes and partial history. Retry adds an attempt; competing collectors cannot own the same run. |
| Evaluation | Known format/category/content outcomes remain distinguishable. A corrected criterion produces a new evaluation of old output without erasing the original or making a new provider call. |
| Metrics | Hand-check a fixture containing success, failure, timeout, missing usage, and ungraded output. Denominators, timing origins, retry selection, and incomplete results are accurate. |
| Review portal | Each field, instruction, and control serves the review goal for a domain-knowledgeable user. Assets are bundled; feedback export uses the same contract on localhost and static hosting. Exported feedback imports against the intended revision; untrusted text is rendered as data. |
| Website packaging | Every build/rebuild produces a `.zip`; extracting it reproduces the complete current static website, including assets/data, with no stale or missing files. Handoff identifies the archive path. |
| Persistent review header | One compact header appears on the index and each review page and stays visible while scrolling. Reviewer identity, active session, and edits survive navigation. Download and resume work through the header; separate-draft actions appear only when supported. Keyboard access and menu focus work; mobile widths and enlarged text cause no horizontal overflow or obscured anchor targets, focused fields, or other pinned controls. Save status remains truthful. |
| Script ownership | New deterministic scripts use Python unless otherwise specified. Existing application scripts are referenced in place; new testing-specific scripts live in the operating skill's scripts directory with documented usage. |
| Operating skill | All paths/commands exist; no template markers remain; invocation metadata matches instructions; ordinary operation needs no builder context. |
| Migration | Existing callers have a supported replacement; historical artifacts remain interpretable; legacy removal follows demonstrated coverage. |

Also exercise scope decisions against realistic requests:

- A small deterministic library should not acquire model judging, checkpointed
  collection, or spreadsheets without a demonstrated need.
- An AI extraction benchmark should distinguish required fields from sample
  wording, preserve source evidence, and keep uncertain judgments visible.
- A feedback-only request should not start collection; a changed reference
  should permit rescoring; a changed input should require recollection before
  claiming new behavioral results.
- A request to build tools without remote-call authorization should still reach
  a working local demonstration and clearly identify any untested integration.

Check skill metadata and linked resources with available validation tooling.
Describe which behavioral checks were actually performed; structural validation
and a written checklist do not prove future applications of the skill succeed.
