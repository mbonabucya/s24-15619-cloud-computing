variable "ami_ids" {
  type    = list(string)
  default = ["ami-04537cfe22bace769", "ami-0d196471a996e58d6", "ami-09400c18bd0c0f94f"] 
}

# region 
variable "region" {
  default = "us-east-1"
}

# instance type
variable "instance_type" {
  default = "t3.micro"
}

# # Update "project_tag" to match the tagging requirement of the ongoing project
# variable "project_tag" {

# }


