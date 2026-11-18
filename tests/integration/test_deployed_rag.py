"""Opt-in deployed smoke test for the S3 -> Bedrock KB -> API path.

Run with RUN_AWS_INTEGRATION=1 and the environment variables documented in
README.md. This test creates and removes one uniquely named S3 object.
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone

import boto3
import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.getenv("RUN_AWS_INTEGRATION") != "1",
    reason="set RUN_AWS_INTEGRATION=1 to run against a deployed AWS stack",
)
def test_s3_ingestion_then_authenticated_rag_query():
    region = os.getenv("AWS_REGION", "eu-central-1")
    bucket = os.environ["DOCUMENTS_BUCKET"]
    kb_id = os.environ["BEDROCK_KB_ID"]
    data_source_id = os.environ["BEDROCK_DATA_SOURCE_ID"]
    api_url = os.environ["RAG_API_URL"].rstrip("/")
    token = os.environ["RAG_BEARER_TOKEN"]

    key = f"integration-tests/{uuid.uuid4().hex}.txt"
    sentinel = f"Cobalt heron {uuid.uuid4().hex[:8]}"
    s3 = boto3.client("s3", region_name=region)
    bedrock = boto3.client("bedrock-agent", region_name=region)
    uploaded_at = datetime.now(timezone.utc)

    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=f"Integration verification phrase: {sentinel}.\n".encode(),
            ContentType="text/plain",
        )

        deadline = time.monotonic() + int(os.getenv("INGESTION_TIMEOUT_SECONDS", "1200"))
        completed = False
        while time.monotonic() < deadline:
            result = bedrock.list_ingestion_jobs(
                knowledgeBaseId=kb_id,
                dataSourceId=data_source_id,
                maxResults=10,
            )
            for job in result.get("ingestionJobSummaries", []):
                created = job.get("startedAt") or job.get("createdAt")
                if created and created >= uploaded_at and job.get("status") == "COMPLETE":
                    completed = True
                    break
                if created and created >= uploaded_at and job.get("status") == "FAILED":
                    pytest.fail(f"Bedrock ingestion failed: {job.get('failureReasons', [])}")
            if completed:
                break
            time.sleep(10)

        assert completed, "No completed Bedrock ingestion job observed before timeout"

        response = httpx.post(
            f"{api_url}/query",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": "What exact phrase follows 'Integration verification phrase' in the newly uploaded integration test document?", "top_k": 5},
            timeout=90,
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert sentinel in payload.get("answer", "")
        assert payload.get("citations"), "Expected at least one source citation"
    finally:
        # The bucket is versioned; remove every version and delete marker for
        # this unique key so the test does not leave billable object versions.
        versions = s3.list_object_versions(Bucket=bucket, Prefix=key)
        objects = [
            {"Key": item["Key"], "VersionId": item["VersionId"]}
            for item in versions.get("Versions", []) + versions.get("DeleteMarkers", [])
            if item["Key"] == key
        ]
        if objects:
            s3.delete_objects(Bucket=bucket, Delete={"Objects": objects, "Quiet": True})
