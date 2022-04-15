resource "aws_ssm_parameter" "rapidapi_token" {
  name        = "/${var.app_env}/Deploy/${var.app_name}/rapidapi_token"
  type        = "SecureString"
  value       = var.rapidapi_token
  tags = {
    cost-center = "rapidapi"
  }
  overwrite   = true
}
resource "aws_ssm_parameter" "trivialscan_url" {
  name        = "/${var.app_env}/Deploy/${var.app_name}/trivialscan_url"
  type        = "String"
  value       = aws_lambda_function_url.trivialscan.function_url
  tags = {
    cost-center = "rapidapi"
  }
  overwrite   = true
}
output "rapidapi_token_parameter_name" {
    value = aws_ssm_parameter.rapidapi_token.name
}
output "rapidapi_token" {
    value = aws_ssm_parameter.rapidapi_token.value
    sensitive = true
}
