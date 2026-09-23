# CampusAI — Dynamic Campus Intelligence Platform

CampusAI is a dynamic campus information platform for students, faculty, and administrators. It centralizes official campus announcements, events, opportunities, deadlines, and official documents, and provides an intelligent campus assistant (CampusAsk AI) grounded in real campus data.

---

## 1. System Architecture

```
              CampusAI
                 |
              Flask
             /     \
            /       \
       SQLite       S3
        |            |
     Notices      Documents
     Users
     Profiles
```

- **Backend**: Python with Flask serving REST API endpoints.
- **Frontend**: Single-Page Application (SPA) in Vanilla HTML5, CSS3, and JavaScript.
- **Primary Database**: SQLite (`campusai.db`) for all structured data (Notices, Users, Sessions).
- **Document Storage**: Amazon S3 for notice PDFs and official documents (with zero-configuration local fallback to `uploads/` for offline/development use).
- **Campus Intelligence**: CampusAsk AI grounded in SQLite notices using `LocalCampusEngine` with Amazon Bedrock cloud provider abstraction.

---

## 2. Core Features

### Student Experience
- **Personalized Dashboard**: Dynamic greeting (`Good morning, {name} 👋`) and top navigation avatar with initials.
- **Notices Discovery**: Search, filter by department and category, view details, and manual "Refresh Notices" button.
- **Official Notice Documents**: View/download uploaded notice PDFs and documents stored in Amazon S3.
- **Events & Deadlines**: Discover workshops, hackathons, and deadlines.
- **Saved Notices**: Bookmark notices locally for quick reference.
- **CampusAsk AI**: Grounded campus intelligence answering questions truthfully with direct notice citations and no hallucinations.
- **Student Profile**: Customize department, year of study, semester, section, and bio.

### Faculty Experience
- **Faculty Dashboard**: Overview of campus notices and quick administrative actions.
- **Create Notice**: Publish announcements with category, department, year, deadline, priority, and optional S3 document upload.
- **Manage Notices**: Complete notice lifecycle management with **View**, **Edit**, and **Delete** actions.
- **Edit Notice**: Update existing announcements with preloaded form fields.
- **Delete Notice**: Remove notices safely with confirmation dialog.
- **Faculty Profile**: Employee ID, cabin location, department, and academic designation.

### Administrator Experience
- **Admin Dashboard**: System-wide announcement statistics and notice operations.
- **Full Administrative Control**: Create, view, edit, and delete any notice.
- **Admin Profile**: Administrator ID, administrative block cabin, and title.

### Role Security
- **Strict Role Boundaries**: Enforced via `roleCanAccess()` in routing and dynamically rendered UI buttons.
- Students can view notices and documents, but are strictly prohibited from creating, editing, or deleting notices.

---

## 3. Technology Stack

- **Frontend**: HTML5, CSS3, JavaScript (Vanilla SPA)
- **Backend**: Python 3.8+, Flask, `boto3`
- **Database**: SQLite3
- **Storage**: Amazon S3 (optional cloud document store with local fallback)
- **AI Intelligence**: `LocalCampusEngine` (Campus RAG Engine) & Amazon Bedrock Ready

---

## 4. Local Setup & Startup

### Step 1: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 2: Configure Environment (Optional for S3)
Copy the example environment file:
```powershell
Copy-Item .env.example .env
```
Fill in your AWS S3 details if you want cloud document storage (see [AWS_S3_SETUP.md](file:///c:/Users/AYESHA/Downloads/CampusAI_Revised_Departments_Updated/AWS_S3_SETUP.md)):
```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your_bucket_name
```
*(If left unconfigured, CampusAI automatically stores uploaded documents in the local `uploads/` folder).*

### Step 3: Start the Flask Application
Run:
```powershell
python app.py
```

### Step 4: Open CampusAI
Navigate to:
```
http://127.0.0.1:5000
```

---

## 5. Demo Accounts

| Role | Email / Identifier | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Student** | `student@campusai.local` | `Student@123` | View Notices, Events, Saved, CampusAsk, Profile |
| **Faculty** | `faculty@campusai.local` | `Faculty@123` | Create, View, Edit, Delete Notices, CampusAsk, Profile |
| **Admin** | `admin@campusai.local` | `Admin@123` | Full Campus Information Management |

---

## 6. Automated Testing

Run the full verification test suites:
```powershell
python test_campusask_api.py
python test_full_suite.py
python test_s3_upload.py
```
All tests verify 100% passing results for backend APIs, notice lifecycle (CRUD), CampusAsk RAG engine, S3 document uploads, and frontend security controls.
