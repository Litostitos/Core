provider "aws" {
  region = "eu-north-1b"
}

resource "aws_instance" "example" {
  ami           = "ami-04c08fd8aa14af291" # Replace with your preferred AMI
  instance_type = "t3.micro"

  tags = {
    Name        = "My Atlantis Test 1"
    Environment = "development1"
    Owner       = "Atlantis-Demo"
  }
}
