---
name: experiment-sync
description: Save or minimally update prepared experiment reports in local Markdown or Feishu, or upload selected raw evidence and trace archives. Use for report publishing, document maintenance and archival synchronization after results exist. Reuse prior evidence; no forced re-recording or new analysis.
---

# Sync

Use the shared launcher/private store. **First follow [mandatory intake](../post-experiment-knowledge/references/intake.md)**: clarify this request, require a user-provided/explicitly selected template and concrete result locations, show the complete summary with native cards and await actual confirmation. Archive-only also requires a template and exact local store. Distinguish report-only, archive-only and both; do not ask for internal skill names. Run setup --stage sync --sync-kind report|archive|both, then pass the confirmed --intake VERSION.

Ask only current missing choices:

- **Report:** selected template, report save method (Markdown/Feishu/both), concrete file/document or authorized parent. Use existing confirmed choices. No archive question/upload when only a report was requested; new report destinations default to no archive upload.
- **Archives only:** mandatory template/local result store plus trace or raw+trace scope and exact Feishu parent. An unrequested report document is unnecessary.
- **Both:** collect the union of missing choices, then confirm the entire request summary. Stored preferences prefill the summary; they do not authorize a new task or upload.

Use native cards for options and free text for paths/URLs. Don't silently select built-in templates, infer a tenant/Drive root or upload evidence because a report is on Feishu. See [template selection](../post-experiment-knowledge/references/templates.md), [stage settings](../post-experiment-knowledge/references/destinations.md) and [archives](../post-experiment-knowledge/references/archives.md) as needed.

For reports, preserve the confirmed template's headings/order, general configuration/metric tables and flexible result formats. Source/version and semantic section mapping are private and reviewed. Prepare with `report-preview --topic TOPIC --sections FILE` from existing Knowledge, or use an already prepared reviewed report without forcing new synthesis. Missing template fields remain explicit. Confirm source/layout mappings instead of ignoring the user's template. Reading source data and analyzing evidence must not be gated on report destinations.

Feishu adapter binds existing documents. An authorized folder is a parent, not a report document: create a new document through available Feishu tools if authorized, then bind the actual document. Creation/moving is not implemented by this runtime. Don't alter formal originals or sharing scope unless explicitly authorized.

Read [sync safeguards](../post-experiment-knowledge/references/sync-and-privacy.md) before writes. Plan concrete changes, inspect the diff, apply within existing user authorization, then read back. Markdown uses managed regions; Feishu replaces only reviewed blocks and preserves tables/resources/references. Version/content conflict stops for re-read/replan; unknown outcomes require reconciliation, not blind replay. Prior verified outputs remain available for independent recovery.

For **both report destinations**, create/apply/verify one plan per adapter; no silent success after only one. Archive uploads use separate `archive plan/apply/verify` and receipts. Explicitly select scope/location with `archive-destination preview --topic TOPIC --scope full|trace --wiki NODE` (or `--folder TOKEN`), then confirm the reviewed selection. A confirmed legacy report archive selection remains usable. Check the exact exported inventory and privacy warnings. Never weaken scanning to pass real suspected secrets. Verify remote membership, downloaded bytes and SHA-256. If the final report needs the archive link, update it minimally and verify again.

Keep all private data/config/token bindings outside the plugin; no telemetry, model API, public fixtures or sharing changes. Feishu uses the user's own optional lark-cli/auth. Missing dependency/permission stays pending, not automatic login or scope escalation.

For multi-stage requests return to the coordinator and run the final `workflow` audit. Deliver verified report links/files and separate archive/index/trace receipts; identify any pending stage. A preview is not a saved report and an uploaded archive is not a saved report.

Archive limits are part of the confirmed intake and sealed export plan; freshness audit reuses the reviewed limit. Close the intake after final delivery. Historic verification remains available, but it never authorizes a new apply.
