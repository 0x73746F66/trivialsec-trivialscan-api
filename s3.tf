resource "aws_s3_bucket" "trivialscan_bucket" {
  bucket = "trivialscan-results"
  tags = {
    Name        = "cost-center"
    Environment = "rapidapi"
  }
}

resource "aws_s3_bucket_acl" "trivialscan_results_acl" {
  bucket = aws_s3_bucket.trivialscan_bucket.id
  acl    = "private"
}
