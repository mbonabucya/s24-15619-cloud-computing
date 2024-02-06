terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  required_version = ">= 1.5.0"
}

provider "aws" {
  region = var.region
}



resource "aws_security_group" "vm_scaling_ami_sg" {
  # inbound internet access
  # allowed: only port 22, 80 are open
  # you are NOT allowed to open all the ports to the public
  ingress {
    from_port = 22
    to_port   = 22
    protocol  = "tcp"

    cidr_blocks = [
      "0.0.0.0/0"
    ]
  }

  ingress {
    from_port = 80
    to_port   = 80
    protocol  = "tcp"

    cidr_blocks = [
      "0.0.0.0/0"
    ]
  }

  # outbound internet access
  # allowed: any egress traffic to anywhere
  egress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"

    cidr_blocks = [
      "0.0.0.0/0"
    ]
  }
}

resource "aws_instance" "starter_code" {
  ami = "ami-04537cfe22bace769"
  instance_type = var.instance_type
  vpc_security_group_ids = [aws_security_group.vm_scaling_ami_sg.id]

  tags = {
    Project = "vm-scaling"
  } 

  key_name = "mykeypair"
}
