data "aws_caller_identity" "current" {}

resource "aws_iam_role_policy" "bedrock_and_s3" {
  name = "cloud-ai-rag-bedrock-s3-ingestion"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [
      {
        Sid    = "RetrieveAndGenerate"
        Effect = "Allow"
        Action = [
          "bedrock:RetrieveAndGenerate",
          "bedrock:InvokeModel"
        ]
        Resource = "*"
      },
      {
        Sid      = "ScopedKnowledgeBaseRead"
        Effect   = "Allow"
        Action   = ["bedrock:Retrieve"]
        Resource = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:knowledge-base/${var.bedrock_kb_id}"
      },
      {
        Sid      = "StartKnowledgeBaseIngestion"
        Effect   = "Allow"
        Action   = ["bedrock:StartIngestionJob"]
        Resource = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:knowledge-base/${var.bedrock_kb_id}"
      },
      {
        Sid      = "ReadDocumentsBucket"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.documents.arn,
          "${aws_s3_bucket.documents.arn}/*"
        ]
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
