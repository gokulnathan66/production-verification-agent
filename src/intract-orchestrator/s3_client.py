"""
S3 Artifact Manager for A2A Multi-Agent System
Handles file uploads to AWS S3
"""
import boto3
from botocore.exceptions import ClientError
from typing import Optional
from datetime import datetime, timedelta
import os
import mimetypes


class S3ArtifactManager:
    """
    Manages artifact uploads to S3 with presigned URL generation
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        region: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None
    ):
        """
        Initialize S3 client with credentials from env or parameters
        """
        self.bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME")
        self.region = region or os.getenv("AWS_REGION", "us-east-1")

        # Initialize boto3 client
        self.s3_client = boto3.client(
            's3',
            region_name=self.region,
            aws_access_key_id=access_key or os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=secret_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        )

        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME must be set in environment or passed as parameter")

    async def upload_artifact(
        self,
        file_content: bytes,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Upload artifact to S3 with metadata

        Args:
            file_content: File bytes to upload
            filename: Original filename
            content_type: MIME type (auto-detected if not provided)
            metadata: Additional metadata to store with file

        Returns:
            dict with s3_key, s3_url, presigned_url, bucket
        """
        try:
            # Generate S3 key with timestamp prefix for organization
            timestamp = datetime.utcnow().strftime("%Y/%m/%d")
            s3_key = f"artifacts/{timestamp}/{filename}"

            # Auto-detect content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(filename)
                content_type = content_type or "application/octet-stream"

            # Prepare metadata
            upload_metadata = {
                "uploaded_at": datetime.utcnow().isoformat(),
                "original_filename": filename
            }
            if metadata:
                # Convert metadata values to strings (S3 requirement)
                upload_metadata.update({k: str(v) for k, v in metadata.items()})

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata=upload_metadata
            )

            # Generate presigned URL (7 day expiry)
            presigned_url = self.generate_presigned_url(s3_key, expiration=604800)

            # Construct S3 URL
            s3_url = f"s3://{self.bucket_name}/{s3_key}"

            return {
                "s3_key": s3_key,
                "s3_url": s3_url,
                "presigned_url": presigned_url,
                "bucket": self.bucket_name,
                "region": self.region,
                "content_type": content_type,
                "size": len(file_content)
            }

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            raise Exception(f"S3 upload failed [{error_code}]: {error_message}")

    def generate_presigned_url(self, s3_key: str, expiration: int = 604800) -> str:
        """
        Generate presigned URL for S3 object

        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default 7 days)

        Returns:
            Presigned URL string
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")

    async def delete_artifact(self, s3_key: str) -> bool:
        """
        Delete artifact from S3

        Args:
            s3_key: S3 object key

        Returns:
            True if deleted successfully
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except ClientError as e:
            raise Exception(f"Failed to delete artifact: {str(e)}")

    async def list_artifacts(self, prefix: str = "artifacts/") -> list:
        """
        List all artifacts in S3 bucket

        Args:
            prefix: S3 key prefix to filter

        Returns:
            List of artifact metadata
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            artifacts = []
            for obj in response.get('Contents', []):
                artifacts.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat(),
                    "presigned_url": self.generate_presigned_url(obj['Key'])
                })

            return artifacts
        except ClientError as e:
            raise Exception(f"Failed to list artifacts: {str(e)}")
