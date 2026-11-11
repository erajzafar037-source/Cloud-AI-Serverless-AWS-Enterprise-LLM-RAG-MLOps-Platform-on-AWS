from __future__ import annotations

import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)
region = os.getenv("BEDROCK_REGION", "eu-central-1")
client = boto3.client("bedrock-agent", region_name=region)


def handler(event, context):
    """Start a Bedrock Knowledge Base ingestion job for each S3 Object Created event.

    The Knowledge Base must already have an S3 data source configured for the
    same bucket. SQS retries failures and sends repeatedly failing events to
    the configured dead-letter queue.
    """
    knowledge_base_id = os.getenv("BEDROCK_KB_ID")
    data_source_id = os.getenv("BEDROCK_DATA_SOURCE_ID")
    expected_bucket = os.getenv("DOCUMENTS_BUCKET")
    if not knowledge_base_id or not data_source_id or not expected_bucket:
        raise RuntimeError(
            "BEDROCK_KB_ID, BEDROCK_DATA_SOURCE_ID and DOCUMENTS_BUCKET must be configured"
        )

    started = []
    for record in (event or {}).get("Records", []):
        body = record.get("body", "{}")
        message = json.loads(body) if isinstance(body, str) else body
        detail = message.get("detail", {}) if isinstance(message, dict) else {}
        bucket = detail.get("bucket", {}).get("name")
        object_key = detail.get("object", {}).get("key")
        if message.get("source") != "aws.s3" or not bucket or not object_key:
            raise ValueError("SQS message is not a valid EventBridge S3 Object Created event")
        if bucket != expected_bucket:
            raise ValueError("S3 event bucket does not match configured document bucket")

        response = client.start_ingestion_job(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id,
            description="Triggered by an S3 document-created event",
        )
        job = response.get("ingestionJob", {})
        job_id = job.get("ingestionJobId", "unknown")
        started.append(job_id)
        # Avoid logging document keys or content, which may contain sensitive names.
        logger.info("Started Bedrock ingestion job id=%s", job_id)

    return {"statusCode": 202, "started_jobs": started, "count": len(started)}
