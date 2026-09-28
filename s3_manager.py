import sys
import boto3
import os
from botocore.exceptions import ClientError

s3 = boto3.client("s3")
REGION = boto3.session.Session().region_name or "us-east-1"


def create_bucket():
    name = input("New bucket name: ").strip()

    try:
        if REGION == "us-east-1":
            s3.create_bucket(Bucket=name)
        else:
            s3.create_bucket(
                Bucket=name,
                CreateBucketConfiguration={
                    "LocationConstraint": REGION
                },
            )

        print(f"Created bucket '{name}'")

    except ClientError as e:
        code = e.response["Error"]["Code"]

        if code == "BucketAlreadyExists":
            print("That name is taken by another AWS account.")

        elif code == "BucketAlreadyOwnedByYou":
            print("You already own that bucket.")

        else:
            print(f"[AWS ERROR] {code}")


def list_buckets():
    try:
        response = s3.list_buckets()

        if not response["Buckets"]:
            print("No buckets found.")
            return

        for bucket in response["Buckets"]:
            created = bucket["CreationDate"].strftime("%Y-%m-%d %H:%M")
            print(f"{bucket['Name']:<45} created {created}")

    except ClientError as e:
        code = e.response["Error"]["Code"]
        print(f"[AWS ERROR] {code}")



def upload_file():
    path = input("Local file path: ").strip()
    bucket = input("Target bucket: ").strip()

    if not os.path.isfile(path):
        print(f"File not found: {path}")
        return

    default_key = os.path.basename(path)
    key = input(f"Object key [{default_key}]: ").strip() or default_key

    s3.upload_file(path, bucket, key)
    print(f"Uploaded {path} -> s3://{bucket}/{key}")

def list_objects():
    bucket = input("Bucket name: ").strip()
    prefix = input("Prefix filter (Enter for all): ").strip()

    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(
        Bucket=bucket,
        Prefix=prefix
    )

    total_objects = 0
    total_bytes = 0

    for page in pages:
        for obj in page.get("Contents", []):
            total_objects += 1
            total_bytes += obj["Size"]

            print(
                f"{obj['Key']:<50} "
                f"{obj['Size']:>12,}  "
                f"{obj['LastModified']:%Y-%m-%d %H:%M}"
            )

    if total_objects == 0:
        print("(bucket is empty)")

    print(
        f"\n{total_objects} object(s), "
        f"{total_bytes / 1024 / 1024:.2f} MB"
    )


def download_file():
    bucket = input("Bucket name: ").strip()
    key = input("Object key: ").strip()
    dest = input("Save as: ").strip() or os.path.basename(key)

    try:
        s3.download_file(bucket, key, dest)
        print(f"Downloaded -> {dest}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            print("That object does not exist.")
        else:
            raise


def generate_presigned_url():
    bucket = input("Bucket name: ").strip()
    key = input("Object key: ").strip()

    raw = input("Valid for how many seconds? [3600]: ").strip()
    expires = int(raw) if raw.isdigit() else 3600

    url = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": bucket,
            "Key": key
        },
        ExpiresIn=expires,
    )

    print(f"\nValid for {expires} seconds:")
    print(url)


def delete_bucket():
    bucket = input("Bucket name: ").strip()

    confirmation = input(
        f"Type the bucket name '{bucket}' to confirm deletion: "
    ).strip()

    if confirmation != bucket:
        print("Deletion cancelled.")
        return

    try:
        s3.delete_bucket(Bucket=bucket)
        print(f"Deleted bucket '{bucket}'")

    except ClientError as e:
        code = e.response["Error"]["Code"]

        if code == "BucketNotEmpty":
            print("Bucket is not empty. Delete all objects first.")
        else:
            print(f"[AWS ERROR] {code}")


def backup_folder():
    folder = input("Local folder: ").strip()
    bucket = input("Target bucket: ").strip()
    prefix = input("S3 prefix (Enter for none): ").strip()

    if not os.path.isdir(folder):
        print(f"Folder not found: {folder}")
        return

    success = 0
    failures = 0

    for root, dirs, files in os.walk(folder):
        for filename in files:
            local_path = os.path.join(root, filename)

            relative = os.path.relpath(local_path, folder)
            key = prefix + relative.replace(os.sep, "/")

            try:
                s3.upload_file(local_path, bucket, key)
                print(f"Uploaded: {local_path} -> s3://{bucket}/{key}")
                success += 1

            except ClientError as e:
                code = e.response["Error"]["Code"]
                print(f"[AWS ERROR] {code}: {local_path}")
                failures += 1

    print(f"\nBackup complete: {success} succeeded, {failures} failed")


MENU = """
=============================
       S3 MANAGER
=============================
1. Create bucket
2. List buckets
3. Upload file
4. List objects
5. Download file
6. Generate presigned URL
7. Delete bucket
8. Backup folder
0. Exit
=============================
"""


ACTIONS = {
    "1": create_bucket,
    "2": list_buckets,
    "3": upload_file,
    "4": list_objects,
    "5": download_file,
    "6": generate_presigned_url,
    "7": delete_bucket,
    "8": backup_folder,
}


def main():
    while True:
        print(MENU)
        choice = input("Choose an option: ").strip()

        if choice == "0":
            print("Goodbye!")
            sys.exit(0)

        action = ACTIONS.get(choice)

        if action:
            action()
        else:
            print("Invalid option.")


if __name__ == "__main__":
    main()