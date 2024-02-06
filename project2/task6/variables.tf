variable "frontdoor_name" {
  description = "Name for the Front Door instance"
  default     = ""
}

variable "resource_group_name" {
  description = "Resource group name in Azure"
  default     = ""
}

variable "gcp_ingress_external_ip" {
  description = "Ingress external IP in GCP"
  default     = ""
}

variable "azure_ingress_external_ip" {
  description = "Ingress external IP in Azure"
  default     = ""
}
