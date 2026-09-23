"""
test_campusask_api.py - Verification tests for CampusAsk AI API and LocalCampusEngine.
"""
import json
from app import app
from database import get_db_connection

client = app.test_client()

print("--- 1. Testing Validation on POST /api/ask ---")
r_empty = client.post("/api/ask", json={})
assert r_empty.status_code == 400, f"Expected 400, got {r_empty.status_code}"
assert "error" in r_empty.get_json()
print("  [OK] Empty payload correctly rejected with 400")

r_blank = client.post("/api/ask", json={"question": "   "})
assert r_blank.status_code == 400, f"Expected 400, got {r_blank.status_code}"
assert "error" in r_blank.get_json()
print("  [OK] Blank question correctly rejected with 400")

print("\n--- 2. Testing Sample Queries on POST /api/ask ---")
queries = [
    ("What notices are available?", True),
    ("When is the next examination?", True),
    ("Show me upcoming workshops.", True),
    ("What events are available for Computer Science students?", True),
    ("Tell me about upcoming deadlines.", True),
    ("How do I register for an event?", True),
    ("What is the latest campus announcement?", True),
    ("Where is the swimming pool?", False),  # No notices exist for swimming pool
    ("Hello, what can you do?", False)  # Greeting/capabilities
]

for q, expect_sources in queries:
    res = client.post("/api/ask", json={"question": q})
    assert res.status_code == 200, f"Query '{q}' failed with {res.status_code}: {res.data}"
    data = res.get_json()
    assert "answer" in data, f"Missing 'answer' in response for '{q}'"
    assert "sources" in data, f"Missing 'sources' in response for '{q}'"
    assert "provider" in data, f"Missing 'provider' in response for '{q}'"
    sources = data["sources"]
    if expect_sources:
        assert len(sources) > 0, f"Expected sources for '{q}', got 0"
    print(f"  [OK] '{q}' -> {len(sources)} source(s), provider: {data['provider']}")

print("\n--- 3. Testing Dynamic Notice Retrieval (Section 37 Lifecycle) ---")
# Query before creation
q_dyn = "Tell me about the dynamic notice test"
res_before = client.post("/api/ask", json={"question": q_dyn}).get_json()
assert len(res_before["sources"]) == 0, f"Expected 0 sources before creation, got {len(res_before['sources'])}"
print(f"  [OK] Before creation: 0 sources matched (honest no-hallucination)")

# Create notice via POST /api/notices
test_notice = {
    "title": "CampusAI Dynamic Notice Test",
    "description": "This notice was created dynamically through the CampusAI application.",
    "department": "Computer",
    "category": "General",
    "priority": "High",
    "deadline": "2026-09-30"
}
res_create = client.post("/api/notices", json=test_notice)
assert res_create.status_code == 201, f"Failed to create notice: {res_create.data}"
created_id = res_create.get_json()["notice_id"]
print(f"  [OK] Created dynamic test notice with ID {created_id}")

# Query after creation
res_after = client.post("/api/ask", json={"question": q_dyn}).get_json()
assert len(res_after["sources"]) >= 1, f"Expected at least 1 source, got {len(res_after['sources'])}"
assert res_after["sources"][0]["id"] == created_id, f"Expected notice {created_id}, got {res_after['sources'][0]['id']}"
assert "CampusAI Dynamic Notice Test" in res_after["answer"], "Expected title in answer"
print(f"  [OK] After creation: dynamically retrieved notice #{created_id} ('CampusAI Dynamic Notice Test')")

# Clean up
conn = get_db_connection()
conn.execute("DELETE FROM notices WHERE id = ?", (created_id,))
conn.commit()
conn.close()
print(f"  [OK] Cleaned up dynamic test notice #{created_id}")

print("\n--- 4. Testing Milestone 6 Notice Management (GET, PUT, DELETE) & AI Lifecycle ---")
# 4.1 Test GET /api/notices/<id> on nonexistent ID
res_get_404 = client.get("/api/notices/999999")
assert res_get_404.status_code == 404, f"Expected 404 for nonexistent notice, got {res_get_404.status_code}"
print("  [OK] GET /api/notices/999999 returned 404")

# 4.2 Test PUT /api/notices/<id> validation
res_put_empty = client.put("/api/notices/1", json={})
assert res_put_empty.status_code == 400, f"Expected 400 for empty PUT, got {res_put_empty.status_code}"
res_put_notitle = client.put("/api/notices/1", json={"description": "No title here"})
assert res_put_notitle.status_code == 400, f"Expected 400 for missing title, got {res_put_notitle.status_code}"
print("  [OK] PUT validation correctly rejected invalid payloads with 400")

