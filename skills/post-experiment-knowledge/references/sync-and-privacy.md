# Sync and privacy

Local record, comparison, synthesis preparation and Markdown operations do not use network access. Only explicitly selected source/platform adapters use configured endpoints. No background training listeners, model calls, telemetry or upload queue exist.

## Markdown

`sync plan --topic quality --adapter markdown --target REPORT_PATH --content PRIVATE_PREVIEW_PATH --root AUTHORIZED_OUTPUT_ROOT`

The target is outside the distributable package. Existing unmanaged bytes remain intact. One managed comment region is added or replaced; ambiguous markers are rejected. The private plan contains original and desired bytes. `sync apply --plan PRIVATE_PLAN --approve PLAN_DIGEST` applies only that exact plan. Verification checks the full desired content; rollback refuses to overwrite a later edit.

## Feishu

Private config:

```json
{"feishu":{"allowed_documents":["synthetic-doc"]},"mlflow":{"url":"http://127.0.0.1:15000","allowed_origins":["http://127.0.0.1:15000"]}}
```

Authenticate lark-cli separately using the user's existing workflow. The plugin never logs in, changes permissions or shares a document. `sync plan --topic quality --adapter feishu --target synthetic-doc --replacements PRIVATE_REPLACEMENTS_JSON` reads a full native XML snapshot and proposes atomic block replacements.

The replacements object maps real block IDs to single-block DocxXML. Native citations/resources must remain unchanged. Automatic insert/delete/reorder and binary-resource migration are deliberately not supported by this write adapter: generate a historical migration preview and obtain a separately reviewed migration workflow instead. Do not emulate those actions with a bulk overwrite.

Applying needs both the exact plan digest and `--allow-feishu-write`. The Skill must first have concrete user authorization; the digest binds content, it does not prove authorization by itself. Global enablement does not authorize every document.

The adapter binds the first write to the original revision and block identities, then acknowledges each observed replacement while preserving unrelated identities. Timeout/unknown writes stop. If readback is still the pre-write state, the operation stays unknown and is not reissued. Only an observed exact post-state resolves success; independently confirmed non-application can be cleared with `sync resolve-unknown --plan PRIVATE_PLAN --approve PLAN_DIGEST --confirm-not-applied`. Never use that flag merely because a read is stale. Apply and rollback both journal pending operations. Journal and original blocks remain private. Changes by another author cause a conflict. Native formatting normalization can conservatively trigger a mismatch; do not relax the check without reviewing actual XML.

Loaded plans are schema/target-validated again at apply/verify/rollback. Mutable CLI output cannot target immutable objects, record revisions, knowledge or journals. Markdown uses optimistic hashes and a cooperating writer lock, not a mandatory lock against every external editor. Feishu concurrency also depends on lark-cli/server revision enforcement; live fault-injection validation must be reported separately from simulated tests.

New CLI plans require a confirmed topic template and seal its version into the plan. Apply rejects a missing or changed binding before contacting the platform. Verification, rollback and unknown-outcome recovery retain access to historical bindings, including legacy plans, so changing templates does not strand recovery. The Agent must verify the proposed content follows the selected layout; a version binding alone cannot certify arbitrary replacement prose.

New CLI plans also require [a confirmed report destination](destinations.md). They use its adapter, target and authorized root, and seal that binding's version. A location override or stale destination cannot apply. With both destinations selected, the Agent creates and verifies two separate plans, reporting partial success accurately. The stored preference never grants remote write permission or uploads raw evidence; no fallback to an unselected platform occurs.

Separately selected trace/full archival uploads use [ArchiveSync](archives.md), an exact Drive folder allowlist and explicit upload opt-in. They retain local originals and upload a private ZIP with a file/hash manifest. That artifact is confidential, never an open-source plugin release. No archive is included merely because the report target is Feishu. Upload timeout/reconciliation is independent of report block-sync recovery.

## Publication

The source package includes only generic code and synthetic fixtures. Private experiments, derived claims, configs, receipts and research reports are outside that directory. Build from the explicit allowlist; scan the final ZIP. A scan is a defense in depth, not proof that arbitrary prose is public. Never add real material to the allowlist merely because a scan did not flag it.

No automatic public publication or license selection occurs. Choose a license and perform an ownership/data review before any future open-source release.
