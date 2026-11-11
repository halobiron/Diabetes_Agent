variable "aws_region" {
  description = "AWS region for the App Runner deployment."
  type        = string
  default     = "us-west-2"
}

variable "project_name" {
  description = "Name used for AWS resources."
  type        = string
  default     = "healthcare-ai-risk"
}

variable "ecr_repository_name" {
  description = "ECR repository name for the API image."
  type        = string
  default     = "healthcare-ai-risk-api"
}

variable "web_ecr_repository_name" {
  description = "ECR repository name for the Next.js web image."
  type        = string
  default     = "healthcare-ai-risk-web"
}

variable "api_image_identifier" {
  description = "Full ECR image URI with tag. Defaults to this stack's ECR repo latest tag."
  type        = string
  default     = ""
}

variable "web_image_identifier" {
  description = "Full ECR web image URI with tag. Defaults to this stack's web ECR repo latest tag."
  type        = string
  default     = ""
}

variable "auto_deployments_enabled" {
  description = "Whether App Runner automatically deploys new ECR image pushes."
  type        = bool
  default     = true
}

variable "api_token" {
  description = "Bearer token required when REQUIRE_API_TOKEN is true."
  type        = string
  sensitive   = true
  default     = ""
}

variable "require_api_token" {
  description = "Require Authorization: Bearer API_TOKEN for prediction endpoints."
  type        = bool
  default     = true
}

variable "openai_api_key" {
  description = "Optional OpenAI API key for generated explanations and recommendations."
  type        = string
  sensitive   = true
  default     = ""
}

variable "api_cpu" {
  description = "API instance vCPU. The bge-m3 embedding model runs on CPU here (no GPU on App Runner)."
  type        = string
  default     = "2 vCPU"
}

variable "api_memory" {
  description = "API instance memory. bge-m3 needs ~3.4 GB peak, so 2 GB is not enough."
  type        = string
  default     = "4 GB"
}

variable "force_delete_ecr" {
  description = "Allow Terraform to delete the ECR repository even if it contains images."
  type        = bool
  default     = false
}