# 4.3 Create a notice for full lifecycle testing
new_notice = {
    "title": "Robotics Championship 2026",
    "description": "Annual campus robotics tournament and exhibition.",
    "department": "Mechanical",
    "category": "Event",
    "priority": "Important",
    "deadline": "2026-10-15",
    "event_date": "2026-10-20",
    "venue": "Campus Arena",
    "registration_url": "https://example.com/robotics-register"
}
res_create2 = client.post("/api/notices", json=new_notice)
assert res_create2.status_code == 201
n_id = res_create2.get_json()["notice_id"]
print(f"  [OK] Created notice #{n_id} for management testing")

# 4.4 GET by ID
res_get_one = client.get(f"/api/notices/{n_id}")
assert res_get_one.status_code == 200
data_one = res_get_one.get_json()
assert data_one["id"] == n_id
assert data_one["title"] == "Robotics Championship 2026"
print(f"  [OK] GET /api/notices/{n_id} retrieved notice data correctly")

# 4.5 Verify CampusAsk AI can answer before update
res_ai_before = client.post("/api/ask", json={"question": "Tell me about the robotics championship"}).get_json()
assert len(res_ai_before["sources"]) >= 1
assert res_ai_before["sources"][0]["id"] == n_id
print(f"  [OK] CampusAsk AI retrieved notice #{n_id} before update")

# 4.6 PUT update the notice (change title, deadline, description)
updated_notice = {
    "title": "International Robotics Championship 2026",
    "description": "Updated international campus robotics grand challenge with prize pool.",
    "department": "Mechanical",
    "category": "Event",
    "priority": "Urgent",
    "deadline": "2026-10-25",
    "event_date": "2026-11-01",
    "venue": "Main Auditorium",
    "registration_url": "https://example.com/international-robotics"
}
res_update = client.put(f"/api/notices/{n_id}", json=updated_notice)
assert res_update.status_code == 200, f"Expected 200, got {res_update.status_code}: {res_update.data}"
print(f"  [OK] PUT /api/notices/{n_id} succeeded")

# 4.7 GET by ID to confirm update in database
res_get_updated = client.get(f"/api/notices/{n_id}")
assert res_get_updated.status_code == 200
data_updated = res_get_updated.get_json()
assert data_updated["title"] == "International Robotics Championship 2026"
assert data_updated["priority"] == "Urgent"
assert data_updated["deadline"] == "2026-10-25"
assert data_updated["venue"] == "Main Auditorium"
print(f"  [OK] Verified updated database fields for notice #{n_id}")

# 4.8 Verify CampusAsk AI dynamically retrieves updated notice and reflects changes
res_ai_after_update = client.post("/api/ask", json={"question": "Tell me about the International Robotics Championship"}).get_json()
assert len(res_ai_after_update["sources"]) >= 1
assert res_ai_after_update["sources"][0]["id"] == n_id
assert "International Robotics Championship" in res_ai_after_update["answer"]
print(f"  [OK] CampusAsk AI dynamically reflected updated title and details in response")

# 4.9 DELETE the notice
res_delete = client.delete(f"/api/notices/{n_id}")
assert res_delete.status_code == 200, f"Expected 200, got {res_delete.status_code}: {res_delete.data}"
print(f"  [OK] DELETE /api/notices/{n_id} succeeded")

# 4.10 Confirm GET returns 404 after deletion
res_get_deleted = client.get(f"/api/notices/{n_id}")
assert res_get_deleted.status_code == 404
print(f"  [OK] GET /api/notices/{n_id} returned 404 after deletion")

# 4.11 Confirm second DELETE returns 404
res_delete_again = client.delete(f"/api/notices/{n_id}")
assert res_delete_again.status_code == 404
print(f"  [OK] Secondary DELETE /api/notices/{n_id} returned 404 (safe idempotent behavior)")

# 4.12 Confirm CampusAsk AI no longer retrieves the deleted notice
res_ai_after_delete = client.post("/api/ask", json={"question": "Tell me about the International Robotics Championship"}).get_json()
assert len(res_ai_after_delete["sources"]) == 0
print(f"  [OK] CampusAsk AI correctly reported 0 sources for deleted notice")

print("\nALL BACKEND API AND CAMPUSASK AI TESTS PASSED!")

