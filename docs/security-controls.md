# Security Controls and Deployment Checklist

## Trust boundaries

- Local FastAPI mock mode is intended for localhost development only and does not authenticate callers.
- The deployed API Gateway route is JWT protected by an Amazon Cognito user-pool authorizer.
- The query Lambda has a separate role for Bedrock Knowledge Base retrieval/generation and model invocation. It has no S3 object-read or SQS-consumer permissions.
- The ingestion Lambda has a separate role for starting Knowledge Base ingestion jobs and consuming only the ingestion queue. The Bedrock Knowledge Base data-source service role, not this Lambda, reads document objects from S3.
- The documents bucket has public-access blocking, AES-256 server-side encryption, versioning and a policy denying non-TLS requests.
- SQS queues use managed encryption, with a dead-letter queue configured.
- API Gateway throttling and a reserved query-Lambda concurrency cap limit accidental traffic spikes.

## Cognito setup

Terraform creates a user pool, public app client and hosted UI domain. The app client uses OAuth authorization-code flow without a client secret, so browser/mobile applications must use PKCE. Set oauth_callback_urls to exact registered callback URLs. Never embed AWS credentials or a Cognito app-client secret in a public client.

The API expects a bearer JWT issued by the configured user pool and intended for the app client. API Gateway performs validation; locally decoding a JWT is not authentication.

## Deployment checklist

1. Provide a globally unique bucket name, Bedrock Knowledge Base ID, data-source ID, model ARN and Cognito callback settings.
2. Run terraform fmt -check, terraform init -backend=false and terraform validate.
3. Review terraform plan; inspect IAM actions and exact resource ARNs for your region/account.
4. Apply only in a disposable/test AWS account with a budget alert.
5. Create or register a test Cognito user through the configured user-pool workflow.
6. Verify missing, expired, wrong-issuer and wrong-audience tokens are rejected by API Gateway.
7. Verify the query role cannot read S3 objects and the ingestion role cannot invoke foundation models.
8. Upload a non-sensitive test document to the configured Knowledge Base S3 source; verify EventBridge → SQS → Lambda → StartIngestionJob and inspect the DLQ on intentional failures.
9. Run the query/evaluation benchmark and record measured p50/p95 latency, token usage, cost and answer/citation quality. Do not publish target numbers as measured results.
10. Destroy resources after testing and inspect the account for retained buckets, logs, snapshots or other billable resources.

## Important limitations

- The Knowledge Base and its S3 data source are existing prerequisites, not provisioned by this Terraform stack.
- The MLOps/retraining Lambda remains an event-trigger scaffold; it is not a training pipeline or model promotion service.
- Cognito configuration is a starting point. Production applications still need account lifecycle policy, MFA policy, abuse protection, audit requirements and a security review.
- This reference is not a multi-tenant document authorization system. Do not use it for confidential or regulated content without document-level authorization, tenant isolation, audit logging and formal review.
