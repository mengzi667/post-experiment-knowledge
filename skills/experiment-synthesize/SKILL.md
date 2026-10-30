---
name: experiment-synthesize
description: Compare existing experiment evidence and maintain conclusions, conflicts and decisions after confirming this request, a mandatory template and exact result location. Use for evidence interpretation and changed conclusions; never starts follow-up experiments.
---

# Synthesize

Use the shared launcher/private store. **First follow [mandatory intake](../post-experiment-knowledge/references/intake.md)**: clarify this request's goal, evidence scope, question and requirements; require a supplied/explicitly selected template and exact result location, even for analysis-only. Prefill known values, show the summary using native cards and wait for confirmation before reading experimental evidence. Run setup --stage synthesize and pass the confirmed --intake VERSION. Analysis-only may save private knowledge locally without selecting an unrequested report platform.

After intake, use synthesize --prepare and compare on the explicitly included topic evidence. The current core uses all topic records; don't silently expand a selected subset. Current authorized Agent performs semantic synthesis. With no Agent, leave a prepared bundle pending; do not call a model API.

After intake, analysis of authorized unarchived sources can proceed when that is all the user wants; label provenance limits. Persistent versioned claims need immutable archived refs: use Record only if included in the confirmed request, or review the necessary scope change before importing. Never silently upload or add a reporting workflow.

Read [contracts](../post-experiment-knowledge/references/contracts.md) for claims, decisions and numerical assertions. Assess comparability per question/metric: dataset/split, protocol, layer, denominator, aggregation, controlled variables, hardware, load and cache. Missing/contradictory context must remain conditional or unknown. Single-metric improvement is not an automatic decision.

Review existing conclusions, classify evidence contribution (repeat support, scope extension, new finding, changed choice, conflict, process-only) and write a private claims/decisions draft. Preserve counterevidence, failure limitations, superseded claims, revision reasons and evidence hashes. Use structured assertions for important numbers. Apply `synthesize --draft FILE --expected-version VERSION` (omit expected-version only for first creation). A changed/stale knowledge version requires review; don't overwrite.

Pure drafts omit report_sections; they update knowledge without generating or saving a report. Previously filled report sections stay preserved. If the user also requests a report, continue to [Sync](../experiment-sync/SKILL.md), where the selected template governs the readable report. Do not infer that claims-only analysis replaces their template.

Return the conclusions, applicability/unknowns, private knowledge version and trace references. Complete remaining user-requested stages through the coordinator. No experiment execution, autonomous next round, telemetry, new model service or public disclosure.

Close the intake after final delivery. New requests need new request confirmation; previous template/location preferences alone cannot authorize analysis.
