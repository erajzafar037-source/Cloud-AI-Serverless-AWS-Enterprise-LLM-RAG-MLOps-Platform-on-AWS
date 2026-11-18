# RAG demo consolidation decision

## Decision

Keep **Cloud AI Serverless AWS** as the single executable flagship. Do not grow
`-RAG-Application-with-AWS` into a second implementation.

The small repository contains only architecture prose. It contributes the
simple S3 -> Lambda -> Bedrock -> vector-search mental model, but no code,
infrastructure, tests, evaluation data, or deployment automation to port.

## Architecture mapping

| Small-demo concept | Flagship implementation |
|---|---|
| S3 document landing zone | `aws_s3_bucket.documents` in `infra/terraform/` |
| S3 event processing | S3 EventBridge notification -> EventBridge rule -> encrypted SQS queue -> ingestion Lambda |
| Bedrock embedding and chunking | Managed by the pre-created Bedrock Knowledge Base S3 data source; the Lambda starts an ingestion job rather than embedding bytes itself |
| OpenSearch vector storage | Managed vector store behind the Bedrock Knowledge Base; no separate OpenSearch domain is provisioned |
| Query endpoint | Cognito JWT-protected API Gateway HTTP API -> RAG Lambda -> Bedrock `RetrieveAndGenerate` |
| Operational recovery | SQS redrive policy and DLQ, CloudWatch log groups |
| Evaluation | `data/eval.jsonl`, `scripts/evaluate.py`, MLflow tracking and deployed benchmark |
| Infrastructure and tests | Terraform, unit tests and the opt-in deployed integration test |

## Why retain Bedrock Knowledge Bases

The flagship already implements managed retrieval, chunking/embedding orchestration,
citations, auth, queue-based ingestion, evaluation and Terraform. Replacing this
with a separately managed OpenSearch domain would add operational surface area
and create a second vector-store path without a demonstrated requirement.

Use direct OpenSearch only if a future requirement needs custom index mappings,
custom analyzers, hybrid-search tuning, independent vector lifecycle, or query
features unavailable through Knowledge Bases. That should be an explicit
architecture decision, not a second demo.

## Scope boundaries

- The Knowledge Base and its S3 data source remain prerequisites and are not
  created by this Terraform stack.
- The ingestion Lambda starts a managed sync; it does not download, parse,
  chunk or embed each object itself.
- The deployed integration test is opt-in, uploads one unique test object,
  waits for a completed ingestion job, queries the authenticated API, checks
  the answer and citations, then deletes all object versions for that key.
- Run integration tests only in a disposable AWS account. Bedrock inference,
  ingestion, Lambda, API Gateway, S3 and CloudWatch can incur charges.
