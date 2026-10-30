# Post-Experiment Knowledge

**0.6.0-beta.1 · 实验后知识管理插件 · Windows x64 一键安装测试版**

把已完成实验整理为“专题主报告 → 实验索引 → 完整证据与追溯档案”，保留原始证据，持续修订结论，避免报告反复堆叠。不执行实验。

1. 在 GitHub Releases 下载 Windows x64 ZIP 并解压。
2. 双击 `install.cmd`，安装器会校验文件并注册到当前用户的 Codex。无需安装 Python 或 pip，无需管理员权限。
3. 新开 Codex 对话，直接说明要归档、分析、保存报告或全部完成；Agent 根据场景选择技能。也可显式输入 `$post-experiment-knowledge`。先简要介绍功能和三层结构，只问当前步骤缺少的信息。

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

| Skill | Select when | Required information |
| --- | --- | --- |
| post-experiment-knowledge | Multi-stage work, historical reorganization, unclear outcome | Desired deliverables; clarify only if unclear |
| experiment-record | Archive completed/failed/partial evidence | Relevant inputs, actual attempt identity, confirmed private local store |
| experiment-synthesize | Compare evidence or maintain conclusions | Relevant evidence and research question; no report template/target |
| experiment-sync | Save a prepared report or upload archives | Report: template + concrete targets; archives: scope + exact parent |

All four allow implicit invocation; users need not name a skill. Selection depends on the host Agent's semantic matching, not a guaranteed keyword dispatcher or task monitor. Clear requests execute directly. Ambiguous requests get an outcome card before stage-specific questions. Native cards are rendered by the host; plain numbered choices are the fallback.

```text
Research topic
├── Main report: current conclusions, key evidence, limitations and decisions
├── Experiment index: attempts, differences, states and archive links
└── Complete archive
    ├── Raw evidence: results, configuration, logs, controlled artifact references
    └── Trace: record IDs, revisions, hashes and claim relationships
```

These views are produced as requested, not a mandatory full workflow. A full request runs Record → Synthesize → Sync and checks every deliverable. All skills share one src/expkm core, private store/config and bundled interpreter under skills/post-experiment-knowledge/python.

## Stage-specific setup and completion

All commands below follow skills/post-experiment-knowledge/scripts/expkm.cmd and a global --store PRIVATE_STORE. Real inputs/settings/receipts remain outside the source and installed plugin.

1. Record: setup --topic quality --stage record. Confirm the exact local archive path via record-location preview/confirm. Only then record explicit existing files and authorized roots. Verify immutable evidence. No report template or destination needed.
2. Synthesize: setup --topic quality --stage synthesize. Prepare evidence with synthesize --prepare; the authorized Agent reviews comparability and writes claims/decisions. synthesize --draft validates immutable references and numerical assertions. Pure analysis omits report_sections and does not publish. MLflow is optional and read-only.
3. Sync report: setup --topic quality --stage sync --sync-kind report. Confirm an existing template or explicitly review a new proposal through template preview/confirm. Confirm local Markdown, Feishu or both and exact file/document via destination preview/confirm. New report selections default to no archive upload. Prior selections are reused. report-preview --topic quality --sections PRIVATE_SECTION_MAPPING renders the chosen template; prepared reports can go straight to sync planning.
4. Sync archives: setup --topic quality --stage sync --sync-kind archive (or both). archive-destination preview/confirm selects trace/full and one exact folder or Wiki parent independently of reports/templates.
5. Plan concrete changes, apply within existing user authorization and read back every requested output. Both report destinations require separate plans/receipts. Archives require their own plan and byte-verified receipt. If permissions/dependencies/conflicts prevent a stage, preserve completed work and explicitly retain pending steps.

For multi-stage work the coordinator keeps a private workflow request and uses workflow --request PRIVATE_REQUEST to audit expected sources, evidence integrity, current knowledge, historical mappings when requested and final readback per destination. New report plans pin existing knowledge versions; stale conclusions cannot be satisfied by an old verified report. An audit verifies the listed scope, not arbitrary semantic truth or unlisted input completeness. Review readability, numbers and mapping manually.

Template heading order and general data/environment/metric tables remain intact; result formats can vary. No template is auto-selected. Template/source changes require review and new confirmation. Recovery of old plans/records remains accessible after upgrades. See the skill's template/destination/archive references.

Feishu uses the user's own optional lark-cli and private allowlist. Document creation/relocation requires the Agent's available external tools and concrete authorization; the core adapter only edits existing supported document blocks. No auto-login, permission escalation, model service or sharing change.


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
