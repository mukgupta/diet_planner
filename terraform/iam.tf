data "aws_iam_policy_document" "lambda_assume_role_iam_policy_document" {
  statement {
    effect = "Allow"

    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "diet_s3_bucket_aws_iam_role_policy" {
  name = local.s3_bucket_policy_name
  role = aws_iam_role.lambda_iam_role.id

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::${local.s3_bucket_name}/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail",
        "ses:SendRawEmail"
      ],
      "Resource": "arn:aws:ses:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"
    }
  ]
}
EOF
}

resource "aws_iam_role" "lambda_iam_role" {
  name               = "${local.lambda_prefix}-iam-role"
  description        = "Role to assign permission to ${local.lambda_prefix} lambda function"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_iam_policy_document.json
}

# resource "aws_iam_role_policy" "lambda_iam_role_policy" {
#   name   = "${local.email_lambda_prefix}-iam-role-policy"
#   role   = aws_iam_role.email_lambda_iam_role.id
#   policy = data.aws_iam_policy_document.lambda_iam_policy_document.json
# }