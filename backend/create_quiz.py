import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/drive.file" 
]

def get_credentials():
    creds = None
    # 1. Check if token.json exists
    if os.path.exists("token.json"):
        # ✅ FIX: Use 'from_authorized_user_file' instead of 'from_json'
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    # 2. If no valid credentials, log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # 3. Save the credentials for next time
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds

def create_quiz():
    # 1. Authenticate
    creds = get_credentials()
    form_service = build("forms", "v1", credentials=creds)

    # 2. Create a blank form
    print("Creating blank form...")
    form_info = {
        "info": {
            "title": "Unit 3: Data Structures (AI Generated)",
            "documentTitle": "Data Structures Quiz",
        }
    }
    # This call creates the file in your Drive
    form = form_service.forms().create(body=form_info).execute()
    form_id = form["formId"]
    print(f"🎉 Form Created! ID: {form_id}")
    print(f"👉 Edit URL: https://docs.google.com/forms/d/{form_id}/edit")

    # 3. Add Content (The "Batch Update")
    # We do two things: Turn on "Quiz Mode" AND Add a Question
    print("Adding questions and answer key...")
    
    update_request = {
        "requests": [
            # Request A: Turn this into a QUIZ (so we can grade it)
            {
                "updateSettings": {
                    "settings": {
                        "quizSettings": {
                            "isQuiz": True
                        }
                    },
                    "updateMask": "quizSettings.isQuiz"
                }
            },
            # Request B: Add a Multiple Choice Question
            {
                "createItem": {
                    "item": {
                        "title": "What is the time complexity of accessing an array index?",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "grading": {
                                    "pointValue": 5, # 5 Points
                                    "correctAnswers": {
                                        "answers": [{"value": "O(1)"}] # The Correct Answer
                                    },
                                    "whenRight": {"text": "Correct! Direct access is constant time."},
                                    "whenWrong": {"text": "Incorrect. Arrays use direct addressing."}
                                },
                                "choiceQuestion": {
                                    "type": "RADIO",
                                    "options": [
                                        {"value": "O(1)"},
                                        {"value": "O(n)"},
                                        {"value": "O(log n)"},
                                        {"value": "O(n^2)"},
                                    ],
                                    "shuffle": True,
                                },
                            }
                        },
                    },
                    "location": {"index": 0},
                }
            },
        ]
    }

    # 4. Execute the update
    form_service.forms().batchUpdate(formId=form_id, body=update_request).execute()
    print("✅ Success! Check your Google Drive.")

if __name__ == "__main__":
    create_quiz()