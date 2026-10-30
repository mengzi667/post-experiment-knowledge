---
name: experiment-synthesize
description: Compare existing experiment evidence and incrementally maintain research conclusions, conflicts and decisions. Use when asking what results support, whether new evidence changes a conclusion or how runs compare. Analysis alone needs no report template or publishing destination; never starts follow-up experiments.
---

# Synthesize

Use the shared `../post-experiment-knowledge/scripts/expkm.cmd --store PRIVATE_STORE`. For first use show the [coordinator](../post-experiment-knowledge/SKILL.md) introduction/tree before necessary questions. Run `setup --topic TOPIC --stage synthesize`. Obtain only relevant evidence and a research question if context is insufficient. Don't ask for a report template, save platform or destination for pure analysis.

For existing archived records use `synthesize --prepare` and `compare`; both work without report bindings. Current authorized Agent performs semantic synthesis. With no Agent, leave a prepared private bundle pending; do not call a model API.

If sources are not archived, read-only analysis can proceed when that is all the user wants. Label provenance limits. Persistent versioned claims need immutable archived refs: use [Record](../experiment-record/SKILL.md) only for that necessary part, with the user's authorized evidence/store. Don't silently upload or require a full reporting workflow.

Read [contracts](../post-experiment-knowledge/references/contracts.md) for claims, decisions and numerical assertions. Assess comparability per question/metric: dataset/split, protocol, layer, denominator, aggregation, controlled variables, hardware, load and cache. Missing/contradictory context must remain conditional or unknown. Single-metric improvement is not an automatic decision.

Review existing conclusions, classify evidence contribution (repeat support, scope extension, new finding, changed choice, conflict, process-only) and write a private claims/decisions draft. Preserve counterevidence, failure limitations, superseded claims, revision reasons and evidence hashes. Use structured assertions for important numbers. Apply `synthesize --draft FILE --expected-version VERSION` (omit expected-version only for first creation). A changed/stale knowledge version requires review; don't overwrite.

Pure drafts omit report_sections; they update knowledge without generating or saving a report. Previously filled report sections stay preserved. If the user also requests a report, continue to [Sync](../experiment-sync/SKILL.md), where the selected template governs the readable report. Do not infer that claims-only analysis replaces their template.

Return the conclusions, applicability/unknowns, private knowledge version and trace references. Complete remaining user-requested stages through the coordinator. No experiment execution, autonomous next round, telemetry, new model service or public disclosure.
