import uuid
import io
import boto3
from django.conf import settings

s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME,
)

def upload_bytes_to_s3(file_bytes: bytes, folder: str, content_type: str) -> str:
    """
    Upload raw bytes to S3 and return public URL
    (ACL NOT USED – bucket owner enforced)
    """
    filename = f"{uuid.uuid4()}.jpg"
    s3_key = f"{folder}/{filename}"

    file_obj = io.BytesIO(file_bytes)

    s3_client.upload_fileobj(
        file_obj,
        settings.AWS_STORAGE_BUCKET_NAME,
        s3_key,
        ExtraArgs={
            "ContentType": content_type
        }
    )

    return f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
