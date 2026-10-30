# Post-Experiment Knowledge

**0.5.0-beta.1 · 实验后知识管理插件 · Windows x64 一键安装测试版**

把已完成实验整理为“专题主报告 → 实验索引 → 完整证据与追溯档案”，保留原始证据，持续修订结论，避免报告反复堆叠。不执行实验。

1. 在 GitHub Releases 下载 Windows x64 ZIP 并解压。
2. 双击 `install.cmd`，安装器会校验文件并注册到当前用户的 Codex。无需安装 Python 或 pip，无需管理员权限。
3. 新开 Codex 对话，输入 `$post-experiment-knowledge`。先确认模板、保存方式、上传范围及具体输出位置，再开始整理。

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

## Normal workflow

Start with `setup --topic quality`. The Agent first introduces the plugin and displays the three-level report hierarchy in a fenced plain-text tree, then asks missing choices through native choice cards when available: template, report save method, archive-upload scope, and a required free-text concrete save location. Provide the actual Feishu report/parent URL and/or local output filename. A platform choice alone is insufficient. Confirmed choices are reused per topic; no choice is silently selected. Card rendering comes from the host Agent, not a separate web application.

First determine the topic's report template. `template show --topic quality` reuses a previously confirmed frozen selection. If none exists, ask the user for an existing template or review a new proposal. Use `template preview --topic quality --file PRIVATE_TEMPLATE_JSON --source SOURCE_VERSION` (or explicitly propose `--builtin`), then wait for user confirmation before `template confirm --topic quality --proposal PRIVATE_PROPOSAL --approve TEMPLATE_VERSION`. Changing a selection also needs `--expected-version CURRENT_VERSION`. No template is chosen automatically. Noninteractive first calls stop with `needs_template_selection`. See the [template contract](skills/post-experiment-knowledge/references/templates.md).

At the same onboarding step, confirm the readable report's save method and exact location. `destination show --topic quality` reuses a confirmed choice. Options: local Markdown, an existing Feishu document, or both. Use `destination preview --topic quality --mode markdown --target ABSOLUTE_REPORT_FILENAME --root ABSOLUTE_AUTHORIZED_DIRECTORY --archive-scope none`, or `--mode feishu --document DOCUMENT_TOKEN`; both mode supplies both locations. Always explicitly choose `--archive-scope none|trace|full`; trace/full also requires `--archive-folder DRIVE_FOLDER_TOKEN`. Review the concrete proposal with the user, then `destination confirm --topic quality --proposal PRIVATE_PROPOSAL --approve DESTINATION_VERSION`. Changes also need `--expected-version CURRENT_VERSION`. Noninteractive missing selections return `needs_destination_selection`. See [save method selection](skills/post-experiment-knowledge/references/destinations.md).

1. Point `record` at explicit existing result files and authorized roots. Use a metadata sidecar for differing formats.
2. Use `synthesize --prepare` to create a private evidence bundle for the current authorized Agent.
3. Review comparability and source conflicts. Author evidence-backed claims, then submit the draft with `synthesize --draft` and the expected knowledge version.
4. Review the rendered main report; use `trace` for full evidence instead of appending all details.
5. Generate `sync plan`, review it, then apply the user-authorized exact plan and verify it.

Rendering follows the confirmed headings, order and configuration tables, with flexible results blocks. Each knowledge snapshot pins its template. New sync plans require `--topic` and bind the selected version; a later template change blocks stale applies. Audit and recovery remain possible. A confirmed template does not authorize production writes.

New sync plans also use the confirmed save method and location; adapter/target/root overrides must match. With one destination, `sync plan --topic quality` derives the adapter and target. With both, create a separate plan per `--adapter` and verify each receipt. A changed destination blocks old applies without stranding recovery. Selection itself does not write anything or grant permissions. Feishu document creation is outside this adapter; bind an existing document after any separately authorized setup. Local raw evidence and knowledge are retained; selected archival uploads create separate private remote snapshots.

Every command supports `--help`. Global `--store` selects the private state directory; the default is under the current user's application-data directory. Private outputs must remain within that store. `--config` reads optional private adapter settings.

MLflow is an optional read-only source. `capture-mlflow` accepts a Run ID, selected metric history keys and explicit artifact paths. It supports approved HTTPS origins or local protected tunnels and does not follow redirects. It does not create, modify or repair Runs. No Run ID is required for local results.

Feishu is an optional output adapter using existing lark-cli authentication. `sync plan` preserves native resources and defaults to read-only; writes require an explicit allowlist, concrete user authorization, a plan digest and `--allow-feishu-write`. The application does not authenticate or share documents for you.

## Upload private evidence and trace archives

Choose no archive upload, trace only, or raw evidence plus trace during setup. `archive plan --topic quality` builds a deterministic ZIP with an experiment index, immutable record revisions, knowledge history and SHA-256 manifest; full scope additionally includes archived raw objects. Configs, credentials and journals are excluded by construction. External weights/resources are references, not implicitly downloaded. Review the exact inventory and credential guard before upload.

`archive apply --plan PRIVATE_PLAN --approve PLAN_DIGEST --allow-feishu-upload` writes only to the selected folder, which must also appear in the private `feishu.allowed_archive_folders` list. It uses the existing user's lark-cli identity and does not change permissions. Verification downloads the uploaded ZIP and checks folder membership, size and SHA-256. A known upload is not repeated after a failed readback; an unknown result stops for reconciliation. Report and archive receipts are separate. See [archive operations](skills/post-experiment-knowledge/references/archives.md) for recovery and size limits. These ZIPs are private evidence artifacts, never plugin release packages.

