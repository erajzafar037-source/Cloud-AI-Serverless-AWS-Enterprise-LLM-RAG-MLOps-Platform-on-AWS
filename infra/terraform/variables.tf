variable "aws_region" {
  type    = string
  default = "eu-central-1"
}

variable "documents_bucket_name" {
  type        = string
  description = "Globally unique S3 bucket name for enterprise documents."
}

variable "rag_provider" {
  type    = string
  default = "bedrock_kb"
}

variable "bedrock_kb_id" {
  type        = string
  default     = ""
  description = "Existing Amazon Bedrock Knowledge Base ID."
}

variable "bedrock_data_source_id" {
  type        = string
  default     = ""
  description = "Existing S3 data source ID attached to the Knowledge Base."
}

variable "bedrock_model_arn" {
  type        = string
  default     = ""
  description = "Existing Bedrock foundation model ARN configured for the Knowledge Base."
}
