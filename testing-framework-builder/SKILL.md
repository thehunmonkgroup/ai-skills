---
name: testing-framework-builder
description: Build or improve a project's testing framework with authoritative cases, reproducible execution, traceable evaluation, human review, and a project operating skill. Use only when the developer explicitly invokes testing-framework-builder; ordinary test runs and individual unit-test changes belong to the project's existing workflow.
---

# Testing framework builder

Use only when the developer explicitly invokes `$testing-framework-builder`.
Deliver a working framework suited to the project's decisions and workload,
plus the local instructions needed to operate it. When the request is limited
to planning, review, or one component, honor that limit.

This skill guides construction and improvement. The project operating skill
guides day-to-day audits, feedback reconciliation, runs, and investigations.
Make that skill self-contained for operation; it must not require loading this
builder or finding the project from which these practices originated.

## Inspect and size the work

Inspect existing tests, ad-hoc runners, fixtures, review artifacts, application
interfaces, and repository conventions before proposing replacements. Identify
competing sources of truth and preserve useful historical results. Reuse working
code where its assumptions fit; do not introduce a shared library merely because
two implementations look similar.

Establish the decision the framework must support, the system under test, the
authority for expected behavior, and the human review workflow. Infer routine
choices from the project; ask only where missing information changes scope,
cost, expected behavior, or interpretation materially.

Scale the design to the task. Deterministic software may need only fixtures,
assertions, and ordinary test reports. Semantic evaluation may also need an
evidence-backed corpus, judgment records, and review exchange. Remote or lengthy
experiments may need durable checkpoints, scheduling, repetitions, and budgets.
Do not impose every capability or a fixed command layout on every project.

## Define the contract before the tools

Read [references/contracts.md](references/contracts.md) when designing records,
review exchange, execution, evaluation, or reporting. Choose applicable parts
and document the concrete project contract alongside the tools or operating
skill. Reuse existing schemas if they preserve the necessary invariants.

Keep these distinctions explicit:

- One authoritative case set; spreadsheets and reports are derived review views.
- Expected behavior versus an illustrative answer or output.
- Evidence-backed facts versus assumptions, undocumented facts, and unresolved cases.
- Mechanical checks versus AI judgments, assistant review, and human approval.
- Correcting expectations versus changing the system under test.
- Rescoring preserved outputs versus recollecting outputs for changed inputs.

Define the authority appropriate to the domain: specifications, labeled data,
source documents, approved policy, or another named source. Do not transplant a
particular company's scope rules or assume every project has a knowledge base.
Reviewer comments are proposals; they do not automatically establish new facts.

## Implement composable tools

Write new deterministic scripts in Python unless the developer specifies
otherwise. Give commands explicit inputs, structured outputs, useful exit
statuses, and diagnostics separate from machine-readable results. Commands may
share a CLI without coupling every operation into one opaque workflow.

Reuse scripts that already exist in the application in place, documenting their
usage in the project operating skill rather than copying them. Put new
testing-specific scripts in that operating skill's `scripts/` directory and
reference them from its instructions. Document working directory, arguments,
inputs, and outputs sufficiently to compose the commands. Browser UI code still
uses JavaScript as needed; the Python default applies to deterministic tooling.

Reuse existing developer environments and applicable coding skills. Do not copy
their lint, formatting, or type-check instructions into framework documentation.
Keep developer-only dependencies and convenience commands out of ordinary
production installation where the project's packaging supports that separation.

Connect execution to the real application boundary through an adapter or small
testability seam. Verify request/input construction and relevant configuration
against production. Prefer minor injection points over major application
refactors. Keep project paths, model names, categories, and policy in project
configuration or the adapter, not generic execution or report code.

Preserve original cases, outputs, attempts, and judgments through migrations.
Use new revisions or derived records for corrections. Test failure handling and
data integrity, not only the happy path. Framework construction does not itself
authorize paid model calls, expanded experiments, prompt changes, or deployment;
use existing authorization and local fixtures for anything outside its scope.

## Add review and operating guidance

When human review is needed, use a simple static portal focused on the actual
review goal. Assume business-domain knowledge, not framework expertise. Show only
the data and controls needed to make the requested judgment, with brief embedded
instructions where necessary. Add filters, comparisons, or summaries only when
they help complete that task. Collect dispositions, proposed corrections, and
notes directly beside the material being reviewed.

Place reviewer identity and review-wide file actions in one compact header that
stays visible while scrolling on every page. Keep Download feedback directly
accessible; group secondary actions such as Resume from feedback file and, where
supported, Keep as separate draft in a Files menu. Show concise save status nearby.
Use [assets/review-header.html](assets/review-header.html) as an adaptable starting
point; connect its controls to the project's feedback and persistence functions.
The review portal UX contract covers navigation, layout, and additional downloads.

Autosave browser-local drafts where supported, then let reviewers download
completed feedback in the project's chosen format, such as Markdown or XLSX.
Support export at any point and import to resume; browser storage is a convenience,
not the authoritative record or the only recovery path. Keep review exchange tied
to exact case and artifact revisions so imports can reject stale edits. Follow
the browser review contract in [references/contracts.md](references/contracts.md)
for storage selection, truthful save status, static delivery, and recovery.

Use [assets/operating-skill.md](assets/operating-skill.md) as a starting point
when creating or revising the project operating skill. Fill its instructions
with verified project paths and commands; remove unused sections and all
template markers. Store detailed command/schema contracts once and link them.
Preserve existing invocation policy; new operating skills should be explicitly
invoked unless the developer specifies otherwise. Configure
`policy.allow_implicit_invocation: false` in `agents/openai.yaml` for explicit-only
skills, as well as stating the boundary in their instructions.

Keep reusable construction guidance here and project execution guidance there.
Do not require a general runtime package or copy this entire builder into each
project. Developer documentation needs only installation, skill invocation,
and the command-help entry point unless the project requires more.

## Verify and finish

Use [references/acceptance.md](references/acceptance.md) to verify the applicable
end-to-end workflow, including feedback and recovery paths. Validate skill
structure and references using the available skill-creation tooling. A schema
validator alone cannot establish that the workflow makes sound decisions.

Retire legacy runners only after checking callers and demonstrating replacement
coverage. Preserve historical evidence. Report what works, how it was verified,
where the operating skill lives, and unresolved limitations. Distinguish local
simulation from authorized live validation; do not claim unrun integration
checks succeeded.
