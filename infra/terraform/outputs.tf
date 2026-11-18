output "api_url" {
  value = aws_apigatewayv2_api.http.api_endpoint
}

output "documents_bucket" {
  value = aws_s3_bucket.documents.bucket
}

output "ingestion_queue_url" {
  value = aws_sqs_queue.ingestion.url
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.api.id
}

output "cognito_app_client_id" {
  value = aws_cognito_user_pool_client.api.id
}

output "cognito_issuer" {
  value = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.api.id}"
}

output "cognito_hosted_ui_domain" {
  value = "https://${aws_cognito_user_pool_domain.api.domain}.auth.${var.aws_region}.amazoncognito.com"
}
