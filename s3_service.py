"""
s3_service.py - Amazon S3 Document Storage Service for CampusAI.
Handles notice documents, PDFs, PPTs, DOCs, and image attachments.
Enforces private S3 bucket security via temporary presigned GET URLs.
Provides seamless fallback to local storage if AWS S3 credentials are not configured.
"""

import os
import re
import uuid
import logging
import urllib.parse
from pathlib import Path

logger = logging.getLogger("CampusAI.S3")

# Supported file extensions
ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg", ".txt"
}

# Local upload directory fallback
UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)

_s3_client = None


def load_env_vars():
    """Dynamically loads environment variables from .env if present."""
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except Exception:
        pass

    env_path = Path(".env")
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'").strip('"')
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception as e:
            logger.warning(f"Could not parse .env file: {e}")


# Initialize environment on module load
load_env_vars()


def get_aws_region() -> str:
    """Returns configured AWS Region with fallback to eu-north-1."""
    load_env_vars()
    return os.environ.get("AWS_REGION", "eu-north-1").strip() or "eu-north-1"


def get_s3_bucket() -> str:
    """Returns configured S3 Bucket Name with fallback to campusai-2026-student."""
    load_env_vars()
    return os.environ.get("S3_BUCKET_NAME", "campusai-2026-student").strip() or "campusai-2026-student"


def is_s3_configured() -> bool:
    """
    Checks if AWS S3 credentials and bucket name are configured.
    Never prints or logs secret credentials.
    """
    load_env_vars()
    key = os.environ.get("AWS_ACCESS_KEY_ID", "").strip()
    secret = os.environ.get("AWS_SECRET_ACCESS_KEY", "").strip()
    bucket = os.environ.get("S3_BUCKET_NAME", "").strip()
    return bool(key and secret and bucket)


def get_s3_client():
    """Initializes and returns boto3 S3 client if configured."""
    global _s3_client
    if _s3_client is not None:
        return _s3_client

    if not is_s3_configured():
        return None

    try:
        import boto3
        key = os.environ.get("AWS_ACCESS_KEY_ID", "").strip()
        secret = os.environ.get("AWS_SECRET_ACCESS_KEY", "").strip()
        region = get_aws_region()

        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=key,
            aws_secret_access_key=secret,
            region_name=region
        )
        return _s3_client
    except Exception as e:
        logger.warning(f"Failed to initialize S3 client: {e}")
        return None


def reset_s3_client():
    """Resets cached S3 client instance."""
    global _s3_client
    _s3_client = None


def is_allowed_file(filename: str) -> bool:
    """Checks if the filename has a supported document extension."""
    if not filename:
        return False
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def sanitize_filename(filename: str) -> str:
    """Generates a clean, unique filename preserving valid extension."""
    ext = Path(filename).suffix.lower() if filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        ext = ".pdf"
    base = re.sub(r"[^a-zA-Z0-9_\-]", "", Path(filename).stem) if filename else "document"
    if not base:
        base = "document"
    unique_suffix = uuid.uuid4().hex[:8]
    return f"{base}_{unique_suffix}{ext}"


def extract_file_key(file_key_or_url: str) -> str:
    """
    Extracts the clean, exact file/object key from a full URL, relative URL, or key.
    Handles:
    - full URLs (http/https)
    - presigned URLs with query parameters (X-Amz-Signature, etc.)
    - URL-encoded strings (%20, etc.)
    - local /uploads paths
    - /api/documents paths
    - malformed paths
    Preserves the exact object key and extension.
    """
    if not file_key_or_url:
        return ""

    s = str(file_key_or_url).strip()
    if not s:
        return ""

    # 1. Unquote in case of URL encoding (e.g. %20, %2F)
    s = urllib.parse.unquote(s)

    # 2. Strip fragment and query parameters (removes ?X-Amz-... and #...)
    s = s.split("#")[0].split("?")[0].strip()

    # 3. If it's a full URL with scheme, extract the URL path
    if s.startswith("http://") or s.startswith("https://"):
        parsed = urllib.parse.urlparse(s)
        s = parsed.path

    # 4. Normalize backslashes to forward slashes
    s = s.replace("\\", "/")

    # 5. Strip prefixes like /api/documents/ or /uploads/
    while True:
        prev = s
        if s.startswith("/api/documents/"):
            s = s[len("/api/documents/"):]
        elif s.startswith("api/documents/"):
            s = s[len("api/documents/"):]
        elif s.startswith("/uploads/"):
            s = s[len("/uploads/"):]
        elif s.startswith("uploads/"):
            s = s[len("uploads/"):]
        if s == prev:
            break

    # 6. Extract the filename/object key
    key = s.strip("/").split("/")[-1].strip()

    # Prevent directory traversal or empty keys
    if key in (".", ".."):
        return ""

    return key


