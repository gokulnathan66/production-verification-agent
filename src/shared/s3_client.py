"""Shared S3 client for all agents"""
import boto3
import os
from typing import Optional
from botocore.exceptions import ClientError


class SharedS3Client:
    def __init__(self):
        self.bucket = os.getenv("S3_BUCKET_NAME")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        
        if not self.bucket:
            raise ValueError("S3_BUCKET_NAME must be set")
        
        self.s3 = boto3.client(
            's3',
            region_name=self.region,
        )
    
    def download_file(self, s3_key: str, local_path: str):
        """Download file from S3"""
        self.s3.download_file(self.bucket, s3_key, local_path)
    
    def upload_file(self, local_path: str, s3_key: str):
        """Upload file to S3"""
        self.s3.upload_file(local_path, self.bucket, s3_key)
    
    def get_presigned_url(self, s3_key: str, expiration=604800):
        """Generate presigned URL"""
        return self.s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': s3_key},
            ExpiresIn=expiration
        )
    
    def file_exists(self, s3_key: str) -> bool:
        """Check if file exists"""
        try:
            self.s3.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except ClientError:
            return False
