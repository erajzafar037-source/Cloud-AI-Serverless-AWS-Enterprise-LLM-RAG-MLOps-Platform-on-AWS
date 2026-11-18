import base64
import json

import lambdas.rag.handler as rag
import lambdas.ingestion.handler as ingestion


def test_rag_lambda_rejects_invalid_payload():
    response = rag.handler({"body": json.dumps({"query": "x", "top_k": 5})}, None)
    assert response["statusCode"] == 400
    assert "error" in json.loads(response["body"])


def test_rag_lambda_masks_provider_errors(monkeypatch):
    def fail(question, top_k):
        raise RuntimeError("sensitive internal detail")

    monkeypatch.setattr(rag, "_query_bedrock", fail)
    response = rag.handler(
        {"body": json.dumps({"query": "What is the policy?", "top_k": 4})}, None
    )
    assert response["statusCode"] == 502
    assert "sensitive internal detail" not in response["body"]


def test_ingestion_lambda_starts_bedrock_job(monkeypatch):
    class FakeClient:
        def start_ingestion_job(self, **kwargs):
            assert kwargs["knowledgeBaseId"] == "KB123"
            assert kwargs["dataSourceId"] == "DS12345678"
            return {"ingestionJob": {"ingestionJobId": "JOB123"}}

    monkeypatch.setattr(ingestion, "client", FakeClient())
    monkeypatch.setenv("BEDROCK_KB_ID", "KB123")
    monkeypatch.setenv("BEDROCK_DATA_SOURCE_ID", "DS12345678")
    monkeypatch.setenv("DOCUMENTS_BUCKET", "portfolio-docs")
    body = {
        "source": "aws.s3",
        "detail": {
            "bucket": {"name": "portfolio-docs"},
            "object": {"key": "policies/hr.pdf"},
        },
    }
    result = ingestion.handler({"Records": [{"body": json.dumps(body)}]}, None)
    assert result["count"] == 1
    assert result["started_jobs"] == ["JOB123"]


def test_ingestion_lambda_rejects_wrong_bucket(monkeypatch):
    monkeypatch.setenv("BEDROCK_KB_ID", "KB123")
    monkeypatch.setenv("BEDROCK_DATA_SOURCE_ID", "DS12345678")
    monkeypatch.setenv("DOCUMENTS_BUCKET", "portfolio-docs")
    body = {
        "source": "aws.s3",
        "detail": {"bucket": {"name": "wrong"}, "object": {"key": "doc.pdf"}},
    }
    try:
        ingestion.handler({"Records": [{"body": json.dumps(body)}]}, None)
    except ValueError as exc:
        assert "bucket" in str(exc)
    else:
        raise AssertionError("Expected mismatched bucket to be rejected")


def test_rag_lambda_decodes_api_gateway_base64_body(monkeypatch):
    def fake_query(question, top_k):
        assert question == "What is the policy?"
        assert top_k == 3
        return {
            "answer": "Use the published policy.",
            "citations": [],
            "cached": False,
            "provider": "amazon_bedrock_knowledge_base",
        }

    monkeypatch.setattr(rag, "_query_bedrock", fake_query)
    encoded = base64.b64encode(
        json.dumps({"query": "What is the policy?", "top_k": 3}).encode("utf-8")
    ).decode("ascii")
    response = rag.handler({"body": encoded, "isBase64Encoded": True}, None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["answer"] == "Use the published policy."


def test_rag_lambda_rejects_invalid_base64():
    response = rag.handler({"body": "%%%not-base64%%%", "isBase64Encoded": True}, None)
    assert response["statusCode"] == 400


def test_ingestion_lambda_rejects_non_object_event(monkeypatch):
    monkeypatch.setenv("BEDROCK_KB_ID", "KB123")
    monkeypatch.setenv("BEDROCK_DATA_SOURCE_ID", "DS12345678")
    monkeypatch.setenv("DOCUMENTS_BUCKET", "portfolio-docs")
    body = json.dumps(["not", "an", "event"])
    try:
        ingestion.handler({"Records": [{"body": body}]}, None)
    except ValueError as exc:
        assert "object" in str(exc)
    else:
        raise AssertionError("Expected a non-object event to be rejected")
