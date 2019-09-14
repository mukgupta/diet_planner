# Todos
# Ses via terraform
# Setup cron
# Use previous week files as input
# Code structuring for local iterations

locals {
  lambda_prefix = "diet-planner"
  deps_layer_name = "${local.lambda_prefix}-python-requirements"
  s3_bucket_name = "${local.lambda_prefix}-s3-bucket"
  s3_bucket_policy_name = "${local.s3_bucket_name}-iam-policy"
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_s3_bucket" "diet_s3_bucket" {
  bucket = local.s3_bucket_name
  acl    = "private"

  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        },
        "Action": [
          "s3:PutObject",
          "s3:GetObject"
        ],
        "Resource": "arn:aws:s3:::${local.s3_bucket_name}/*"
    }
  ]
}
POLICY
}

resource "null_resource" "pip" {
  triggers = {
    requirements = "${base64sha256(file("requirements.txt"))}"
  }

  provisioner "local-exec" {
    command = <<EOF
    docker run --rm \
    -v ${abspath(path.root)}/:/src \
    lambci/lambda:build-python3.7 \
    bash -c 'pip install -r /src/requirements.txt -t /src/lambda/layers/deps/python/lib/python3.7/site-packages/'
    EOF
  }
}

data "archive_file" "lambda_layer_deps_zip" {
  type        = "zip"
  source_dir  = "${path.root}/lambda/layers/deps/"
  output_path = "${path.root}/lambda/lambda-deps.zip"

  depends_on = ["null_resource.pip"]
}

resource "aws_lambda_layer_version" "lambda_layer" {
  filename   = data.archive_file.lambda_layer_deps_zip.output_path
  layer_name = local.deps_layer_name

  compatible_runtimes = ["python3.6", "python3.7"]
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.root}/lambda/src"
  output_path = "${path.root}/lambda/lambda.zip"
}

resource "aws_lambda_function" "lambda_function" {
  filename = data.archive_file.lambda_zip.output_path

  function_name = "${local.lambda_prefix}-function"

  role             = aws_iam_role.lambda_iam_role.arn
  handler          = "main.handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = "python3.7"
  timeout          = 30
  memory_size      = 256

  layers  = [aws_lambda_layer_version.lambda_layer.arn]

  lifecycle {
    ignore_changes = [
      filename,
      last_modified,
    ]
  }
}

resource "aws_cloudwatch_event_rule" "cloudwatch_event_rule" {
    name = "every-friday"
    description = "Fires every friday"
    schedule_expression = "cron(0 10 ? * 6 *)"
}

resource "aws_cloudwatch_event_target" "cloudwatch_event_target" {
    rule = "${aws_cloudwatch_event_rule.cloudwatch_event_rule.name}"
    target_id = "diet_planner_lambda"
    arn = "${aws_lambda_function.lambda_function.arn}"
}

resource "aws_lambda_permission" "lambda_permission" {
    statement_id = "AllowExecutionFromCloudWatch"
    action = "lambda:InvokeFunction"
    function_name = "${aws_lambda_function.lambda_function.function_name}"
    principal = "events.amazonaws.com"
    source_arn = "${aws_cloudwatch_event_rule.cloudwatch_event_rule.arn}"
}