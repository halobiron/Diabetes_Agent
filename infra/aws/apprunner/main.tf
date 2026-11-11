provider "aws" {
  region = var.aws_region
}

locals {
  api_image_identifier = var.api_image_identifier != "" ? var.api_image_identifier : "${aws_ecr_repository.api.repository_url}:latest"
  web_image_identifier = var.web_image_identifier != "" ? var.web_image_identifier : "${aws_ecr_repository.web.repository_url}:latest"
  tags = {
    Project   = var.project_name
    ManagedBy = "terraform"
  }
}

resource "aws_ecr_repository" "api" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE"
  force_delete         = var.force_delete_ecr

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.tags
}

resource "aws_ecr_repository" "web" {
  name                 = var.web_ecr_repository_name
  image_tag_mutability = "MUTABLE"
  force_delete         = var.force_delete_ecr

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.tags
}

data "aws_iam_policy_document" "apprunner_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["build.apprunner.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "apprunner_ecr_access" {
  name               = "${var.project_name}-apprunner-ecr-access"
  assume_role_policy = data.aws_iam_policy_document.apprunner_assume_role.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr_access" {
  role       = aws_iam_role.apprunner_ecr_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

resource "aws_apprunner_service" "api" {
  service_name = "${var.project_name}-api"

  instance_configuration {
    cpu    = var.api_cpu
    memory = var.api_memory
  }

  source_configuration {
    auto_deployments_enabled = var.auto_deployments_enabled

    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access.arn
    }

    image_repository {
      image_identifier      = local.api_image_identifier
      image_repository_type = "ECR"

      image_configuration {
        port = "8000"

        runtime_environment_variables = {
          API_TOKEN           = var.api_token
          LOG_DIR             = "/app/logs"
          MODEL_ARTIFACT_PATH = "/app/artifacts/risk_model.joblib"
          OPENAI_API_KEY      = var.openai_api_key
          REQUIRE_API_TOKEN   = tostring(var.require_api_token)
        }
      }
    }
  }

  health_check_configuration {
    healthy_threshold   = 1
    interval            = 10
    path                = "/health"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 5
  }

  tags = local.tags
}

resource "aws_apprunner_service" "web" {
  service_name = "${var.project_name}-web"

  source_configuration {
    auto_deployments_enabled = var.auto_deployments_enabled

    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access.arn
    }

    image_repository {
      image_identifier      = local.web_image_identifier
      image_repository_type = "ECR"

      image_configuration {
        port = "3000"

        runtime_environment_variables = {
          API_BASE_URL = "https://${aws_apprunner_service.api.service_url}"
          API_TOKEN    = var.api_token
        }
      }
    }
  }

  health_check_configuration {
    healthy_threshold   = 1
    interval            = 10
    path                = "/"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 5
  }

  tags = local.tags
}
