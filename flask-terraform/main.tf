provider "aws" {
  region = "eu-west-1"
}

resource "aws_instance" "example" {
  ami           = "ami-0c55b159cbfafe1f0" # Replace with your preferred AMI
  instance_type = "t2.micro"

  tags = {
    Name        = "First-Instance-Development-Test"
    Environment = "development1"
    Owner       = "Atlantis-Demo"
  }
}
