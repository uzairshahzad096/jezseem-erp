from functools import lru_cache

import boto3
from botocore.config import Config

from app.core.config import settings


@lru_cache
def get_r2_client():
    if not all((
        settings.R2_ACCOUNT_ID,
        settings.R2_ACCESS_KEY_ID,
        settings.R2_SECRET_ACCESS_KEY,
        settings.R2_BUCKET_NAME,
    )):
        raise RuntimeError("Cloudflare R2 is not configured")

    return boto3.client(
        "s3",
        endpoint_url=(
            f"https://{settings.R2_ACCOUNT_ID}"
            ".r2.cloudflarestorage.com"
        ),
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )