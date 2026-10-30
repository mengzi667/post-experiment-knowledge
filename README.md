# Post-Experiment Knowledge

**0.7.0-beta.1 · 实验后知识管理插件 · Windows x64 一键安装测试版**

把已完成实验整理为“专题主报告 → 实验索引 → 完整证据与追溯档案”，保留原始证据，持续修订结论，避免报告反复堆叠。不执行实验。

1. 在 GitHub Releases 下载 Windows x64 ZIP 并解压。
2. 双击 `install.cmd`，安装器会校验文件并注册到当前用户的 Codex。无需安装 Python 或 pip，无需管理员权限。
3. 新开 Codex 对话，直接说明要归档、分析、保存报告或全部完成；Agent 根据场景选择技能。也可显式输入 `$post-experiment-knowledge`。每次新请求先用原生选项卡问清需求、确认模板和具体保存位置，再开始处理；已有偏好仅预填，不自动执行。

需要已有支持插件的 Codex。飞书功能另外需要自己的 lark-cli 和账号授权；本地 Markdown 无需飞书。请先阅读 [Beta 已知限制](BETA.md)。本包不会携带作者的实验资料、私有地址或凭据。

Record, Synthesize, Sync for **already-produced** experiment results. The Windows x64 release includes its own CPython 3.14.10 runtime: users do not install Python or pip. The core has no third-party dependencies. No training execution, scheduling, monitoring, GPU management, model APIs or telemetry.

Designed for Codex and similar local development Agents. Distribute the local plugin/Skill directly; no public plugin-directory submission, hosted application or extra MCP server is required. Feishu is optional and uses each installer's own lark-cli installation and existing account authorization. No account, tenant or experiment data is bundled.

An explicitly confirmed personal-space Wiki parent may be kept in private application-data preferences. Setup exposes that default to the Agent; it never becomes a public plugin default, silently selects an upload scope or falls back to Drive root. Topic-specific report/doc bindings remain separate.

## Start without a platform

From an extracted Windows x64 release directory:

```text
skills\post-experiment-knowledge\scripts\expkm.cmd --help
skills\post-experiment-knowledge\scripts\expkm.cmd doctor
skills\post-experiment-knowledge\python\python.exe -I -B examples\synthetic30.py --output PRIVATE_DEMO_DIRECTORY
```

The synthetic example produces 30 independent archived records, a single maintained conclusion, an experiment index, history and a Markdown sync preview. It does not run an ML model. Choose a destination outside this source tree. A source checkout or another platform can use `python skills/post-experiment-knowledge/scripts/expkm.py` and `python examples/synthetic30.py` with an existing Python 3.10+ installation; source-only ZIPs do not include an interpreter.

Optional core installation: `python -m pip install --no-build-isolation --no-deps .`. For an Agent Skill or Plugin package, use the packaging helpers described below; do not copy private data into the repository.

## Four skills, one runtime

| Skill | Purpose |
| --- | --- |
| post-experiment-knowledge | Clarify the request and coordinate all required stages |
| experiment-record | Archive existing completed/failed/partial evidence with immutable identities |
| experiment-synthesize | Compare evidence and maintain conclusions/decisions |
| experiment-sync | Save reports and explicitly selected archives; read back each output |

All four allow implicit invocation and share one core, private store/config and isolated bundled interpreter. A full request completes every required stage; a narrower confirmed request cannot silently add others. Host semantic matching is not a deterministic watcher.

```text
Research topic
├── Main report: current conclusions, key evidence, limits and decisions
├── Experiment index: attempts, differences, states and archive links
└── Complete archive
    ├── Raw evidence: results, configuration, logs and artifact references
    └── Trace: record IDs, revisions, hashes and claim relationships
```

## Every request starts with confirmed intake

Before formal experiment processing, clarify this request's goal, source scope, requirements and expected outputs, require a confirmed template and exact save locations, then obtain confirmation of the complete summary. This also applies to Record-only and analysis-only. Prior topic choices may prefill fields; they do not authorize a new request.

Use native choice cards for goal/scope, template source, save method, upload scope and final confirmation. Paths, links and special requirements use the same tool's free-text fields. A preselection or silence is not confirmation. Without native cards, use concise numbered text.

The template card offers:

1. Provide an existing template file/link/structure.
2. Explicitly reuse a previously supplied template.
3. Ask Codex to recommend a template from actual experiment content/results, then review it.

The recommendation branch first confirms requirements, bounded source scope and exact positions, then uses a restricted template-recommendation intake for necessary read-only context. It cannot archive, synthesize research conclusions or publish. Show the recommendation/reasons and obtain template confirmation before a separate final execution intake. No recommendation is automatically adopted.

