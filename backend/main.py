import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- CONFIGURATION ---
SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file"
]

# ⚠️ REPLACE WITH YOUR EMAIL
USER_EMAIL = "utkarshmalik088@gmail.com"
FOLDER_ID = "1vmg5rrYVFu1OROeEu9stSgqfwy0QIJ0K"

SERVICE_ACCOUNT_FILE = "service_account.json"

def get_authenticated_services():
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(f"CRITICAL: {SERVICE_ACCOUNT_FILE} not found.")

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("forms", "v1", credentials=creds), build("drive", "v3", credentials=creds)

def json_to_forms_requests(quiz_data):
    requests = []
    
    # 1. Turn on Quiz Mode
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

def create_quiz(title, questions):
    try:
        form_service, drive_service = get_authenticated_services()

        # --- STRATEGY CHANGE: DRIVE-FIRST CREATION ---
        # Instead of creating in root (which causes 500 errors),
        # we create the file DIRECTLY inside the folder using the Drive API.
        print(f"🤖 Creating file directly in folder {FOLDER_ID}...")
        
        file_metadata = {
            'name': title,
            'mimeType': 'application/vnd.google-apps.form',
            'parents': [FOLDER_ID] 
        }
        
        # 1. Create Blank Form File via Drive API (This avoids the 500 error)
        file = drive_service.files().create(body=file_metadata, fields='id').execute()
        form_id = file.get('id')
        edit_url = f"https://docs.google.com/forms/d/{form_id}/edit"
        print(f"✅ File created! ID: {form_id}")

        # 2. Populate Title and Questions via Forms API
        print(f"📝 Populating form content...")
        update_requests = []
        
        # Set Title
        update_requests.append({
            "updateFormInfo": {
                "info": {
                    "title": title,
                    "documentTitle": title
                },
                "updateMask": "title,documentTitle"
            }
        })
        
        # Add Questions
        if questions:
            question_requests = json_to_forms_requests(questions)
            update_requests.extend(question_requests)

        # Execute all updates
        form_service.forms().batchUpdate(
            formId=form_id, 
            body={"requests": update_requests}
        ).execute()

        # 3. Share with User
        print(f"🤝 Sharing with {USER_EMAIL}...")
        drive_service.permissions().create(
            fileId=form_id,
            body={"type": "user", "role": "writer", "emailAddress": USER_EMAIL}
        ).execute()
            
        print("✅ Quiz created successfully!")
        return edit_url

    except Exception as e:
        print(f"❌ Error in create_quiz: {e}")
        raise e
