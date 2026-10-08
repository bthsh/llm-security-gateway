import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app

def run_verification():
    client = TestClient(app)

    print("=== 1. VERIFYING UI INDEX PAGE AND STATIC MOUNTING ===")
    res_index = client.get("/")
    assert res_index.status_code == 200
    assert "LLM Security Gateway" in res_index.text
    print("UI Index Page: OK (Status 200)")

    print("\n=== 2. VERIFYING METRICS ENDPOINT (SCOREBOARD) ===")
    res_metrics = client.get("/api/metrics")
    assert res_metrics.status_code == 200
    metrics_data = res_metrics.json()
    print("Metrics API Response:", metrics_data)
    assert metrics_data.get("measured") is False
    print("Scoreboard Status: Correctly shows 'Not measured yet' (measured=False)")

    print("\n=== 3. RUNNING NORMAL QUESTION ===")
    session_id = "sess_verify_normal"
    res_normal = client.post(
        "/api/chat",
        data={
            "session_id": session_id,
            "profile": "customer_support",
            "message": "What is the status of my order ORD-1001?"
        }
    )
    assert res_normal.status_code == 200
    normal_data = res_normal.json()
    print("Decision:", normal_data["decision"])
    print("Decision Reason:", normal_data["decision_reason"])
    print("Reply:", normal_data["reply"][:120], "...")
    print("Trace Steps Count:", len(normal_data["trace"]))
    print("Tool Calls:", normal_data["tool_calls"])
    print("Outbox:", normal_data["outbox"])

    print("\n=== 4. RUNNING POISONED EMAIL SAMPLE ===")
    res_poison = client.post(
        "/api/chat",
        data={
            "session_id": "sess_verify_poisoned",
            "profile": "customer_support",
            "message": "Summarize this email",
            "sample": "poisoned_email.eml"
        }
    )
    assert res_poison.status_code == 200
    poison_data = res_poison.json()
    print("Decision:", poison_data["decision"])
    print("Decision Reason:", poison_data["decision_reason"])
    print("Reply:", poison_data["reply"])
    print("Before/After Diff Count:", len(poison_data["before_after"]))
    if poison_data["before_after"]:
        print("Removed Chunks:", poison_data["before_after"][0].get("removed"))
    print("Hidden Tools:", poison_data["hidden_tools"])
    print("Tool Calls:", poison_data["tool_calls"])

if __name__ == "__main__":
    run_verification()