## Commands and boundaries

Use skills/post-experiment-knowledge/scripts/expkm.cmd on Windows. Global --store, --config and --intake options precede the command. Real data/settings/receipts stay outside the source and installed plugin.

1. setup --topic quality --stage record|synthesize|sync (Sync --sync-kind report|archive|both) returns required questions. The coordinator's default workflow mode clarifies an ambiguous outcome.
2. Confirm the chosen template with template preview/confirm and the exact private result directory with record-location preview/confirm. Requested reports additionally select exact destination targets; requested uploads select archive-destination scope/parent. No arbitrary default platform or path.
3. Author the private request metadata file, run intake preview --file PRIVATE_REQUEST, show the concrete summary, await the user's response and intake confirm --proposal PRIVATE_PROPOSAL --approve VERSION.
4. Pass --intake VERSION to Record/Synthesize/new Sync and export commands. The CLI checks scope, stages, authorized roots and current template/location versions before payload reads. New report/archive plans bind the intake; apply cannot replay a plan under another intake. Original plan review, allowlists and write/upload flags still apply.
5. Keep the coordinator's workflow manifest current and verify every requested output separately. Both report targets require two receipts; archives require exact parent and downloaded size/SHA-256. Archive freshness audits reuse the sealed size budget, including explicit large export limits.
6. Close the request with intake close --version VERSION after delivery. A closed request cannot be reused. New requests use new IDs and confirmation, even with identical preferences.

See [the intake schema and recommendation procedure](skills/post-experiment-knowledge/references/intake.md). Current synthesis/export operates on all existing records of the selected topic. Do not silently widen a subset request; use an explicitly separate topic/store or explain the unsupported scope.

The mandatory result location for local-only work is the exact private store. No unrequested report document is required, but the mandatory template still is. Prepared reports can go directly to Sync after intake; don't force re-recording or re-analysis.

Templates preserve headings/order and general data/environment/metric tables while allowing different result formats. No built-in template is silently chosen. Historical records/plans remain verifiable; new applies need current intake. Core Python primitives are trusted application APIs and remain platform independent; the CLI gate cannot prevent an authorized developer from calling them directly.

The runtime proves explicit confirmation parameters and bindings, not that a human saw a card or who clicked. It cannot force a host to invoke this plugin. Semantic interpretation and readability still need Agent/user review.

Feishu uses each user's own optional lark-cli, account and exact target authorization. Node creation/relocation uses available external tools only after the concrete parent/names/setup scope are confirmed; no experimental content is populated before final intake. No automatic login, permission escalation, model service, telemetry or sharing change.


## Upload private evidence and trace archives

Only for requested archival Sync, choose no upload, trace only, or raw evidence plus trace; report-only work does not ask about uploads. `archive plan --topic quality` builds a deterministic ZIP with an experiment index, immutable record revisions, knowledge history and SHA-256 manifest; full scope additionally includes archived raw objects. Configs, credentials and journals are excluded by construction. External weights/resources are references, not implicitly downloaded. Review the exact inventory and credential guard before upload.

`archive apply --plan PRIVATE_PLAN --approve PLAN_DIGEST --allow-feishu-upload` writes only to the selected folder, which must also appear in the private `feishu.allowed_archive_folders` list. It uses the existing user's lark-cli identity and does not change permissions. Verification downloads the uploaded ZIP and checks folder membership, size and SHA-256. A known upload is not repeated after a failed readback; an unknown result stops for reconciliation. Report and archive receipts are separate. See [archive operations](skills/post-experiment-knowledge/references/archives.md) for recovery and size limits. These ZIPs are private evidence artifacts, never plugin release packages.

For Wiki archives, select `--archive-wiki WIKI_PARENT_TOKEN` instead of `--archive-folder` and allowlist it under private `feishu.allowed_archive_wiki_nodes`. The adapter uploads directly under that node and verifies exact Wiki parent/object/name plus downloaded size/SHA-256. Folder and Wiki targets cannot be mixed. After an explicitly authorized relocation, `archive adopt` can verify and bind the existing file to a new reviewed location plan without uploading it again; original receipts remain history.

Before a new upload, the adapter checks the actual folder-list read capability. A valid login or successful upload does not prove that permission. Missing scopes return `needs_feishu_authorization` with the exact scope names, before any upload or pending-write journal; current lark-cli directory listing can require `space:document:retrieve` separately from upload/download scopes. No permission is silently added. UTF-8 `.log` inputs are supported as plain text.

## Historical reports

