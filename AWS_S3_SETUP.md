# CampusAI — Amazon S3 Setup Guide

This guide walks you through configuring an Amazon S3 bucket for storing uploaded notice documents, event PDFs, and attachments in CampusAI.

> [!NOTE]
> CampusAI runs completely out-of-the-box locally with an automated local storage fallback (`uploads/`). Configuring AWS S3 is optional and only required when you want cloud-hosted document storage.

---

## 1. Create an AWS Account
1. Go to [https://aws.amazon.com](https://aws.amazon.com) and sign in or create an AWS account.
2. Ensure you have access to the AWS Management Console.

---

## 2. Create an S3 Bucket
1. Open the **Amazon S3 Console** at [https://s3.console.aws.amazon.com](https://s3.console.aws.amazon.com).
2. Click **Create bucket**.
3. Configure bucket settings:
   - **Bucket name**: Choose a globally unique name (e.g., `campusai-documents-bucket`).
   - **AWS Region**: Select your nearest region (e.g., `us-east-1` or `ap-south-1`).
4. Click **Create bucket** at the bottom.

---

## 3. Configure Bucket Permissions & CORS

### A. CORS Configuration (Allow Browser Uploads & Previews)
1. Select your bucket and open the **Permissions** tab.
2. Scroll to **Cross-origin resource sharing (CORS)** and click **Edit**.
3. Paste the following configuration:
```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "HEAD"],
    "AllowedOrigins": ["*"],
    "ExposeHeaders": []
  }
]
```
4. Click **Save changes**.

### B. Public Read Access (For Public Notice PDF Downloads)
If you want uploaded documents to be publicly downloadable by students:
1. Under **Permissions**, edit **Block public access (bucket settings)** and uncheck "Block *all* public access".
2. Add a Bucket Policy granting `s3:GetObject` permission:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/*"
    }
  ]
]
```
*(Replace `YOUR_BUCKET_NAME` with your actual bucket name).*

---

## 4. Create IAM User & Credentials
1. Open the **IAM Console** at [https://console.aws.amazon.com/iam](https://console.aws.amazon.com/iam).
2. Click **Users** &rarr; **Create user**.
3. Name: `campusai-s3-user`.
4. Select **Attach policies directly** and attach a policy with minimum required permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/*"
    }
  ]
}
```
5. Complete user creation.
6. Open the user details, click **Security credentials** &rarr; **Create access key** (Application running outside AWS).
7. Save the **Access Key ID** and **Secret Access Key**.

---

## 5. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```

Open `.env` and fill in your values:
```env
AWS_ACCESS_KEY_ID=your_access_key_id_here
AWS_SECRET_ACCESS_KEY=your_secret_access_key_here
AWS_REGION=us-east-1
S3_BUCKET_NAME=your_bucket_name_here
```

> [!WARNING]
> Never commit `.env` or your secret keys to Git. `.env` is already included in `.gitignore`.

---

## 6. Run Flask & Test Document Upload
1. Start the server:
   ```powershell
   python app.py
   ```
2. Open `http://127.0.0.1:5000` in your browser.
3. Login as Faculty (`faculty@campusai.local` / `Faculty@123`).
4. Go to **Create Notice** (or **Edit Notice**).
5. Click **Choose File** in the *Official notice document* card and select a PDF.
6. The file is uploaded directly to your Amazon S3 bucket, and the S3 URL is stored with the notice in SQLite.
7. Students can view and download the document directly from the notice details page.
