from flask import Flask, jsonify, request, send_from_directory, redirect
from database import get_db_connection, create_tables
from ai_provider import ask_campus_ai
from s3_service import (
    upload_file,
    is_s3_configured,
    generate_presigned_download_url,
    delete_file,
    extract_file_key,
    is_allowed_file,
    document_exists,
    get_s3_bucket,
    get_aws_region
)

app = Flask(__name__)

# Make sure the database and tables exist
create_tables()


# Enable CORS for local development and testing
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
    return response


# Serve the CampusAI frontend
@app.route("/")
def home():
    return send_from_directory(".", "index.html")


# Upload document to Amazon S3 (with local fallback)
@app.route("/api/upload", methods=["POST", "OPTIONS"])
def upload_document():
    if request.method == "OPTIONS":
        return "", 204

    if "file" not in request.files:
        return jsonify({"error": "No file part in request."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not is_allowed_file(file.filename):
        return jsonify({
            "error": "Invalid file type. Supported formats: PDF, DOC, DOCX, PPT, PPTX, PNG, JPG, JPEG."
        }), 400

    result = upload_file(file, file.filename, content_type=file.content_type)
    if not result.get("success"):
        return jsonify({"error": result.get("error", "Failed to upload file")}), 500

    return jsonify(result), 200


# Secure document viewing / download route via S3 Presigned GET URL
@app.route("/api/documents/<path:file_key>", methods=["GET"])
def get_document(file_key):
    """
    Generates a secure temporary presigned GET URL for S3 files (or serves local file).
    Enforces that private S3 buckets remain completely private without public access.
    """
    clean_key = extract_file_key(file_key)
    if not clean_key:
        return jsonify({"error": f"Invalid document key '{file_key}'."}), 400

    url = generate_presigned_download_url(clean_key)
    if not url:
        return jsonify({"error": f"Document '{clean_key}' not found."}), 404

    if url.startswith("http://") or url.startswith("https://"):
        # 302 Found redirect to temporary presigned S3 GET URL
        return redirect(url, code=302)
    else:
        # Local fallback storage
        return send_from_directory("uploads", clean_key)


# Programmatic endpoint to get the presigned URL
@app.route("/api/documents/<path:file_key>/url", methods=["GET"])
def get_document_presigned_url(file_key):
    clean_key = extract_file_key(file_key)
    if not clean_key:
        return jsonify({"error": f"Invalid document key '{file_key}'."}), 400

    url = generate_presigned_download_url(clean_key)
    if not url:
        return jsonify({"error": f"Document '{clean_key}' not found."}), 404

    configured = is_s3_configured()
    return jsonify({
        "key": clean_key,
        "url": url,
        "storage": "s3" if (configured and url.startswith("http")) else "local"
    }), 200


# Serve locally uploaded files (fallback when S3 not configured)
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory("uploads", filename)


# S3 Status Endpoint
@app.route("/api/s3/status", methods=["GET"])
def s3_status():
    configured = is_s3_configured()
    return jsonify({
        "configured": configured,
        "storage": "Amazon S3" if configured else "Local Storage (S3 Ready)",
        "bucket": get_s3_bucket(),
        "region": get_aws_region()
    }), 200


# CampusAsk AI Endpoint
@app.route("/api/ask", methods=["POST", "OPTIONS"])
def ask_ai():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({
            "error": "Invalid JSON payload. Expected object with 'question' property."
        }), 400

    question = data.get("question")
    if not question or not str(question).strip():
        return jsonify({
            "error": "Question cannot be empty."
        }), 400

    try:
        result = ask_campus_ai(str(question).strip())
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            "error": "Failed to process question with CampusAI Intelligence",
            "details": str(e)
        }), 500


# Get all notices
@app.route("/api/notices", methods=["GET"])
def get_notices():
    connection = get_db_connection()

    notices = connection.execute("""
        SELECT
            id,
            title,
            description,
            department,
            category,
            year,
            event_date,
            deadline,
            venue,
            priority,
            registration_url,
            document_url,
            created_at
        FROM notices
        ORDER BY created_at DESC
    """).fetchall()

    connection.close()

    return jsonify([dict(notice) for notice in notices])