`organize --topic quality --input SNAPSHOT --out PRIVATE_INVENTORY` inventories full DocxXML or a lark-cli fetch envelope without requiring report settings. This is structural diagnosis, not automatic semantic migration. The Agent creates an explicit block mapping, a concise main report, an experiment index and a complete archive. Re-run with `--mapping` and `--main` to validate coverage and produce a private migration preview. Plain Markdown history can be recorded as evidence; use Markdown sync for maintained sections.

Original bytes and resource references are retained. External resource binaries are not implicitly downloaded. Live Feishu writes support atomic replacements, not automatic archival reorganization; full historical relocation remains a separately approved operation.

## Package or install

For local plugin installation, extract a release ZIP and run the following from its `post-experiment-knowledge` directory on a host with Codex plugin CLI support:

```text
codex plugin marketplace add .
codex plugin add post-experiment-knowledge@post-experiment-knowledge-beta
```

The packaged local marketplace points at the extracted plugin. Keep that directory available for refreshes. Start a new chat or refresh/restart the host if discovery has not updated, then invoke `$post-experiment-knowledge`. Follow the first-use introduction and selection cards. This uses a local marketplace, not public submission. Refer to the [official local marketplace instructions](https://developers.openai.com/plugins/build/plugins) for host-specific UI differences. Other Agents can adapt the Skill format; their native plugin installation and implicit routing are not claimed to be tested.

For the Windows x64 release, the Agent invokes `scripts\expkm.cmd` inside the installed Skill. It always uses that Skill's bundled interpreter with isolated imports, ignores PYTHONHOME/PYTHONPATH, and does not modify registry or PATH. Runtime files and licenses are included at `skills/post-experiment-knowledge/python/`. It runs from arbitrary working directories and paths with spaces/non-ASCII names. It does not install packages or download a runtime on first use. If `python/python.exe` is missing, the launcher reports an incomplete package rather than using system Python. Other platform bundles are not yet provided; their source/Skill installation still requires Python 3.10+.

Feishu additionally requires lark-cli and each user's own authorization/private allowlist; local Markdown works without them. Missing dependencies are explained during setup rather than silently installed or configured.

```python
from pathlib import Path
from expkm.packaging import build_plugin, install_skill
official_zip = Path('OFFICIAL_DOWNLOAD_DIRECTORY') / 'python-3.14.10-embed-amd64.zip'
build_plugin(Path('.'), Path('PRIVATE_BUILD_DIRECTORY') / 'post-experiment-knowledge-windows-x64.zip', windows_runtime=official_zip)
install_skill(Path('.'), Path('PRIVATE_SKILLS_DIRECTORY') / 'post-experiment-knowledge', windows_runtime=official_zip)
```

The legacy install_skill helper installs one discoverable coordinator with companion instructions and one runtime; use the plugin for four independently discoverable skills. The standalone entry includes generic core and, with windows_runtime, the same interpreter/licenses. Existing Skill directories are never overwritten. Omitting that argument deliberately builds a source-only package. The ZIP has portable and compatibility manifests, a local marketplace catalog and an onboarding entrypoint; no MCP server or hooks are required. Host UI rendering and account setup remain host-specific.

Builders obtain the embedded ZIP from the [official Python 3.14.10 release](https://www.python.org/downloads/release/python-31410/). `runtime/windows-x86_64.json` pins the official archive SHA-256 and every member name, size and SHA-256. A different archive, extra member or modified member fails packaging. Binary runtime files bypass text scanning only after exact lock verification; all generic code/doc files still use the distribution allowlist and scan. The final ZIP is checked again. CPython and bundled third-party notices are retained in its original `LICENSE.txt`. The runtime is upgraded only through a reviewed lock/package update, never silently from a user's environment. See [Python embedded-distribution guidance](https://docs.python.org/3/using/windows.html#the-embeddable-package).

## Validate and troubleshoot

Install pytest in a development environment, then run `python -m pytest -q`. It is not a runtime dependency. Use `verify --record RECORD_ID` to check archived evidence and `reindex` to rebuild the disposable SQLite index. CLI failures deliberately suppress raw exception payloads; inspect the private input and config in the authorized local session.

Conflicts: regenerate the preview from the current source. Unknown write outcome: re-read/verify the same plan before any further apply. Never rerun an experiment to fix a record or upload problem.

See [ARCHITECTURE.md](ARCHITECTURE.md), [RESEARCH.md](RESEARCH.md), [VALIDATION.md](VALIDATION.md), [BETA.md](BETA.md) and [ROADMAP.md](ROADMAP.md). Real research and real acceptance artifacts are private and excluded from this package. Project code is provided under [MIT License](LICENSE); the bundled CPython runtime retains its original PSF and third-party notices.
