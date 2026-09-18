terraform { required_version=">= 1.6.0" }
variable "environment" { default="production" }
variable "project_name" { default="multimodal-sre" }
resource "local_file" "deployment_manifest" { filename="${path.module}/generated-${var.environment}.txt" content="${var.project_name} deployment target: ${var.environment}\n" }
output "environment" { value=var.environment }
output "project_name" { value=var.project_name }