def generate_presigned_download_url(file_key_or_url: str, expires_in: int = 3600) -> str | None:
    """
    Generates a temporary S3 presigned GET URL for secure downloading/viewing without public bucket access.
    If storage is local fallback, returns the local URL /uploads/<key>.
    Returns None if document does not exist.
    """
    if not file_key_or_url:
        return None

    key = extract_file_key(file_key_or_url)
    if not key:
        return None

    client = get_s3_client()
    bucket = get_s3_bucket()
    configured = is_s3_configured()

    if client and bucket and configured:
        # Verify document exists before generating presigned download URL
        if not document_exists(key):
            local_path = UPLOAD_FOLDER / key
            if local_path.exists():
                logger.info(
                    f"Presigned URL generation (local fallback): document_key='{key}', bucket='{bucket}', "
                    f"s3_configured={configured}, succeeded=True"
                )
                return f"/uploads/{key}"
            logger.warning(
                f"Presigned URL generation: document_key='{key}', bucket='{bucket}', "
                f"s3_configured={configured}, succeeded=False"
            )
            return None

        try:
            presigned_url = client.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": bucket,
                    "Key": key
                },
                ExpiresIn=expires_in
            )
            logger.info(
                f"Presigned URL generation: document_key='{key}', bucket='{bucket}', "
                f"s3_configured={configured}, succeeded={bool(presigned_url)}"
            )
            return presigned_url
        except Exception as e:
            logger.warning(
                f"Presigned URL generation failed: document_key='{key}', bucket='{bucket}', "
                f"s3_configured={configured}, succeeded=False"
            )

    # Fallback to local file if available
    local_path = UPLOAD_FOLDER / key
    if local_path.exists():
        logger.info(
            f"Presigned URL generation (local fallback): document_key='{key}', bucket='{bucket}', "
            f"s3_configured={configured}, succeeded=True"
        )
        return f"/uploads/{key}"

    logger.warning(
        f"Presigned URL generation: document_key='{key}', bucket='{bucket}', "
        f"s3_configured={configured}, succeeded=False"
    )
    return None


def document_exists(file_key_or_url: str) -> bool:
    """Checks whether a document exists in S3 or local storage."""
    if not file_key_or_url:
        return False
    key = extract_file_key(file_key_or_url)
    if not key:
        return False

    client = get_s3_client()
    bucket = get_s3_bucket()
    if client and bucket and is_s3_configured():
        try:
            client.head_object(Bucket=bucket, Key=key)
            return True
        except Exception:
            pass

    local_path = UPLOAD_FOLDER / key
    return local_path.exists()


def upload_file(file_obj, filename: str, content_type: str = None) -> dict:
    """
    Uploads a document to Amazon S3 (or falls back to local storage if AWS is not configured).
    Returns dict: {'success': True, 'url': ..., 'key': ..., 'storage': 's3'|'local'}
    """
    if not is_allowed_file(filename):
        return {
            "success": False,
            "error": f"Invalid file type. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        }

    safe_name = sanitize_filename(filename)
    bucket = get_s3_bucket()

    # 1. Attempt upload to Amazon S3 if configured
    client = get_s3_client()
    if client and bucket and is_s3_configured():
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            if isinstance(file_obj, bytes):
                client.put_object(
                    Bucket=bucket,
                    Key=safe_name,
                    Body=file_obj,
                    **extra_args
                )
            else:
                client.upload_fileobj(
                    file_obj,
                    bucket,
                    safe_name,
                    ExtraArgs=extra_args if extra_args else None
                )

            # Return secure document endpoint URL & object key
            secure_url = f"/api/documents/{safe_name}"
            logger.info(f"Uploaded file to Amazon S3 (Key: {safe_name})")
            return {
                "success": True,
                "url": secure_url,
                "key": safe_name,
                "storage": "s3"
            }
        except Exception as e:
            logger.warning(f"S3 upload failed ({e}). Falling back to local storage.")

    # 2. Local Storage Fallback (if S3 not configured or offline)
    local_path = UPLOAD_FOLDER / safe_name
    try:
        if isinstance(file_obj, bytes):
            with open(local_path, "wb") as f:
                f.write(file_obj)
        elif hasattr(file_obj, "save"):
            file_obj.save(str(local_path))
        elif hasattr(file_obj, "read"):
            content = file_obj.read()
            with open(local_path, "wb") as f:
                f.write(content)

        secure_url = f"/api/documents/{safe_name}"
        logger.info(f"Saved file locally to: {secure_url}")
        return {
            "success": True,
            "url": secure_url,
            "key": safe_name,
            "storage": "local"
        }
    except Exception as e:
        logger.error(f"Local file save failed: {e}")
        return {
            "success": False,
            "error": f"Storage error: {str(e)}"
        }


def delete_file(file_key_or_url: str) -> bool:
    """Deletes a file from Amazon S3 or local storage."""
    if not file_key_or_url:
        return False

    key = extract_file_key(file_key_or_url)
    if not key:
        return False

    deleted = False

    # Delete from S3 if configured
    client = get_s3_client()
    bucket = get_s3_bucket()
    if client and bucket and is_s3_configured():
        try:
            client.delete_object(Bucket=bucket, Key=key)
            deleted = True
            logger.info(f"Deleted object from S3: {key}")
        except Exception as e:
            logger.warning(f"Error deleting object from S3: {e}")

    # Delete from local if exists
    local_path = UPLOAD_FOLDER / key
    if local_path.exists():
        try:
            local_path.unlink()
            deleted = True
            logger.info(f"Deleted local file: {key}")
        except Exception as e:
            logger.warning(f"Error deleting local file: {e}")

    return deleted
