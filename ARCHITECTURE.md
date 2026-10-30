# Architecture and decisions

Sources feed immutable evidence/records; the current authorized Agent proposes knowledge revisions; report adapters apply reviewed changes. No source adapter executes experiment code. No report adapter controls experiments.

## Data and interfaces

Four implicitly callable skills share src/expkm, one private store/config and one bundled interpreter under the coordinator. Stage-specific setup avoids unrelated questions. Selections stores record-location and archive-destination independently. workflow audits expected source coverage, evidence bytes, pinned knowledge, reviewed historical mappings and separate current readbacks; it never executes experiments or calls a model. Implicit matching is a host Agent decision, not a task watcher.


- `Store.record`: explicit topic, actual attempt identity, metadata, evidence files and approved roots. Immutable content-addressed object bytes; atomic record head/history; advisory single-writer lock.
- `Templates`: private topic-bound proposal, explicit digest confirmation and compare-and-swap changes. Frozen definitions are data, not executable templates. Only report preparation/sync requires a template; recording and pure knowledge maintenance are independent.
- `Destinations`: separate private topic-bound save-method/location selection. No default platform, implicit target override, network contact or write permission on confirmation. Only report sync requires report selections; plans seal template/destination and, when present, knowledge versions. The core record/knowledge model remains independent of the destination.
- `setup_status`: presentation-neutral introduction, fenced plain-text hierarchy and missing choice-card data; the local Agent renders the host's native questions. No new UI/model service.
- `ArchiveSync`: deterministic topic-scoped trace/full ZIP with a checksum manifest and readable index. Explicit scope/folder/version-bound upload plans, private pending/token journals, byte-level download verification and unknown-result reconciliation. `LarkDrive` uses existing user authentication with explicit folder allowlists; no sharing or credential management.
- `read_result` and optional `MLflowSource`: preserve source distinctions and access errors. Unknown formats require an explicit conversion/profile. No generic parser claims to understand arbitrary experiment logs.
- `compare`: assess one defined metric within data/protocol/layer/aggregation boundaries. Conditional differences are not causal conclusions or automatic decisions.
- `Knowledge.update`: verify evidence identities/hashes, optional quotes and numeric assertions, enforce expected-version checks, preserve conclusion/decision history. Agent semantic claims remain reviewable.
- `inventory` / `migration_preview`: structural inventory and exhaustive explicit block destinations with original XML retained. The Agent supplies semantic placement and the actual concise main report.
- Markdown and Feishu share plan/digest/verify concepts, not platform identifiers. Feishu identities and reference maps remain adapter state.

## Why these choices

MLflow-only storage excludes experiments without tracking and does not maintain topic conclusions. Document-only append preserves detail but grows linearly. A new web platform or orchestration framework adds unrelated infrastructure. JSON plus a rebuildable SQLite index keeps the first release portable and auditable.

Snapshots are authoritative; SQLite is disposable. A crash can leave orphaned content objects, but cannot erase original evidence. History/head writes are atomic individually, not a cross-file database transaction. Audit and recovery must preserve prior snapshots.

The renderer follows a confirmed, version-pinned template and typed section blocks. Claims group by question inside the selected results section; full references live in trace/index. Repeated experimental support does not create repeated main sections. Changed claims and template adoption need reasons; old claims can be superseded, not silently removed. Missing sections are explicit rather than implying completion. New sync plans seal the template reference; historical recovery remains accessible after a switch.

## Privacy and trust

Private stores are forbidden under the package/source root. Archive inputs must be regular, non-symlink files within explicit roots. JSON/CSV/text/XML are parsed as data; code and executable serialization are not loaded. Network adapters require configured origins/documents. Public packaging uses an explicit file list and final-byte scanning. No model provider, telemetry, background daemon or production experiment operation exists.

Current Agent access is authorized processing, not a claim that Codex is an offline application. The package makes no promise against an administrator or a compromised host. User storage controls and the existing Agent/account policies still apply.

Distribution targets local developer Agents. The package includes a local marketplace and its source runtime, with no public listing dependency. Private upload payloads are deliberately separate from the allowlisted plugin ZIP. Native plugin loading is tested separately from clean extraction/launcher tests; host UI and real Feishu write behavior require their own acceptance evidence.
