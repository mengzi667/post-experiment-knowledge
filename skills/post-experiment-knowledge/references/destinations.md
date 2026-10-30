# Report save method and location

At first use, confirm both the template and where the readable report belongs. Ask for missing selections together. Valid save modes are local Markdown (`markdown`), an existing Feishu document (`feishu`), or both (`both`). A topic reuses its confirmed selection. Other platforms can be added through adapters; do not claim an unavailable adapter already works.

## Private confirmation workflow

1. `setup --topic quality` supplies the introduction, text-tree hierarchy and missing choice cards. Present the introduction/tree first, then render available native cards for template, report save method and upload scope. `destination show --topic quality` reads a confirmed selection. Do not choose local storage or Feishu implicitly.
2. For Markdown, generate `destination preview --topic quality --mode markdown --target ABSOLUTE_REPORT_FILENAME --root ABSOLUTE_AUTHORIZED_DIRECTORY --archive-scope none`. Feishu uses `--mode feishu --document DOCUMENT_TOKEN`. Both uses `--mode both` and both locations. Always explicitly supply `--archive-scope none|trace|full`. Trace/full requires exactly one `--archive-folder DRIVE_FOLDER_TOKEN` or `--archive-wiki WIKI_PARENT_NODE_TOKEN`.
3. Read the private proposal and show the exact locations and method. Explain that raw evidence, knowledge state and drafts remain in the private store and are not automatically uploaded.
4. After the user's explicit selection, run `destination confirm --topic quality --proposal PRIVATE_PROPOSAL --approve DESTINATION_VERSION`. A change also needs `--expected-version CURRENT_VERSION`. A content digest is not evidence of conversation authorization. Do not preview and auto-confirm a new choice unattended.

The saved binding has `schema_version`, `topic`, `definition` and `version`. The definition contains `mode`, report location objects (`markdown: {target, root}`, `feishu: {document}`) and `archives: {scope}`, `{scope, folder}` or `{scope, wiki}`. Folder and Wiki parents are distinct, mutually exclusive namespaces. Tokens, paths and bindings are private. They are not plugin defaults or public examples. Confirmation does not contact a platform, create a report, grant scopes or enable writes. Legacy selections without an explicit archive scope remain readable for recovery but require a new reviewed scope selection before new report workflows.

User-specific defaults live in the private application-data `PostExperimentKnowledge/preferences.json`, outside every plugin package. `personal_space` contains an explicitly user-confirmed HTTPS Wiki `url`, matching `node_token`, and `confirmed_by_user: true`; optional space metadata stays private. Setup returns this parent separately from the topic's confirmed selections. A default does not auto-select the template, save method, upload scope or write authorization.

## Route and verify

`synthesize --prepare` includes the selected destination and template. The Agent fills the template and generates a private preview. `sync plan --topic quality --content PRIVATE_PREVIEW` uses the selected Markdown target/root if Markdown alone was selected. For Feishu alone, the adapter and target come from the binding; supply `--replacements PRIVATE_BLOCK_REPLACEMENTS` after reviewing native document blocks.

With both selected, explicitly plan Markdown and Feishu separately via `--adapter`. Both use their confirmed targets. Apply and verify each reviewed plan under the existing authorization. Neither requires the user to repeat the platform choice. Report partial completion accurately and retain separate receipts; there is no cross-platform transaction.

Explicit CLI target/root overrides must equal the confirmed location. Changing the platform or filename requires a new proposal and confirmation. Plans seal both template and destination versions. A changed/missing selection blocks a new apply before platform access. Legacy plans without destination bindings can still be verified or recovered; regenerate them before a new apply. Historical versions remain available for rollback and unknown-write reconciliation.

The Feishu adapter edits supported blocks in an existing document; it does not create reports/folders or relocate documents. Resolve authorized document links to their real document tokens using available Feishu tools before binding. A folder request needs authorized creation through those tools and a resulting document token. Do not bind a folder as a report or claim successful setup before that step. Document allowlists, existing authentication and write approval remain separate checks. Never silently fall back to local output when the selected Feishu destination is unavailable; keep the private preview and mark remote saving pending.

The report location is separate from the raw evidence store. Main reports, private indexes and immutable archives retain their existing roles. Selected trace/full uploads use a separate private ZIP in the confirmed Drive folder, including a readable experiment index; see [archives](archives.md). Local originals are retained. Low-level archival/synthesis libraries remain platform-independent; the Skill/CLI workflow enforces onboarding.
