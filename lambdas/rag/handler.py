from __future__ import annotations

import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)
client = boto3.client(
    "bedrock-agent-runtime",
    region_name=os.getenv("BEDROCK_REGION", "eu-central-1"),
)


def _query_bedrock(question: str, top_k: int = 5) -> dict:
    kb_id = os.getenv("BEDROCK_KB_ID")
    model_arn = os.getenv("BEDROCK_MODEL_ARN")
    if not kb_id or not model_arn:
        raise RuntimeError("Bedrock Knowledge Base configuration is incomplete")

    response = client.retrieve_and_generate(
        input={"text": question},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": kb_id,
                "modelArn": model_arn,
                "retrievalConfiguration": {
                    "vectorSearchConfiguration": {"numberOfResults": top_k}
                },
            },
        },
    )

    citations = []
    for item in response.get("citations", []):
        for ref in item.get("retrievedReferences", []):
            location = ref.get("location", {})
            uri = (
                location.get("s3Location", {}).get("uri")
                or location.get("webLocation", {}).get("url")
                or "unknown"
            )
            citations.append({"source": uri, "score": ref.get("score")})

    return {
        "answer": response.get("output", {}).get("text", ""),
        "citations": citations,
        "cached": False,
        "provider": "amazon_bedrock_knowledge_base",
    }


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }


def handler(event, context):
    raw_body = (event or {}).get("body") or "{}"
    try:
        payload = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
    except (json.JSONDecodeError, TypeError):
        return _response(400, {"error": "Request body must be valid JSON."})

    if not isinstance(payload, dict):
        return _response(400, {"error": "Request body must be a JSON object."})
    question = payload.get("query")
    if not isinstance(question, str) or not 3 <= len(question.strip()) <= 4000:
        return _response(400, {"error": "query must contain between 3 and 4000 characters."})
    top_k = payload.get("top_k", 5)
    if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 20:
        return _response(400, {"error": "top_k must be an integer between 1 and 20."})

    try:
        return _response(200, _query_bedrock(question.strip(), top_k))
    except Exception:
        logger.exception("Bedrock query failed")
        return _response(502, {"error": "The knowledge-base query could not be completed."})