# Create a new notice
@app.route("/api/notices", methods=["POST"])
def create_notice():
    data = request.get_json()

    title = data.get("title")
    description = data.get("description")
    department = data.get("department")
    category = data.get("category")
    year = data.get("year")
    event_date = data.get("event_date")
    deadline = data.get("deadline")
    venue = data.get("venue")
    priority = data.get("priority")
    registration_url = data.get("registration_url")
    raw_doc = data.get("document_url")
    document_url = None
    if raw_doc and str(raw_doc).strip():
        clean_key = extract_file_key(raw_doc)
        if clean_key:
            document_url = f"/api/documents/{clean_key}"

    if not title or not description:
        return jsonify({
            "error": "Title and description are required"
        }), 400

    connection = get_db_connection()

    cursor = connection.execute("""
        INSERT INTO notices (
            title,
            description,
            department,
            category,
            year,
            event_date,
            deadline,
            venue,
            priority,
            registration_url,
            document_url
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        title,
        description,
        department,
        category,
        year,
        event_date,
        deadline,
        venue,
        priority,
        registration_url,
        document_url
    ))

    connection.commit()

    notice_id = cursor.lastrowid

    connection.close()

    return jsonify({
        "message": "Notice created successfully!",
        "notice_id": notice_id
    }), 201


# Get a single notice by ID
@app.route("/api/notices/<int:notice_id>", methods=["GET"])
def get_notice_by_id(notice_id):
    connection = get_db_connection()
    notice = connection.execute("""
        SELECT
            id,
            title,
            description,
            department,
            category,
            year,
            event_date,
            deadline,
            venue,
            priority,
            registration_url,
            document_url,
            created_at
        FROM notices
        WHERE id = ?
    """, (notice_id,)).fetchone()
    connection.close()

    if not notice:
        return jsonify({
            "error": f"Notice with ID {notice_id} not found."
        }), 404

    return jsonify(dict(notice)), 200


# Update an existing notice
@app.route("/api/notices/<int:notice_id>", methods=["PUT"])
def update_notice(notice_id):
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({
            "error": "Invalid JSON payload."
        }), 400

    title = data.get("title")
    description = data.get("description")
    department = data.get("department")
    category = data.get("category")
    year = data.get("year")
    event_date = data.get("event_date")
    deadline = data.get("deadline")
    venue = data.get("venue")
    priority = data.get("priority")
    registration_url = data.get("registration_url")
    raw_doc = data.get("document_url")
    document_url = None
    if raw_doc and str(raw_doc).strip():
        clean_key = extract_file_key(raw_doc)
        if clean_key:
            document_url = f"/api/documents/{clean_key}"

    if not title or not str(title).strip():
        return jsonify({"error": "Title is required."}), 400
    if not description or not str(description).strip():
        return jsonify({"error": "Description is required."}), 400

    connection = get_db_connection()
    existing = connection.execute("SELECT id, document_url FROM notices WHERE id = ?", (notice_id,)).fetchone()
    if not existing:
        connection.close()
        return jsonify({
            "error": f"Notice with ID {notice_id} not found."
        }), 404

    old_doc = existing["document_url"]
    # If a replacement document is provided, clean up the previous document
    if old_doc and document_url and extract_file_key(old_doc) != extract_file_key(document_url):
        delete_file(old_doc)

    connection.execute("""
        UPDATE notices SET
            title = ?,
            description = ?,
            department = ?,
            category = ?,
            year = ?,
            event_date = ?,
            deadline = ?,
            venue = ?,
            priority = ?,
            registration_url = ?,
            document_url = ?
        WHERE id = ?
    """, (
        str(title).strip(),
        str(description).strip(),
        department,
        category,
        year,
        event_date,
        deadline,
        venue,
        priority,
        registration_url,
        document_url,
        notice_id
    ))
    connection.commit()
    connection.close()

    return jsonify({
        "message": f"Notice {notice_id} updated successfully!",
        "notice_id": notice_id
    }), 200


# Delete a notice
@app.route("/api/notices/<int:notice_id>", methods=["DELETE"])
def delete_notice(notice_id):
    connection = get_db_connection()
    existing = connection.execute("SELECT id, document_url FROM notices WHERE id = ?", (notice_id,)).fetchone()
    if not existing:
        connection.close()
        return jsonify({
            "error": f"Notice with ID {notice_id} not found."
        }), 404

    # Clean up attached document from S3 (or local fallback)
    doc_url = existing["document_url"]
    if doc_url:
        delete_file(doc_url)

    connection.execute("DELETE FROM notices WHERE id = ?", (notice_id,))
    connection.commit()
    connection.close()

    return jsonify({
        "message": f"Notice {notice_id} deleted successfully!",
        "notice_id": notice_id
    }), 200


if __name__ == "__main__":
    app.run(debug=True)