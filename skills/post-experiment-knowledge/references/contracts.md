# Record and synthesis contracts

All examples are synthetic. Put real sidecars and drafts in the private store.

Every formal CLI request needs confirmed goal/scope/requirements, a mandatory [template](templates.md), an exact local result store and this request's [intake](intake.md). Requested reports/uploads additionally need their exact destinations. Low-level library independence does not bypass the Skill/CLI procedure.

## Record

`record --topic quality --source-id actual-attempt-01 --file result.json --root INPUT_DIRECTORY --metadata metadata.json`

An actual source ID identifies an execution, not a configuration. Re-importing that source with changed bytes creates a revision; independent repetitions require independent IDs. Existing files are read, never executed. Record defaults to auto mode: JSON, JSONL, CSV, UTF-8 text (.txt / .log), Markdown and DocxXML extract finite data when valid; all other selected regular files, including code/binary and invalid/non-finite structured inputs, retain their original bytes as raw-only evidence. Extraction descriptors include SHA-256, byte count, format, extraction state and reason; unavailable row counts remain null. No metrics are inferred from raw-only sources, and NaN/Infinity are never changed to zero/null in the original. Strict structured and explicit raw modes are available. Metadata sidecars always require finite JSON objects. CSV cells stay strings and blanks are not zero. Export privacy checks remain mandatory.

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

Subsequent updates require `--expected-version` from the current head. Changed text/status/questions, decisions, filled report sections or adopted template versions require a top-level `reason`. Keep previous claim IDs and mark them superseded when needed; omission is rejected. Pure synthesis omits report_sections and preserves previously filled report sections. Explicit report_sections requires a confirmed template; the example report_sections is optional. All previous snapshots remain traceable.

Thirty supporting experiments can attach to one claim. The main report shows the conclusion and evidence count, while the context and trace retain every record.
