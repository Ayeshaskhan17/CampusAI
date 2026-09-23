# Next Build Steps

1. Run `code.html` locally and test the navigation and interactions.
2. Split the single prototype into frontend files (HTML/CSS/JS modules) once the UX is approved.
3. Replace local `notices` data with API calls.
4. Build Python Lambda handlers:
   - GET /notices
   - GET /notices/{id}
   - POST /notices
   - PUT /notices/{id}
   - PATCH /notices/{id}/archive
   - POST /ask
5. Connect API Gateway -> Lambda -> DynamoDB.
6. Host the frontend in Amazon S3.
7. Add Amazon Bedrock to `/ask`.
8. Add IAM permissions and CloudWatch logging.
9. Add Cognito only after the core flow works.
