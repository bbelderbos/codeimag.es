import os
from typing import Optional

import boto3

from .config import AWS_S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION

DEFAULT_BUCKET_PERMISSION = "public-read"


def upload_to_s3(
    filepath: str, bucket: Optional[str] = None, acl: Optional[str] = None
) -> str:
    s3_bucket = bucket or AWS_S3_BUCKET
    acl = acl or DEFAULT_BUCKET_PERMISSION

    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    s3 = session.resource("s3")
    response = s3.Bucket(s3_bucket).put_object(
        Key=os.path.basename(filepath), Body=open(filepath, "rb"), ACL=acl
    )

    s3_file_link = f"https://{s3_bucket}.s3.{AWS_REGION}.amazonaws.com/{response.key}"
    return s3_file_link
