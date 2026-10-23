# Cloud AI Serverless AWS

> **Flagship portfolio project:** LLM/RAG + MLOps + AWS Cloud AI

A production-oriented reference architecture for serving enterprise RAG workloads on AWS. The project combines **Amazon Bedrock Knowledge Bases**, **LLM inference**, **Redis caching**, **event-driven document ingestion**, **ML evaluation with MLflow**, **Terraform Infrastructure as Code**, and **GitHub Actions CI**.

## What this demonstrates

- **LLM/RAG:** Bedrock Knowledge Base retrieval + generation, citations, prompt versioning, configurable provider.
- **MLOps:** reproducible evaluation set, retrieval/answer quality scoring, MLflow experiment logging, prompt/model registry pattern.
- **AWS Cloud AI:** API Gateway, Lambda, S3, EventBridge, SQS, CloudWatch, IAM, Terraform.
- **Production engineering:** Pydantic contracts, structured errors, Redis response caching, unit tests, benchmark script, CI.

## Architecture

```text
                         +----------------------+
                         |      End User        |
                         +----------+-----------+
                                    | HTTPS
                         +----------v-----------+
                         | API Gateway HTTP API |
                         +----------+-----------+
                                    |
                         +----------v-----------+
                         | RAG Lambda / FastAPI |
                         | orchestration layer  |
                         +-------+-------+-------+
                                 |       |
                         cache hit|       |cache miss
                                 |       v
                         +-------+---+ +---------------+
                         |   Redis   | | Amazon Bedrock|
                         | response  | | Knowledge Base|
                         |  cache    | | + LLM         |
                         +-----------+ +------+--------+
                                              |
                                   +----------v---------+
                                   | answer + citations |
                                   +--------------------+

  Document lifecycle
  +-------------+   object event   +------------+   queue   +--------------+
  | S3 documents| ----------------> | EventBridge| -------> | SQS ingestion|
  +-------------+                   +------------+           +------+-------+
                                                                   |
                                                           +-------v--------+
                                                           | Ingestion worker|
                                                           +----------------+

  MLOps
  eval dataset -> retrieval/answer scoring -> MLflow -> promotion decision -> versioned config
```

See [`docs/architecture.svg`](docs/architecture.svg) for a renderable diagram.

## Repository layout

```text
app/                 # local FastAPI + RAG + cache + evaluation
lambdas/             # AWS Lambda handlers
infra/terraform/     # AWS infrastructure as code
scripts/             # local evaluation + deployed benchmarking
models/              # versioned model/provider metadata
prompts/             # versioned prompts
data/                # small golden evaluation set
tests/               # unit tests
docs/                # architecture
.github/workflows/   # CI
```

## Local development

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then:

```bash
curl -X POST http://127.0.0.1:8000/query ^
  -H "content-type: application/json" ^
  -d "{\"query\":\"What is the incident response policy?\"}"
```

The application can run in `MOCK` mode without AWS credentials. Set `RAG_PROVIDER=bedrock_kb` for the live AWS path.

## AWS path

1. Upload enterprise documents to the Terraform-managed S3 bucket.
2. Connect that bucket to an **Amazon Bedrock Knowledge Base** and configure your embedding/vector store.
3. Set `BEDROCK_KB_ID` and `BEDROCK_MODEL_ARN` in the Lambda environment.
4. Apply Terraform from `infra/terraform/`.
5. Run `scripts/benchmark.py` against the deployed endpoint.

The Terraform layer intentionally keeps the Bedrock Knowledge Base identifier configurable rather than embedding account-specific managed state into source control.

## MLOps evaluation

```bash
python scripts/evaluate.py --dataset data/eval.jsonl
```

For experiment tracking:

```bash
export MLFLOW_TRACKING_URI=http://localhost:5000
python scripts/evaluate.py --dataset data/eval.jsonl --log-mlflow
```

The repository includes a small evaluation harness for **answer similarity** and a structure that can be expanded with RAGAS/DeepEval or an internal golden dataset.

## Important metric rule

Do **not** claim a latency number such as `<200 ms` just from the architecture. Run the benchmark against the deployed AWS environment and report the measured p50/p95 values.

## Security posture

- IAM roles are separated by workload.
- Secrets are loaded from environment variables / AWS secret stores rather than committed.
- API payloads are validated with Pydantic.
- The cache is optional and can be disabled.
- Terraform uses public-access blocking for the document bucket.
- CloudWatch logs are provisioned for operational visibility.

## Portfolio positioning

Using this as a single flagship project because it demonstrates a cohesive path from **enterprise documents -> retrieval -> LLM answer generation -> caching -> evaluation -> MLOps -> AWS infrastructure** rather than a collection of disconnected demos.

## License

MIT
