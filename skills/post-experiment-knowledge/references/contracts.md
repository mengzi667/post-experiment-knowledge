# Record and synthesis contracts

All examples are synthetic. Put real sidecars and drafts in the private store.

First complete [template selection](templates.md). Reuse the topic's confirmed version for later calls. No implicit default is selected.

Also confirm [the report save method and location](destinations.md). The prepared bundle includes both bindings. Evidence remains local and private even when the readable report is destined for Feishu.

## Record

`record --topic quality --source-id actual-attempt-01 --file result.json --root INPUT_DIRECTORY --metadata metadata.json`

An actual source ID identifies an execution, not a configuration. Re-importing that source with changed bytes creates a revision; independent repetitions require independent IDs. Existing files are read, never executed. Formats: JSON, JSONL, CSV, UTF-8 text (.txt / .log), Markdown and DocxXML. Unknown formats need an explicit conversion outside this tool. CSV cells stay strings and blanks are not zero.

Normalized metadata example:

```json
{
  "status": "completed",
  "comparison": {"dataset": "synthetic-data-v1", "split": "validation", "protocol": "paired-v1", "layer": "offline", "aggregation": "per-round-median"},
  "config": {"rank": 8},
  "environment": {"hardware": "synthetic-device"},
  "metrics": {"score": {"value": 0.8, "unit": "ratio", "direction": "max", "definition": "correct/n", "denominator": 30}}
}
```

Supported record states: completed, failed, aborted, partial, unknown. Do not translate an unverified Run status into completion. Missing fields remain missing. Differing protocol/data/layer/aggregation or metric definition prevents direct ranking; undeclared environment/config changes make the comparison conditional. `--changed-variable config.rank` explicitly identifies a controlled target variable; it does not erase other limitations.

## Knowledge

Prepare a context bundle with `synthesize --topic quality --prepare`. The current Agent writes a complete draft:

```json
{
  "claims": [{
    "id": "quality-baseline",
    "question": "Which baseline is supported?",
    "text": "Current evidence supports the baseline within this evaluation scope.",
    "status": "candidate",
    "evidence": [{"record_id": "RECORD_ID", "revision": "REVISION", "sha256": "EVIDENCE_SHA256"}]
  }],
  "decisions": [],
  "report_sections": {
    "overview": [{"type": "paragraph", "text": "Purpose and scope of these already-produced results."}]
  }
}
```

Use actual IDs from the private context bundle. Statuses: candidate, confirmed, disputed, superseded. `confirmed` means the submitting reviewer explicitly assigned that state; the tool cannot independently certify human approval.

Optional structured assertions use `record_id`, `revision`, a JSON `path` array, and `value`. They must cite a record in the claim's evidence and equal the stored value. An evidence `quote`, when given, must occur in the archived UTF-8 source. Programmatic validation is not semantic proof.

Subsequent updates require `--expected-version` from the current head. Changed text/status/questions, decisions, filled report sections or adopted template versions require a top-level `reason`. Keep previous claim IDs and mark them superseded when needed; omission is rejected. Drafts are complete snapshots: preserve previously filled report sections when updating. All previous snapshots remain traceable.

Thirty supporting experiments can attach to one claim. The main report shows the conclusion and evidence count, while the context and trace retain every record.
