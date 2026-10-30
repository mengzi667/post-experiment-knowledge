# Private evidence and trace archive uploads

Archive-only Sync needs the mandatory request/template/exact-store intake and archival scope/parent; an unrequested report document is unnecessary. Use setup --topic quality --stage sync --sync-kind archive. Select scope and exact parent with archive-destination preview --topic quality --scope full|trace --wiki NODE (or --folder TOKEN), then confirm the reviewed proposal. Independent selections override legacy report archive settings. All commands share the coordinator launcher/store.

Use only after the user explicitly selects `archives.scope` and an exact existing Drive folder. Report destination and archival upload are independent: Feishu-only reports can use no upload, trace or full. Local reports can also have an explicitly selected private Drive archive. No public upload, share change, folder creation or source execution occurs.

Wiki parents are also supported explicitly via `archives: {scope, wiki}` and `--archive-wiki`. Configure their exact tokens separately in private `feishu.allowed_archive_wiki_nodes`. Upload uses `drive +upload --wiki-token`; verification resolves the resulting file's Wiki node and checks its object identity, name and exact parent, then downloads and checks its bytes. Wiki verification uses node metadata, not Drive folder enumeration. Do not pass a Wiki token to `--archive-folder` or silently fall back to Drive root.

## Contents

- `trace`: all record revisions for the selected topic, knowledge/conclusion history, experiment index, evidence IDs and hashes. Raw evidence objects are omitted and the manifest says so. Trace snapshots contain experimental metadata and may contain historical source locations: they are confidential too.
- `full`: the same trace plus every locally archived raw evidence object referenced by every record revision, deduplicated by SHA-256. Independent experiment records are never collapsed. Failed/aborted/partial attempts remain records.
- `none`: no archive export/upload is permitted.

The ZIP contains `manifest.json`, `experiment-index.md`, `records/`, `knowledge/`, and optionally `objects/`. The manifest lists each entry's byte length and SHA-256; records link conclusions to immutable experimental evidence. Only the selected topic is exported. Adapter credentials/configs, destination profiles, sync journals and unrelated files are not included. Large externally referenced weights/data/resources remain references; they are not fetched implicitly. Native report-resource binaries must already have been explicitly archived to be included.

## Preview and upload

1. `archive plan --topic quality` creates a deterministic private ZIP and sealed file inventory. It makes no network call. Default limit: 100 MB of payload and resulting ZIP; `--max-bytes` explicitly changes it, up to 1 GB. Oversized or unreadable/corrupt evidence stops export without partial upload.
2. Privately inspect the concrete inventory and payloads as necessary for authorization. The credential guard blocks known token shapes and unknown credential literals, including those inside test samples. For `.py` sources it statically recognizes direct environment reads and simple dynamically interpolated Bearer headers; explicitly masked values and a narrow set of obvious test fixture markers are allowed. No code is executed. ZIP evidence is inspected recursively with depth/size limits. These checks are not comprehensive secret detection; syntax context is not permission to upload. Do not bypass the guard, silently edit originals or claim the scan proves privacy. Keep originals local and resolve scope/sanitization explicitly if needed. Use a separately authorized sanitized copy rather than changing frozen experiment inputs.
3. Configure the exact folder in private adapter settings, e.g. `{"feishu":{"allowed_archive_folders":["synthetic-folder"]}}`, using existing lark-cli authentication. Do not add broad scopes or change sharing. Raw evidence is uploaded only inside the confirmed scope and location. A selected destination does not by itself authorize an arbitrary payload.

   A valid login is not a capability check. The adapter checks the actual folder-list read operation before a new upload; current lark-cli may require `space:document:retrieve` (or an API-supported legacy equivalent) in addition to file upload/download permissions. A missing scope returns `needs_feishu_authorization` with only the scope names, before upload or a pending-write journal. Never infer directory access from successful upload/download. Previously acknowledged uploads keep their tokens and can be verified after authorization without re-uploading.
4. `archive apply --plan PRIVATE_PLAN --approve PLAN_DIGEST --allow-feishu-upload` uploads a new immutable ZIP snapshot using `--as user`. The CLI uses an explicit folder and relative staging filename. No overwrite or default-root upload is used.
5. Readback confirms token/name membership in that folder, downloads the file to private temporary storage and checks exact size/SHA-256. The returned private receipt contains the file token and platform URL when provided by the folder response. Only verified receipts support a success claim. Link the archive from the report through a separately authorized minimal Sync change when appropriate.

Report sync and archive upload have independent receipts, not an atomic cross-platform transaction. Keep the report concise; do not append the archive bytes/details to its body. A ZIP archive preserves all evidence and its internal experiment index; it is not a set of individually rendered Feishu documents.

## Recovery

`archive verify --plan PRIVATE_PLAN` rechecks uploaded bytes. Repeating apply with an acknowledged token verifies that token without uploading again. Failed readback retains the known token. A pending upload whose result is unknown is never blindly reissued, even if a read temporarily finds nothing.

After independently locating the candidate remote file, use `archive reconcile --plan PRIVATE_PLAN --approve PLAN_DIGEST --file-token FILE_TOKEN`; it must match the exact folder, name, size and SHA-256. If an operator authoritatively established non-upload, `archive resolve-unknown --plan PRIVATE_PLAN --approve PLAN_DIGEST --confirm-not-uploaded` clears the pending state without performing a write. A missing file in a stale listing is not authoritative non-upload.

Changing the destination/scope invalidates old upload plans. Historical verify/reconcile remains possible. This adapter never deletes remote archives as rollback; retaining immutable snapshots is intentional. Do not upload a fresh copy simply to resolve ambiguity. Platform permission errors stop; code does not log in, grant access or automatically add `--yes` after a CLI rejection.

After an explicitly authorized relocation, generate a plan for the newly confirmed location and use `archive adopt --plan PRIVATE_PLAN --approve PLAN_DIGEST --file-token EXISTING_TOKEN` to bind an already-existing file. Adoption performs readback only: its parent, name, size and hash must match the exact plan, and no unresolved/conflicting receipt may be overwritten. It does not upload or move a file. Keep the original receipt plus migration evidence; do not claim its historical folder remains the current parent after a move.
