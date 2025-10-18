provider "aws" {
  region = "eu-north-1"
}

resource "aws_instance" "example" {
  ami           = "ami-04c08fd8aa14af291" # Replace with your preferred AMI
  instance_type = "t3.micro"

  tags = {
    Name        = "My Atlantis V1.2 Test 3"
    Environment = "development1"
    Owner       = "Atlantis-Demo"
  }
}
