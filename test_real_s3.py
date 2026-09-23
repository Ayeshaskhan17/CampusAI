import os
import boto3
from dotenv import load_dotenv

load_dotenv()

region = os.getenv("AWS_REGION")
bucket = os.getenv("S3_BUCKET_NAME")

print("Region:", region)
print("Bucket:", bucket)

s3 = boto3.client("s3", region_name=region)

try:
    response = s3.list_objects_v2(
        Bucket=bucket,
        MaxKeys=5
    )

    print("✅ AWS S3 connection successful!")
    print("Bucket:", bucket)
    print("Region:", region)
    print("Objects found:", response.get("KeyCount", 0))

except Exception as e:
    print("❌ S3 connection failed")
    print(type(e).__name__)
    print(e)