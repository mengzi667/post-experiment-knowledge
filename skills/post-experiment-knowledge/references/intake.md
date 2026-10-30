# Mandatory request intake — all four skills

Each new post-experiment request must clarify the goal, scope and requirements and confirm **a template and exact save locations before formal processing**. This applies to Record and Synthesize too. The narrowly authorized recommendation phase below is the sole template-pending exception for necessary read-only material inspection. Prior preferences may prefill the summary, never silently authorize a new request.

## Ask with native cards, then bind the confirmed request

1. Present the short plugin introduction and fenced three-layer tree on first use. On every new request run setup for the intended stage, then show a concise summary: goal; included sources/topic history; constraints; selected stages/deliverables; mandatory template/source/version; exact private local directory; requested report files/documents/parents; archival scope and parent; privacy exceptions if known.
2. Prefer native selection cards whenever available. Use options for goals/scope, template source, save method, archival upload scope and final confirmation. Put paths, document links, template files and special requirements in the card tool's free-text fields. If the host limits choices/questions, split them into small batches. A preselected option is not a response. Only when native cards are unavailable use numbered text choices.
3. Ask for missing details; don't require the user to repeat known values individually. Still ask them to confirm this request's complete summary before any experimental payload reads, recording, synthesis or writes. If they revise a requirement, update the summary and obtain confirmation of the changed concrete scope. Do not treat providing a digest, an old session, or defaults as user confirmation.
4. The template card offers: (1) provide an existing link/file/structure, (2) explicitly reuse a previously supplied template, (3) Codex recommends a template from the actual experiment/results for review. No automatic built-in/default adoption. Use template preview/confirm with the reviewed source. Local save location: use record-location preview/confirm under the exact selected --store, even for analysis-only. Requested reports additionally use destination preview/confirm; uploads use archive-destination preview/confirm. A platform name without its concrete path/document/parent is insufficient.
5. Setup may read template data, request metadata and saved preferences; it may write private proposals. Do not read/scan experiment content, execute experiment code, fetch MLflow evidence or generate a report to fill missing intake details. If new Feishu nodes are needed, first confirm their exact parent, names and purpose in the request summary. Only then perform the specifically authorized empty-node setup through available tools, bind the resulting document tokens, and finish intake. Do not populate the nodes with experiment content before intake is confirmed. Sharing/permissions never change automatically.
6. Write a private request definition, run intake preview, present that concrete summary, and confirm only after the user's actual response. Persist only user-confirmed choices. Use existing explicit confirmation for those exact details in the current request; never auto-confirm a new proposal just because the Agent has its digest.

All commands use the coordinator's shared launcher. Global options precede the command:

```text
scripts\expkm.cmd --store PRIVATE_STORE intake preview --file REQUEST_JSON
scripts\expkm.cmd --store PRIVATE_STORE intake confirm --proposal PROPOSAL --approve VERSION
scripts\expkm.cmd --store PRIVATE_STORE --intake VERSION record ...
```

The request file is data:

```json
{
  "request_id": "unique-current-request",
  "topic": "synthetic-topic",
  "goal": "Organize existing results and save the agreed outputs",
  "scope": "The explicitly selected input directory and all existing records in this topic",
  "requirements": ["Preserve originals", "No experiment execution"],
  "stages": ["record", "synthesize", "sync"],
  "source_roots": ["ABSOLUTE_USER_SELECTED_INPUT_ROOT"],
  "all_topic_records": true,
  "reports": ["markdown", "feishu"],
  "archives": "full",
  "max_archive_bytes": 500000000
}
```

Replace placeholders with actual private choices. Report-only/analysis-only does not authorize other steps; include only selected stages/outputs. An archive-free request uses archives=none and omits max_archive_bytes. MLflow capture additionally requires an explicit mlflow_runs list; origins remain allowlisted in private config. The local store is a required save location for private records/knowledge. No unrequested report platform is needed, but the mandatory template still is.

Current topic synthesis/export uses **all** topic records. If the user only selects a subset, don't widen scope: current core rejects that combination; select a separate explicitly authorized topic/store or explain the limitation. Record may accept a precisely bounded input root without including all history.

## When Codex recommends the template

First confirm the goal, source scope, constraints, stages and exact save locations with native cards. Create an intake definition with phase=template-recommendation and a unique recommendation request ID; intake preview/confirm binds this restricted authorization without adopting a template.

Use template-context --topic TOPIC --file SELECTED_SMALL_RESULT_FILE under that confirmed --intake. It only collects explicitly selected, bounded UTF-8 materials in the approved roots (1MB total default, at most 5MB); choose necessary representative summaries, not a scan of the entire input tree. The current authorized Agent uses that private context solely to recommend the report structure, configurable fields and result presentation. It does not create records, revise research conclusions, fetch model services or publish. The recommendation token cannot execute Record/Synthesize/Sync.

Present the recommended template, reasons, source mapping and any omissions to the user. Wait for actual confirmation, then use template preview/confirm and create a new final execution intake with a separate request ID and the confirmed template. Preferences can be reused, but neither recommendation nor template preview automatically authorizes execution. Close the recommendation intake. If the user changes scope or positions, revise those concrete choices before continuing.

## Execute, verify, close

Pass the exact --intake VERSION for each processing command. It binds topic, stages, roots, template, local store and requested output versions. Changed bindings, out-of-scope inputs/stages, closed sessions and missing confirmations stop before payload access. New report/archive plans seal the intake; apply cannot reuse a plan from another intake. The original concrete plan approval and remote write/upload flags are still required.

Keep the full-workflow deliverable manifest current. Verify every requested destination and separate archive receipt. Preserve completed work on faults; do not silently omit a stage. After delivery, close this request with intake close --version VERSION. A closed token cannot start a later request. New requests require new request IDs and confirmation; unchanged settings may be prefilled.

Doctor, existing-record hash verification and historical plan verification/workflow audit remain available for readback and recovery diagnosis; they don't grant a new write or processing scope. Trace exports, reindex, rollback, reconciliation and new processing use confirmed scope. No global automatic default session exists.

## Guarantee boundary

The CLI validates explicit confirmation parameters and bindings. It cannot prove a human saw cards, authenticate who clicked, force a host to invoke a skill, or constrain trusted direct Python library callers. Keep implicit skill invocation enabled, require the Agent to follow the card/confirmation procedure, and describe these limits honestly. Do not promise that a local JSON flag proves human authorization.
