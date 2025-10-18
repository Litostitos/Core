provider "aws" {
  region = "eu-north-1"
}

resource "aws_instance" "example" {
  ami           = "ami-04c08fd8aa14af291" # Replace with your preferred AMI
  instance_type = "t3.small"

  tags = {
    Name        = "My Atlantis V1.2 Test 5"
    Environment = "development1"
    Owner       = "Atlantis-Demo"
  }
}
