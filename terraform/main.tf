provider "aws" {                                                                         
  region = "ap-southeast-2"
}

# Security group to allow Postgres access                                                
resource "aws_security_group" "rds_sg" {
    name        = "screenshots-db-sg"                                                      
    description = "Allow PostgreSQL inbound"
                                                                                            
    ingress {
        from_port   = 5432                                                                   
        to_port     = 5432
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
    }                                                                                      

    egress {                                                                               
        from_port   = 0
        to_port     = 0
        protocol    = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }                                                                                      
}
                                                                                        
# S3 bucket for screenshots
resource "aws_s3_bucket" "screenshots" {
    bucket = "screeenshots-bucket"
}

# RDS PostgreSQL instance                                                                
resource "aws_db_instance" "screenshots_db" {
    identifier              = "screenshots-db"                                             
    engine                  = "postgres"
    engine_version          = "16"
    instance_class          = "db.t3.micro"                                                
    allocated_storage       = 20
    db_name                 = "screenshots_db"                                             
    username                = "postgres"
    password                = var.db_password
    skip_final_snapshot     = true                                                         
    publicly_accessible     = true
    vpc_security_group_ids  = [aws_security_group.rds_sg.id]                               
}               
                                                                                        
variable "db_password" {
    description = "Password for the RDS database"                                          
    type        = string
    sensitive   = true
}
