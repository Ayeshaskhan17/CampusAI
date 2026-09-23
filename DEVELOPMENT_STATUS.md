# CampusAI — Development & Operational Status

## 1. Project Overview
CampusAI is a dynamic campus intelligence platform for students, faculty, and administrators built with a lightweight, maintainable stack:
- **Frontend**: HTML5, CSS3, Vanilla JavaScript (Single-Page Application).
- **Backend**: Python, Flask, REST API.
- **Database**: SQLite (`campusai.db`).
- **AI Intelligence**: Grounded Campus RAG engine (`LocalCampusEngine`) with AWS Amazon Bedrock cloud provider abstraction (`ai_provider.py`).

---

## 2. How to Run CampusAI Locally

### Prerequisites
- Python 3.8+ (Windows, macOS, or Linux)
- Required packages: `Flask`

### Starting the Server
From the project root directory (`CampusAI_Revised_Departments_Updated`):
```powershell
python app.py
```
*The server will start at: `http://127.0.0.1:5000`*

### Accessing the Web Application
Open your browser and navigate to:
```
http://127.0.0.1:5000/
```

---

## 3. Demo Accounts & Credentials

| Role | Email / Identifier | Password | Access Rights |
| :--- | :--- | :--- | :--- |
| **Student** | `student@campusai.local` | `Student@123` | View Notices, Events, Saved Bookmarks, CampusAsk AI, Profile. *(Cannot create, edit, or delete notices)* |
| **Faculty** | `faculty@campusai.local` | `Faculty@123` | Faculty Dashboard, Create Notice, View, Edit, and Delete Notices, CampusAsk AI, Profile. |
| **Administrator** | `admin@campusai.local` | `Admin@123` | Admin Dashboard, Create Notice, View, Edit, and Delete Notices, CampusAsk AI, Profile. |

*Self-registration with automatic role profile setup is also supported for all roles.*

---

## 4. Completed Functional Architecture

### A. Notice Management & CRUD
- **Create Notice**: Submits to `POST /api/notices`, validates fields, and stores in SQLite.
- **Read Notices**: `GET /api/notices` retrieves all notices in descending order of `created_at`.
- **Read Single Notice**: `GET /api/notices/<id>` retrieves notice details.
- **Edit Notice**: `PUT /api/notices/<id>` loads existing notice data into the form, updates fields in SQLite, and immediately reflects updates.
- **Delete Notice**: `DELETE /api/notices/<id>` prompts a confirmation modal (`"Are you sure you want to delete this notice?"` with Cancel/Delete buttons), removes from SQLite, and updates UI immediately.
- **Refresh Notices**: Dedicated "Refresh Notices" button re-fetches latest database notices dynamically.

### B. CampusAsk AI (RAG Intelligence)
- **Endpoint**: `POST /api/ask`
- **Engine**: `LocalCampusEngine` performs keyword extraction, stop-word elimination, intent classification (examinations, deadlines, workshops, venues, registrations), and ranks notices from SQLite.
- **Zero Hallucination**: If no matching notice exists, the AI states that no matching campus announcements were found.
- **Cloud Ready**: `BedrockProvider` is configured for AWS Amazon Bedrock (Claude 3 / Titan) via `boto3`.

### C. Role-Based Access Control
- `roleCanAccess()` enforces strict boundary checks:
  - **Student**: Blocked from `manage`, `create`, and `edit`. Attempting direct URL access redirects to `#home` with a permission notice.
  - **Faculty & Admin**: Full notice lifecycle permissions (`manage`, `create`, `edit`).
- UI Controls: `manageRows()` dynamically displays **View**, **Edit**, and **Delete** actions for Faculty/Admin, and restricts Students to **View** only.

---

## 5. Verification & Test Suite
Run the automated test suites:
```powershell
python test_campusask_api.py
python test_full_suite.py
```
*Both suites verify 100% passing results for backend API validation, notice management lifecycle, CampusAsk RAG queries, and frontend security rules.*
