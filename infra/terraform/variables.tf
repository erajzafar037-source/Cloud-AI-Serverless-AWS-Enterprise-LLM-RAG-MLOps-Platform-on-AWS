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

variable "cognito_domain_prefix" {
  type        = string
  default     = "cloud-ai-rag"
  description = "Prefix for the Cognito hosted authentication domain; the AWS account ID is appended."
  validation {
    condition     = can(regex("^[a-z0-9-]{3,40}$", var.cognito_domain_prefix))
    error_message = "Use 3-40 lowercase letters, digits or hyphens."
  }
}

variable "oauth_callback_urls" {
  type        = list(string)
  default     = ["http://localhost:3000/callback"]
  description = "Allowed OAuth callback URLs. Replace with the exact callback URL of your application."
}

variable "api_throttling_burst_limit" {
  type        = number
  default     = 10
  description = "HTTP API burst request limit."
}

variable "api_throttling_rate_limit" {
  type        = number
  default     = 5
  description = "HTTP API steady-state request limit per second."
}

variable "lambda_reserved_concurrency" {
  type        = number
  default     = 5
  description = "Concurrency cap for the query Lambda to limit accidental spend."
  validation {
    condition     = var.lambda_reserved_concurrency >= 1 && var.lambda_reserved_concurrency <= 50
    error_message = "lambda_reserved_concurrency must be between 1 and 50."
  }
}
