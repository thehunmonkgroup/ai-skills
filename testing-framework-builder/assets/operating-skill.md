---
name: {{project-testing-skill}}
description: {{Project-specific testing operations and explicit invocation boundary.}}
---

# {{Project}} testing

Use only when the developer explicitly invokes `${{project-testing-skill}}`.

Work from {{working directory}}. Use {{verified help command}} to discover
operations. Read {{relative link to maintained command/schema reference}} for
the contracts relevant to the requested operation.

## Deterministic tools

{{Document usage of existing application scripts in place. Reference new
testing-specific Python scripts under this skill's scripts/ directory, unless
the developer specified another language. Provide the working directory,
arguments, inputs, and outputs, or link to their single maintained reference.
Do not duplicate application implementations or coding-skill instructions.}}

## Authority and boundaries

{{Name the authoritative case set, sources for expected behavior, categorization
policy if relevant, and project-specific unresolved/approval states. Explain
what constitutes evidence and which sources cannot establish project facts.}}

{{State experiment authorization boundaries and any protected prompts or
configuration. Audits and report generation do not authorize remote collection.
Use the developer's existing authorization; do not demand repeated approval.}}

## Choose the requested operation

{{Retain only implemented operations. For each, give the actual entry point or
reference and the decision guidance the AI needs beyond CLI help.}}

- Audit: validate records, inspect source evidence, identify ambiguity and gaps,
  propose or apply supported changes within scope, and report unresolved cases.
- Feedback: validate the export's base identities, inspect proposals, resolve
  conflicts explicitly, and record accept/reject/defer decisions before revision.
- Compare: establish cases/configurations/repetitions/limits, freeze inputs,
  collect, evaluate, review, and report within the requested scope.
- Investigate: inspect full inputs/outputs, criteria, sources, and execution
  provenance before recommending changes.

## Review and evaluation

{{State actual deterministic checks, semantic grading method, evaluator
provenance, review sampling, override/revision mechanism, and uncertainty rules.
Keep examples separate from required behavior. AI review is not human approval.}}

{{Explain project-specific diagnosis boundaries: case, reference, authoritative
source, adapter, application, evaluator, prompt, or configuration. Separate
rescoring preserved outputs from recollecting changed inputs.}}

## Execution and recovery

{{For long/remote runs, provide verified status/pause/resume commands, checkpoint
identities, ownership checks, retry policy, and timeout semantics. Omit this
section for frameworks without such execution. Never duplicate an active run
because a tool stopped waiting for it.}}

## Report and handoff

{{Give actual report/export commands and locations, feedback format, metric
definitions or their reference, and comparison limitations. Show incomplete or
ungraded results. Preserve previous evaluations when applying corrections.}}

{{For interactive review reports, state the review goal and explain only the
controls and context needed by a domain-knowledgeable reviewer. Document the build
command that produces a complete website `.zip` on every build/rebuild and its
output path. Document static hosting and localhost usage, autosave status,
export/import recovery, and handling
of stale or conflicting drafts. Name the completed-feedback and optional lossless
draft formats. Browser drafts remain proposals; restoring a draft does not apply
its changes to the authoritative case set. Omit for workflows without reports.}}

Finish with artifact locations and identities, observed results, unresolved
issues, and the next useful developer decision. Do not silently expand runs or
change production behavior.
