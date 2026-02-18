import os
import json
from google.oauth2.credentials import Credentials  # ✅ NEW IMPORT
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- CONFIGURATION ---
SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file"
]

# Fallback Robot File
SERVICE_ACCOUNT_FILE = "service_account.json"

def get_authenticated_services(user_creds_dict=None):
    """
    1. If user_creds_dict is passed (Real User), use it.
    2. If not, try to use the Robot (Service Account).
    """
    creds = None
    
    # CASE A: Real User Login
    if user_creds_dict:
        creds = Credentials(**user_creds_dict)
    
    # CASE B: Robot Fallback
    elif os.path.exists(SERVICE_ACCOUNT_FILE):
        print("🤖 Using Robot (Service Account) Credentials")
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
    else:
        raise ValueError("No valid credentials found (User or Robot).")

    return build("forms", "v1", credentials=creds), build("drive", "v3", credentials=creds)

def json_to_forms_requests(quiz_data):
    # ... (Keep this function EXACTLY as it was before) ...
    # I am omitting the body to save space, but DO NOT DELETE IT.
    # Just paste your existing logic here.
    requests = []
    requests.append({
        "updateSettings": {
            "settings": {"quizSettings": {"isQuiz": True}},
            "updateMask": "quizSettings.isQuiz"
        }
    })
    for index, q in enumerate(quiz_data):
        options = q.get("options", [])
        correct_answer_text = q.get("correct_answer", "")
        final_correct_value = options[0] if options else ""
        for opt in options:
            if opt.strip().lower() == correct_answer_text.strip().lower():
                final_correct_value = opt
                break
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

# ✅ UPDATED FUNCTION SIGNATURE
def create_quiz(title, questions, user_creds_dict=None):
    try:
        form_service, drive_service = get_authenticated_services(user_creds_dict)

        print(f"🚀 Creating form '{title}'...")
        file_metadata = {
            'name': title,
            'mimeType': 'application/vnd.google-apps.form'
        }
        
        # Folder logic for Robot
        if not user_creds_dict:
             FOLDER_ID = "1vmg5rrYVFu1OROeEu9stSgqfwy0QIJ0K" 
             file_metadata['parents'] = [FOLDER_ID]

        file = drive_service.files().create(body=file_metadata, fields='id').execute()
        form_id = file.get('id')
        edit_url = f"https://docs.google.com/forms/d/{form_id}/edit"
        print(f"✅ File created! ID: {form_id}")

        print(f"📝 Populating content...")
        update_requests = []
        
        update_requests.append({
            "updateFormInfo": {
                "info": {
                    "title": title
                },
                "updateMask": "title"
            }
        })

        if questions:
            update_requests.extend(json_to_forms_requests(questions))

        form_service.forms().batchUpdate(
            formId=form_id, 
            body={"requests": update_requests}
        ).execute()

        if not user_creds_dict:
            USER_EMAIL = "utkarshmalik088@gmail.com" 
            print(f"🤝 Sharing with {USER_EMAIL}...")
            drive_service.permissions().create(
                fileId=form_id,
                body={"type": "user", "role": "writer", "emailAddress": USER_EMAIL}
            ).execute()
            
        return edit_url

    except Exception as e:
        print(f"❌ Error in create_quiz: {e}")
        raise e