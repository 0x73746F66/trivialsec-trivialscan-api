resource "aws_lambda_function" "trivialscan" {
  filename      = "${abspath(path.module)}/${local.source_file}"
  source_code_hash = filebase64sha256("${abspath(path.module)}/${local.source_file}")
  function_name = "trivialscan"
  role          = aws_iam_role.trivialscan_role.arn
  handler       = "handler.lambda_handler"
  runtime       = local.python_version
  timeout       = 900

  environment {
    variables = {
      APP_ENV = var.app_env
      APP_NAME = var.app_name
    }
  }
  lifecycle {
    create_before_destroy = true
  }
  depends_on    = [
    aws_iam_role_policy_attachment.policy_attach
  ]
}

resource "aws_lambda_function_url" "trivialscan" {
  function_name      = aws_lambda_function.trivialscan.arn
  authorization_type = "NONE"
}

output "trivialscan_arn" {
    value = aws_lambda_function.trivialscan.arn
}
output "function_url" {
    value = aws_lambda_function_url.trivialscan.function_url
}
