"""
test_e2e_s3_flow.py - End-to-end verification of CampusAI S3 document upload and download flow.

Tests:
1. Faculty/Admin: Upload document to Amazon S3 -> returns clean object key and /api/documents/<key> URL.
2. Faculty/Admin: Create notice with attached document -> stored cleanly in database.
3. Student: Open notice details -> verify document_url is /api/documents/<key>.
4. Student: Click View / Download -> GET /api/documents/<key> returns 302 Redirect to boto3 presigned S3 URL.
5. Browser download: Fetch presigned S3 URL directly -> returns HTTP 200 OK with exact file content.
6. Verify document deletion and 404 behavior.
"""
import io
import urllib.request
from app import app
from s3_service import is_s3_configured, delete_file, document_exists

client = app.test_client()

print("==================================================")
print("1. FACULTY/ADMIN: UPLOAD DOCUMENT TO S3")
print("==================================================")
test_content = b"%PDF-1.4 CampusAI Complete Flow Verification - Private S3 Document"
upload_res = client.post(
    "/api/upload",
    data={"file": (io.BytesIO(test_content), "faculty_guidelines.pdf")},
    content_type="multipart/form-data"
)
assert upload_res.status_code == 200
up_data = upload_res.get_json()
assert up_data["success"] is True
doc_key = up_data["key"]
doc_url = up_data["url"]
assert doc_url == f"/api/documents/{doc_key}"
print(f"  [OK] Uploaded file: key={doc_key}, url={doc_url}, storage={up_data['storage']}")

print("\n==================================================")
print("2. FACULTY/ADMIN: PUBLISH NOTICE")
print("==================================================")
notice_payload = {
    "title": "Faculty Exam Guidelines 2026",
    "description": "Important guidelines for upcoming semester examinations.",
    "department": "Computer",
    "category": "Academic",
    "year": "All Years",
    "event_date": "2026-10-15",
    "deadline": "2026-10-10",
    "venue": "Examination Hall 1",
    "priority": "High",
    "registration_url": None,
    "document_url": doc_url
}
create_res = client.post("/api/notices", json=notice_payload)
assert create_res.status_code == 201
notice_id = create_res.get_json()["notice_id"]
print(f"  [OK] Notice published successfully with ID #{notice_id}")

print("\n==================================================")
print("3. STUDENT: OPEN NOTICE & VIEW / DOWNLOAD")
print("==================================================")
get_notice_res = client.get(f"/api/notices/{notice_id}")
assert get_notice_res.status_code == 200
notice_data = get_notice_res.get_json()
assert notice_data["document_url"] == f"/api/documents/{doc_key}"
print(f"  [OK] Student viewed notice #{notice_id}: document_url='{notice_data['document_url']}'")

# Simulate clicking 'View / Download' -> GET /api/documents/<key>
download_res = client.get(f"/api/documents/{doc_key}")
assert download_res.status_code == 302, f"Expected 302, got {download_res.status_code}"
s3_presigned_url = download_res.headers.get("Location")
assert s3_presigned_url is not None
assert "campusai-2026-student" in s3_presigned_url
assert "X-Amz-Signature=" in s3_presigned_url
print("  [OK] GET /api/documents/<key> returned HTTP 302 Found redirect to presigned S3 URL!")

# Simulate browser following 302 redirect and fetching from S3
req = urllib.request.Request(s3_presigned_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
with urllib.request.urlopen(req) as s3_response:
    assert s3_response.status == 200
    downloaded_bytes = s3_response.read()
    assert downloaded_bytes == test_content
    print(f"  [OK] Browser successfully opened document from private S3 bucket! (HTTP 200, {len(downloaded_bytes)} bytes)")

print("\n==================================================")
print("4. CLEANUP TEST NOTICE & VERIFY S3 CLEANUP")
print("==================================================")
del_res = client.delete(f"/api/notices/{notice_id}")
assert del_res.status_code == 200
print(f"  [OK] Notice #{notice_id} deleted and attached S3 document cleaned up")

# Verify non-existent document returns 404
res_404 = client.get(f"/api/documents/{doc_key}")
assert res_404.status_code == 404
print(f"  [OK] GET /api/documents/{doc_key} returned 404 after deletion")

print("\n==================================================")
print("END-TO-END S3 DOCUMENT FLOW VERIFIED 100% WORKING!")
print("==================================================")
