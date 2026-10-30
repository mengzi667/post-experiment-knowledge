# Report save method and location

Record needs only a confirmed private local store; pure analysis needs evidence, not report settings. At report Sync run setup --topic quality --stage sync --sync-kind report. For archives only use archive; for both outputs use both. Ask missing relevant choices after the first-use introduction and fenced tree.

Report modes: local Markdown (markdown), an existing Feishu document (feishu), or both. Use destination preview --topic quality --mode markdown --target ABSOLUTE_REPORT_FILENAME --root AUTHORIZED_DIRECTORY; Feishu uses --mode feishu --document DOCUMENT_TOKEN; both supplies both locations. Review the exact proposal then destination confirm --topic quality --proposal PRIVATE_PROPOSAL --approve VERSION. A changed binding also needs --expected-version CURRENT_VERSION. Existing explicit conversation authorization can cover the exact selection; a self-supplied digest cannot replace it.

New report selections default to no archive upload. Ask no unrelated upload question for report-only requests. For requested archives use archive-destination preview --topic quality --scope trace|full --folder FOLDER_TOKEN (or --wiki NODE_TOKEN), followed by archive-destination confirm. Legacy combined --archive-scope/--archive-folder/--archive-wiki remain supported; independent archive selections take priority. Local Record uses record-location preview/confirm under its explicitly selected --store.

Selections are private immutable versioned JSON with topic/definition/version; stage selections also have kind. Changes use compare-and-swap. Folder and Wiki are distinct namespaces. Confirmation never creates a document, grants scopes or enables writes. Old report bindings without upload scope may still save reports; only requested uploads need that scope.

Private preferences can supply an explicitly confirmed HTTPS personal-space Wiki parent. Reuse the exact node, never Drive root. Preferences do not select a template, upload scope or grant writes. A malformed optional preference produces a warning instead of blocking local work.


## Route and verify

Synthesize prepares evidence independently. At report Sync, report-preview --topic quality --sections PRIVATE_SECTION_MAPPING fills the confirmed template from existing knowledge; an already prepared report can be synced directly. `sync plan --topic quality --content PRIVATE_PREVIEW` uses the selected Markdown target/root if Markdown alone was selected. For Feishu alone, the adapter and target come from the binding; supply `--replacements PRIVATE_BLOCK_REPLACEMENTS` after reviewing native document blocks.

With both selected, explicitly plan Markdown and Feishu separately via `--adapter`. Both use their confirmed targets. Apply and verify each reviewed plan under the existing authorization. Neither requires the user to repeat the platform choice. Report partial completion accurately and retain separate receipts; there is no cross-platform transaction.

Explicit CLI target/root overrides must equal the confirmed location. Changing the platform or filename requires a new proposal and confirmation. Plans seal both template and destination versions. A changed/missing selection blocks a new apply before platform access. Legacy plans without destination bindings can still be verified or recovered; regenerate them before a new apply. Historical versions remain available for rollback and unknown-write reconciliation.

The Feishu adapter edits supported blocks in an existing document; it does not create reports/folders or relocate documents. Resolve authorized document links to their real document tokens using available Feishu tools before binding. A folder request needs authorized creation through those tools and a resulting document token. Do not bind a folder as a report or claim successful setup before that step. Document allowlists, existing authentication and write approval remain separate checks. Never silently fall back to local output when the selected Feishu destination is unavailable; keep the private preview and mark remote saving pending.

The report location is separate from the raw evidence store. Main reports, private indexes and immutable archives retain their existing roles. Selected trace/full uploads use a separate private ZIP in the confirmed Drive folder, including a readable experiment index; see [archives](archives.md). Local originals are retained. Low-level archival/synthesis libraries remain platform-independent; the Skill/CLI workflow enforces onboarding.
