#!/usr/bin/env python3
"""
Step 2: Upload sample case files to a DigitalOcean Spaces bucket.

Requires boto3:  pip install boto3
Run from repo root:  source config.env && python3 scripts/02_upload_to_spaces.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    import boto3
    from botocore.config import Config
except ImportError:
    print("Install boto3 first:  pip install boto3")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = ROOT / "sample-case-files"


def main() -> None:
    access_key = os.environ.get("SPACES_ACCESS_KEY_ID")
    secret_key = os.environ.get("SPACES_SECRET_ACCESS_KEY")
    region = os.environ.get("SPACES_REGION", "tor1")
    bucket = os.environ.get("SPACES_BUCKET", "legaltech-casefiles-tutorial")
    prefix = os.environ.get("SPACES_PREFIX", "cases").strip("/")

    missing = [
        name
        for name, val in [
            ("SPACES_ACCESS_KEY_ID", access_key),
            ("SPACES_SECRET_ACCESS_KEY", secret_key),
        ]
        if not val or "your_" in val
    ]
    if missing:
        print(f"Set these in config.env: {', '.join(missing)}")
        sys.exit(1)

    if not SAMPLE_DIR.is_dir():
        print(f"Missing sample directory: {SAMPLE_DIR}")
        sys.exit(1)

    endpoint = f"https://{region}.digitaloceanspaces.com"
    session = boto3.session.Session()
    client = session.client(
        "s3",
        region_name=region,
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
    )

    # Create bucket if missing (many accounts already have a bucket with this name)
    try:
        client.head_bucket(Bucket=bucket)
        print(f"Bucket exists: {bucket}")
    except client.exceptions.ClientError:
        print(f"Creating bucket: {bucket} in {region}")
        client.create_bucket(Bucket=bucket)

    files = sorted(SAMPLE_DIR.glob("*.md"))
    if not files:
        print(f"No .md files found in {SAMPLE_DIR}")
        sys.exit(1)

    print(f"Uploading {len(files)} files to s3://{bucket}/{prefix}/")
    for path in files:
        key = f"{prefix}/{path.name}"
        client.upload_file(
            str(path),
            bucket,
            key,
            ExtraArgs={"ContentType": "text/markdown"},
        )
        print(f"  uploaded {key}")

    print("")
    print("Upload complete.")
    print(f"Bucket: {bucket}")
    print(f"Region: {region}")
    print(f"Prefix: {prefix}/")
    print("Next:  source config.env && python3 scripts/03_create_knowledge_base.py")


if __name__ == "__main__":
    main()
