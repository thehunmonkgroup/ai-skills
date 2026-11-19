# Framework contracts

Use these as design constraints, not a mandatory schema or list of commands.
Choose the smallest representation that preserves the applicable guarantees.
Keep domain rules and actual command syntax in the project.

## Cases and authority

Use one authoritative, versioned case set. A small deterministic suite may use
ordinary fixtures; an audited evaluation corpus may use JSON records in Git.
Generated workbooks must not become a second independently edited authority.

For reviewed corpora, preserve:

| Record | Meaning |
| --- | --- |
| Identity and revision | Stable case ID, case revision, corpus version and content identity |
| Input | Question, payload, fixture, or scenario supplied to the system |
| Expected behavior | Category or outcome, required properties, acceptable variation, prohibited claims or outputs |
| Example output | Illustrative answer, kept separate from the grading requirements |
| Evidence | Source identity, revision/hash, locator, and supporting passage where applicable |
| Organization | Topics or tags useful for selection and coverage |
| Review | State, actor type and identity, rationale, unresolved issues, and provenance |

Retain IDs through wording changes and recategorization; increment revisions.
Record replacements or merges instead of silently reassigning identities.
Validate uniqueness, required fields, allowed states, source references, and
evidence matches. Mechanical validation cannot prove that a passage supports a
claim. Treat duplicate and stale-evidence detection as audit leads.

For knowledge-grounded tasks, absence from a feature list does not establish
that a feature is unavailable. An explicit boundary may establish a negative.
Separate factual authority from the policy defining what the system should
answer. Unsupported expectations remain unresolved until authority is supplied
or the expectation is corrected. AI review cannot confer human approval.

## Feedback and revision

Export completed feedback in the project's chosen format, such as Markdown or
XLSX, with stable IDs, corpus version/content hash, case revision, and relevant
run/evaluation IDs. Preserve protected identity fields
separately from editable suggestions. Freeform comments require interpretation;
they are not executable instructions or automatically accepted patches.

Validate imports before applying changes: unknown IDs, wrong versions, stale
base records, duplicate entries, conflicting edits, and malformed fields must
be visible. Reject or explicitly reconcile conflicts; never silently use the
last row. Keep an import/proposal record and explicit accept, reject, or defer
decisions with actor and rationale. Apply accepted edits to a new revision,
validate it, and preserve the prior version.

Review unsupported claims, ambiguous inputs, incorrect categories, excessive
answer requirements, duplicates, coverage gaps, and changed source evidence.
Changing expected behavior and changing application behavior must be separately
identifiable even when both are authorized in one task.

### Browser review and draft recovery

Prefer collecting feedback inside the static report: dispositions, proposed
corrections, and freeform notes beside the evidence and outputs, as needed for
the review goal. Distinguish untouched cases, draft comments, and explicitly
completed reviews; viewing a case is not approval.
Keep source data immutable and store proposed changes separately. Browser edits,
draft imports, and downloads do not themselves revise the authoritative corpus.

Keep the workflow entirely client-side, with bundled JavaScript and no required
backend, cloud synchronization, CDN, or network call. Choose a storage adapter
appropriate to the data: prefer IndexedDB, optionally through Dexie.js, for
structured drafts; permit localStorage for small serialized drafts. SQL is not
required. Only introduce SQLite/WASM when SQL serves an actual need and its
loading/persistence requirements fit the delivery mode.

Use ordinary static hosting for reviewers and localhost for developer use.
The same completed-feedback download works in both environments; no special
localhost extraction service is needed. Keep drafts portable through export/import
because browser storage belongs to the current origin and browser profile.
Direct file:// delivery and browser compatibility testing are not baseline
requirements; add them only when requested. Static hosting serves files only;
feedback collection and storage remain entirely in the browser.

Probe storage with a real write/read and handle subsequent write failures.
Autosave edits promptly, show saving/saved/failed state, and report "Saved in
this browser" only after successful storage completion. If persistence fails,
retain the current draft in memory, keep editing and export available, and say
that changes are only held in this page until exported. Never show success for
a failed save or discard the draft while switching storage modes. Browser data
may be cleared or evicted; private browsing may discard it on exit. A persistent
storage request, where available, does not replace export/import recovery.

Namespace drafts by project, corpus content identity, applicable run/evaluation
IDs, and review session. Include stable case IDs/revisions, draft schema version,
reviewer identity as supplied, and edit revision metadata. Reopen only compatible
drafts automatically. Detect stale imports and competing edits, including another
tab editing the same draft; do not silently overwrite either version. Migration
or reconciliation must preserve the original data.

Provide export at any point, not only after all cases are reviewed. Export the
latest editor state, including pending autosaves, through the same feedback
contract used by the importer. Do not clear drafts after initiating a download;
starting a download does not prove the user saved the file. Allow importing an
export to resume elsewhere. If the chosen submission format cannot preserve all
editor state, offer a lossless draft artifact such as JSON as well. Validate
schema, identities, base revisions, and conflicts before applying an import to
the editor. Distinguish restoring a browser draft from accepting proposals into
the authoritative corpus; the latter follows the review/revision process above.

## Execution and reproducibility

