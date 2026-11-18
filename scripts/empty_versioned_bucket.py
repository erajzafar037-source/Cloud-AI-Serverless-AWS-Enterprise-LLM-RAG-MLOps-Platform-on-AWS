"""Permanently empty a versioned S3 bucket after explicit confirmation."""
from __future__ import annotations

import argparse
import os

import boto3


def empty_bucket(bucket: str, region: str) -> int:
    client = boto3.client("s3", region_name=region)
    paginator = client.get_paginator("list_object_versions")
    deleted = 0
    for page in paginator.paginate(Bucket=bucket):
        objects = [
            {"Key": item["Key"], "VersionId": item["VersionId"]}
            for item in page.get("Versions", []) + page.get("DeleteMarkers", [])
        ]
        for offset in range(0, len(objects), 1000):
            batch = objects[offset : offset + 1000]
            if batch:
                response = client.delete_objects(
                    Bucket=bucket,
                    Delete={"Objects": batch, "Quiet": True},
                )
                errors = response.get("Errors", [])
                if errors:
                    raise RuntimeError(f"Failed to delete S3 object versions: {errors[:5]}")
                deleted += len(batch)
    return deleted


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Permanently delete every object version and delete marker in a bucket."
    )
    parser.add_argument("--bucket", default=os.getenv("DOCUMENTS_BUCKET"))
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "eu-central-1"))
    parser.add_argument(
        "--confirm-bucket",
        required=True,
        help="Must exactly match --bucket; this operation is irreversible.",
    )
    args = parser.parse_args()
    if not args.bucket or args.confirm_bucket != args.bucket:
        parser.error("--confirm-bucket must exactly match the non-empty bucket name")
    count = empty_bucket(args.bucket, args.region)
    print(f"Deleted {count} object versions/delete markers from {args.bucket}")


if __name__ == "__main__":
    main()
