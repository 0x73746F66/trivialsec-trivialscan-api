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

resource "aws_s3_bucket_public_access_block" "example" {
  bucket = aws_s3_bucket.trivialscan_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  restrict_public_buckets = true
  ignore_public_acls      = true
}
