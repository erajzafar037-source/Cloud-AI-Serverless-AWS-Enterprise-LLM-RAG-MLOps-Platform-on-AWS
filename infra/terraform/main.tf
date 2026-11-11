terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "archive_file" "rag_lambda" {
  type        = "zip"
  source_dir  = "../../lambdas/rag"
  output_path = "${path.module}/rag_lambda.zip"
}

data "archive_file" "ingestion_lambda" {
  type        = "zip"
  source_dir  = "../../lambdas/ingestion"
  output_path = "${path.module}/ingestion_lambda.zip"
}

data "archive_file" "retraining_lambda" {
  type        = "zip"
  source_dir  = "../../lambdas/retraining"
  output_path = "${path.module}/retraining_lambda.zip"
}

resource "aws_s3_bucket" "documents" {
  bucket = var.documents_bucket_name
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket                  = aws_s3_bucket.documents.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_notification" "documents" {
  bucket      = aws_s3_bucket.documents.id
  eventbridge = true
}

resource "aws_cloudwatch_event_rule" "document_created" {
  name = "cloud-ai-document-created"
  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = { name = [aws_s3_bucket.documents.bucket] }
    }
  })
}

resource "aws_cloudwatch_event_target" "document_queue" {
  rule = aws_cloudwatch_event_rule.document_created.name
  arn  = aws_sqs_queue.ingestion.arn
}

resource "aws_sqs_queue_policy" "eventbridge" {
  queue_url = aws_sqs_queue.ingestion.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.ingestion.arn
      Condition = {
        ArnEquals = { "aws:SourceArn" = aws_cloudwatch_event_rule.document_created.arn }
      }
    }]
  })
}

resource "aws_sqs_queue" "ingestion_dlq" {
  name = "cloud-ai-ingestion-dlq"
}

resource "aws_sqs_queue" "ingestion" {
  name                       = "cloud-ai-ingestion"
  visibility_timeout_seconds = 180
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ingestion_dlq.arn
    maxReceiveCount     = 5
  })
}

resource "aws_iam_role" "lambda_role" {
  name = "cloud-ai-serverless-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "rag" {
  function_name    = "cloud-ai-rag"
  role             = aws_iam_role.lambda_role.arn
  runtime          = "python3.12"
  handler          = "handler.handler"
  filename         = data.archive_file.rag_lambda.output_path
  source_code_hash = data.archive_file.rag_lambda.output_base64sha256
  timeout          = 30
  memory_size      = 1024
  environment {
    variables = {
      RAG_PROVIDER      = var.rag_provider
      BEDROCK_REGION    = var.aws_region
      BEDROCK_KB_ID     = var.bedrock_kb_id
      BEDROCK_MODEL_ARN = var.bedrock_model_arn
      CACHE_ENABLED     = "false"
      PROMPT_VERSION    = "v1"
    }
  }
}

resource "aws_lambda_function" "ingestion" {
  function_name    = "cloud-ai-ingestion"
  role             = aws_iam_role.lambda_role.arn
  runtime          = "python3.12"
  handler          = "handler.handler"
  filename         = data.archive_file.ingestion_lambda.output_path
  source_code_hash = data.archive_file.ingestion_lambda.output_base64sha256
  timeout          = 30
  memory_size      = 512
  environment {
    variables = {
      BEDROCK_REGION         = var.aws_region
      BEDROCK_KB_ID          = var.bedrock_kb_id
      BEDROCK_DATA_SOURCE_ID = var.bedrock_data_source_id
      DOCUMENTS_BUCKET       = aws_s3_bucket.documents.bucket
    }
  }
}

resource "aws_lambda_function" "retraining" {
  function_name    = "cloud-ai-mlops"
  role             = aws_iam_role.lambda_role.arn
  runtime          = "python3.12"
  handler          = "handler.handler"
  filename         = data.archive_file.retraining_lambda.output_path
  source_code_hash = data.archive_file.retraining_lambda.output_base64sha256
  timeout          = 60
  memory_size      = 512
}

resource "aws_lambda_event_source_mapping" "ingestion" {
  event_source_arn = aws_sqs_queue.ingestion.arn
  function_name    = aws_lambda_function.ingestion.arn
  batch_size       = 1
}

resource "aws_apigatewayv2_api" "http" {
  name          = "cloud-ai-rag-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "rag" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.rag.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "query" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "POST /query"
  target    = "integrations/${aws_apigatewayv2_integration.rag.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "api" {
  statement_id  = "AllowApiGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.rag.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

resource "aws_cloudwatch_log_group" "rag" {
  name              = "/aws/lambda/${aws_lambda_function.rag.function_name}"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "ingestion" {
  name              = "/aws/lambda/${aws_lambda_function.ingestion.function_name}"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "mlops" {
  name              = "/aws/lambda/${aws_lambda_function.retraining.function_name}"
  retention_in_days = 14
}
