import os
import sys
import mimetypes
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config


ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
ACCESS_KEY = os.environ.get("R2_ACCESS_KEY_ID")
SECRET_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
BUCKET = os.environ.get("R2_BUCKET_NAME", "jezseem-erp-media")

UPLOAD_ROOT = Path(__file__).resolve().parents[1] / "uploads"

if not all([ACCOUNT_ID, ACCESS_KEY, SECRET_KEY]):
    sys.exit("Missing R2 environment variables.")

client = boto3.client(
    "s3",
    endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    region_name="auto",
    config=Config(signature_version="s3v4"),
)

uploaded = 0
skipped = 0
failed = 0

for subdir in ("items", "employees"):
    folder = UPLOAD_ROOT / subdir

    if not folder.exists():
        print(f"Skipping missing directory: {folder}")
        continue

    for file in sorted(folder.rglob("*")):
        if not file.is_file():
            continue

        if file.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue

        key = file.relative_to(UPLOAD_ROOT).as_posix()

        try:
            try:
                existing = client.head_object(Bucket=BUCKET, Key=key)

                if existing["ContentLength"] == file.stat().st_size:
                    print(f"SKIP: {key}")
                    skipped += 1
                    continue

                print(f"SIZE MISMATCH (not overwriting): {key}")
                failed += 1
                continue

            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")

                if code not in ("404", "NoSuchKey", "NotFound"):
                    raise

            content_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"

            client.upload_file(
                str(file),
                BUCKET,
                key,
                ExtraArgs={"ContentType": content_type},
            )

            print(f"UPLOADED: {key}")
            uploaded += 1

        except Exception as exc:
            print(f"FAILED: {key} ({type(exc).__name__})")
            failed += 1

print()
print("Migration completed")
print(f"Uploaded: {uploaded}")
print(f"Skipped:  {skipped}")
print(f"Failed:   {failed}")

if failed:
    sys.exit(1)