Choose operations such as validate, review export/import, prepare, collect,
status, pause/resume, evaluate, and report according to actual needs. Expose
intermediate artifacts so operations can be composed or repeated independently.

For experiments, freeze selected case revisions and applicable source documents,
prompts/templates, effective settings including overrides, application/adapter
revision, environment versions, scheduling seed, repetitions, and limits.
Record configuration without copying credentials or secrets. A frozen local
configuration does not guarantee an external provider stays unchanged; record
provider/model identifiers and collection time when available.

Allow useful selection by ID, category, topic, prior failures, or seeded sample.
Record the exact selected IDs. Interleave configurations where time-dependent
provider behavior could bias comparisons. Request counts, retry limits,
concurrency, and time/cost limits belong in the experiment configuration.

For long or remote collection, persist each attempt with a unique identity,
timestamps, raw output, stream events if relevant, status, and errors. Write
checkpoints atomically. Preserve partial and failed attempts; retries append
new attempts and declare which attempt feeds each metric. Resume must not
overwrite successes or accidentally launch a second active collector. Specify
ownership/locking and how an interrupted or stale owner is safely recovered.

Define graceful versus immediate pause behavior if supported. Save run path,
identity, progress, process state, and next command. A tool observation timeout
is not proof the collector stopped. Bound waits and provider calls. Test these
paths locally without requiring paid calls.

## Evaluation and interpretation

Use deterministic checks for properties they can establish: schema, category
syntax, required markers, exact outputs where appropriate, or executable
assertions. Record semantic judgments separately, including case/output
identity, criteria revision, evaluator identity/type, rationale, uncertainty,
and evidence. For automated judges retain model/settings and prompt identity;
blinding candidates is useful when comparing models or implementations.

Audit failures, uncertain judgments, changed grades, and a seeded sample of
passes against full outputs and authority. Preserve initial judgments; corrections
create a new evaluation linked to its parent. Changed references can rescore
preserved outputs. Changed system inputs require recollection for valid claims
about the changed inputs. Exposed cases become regression cases; reserve new
holdouts before optimizing against them.

Diagnose in order of evidence, not a fixed blame hierarchy: ambiguous input,
unsupported criterion, missing/conflicting source, adapter drift, evaluator
error, application defect, and model/configuration limitations are distinct.
Do not alter optimized prompts or business policy merely to raise scores.

## Metrics and presentation

Define each metric, population, denominator, and missing-data handling. Show
collection and grading completeness, failures, exclusions, and retry policy.
Do not count ungraded cases as correct or silently exclude errors. Separate
content correctness, category correctness, format compliance, and any combined
success measure when those distinctions matter.

Collect timing, resource usage, or cost only when relevant to the decision.
Define measurement boundaries and units; leave unavailable measurements unknown
and label estimates with their assumptions. Choose milestones and summaries
appropriate to the system under test.

Compare alternatives on matching cases and report the size of the difference
and sample size. If estimating uncertainty, account for repeated measurements
of the same case instead of treating them as independent cases. Limit conclusions
to the evidence and show relevant tradeoffs; do not invent a combined score.

### Review portal UX

Design for an end user with ordinary knowledge of the business domain. Make the
review goal and next action clear. Put the item, necessary context, and feedback
controls together; use familiar domain language and brief instructions only
where the action would otherwise be unclear. Preserve edits during navigation.
Use labeled controls, keyboard access, and readable layouts.

Keep reviewer identity and review-wide file actions in a compact header that
remains visible on the index and each review page while scrolling. Render these
controls once per page, consistently across pages; keep case-specific judgments
beside their evidence. Keep Download feedback directly accessible and put resume
and optional separate-draft actions in a Files menu. Preserve the active reviewer,
session, and edits during navigation, and reflect the actual persistence state
in a concise status message. Offer additional downloads only when they serve the
review task.

Prefer a top-level sticky header when it provides this behavior. Account for its
rendered height in anchor scrolling, focused content, and other pinned controls;
avoid hard-coded offsets that fail when text wraps or the viewport narrows. Keep
the header low profile, without horizontal overflow or obscured content at mobile
widths and increased text size. File actions need accessible labels, keyboard
operation, and predictable focus when their menu closes. The bundled
[header example](../assets/review-header.html) demonstrates presentation and
callback integration; the browser review contract governs persistence and exchange.

Include just enough information to make the requested judgment. Keep technical
IDs, hashes, and provenance in the artifact; expose them in the UI only if useful
to the reviewer. Add search, filters, progress summaries, side-by-side comparisons,
or extra export choices only when the review task benefits. Avoid dashboards,
configuration panels, and explanatory text without a concrete review purpose.
Make saving state and the completed-feedback download easy to find. Feedback
proposals and approved changes must remain distinguishable.

Generate portable static HTML with bundled assets/data and no application backend
or external asset dependency. Every build or rebuild must also produce a `.zip`
of the complete current website, including all assets/data; report its path at
handoff. Make packaging part of the build command so the archive stays current.
Escape untrusted outputs and feedback; render
them as data, not executable markup. Protect spreadsheet exports against formula
execution from untrusted text. Feedback downloads must carry the identities used by
the importer. Distinguish automated judgments, assistant review, and human review.
