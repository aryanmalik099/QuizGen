from fastapi.testclient import TestClient
from server import app

client = TestClient(app)

def test_read_root():
    # We haven't defined a root "/" endpoint, but this tests 
    # if the app object initializes correctly.
    # If the server was broken, this line would crash.
    assert app is not None

def test_generate_quiz_no_file():
    # Test that calling generate without a file fails gracefully
    response = client.post("/generate-quiz")
    assert response.status_code == 422  # Validation Error (Missing file)