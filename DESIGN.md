# CampusAI — Revised Product Design

## Product
CampusAI is an AI-powered campus information platform. It centralizes official notices, events, opportunities and deadlines, then helps students discover, organize and understand that information through search, filters, saved notices and an AI assistant.

## Product pillars
1. Discover — notices, events, workshops, placements, scholarships and deadlines.
2. Organize — search, filters, bookmarks and deadline tracking.
3. Understand — Ask CampusAI for answers grounded in campus information.

## Scope for v1
### Student
- Home dashboard
- Notices
- Search
- Filters
- Notice details
- Deadline tracking
- Events
- Saved notices
- Ask CampusAI

### Admin
- Dashboard
- Notice management
- Create/edit/archive notice
- Notice document upload UI

### AWS target architecture
Frontend: HTML/CSS/JavaScript
Hosting: Amazon S3
API: API Gateway
Backend: AWS Lambda (Python)
Database: DynamoDB
AI: Amazon Bedrock
Monitoring: CloudWatch
Security: IAM
Future authentication: Amazon Cognito

## Design system
- Background: #F8FAFC
- Surface: #FFFFFF
- Primary: #4F46E5
- AI accent: #06B6D4
- Text: #0F172A
- Muted text: #64748B
- Border: #E2E8F0
- Success: #10B981
- Warning: #F59E0B
- Urgent: #EF4444
- Fonts: Plus Jakarta Sans for headings, Inter for body/UI
- Rounded cards: 16px
- Controls: 8px
- Tags: pill
- Subtle shadows and borders, no heavy gradients

## Important product boundary
CampusAI is NOT an ERP and does not include GPA, attendance, thesis workflows, syllabus ingestion, timetable management or other unrelated academic-OS features in v1. These can be future roadmap ideas only.