For Wiki archives, select `--archive-wiki WIKI_PARENT_TOKEN` instead of `--archive-folder` and allowlist it under private `feishu.allowed_archive_wiki_nodes`. The adapter uploads directly under that node and verifies exact Wiki parent/object/name plus downloaded size/SHA-256. Folder and Wiki targets cannot be mixed. After an explicitly authorized relocation, `archive adopt` can verify and bind the existing file to a new reviewed location plan without uploading it again; original receipts remain history.

Before a new upload, the adapter checks the actual folder-list read capability. A valid login or successful upload does not prove that permission. Missing scopes return `needs_feishu_authorization` with the exact scope names, before any upload or pending-write journal; current lark-cli directory listing can require `space:document:retrieve` separately from upload/download scopes. No permission is silently added. UTF-8 `.log` inputs are supported as plain text.

## Historical reports

`organize --topic quality --input SNAPSHOT --out PRIVATE_INVENTORY` inventories full DocxXML or a lark-cli fetch envelope after template selection. This is structural diagnosis, not automatic semantic migration. The Agent creates an explicit block mapping, a concise main report, an experiment index and a complete archive. Re-run with `--mapping` and `--main` to validate coverage and produce a private migration preview. Plain Markdown history can be recorded as evidence; use Markdown sync for maintained sections.

Original bytes and resource references are retained. External resource binaries are not implicitly downloaded. Live Feishu writes support atomic replacements, not automatic archival reorganization; full historical relocation remains a separately approved operation.

## Package or install

For local plugin installation, extract a release ZIP and run the following from its `post-experiment-knowledge` directory on a host with Codex plugin CLI support:

```text
codex plugin marketplace add .
codex plugin add post-experiment-knowledge@post-experiment-knowledge-beta
```

The packaged local marketplace points at the extracted plugin. Keep that directory available for refreshes. Start a new chat or refresh/restart the host if discovery has not updated, then invoke `$post-experiment-knowledge`. Follow the first-use introduction and selection cards. This uses a local marketplace, not public submission. Refer to the [official local marketplace instructions](https://developers.openai.com/plugins/build/plugins) for host-specific UI differences. Other Agents that support Agent Skills can use the standalone Skill/runtime; their native plugin formats are not claimed to be tested.

For the Windows x64 release, the Agent invokes `scripts\expkm.cmd` inside the installed Skill. It always uses that Skill's bundled interpreter with isolated imports, ignores PYTHONHOME/PYTHONPATH, and does not modify registry or PATH. Runtime files and licenses are included at `skills/post-experiment-knowledge/python/`. It runs from arbitrary working directories and paths with spaces/non-ASCII names. It does not install packages or download a runtime on first use. If `python/python.exe` is missing, the launcher reports an incomplete package rather than using system Python. Other platform bundles are not yet provided; their source/Skill installation still requires Python 3.10+.

Feishu additionally requires lark-cli and each user's own authorization/private allowlist; local Markdown works without them. Missing dependencies are explained during setup rather than silently installed or configured.

```python
from pathlib import Path
from expkm.packaging import build_plugin, install_skill
official_zip = Path('OFFICIAL_DOWNLOAD_DIRECTORY') / 'python-3.14.10-embed-amd64.zip'
build_plugin(Path('.'), Path('PRIVATE_BUILD_DIRECTORY') / 'post-experiment-knowledge-windows-x64.zip', windows_runtime=official_zip)
install_skill(Path('.'), Path('PRIVATE_SKILLS_DIRECTORY') / 'post-experiment-knowledge', windows_runtime=official_zip)
```

The standalone installed Skill includes a copy of the generic core and, when `windows_runtime` is supplied, the same bundled interpreter and licenses. Existing Skill directories are never overwritten. Omitting that argument deliberately builds a source-only package. The ZIP has portable and compatibility manifests, a local marketplace catalog and an onboarding entrypoint; no MCP server or hooks are required. Host UI rendering and account setup remain host-specific.

Builders obtain the embedded ZIP from the [official Python 3.14.10 release](https://www.python.org/downloads/release/python-31410/). `runtime/windows-x86_64.json` pins the official archive SHA-256 and every member name, size and SHA-256. A different archive, extra member or modified member fails packaging. Binary runtime files bypass text scanning only after exact lock verification; all generic code/doc files still use the distribution allowlist and scan. The final ZIP is checked again. CPython and bundled third-party notices are retained in its original `LICENSE.txt`. The runtime is upgraded only through a reviewed lock/package update, never silently from a user's environment. See [Python embedded-distribution guidance](https://docs.python.org/3/using/windows.html#the-embeddable-package).

## Validate and troubleshoot

Install pytest in a development environment, then run `python -m pytest -q`. It is not a runtime dependency. Use `verify --record RECORD_ID` to check archived evidence and `reindex` to rebuild the disposable SQLite index. CLI failures deliberately suppress raw exception payloads; inspect the private input and config in the authorized local session.

Conflicts: regenerate the preview from the current source. Unknown write outcome: re-read/verify the same plan before any further apply. Never rerun an experiment to fix a record or upload problem.

See [ARCHITECTURE.md](ARCHITECTURE.md), [RESEARCH.md](RESEARCH.md), [VALIDATION.md](VALIDATION.md), [BETA.md](BETA.md) and [ROADMAP.md](ROADMAP.md). Real research and real acceptance artifacts are private and excluded from this package. Project code is provided under [MIT License](LICENSE); the bundled CPython runtime retains its original PSF and third-party notices.
