import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- CONFIGURATION ---
# 1. SCOPES: What the robot is allowed to do
SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file"
]

# 2. YOUR EMAIL: The robot needs to know who to share the form with.
# ⚠️ REPLACE THIS WITH YOUR ACTUAL EMAIL ADDRESS
USER_EMAIL = "utkarshmalik088@gmail.com"  # Example: "john.doe@gmail.com"

SERVICE_ACCOUNT_FILE = "service_account.json"

def get_authenticated_services():
    """Authenticates the Robot using the Service Account JSON file."""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(f"CRITICAL: {SERVICE_ACCOUNT_FILE} not found. Did you add it to Render's Secret Files?")

    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        # Build services for Forms (to create quiz) and Drive (to share it)
        form_service = build("forms", "v1", credentials=creds)
        drive_service = build("drive", "v3", credentials=creds)
        return form_service, drive_service
    except Exception as e:
        print(f"❌ Authentication Failed: {e}")
        raise e

def json_to_forms_requests(quiz_data):
    """Converts the AI's JSON into Google Forms batchUpdate requests."""
    requests = []
    
    # 1. Turn on Quiz Mode (Auto-grading)
    requests.append({
        "updateSettings": {
            "settings": {"quizSettings": {"isQuiz": True}},
            "updateMask": "quizSettings.isQuiz"
        }
    })

    # 2. Create Questions
    for index, q in enumerate(quiz_data):
        options = q.get("options", [])
        correct_answer_text = q.get("correct_answer", "")
        
        # Logic: Find exact match for correct answer
        # If AI returns "A", map it to options[0]. If "Paris", map it to "Paris".
        final_correct_value = options[0] # Default fallback
        
        # Try to find the exact string match
        for opt in options:
            if opt.strip().lower() == correct_answer_text.strip().lower():
                final_correct_value = opt
                break
        
        # Create the Question Item
        new_question = {
            "createItem": {
                "item": {
                    "title": q["question"],
                    "questionItem": {
                        "question": {
                            "required": True,
                            "grading": {
                                "pointValue": 1,
                                "correctAnswers": {
                                    "answers": [{"value": final_correct_value}]
                                }
                            },
                            "choiceQuestion": {
                                "type": "RADIO",
                                "options": [{"value": opt} for opt in options],
                                "shuffle": True
                            }
                        }
                    }
                },
                "location": {"index": index}
            }
        }
        requests.append(new_question)
        
    return requests

def create_quiz(title, questions):
    """Main function to create, populate, and share the quiz."""
    try:
        form_service, drive_service = get_authenticated_services()

        # Step A: Create a blank form
        print(f"🤖 Creating form: '{title}'...")
        form_body = {"info": {"title": title, "documentTitle": title}}
        form = form_service.forms().create(body=form_body).execute()
        
        form_id = form["formId"]
        form_url = form["responderUri"]
        # The URL needed for you to EDIT the form (not just fill it out)
        edit_url = f"https://docs.google.com/forms/d/{form_id}/edit"

        # Step B: Share the form with YOU (The Human)
        print(f"🤝 Sharing form {form_id} with {USER_EMAIL}...")
        try:
            drive_service.permissions().create(
                fileId=form_id,
                body={
                    "type": "user",
                    "role": "writer",  # "writer" = Editor permission
                    "emailAddress": USER_EMAIL
                },
                fields="id"
            ).execute()
        except HttpError as e:
            print(f"⚠️ Warning: Could not share file. Error: {e}")
            # We continue anyway, because the form WAS created.
        
        # Step C: Add Questions to the Form
        if questions:
            print(f"📝 Adding {len(questions)} questions...")
            update_requests = json_to_forms_requests(questions)
            
            # Google API batchUpdate allows all changes in one go
            form_service.forms().batchUpdate(
                formId=form_id, 
                body={"requests": update_requests}
            ).execute()
            
        print("✅ Quiz created successfully!")
        return edit_url

    except Exception as e:
        print(f"❌ Error in create_quiz: {e}")
        raise e

# --- Test Block (Run this file directly to test) ---
if __name__ == "__main__":
    # Dummy data for testing
    test_questions = [
        {
            "question": "What is the capital of France?",
            "options": ["Berlin", "Madrid", "Paris", "Rome"],
            "correct_answer": "Paris"
        }
    ]
    try:
        url = create_quiz("Test Quiz from Robot", test_questions)
        print(f"🔗 Access your quiz here: {url}")
    except Exception as e:
        print(f"Test Failed: {e}")