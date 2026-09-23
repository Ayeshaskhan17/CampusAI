"""
test_s3_upload.py - Comprehensive Verification for CampusAI S3 & Document Storage
Verifies:
1. Configuration & file extension validations (PDF, DOC, DOCX, PPT, PPTX, PNG, JPG, JPEG)
2. Direct upload, key generation, and presigned download URL generation
3. POST /api/upload endpoint with valid and invalid file types
4. Secure document access route GET /api/documents/<key>
5. GET /api/documents/<key>/url programmatic endpoint
6. Document 404 handling
7. Full Notice Lifecycle:
   - Create notice with document attachment
   - Edit notice with replacement document (verifies old document cleanup)
   - Delete notice (verifies attached document cleanup)
"""
import io
import os
from pathlib import Path
from app import app
from s3_service import (
    upload_file,
    delete_file,
    generate_presigned_download_url,
    is_s3_configured,
    is_allowed_file,
    extract_file_key,
    get_s3_bucket,
    get_aws_region,
    document_exists
)

client = app.test_client()

print("==================================================")
print("1. S3 SERVICE & EXTENSION VALIDATION TESTS")
print("==================================================")
print(f"  [INFO] is_s3_configured(): {is_s3_configured()}")
print(f"  [INFO] Target S3 Bucket: {get_s3_bucket()}")
print(f"  [INFO] Target AWS Region: {get_aws_region()}")

# File extension checks
assert is_allowed_file("sample.pdf") is True
assert is_allowed_file("workshop.pptx") is True
assert is_allowed_file("presentation.ppt") is True
assert is_allowed_file("circular.docx") is True
assert is_allowed_file("document.doc") is True
assert is_allowed_file("diagram.png") is True
assert is_allowed_file("photo.jpg") is True
assert is_allowed_file("banner.jpeg") is True
assert is_allowed_file("script.exe") is False
assert is_allowed_file("payload.sh") is False
print("  [OK] File extension whitelist validation passed (PDF, DOC, DOCX, PPT, PPTX, PNG, JPG, JPEG).")

# Direct upload test (PDF)
sample_pdf_bytes = b"%PDF-1.4 CampusAI S3 Integration Verification Document"
res_pdf = upload_file(sample_pdf_bytes, "campus_test.pdf", content_type="application/pdf")
assert res_pdf["success"] is True
pdf_key = res_pdf["key"]
pdf_url = res_pdf["url"]
print(f"  [OK] Direct upload succeeded: key={pdf_key}, url={pdf_url}, storage={res_pdf['storage']}")

# Presigned URL generation test
dl_url = generate_presigned_download_url(pdf_key)
assert dl_url is not None
print(f"  [OK] generate_presigned_download_url succeeded: {dl_url[:70]}...")

# Clean up test file
assert delete_file(pdf_key) is True
print(f"  [OK] delete_file cleaned up test document: {pdf_key}")


print("\n==================================================")
print("2. API UPLOAD & SECURE DOWNLOAD ENDPOINT TESTS")
print("==================================================")

# 2.1 Rejection of missing file
res_empty = client.post("/api/upload")
assert res_empty.status_code == 400
print("  [OK] POST /api/upload without file part rejected with 400")

# 2.2 Rejection of unauthorized file format
bad_data = {
    "file": (io.BytesIO(b"echo Malicious"), "danger.exe")
}
res_bad = client.post("/api/upload", data=bad_data, content_type="multipart/form-data")
assert res_bad.status_code == 400
assert "Invalid file type" in res_bad.get_json()["error"]
print("  [OK] POST /api/upload with invalid extension (.exe) rejected with 400")

# 2.3 Successful PPTX upload
pptx_data = {
    "file": (io.BytesIO(b"PK\x03\x04 PPTX test slide content for workshop"), "cloud_seminar.pptx")
}
res_pptx = client.post("/api/upload", data=pptx_data, content_type="multipart/form-data")
assert res_pptx.status_code == 200
pptx_json = res_pptx.get_json()
assert pptx_json["success"] is True
pptx_key = pptx_json["key"]
pptx_url = pptx_json["url"]
print(f"  [OK] POST /api/upload (PPTX) succeeded: key={pptx_key}, url={pptx_url}")

# 2.4 Secure Document Download Route GET /api/documents/<key>
res_doc = client.get(f"/api/documents/{pptx_key}")
# If S3 presigned URL is returned, response is 302 redirect. If local storage, response is 200.
assert res_doc.status_code in [200, 302]
if res_doc.status_code == 302:
    redirect_target = res_doc.headers.get("Location", "")
    assert "https://" in redirect_target or "http://" in redirect_target
    print(f"  [OK] GET /api/documents/{pptx_key} returned 302 Redirect to Presigned S3 URL!")
