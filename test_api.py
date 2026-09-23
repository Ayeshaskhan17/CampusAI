import requests

url = "http://127.0.0.1:5000/api/notices"

notice = {
    "title": "AWS Cloud Workshop",
    "description": "A hands-on introduction to cloud computing and AWS services for students.",
    "department": "Computer",
    "category": "Workshop",
    "year": "3rd Year",
    "event_date": "2026-09-20",
    "deadline": "2026-09-18",
    "venue": "Seminar Hall",
    "priority": "Important",
    "registration_url": "https://example.com/register",
    "document_url": None
}

response = requests.post(url, json=notice)

print("Status Code:", response.status_code)
print("Response:", response.json())