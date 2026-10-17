"""Test helper: exercise actual HTTP endpoint contracts for the JS adapter."""
import json
from fastapi.testclient import TestClient
from app.main import app

if __name__ == "__main__":
    client = TestClient(app)
    output = {}
    for name in ("common", "ring", "normal", "local"):
        scenario = client.get("/demo/scenario", params={"name": name}).json()
        response = client.post("/analyze", json=scenario["analysis_request"])
        response.raise_for_status()
        output[name] = {"scenario": scenario, "analysis": response.json()}
    print(json.dumps(output))