else:
    assert b"PPTX test slide" in res_doc.data
    print(f"  [OK] GET /api/documents/{pptx_key} served document via local fallback!")

# 2.5 Programmatic URL endpoint GET /api/documents/<key>/url
res_json_url = client.get(f"/api/documents/{pptx_key}/url")
assert res_json_url.status_code == 200
url_info = res_json_url.get_json()
assert url_info["key"] == pptx_key
assert url_info["url"] is not None
print(f"  [OK] GET /api/documents/{pptx_key}/url returned presigned JSON descriptor")

# 2.6 Non-existent document 404 test
res_404 = client.get("/api/documents/non_existent_file_99999.pdf")
assert res_404.status_code == 404
print("  [OK] GET /api/documents/non_existent returns 404 Not Found")

# Close response file handle before deleting on Windows
res_doc.close()
delete_file(pptx_key)


print("\n==================================================")
print("3. NOTICE LIFECYCLE WITH S3 DOCUMENT ATTACHMENT")
print("==================================================")

# 3.1 Upload initial document
doc1_data = {
    "file": (io.BytesIO(b"%PDF-1.4 Initial Notice Circular 2026"), "circular_initial.pdf")
}
res_doc1 = client.post("/api/upload", data=doc1_data, content_type="multipart/form-data")
assert res_doc1.status_code == 200
doc1_key = res_doc1.get_json()["key"]
doc1_url = res_doc1.get_json()["url"]

# 3.2 Create notice with attached document
notice_payload = {
    "title": "Annual Innovation & Tech Fair 2026",
    "description": "Notice for the annual university hackathon and paper presentations.",
    "department": "Computer",
    "category": "Event",
    "year": "All Years",
    "event_date": "2026-11-20",
    "deadline": "2026-11-15",
    "venue": "Campus Auditorium",
    "priority": "Urgent",
    "registration_url": "https://campusai.local/register-fair",
    "document_url": doc1_url
}
res_create = client.post("/api/notices", json=notice_payload)
assert res_create.status_code == 201
notice_id = res_create.get_json()["notice_id"]
print(f"  [OK] Created notice #{notice_id} with document {doc1_key}")

# Verify notice has the document URL
res_read = client.get(f"/api/notices/{notice_id}")
assert res_read.status_code == 200
read_notice = res_read.get_json()
assert read_notice["document_url"] == doc1_url
print(f"  [OK] Verified notice #{notice_id} stores document reference in SQLite")

# 3.3 Replace document during notice edit (test orphan cleanup)
doc2_data = {
    "file": (io.BytesIO(b"%PDF-1.4 Revised Schedule & Rules Circular"), "circular_revised.pdf")
}
res_doc2 = client.post("/api/upload", data=doc2_data, content_type="multipart/form-data")
assert res_doc2.status_code == 200
doc2_key = res_doc2.get_json()["key"]
doc2_url = res_doc2.get_json()["url"]

notice_payload["title"] = "Annual Innovation & Tech Fair 2026 (REVISED SCHEDULE)"
notice_payload["document_url"] = doc2_url

res_update = client.post(f"/api/notices/{notice_id}", json=notice_payload) if hasattr(client, 'put') else None
res_update = client.put(f"/api/notices/{notice_id}", json=notice_payload)
assert res_update.status_code == 200
print(f"  [OK] Updated notice #{notice_id} with replacement document {doc2_key}")

# Check that old document doc1_key was deleted from storage
# (If local storage, verify file does not exist)
if not is_s3_configured():
    old_file_path = Path("uploads") / doc1_key
    assert not old_file_path.exists(), f"Old document {doc1_key} was not deleted during edit replacement!"
    print(f"  [OK] Old document {doc1_key} was cleaned up on replacement.")

# 3.4 Delete notice and verify attached document is cleaned up
res_delete = client.delete(f"/api/notices/{notice_id}")
assert res_delete.status_code == 200
print(f"  [OK] Deleted notice #{notice_id}")

if not is_s3_configured():
    revised_file_path = Path("uploads") / doc2_key
    assert not revised_file_path.exists(), f"Attached document {doc2_key} was not deleted when notice was deleted!"
    print(f"  [OK] Attached document {doc2_key} was cleaned up when notice was deleted.")

print("\n==================================================")
print("ALL S3 & DOCUMENT STORAGE TESTS PASSED SUCCESSFULLY!")
print("==================================================")
