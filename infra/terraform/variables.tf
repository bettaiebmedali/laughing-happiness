variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "project_name" {
  type    = string
  default = "python-devops-demo"
}

variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "subnet_cidr" {
  type    = string
  default = "10.20.1.0/24"
}

variable "admin_cidr" {
  description = "Your public IP in CIDR notation, e.g. 203.0.113.10/32"
  type        = string
}

variable "app_cidr" {
  description = "CIDR allowed to access the demo app; restrict this in real environments"
  type        = string
  default     = "0.0.0.0/0"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "key_name" {
  description = "Existing EC2 key pair name"
  type        = string
}

variable "ami_id" {
  description = "Valid AMI ID for the selected region and chosen OS"
  type        = string
}

variable "docker_image" {
  description = "Image URI to deploy"
  type        = string
  default     = "docker.io/library/python:3.12-slim"
}
