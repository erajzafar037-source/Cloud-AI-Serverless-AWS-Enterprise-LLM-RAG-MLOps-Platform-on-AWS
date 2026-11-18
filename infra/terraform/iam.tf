data "aws_caller_identity" "current" {}

locals {
  bedrock_knowledge_base_arn = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:knowledge-base/${var.bedrock_kb_id}"
  bedrock_model_resource     = var.bedrock_model_arn != "" ? var.bedrock_model_arn : "arn:aws:bedrock:${var.aws_region}::foundation-model/*"
}

resource "aws_iam_role_policy" "rag_bedrock" {
  name = "cloud-ai-rag-bedrock-query"
  role = aws_iam_role.rag_lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "KnowledgeBaseQuery"
        Effect   = "Allow"
        Action   = ["bedrock:RetrieveAndGenerate", "bedrock:Retrieve"]
        Resource = local.bedrock_knowledge_base_arn
      },
      {
        Sid      = "InvokeConfiguredModel"
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel"]
        Resource = local.bedrock_model_resource
      }
    ]
  })
}

resource "aws_iam_role_policy" "ingestion_bedrock" {
  name = "cloud-ai-ingestion-start-sync-and-consume"
  role = aws_iam_role.ingestion_lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "StartKnowledgeBaseIngestion"
        Effect   = "Allow"
        Action   = ["bedrock:StartIngestionJob"]
        Resource = local.bedrock_knowledge_base_arn
      },
      {
        Sid      = "ConsumeIngestionQueue"
        Effect   = "Allow"
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
        Resource = aws_sqs_queue.ingestion.arn
      }
    ]
  })
}
