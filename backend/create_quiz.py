import os
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# --- CONFIGURATION ---
SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]

# Optional env-based settings
USER_EMAIL = os.getenv("QUIZGEN_USER_EMAIL", "utkarshmalik088@gmail.com")
FOLDER_ID = os.getenv("QUIZGEN_FOLDER_ID", "1vmg5rrYVFu1OROeEu9stSgqfwy0QIJ0K")
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")


def _oauth_credentials_from_env():
    """Build OAuth credentials from env vars for user-owned forms publishing."""
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_OAUTH_REFRESH_TOKEN")
    access_token = os.getenv("GOOGLE_OAUTH_ACCESS_TOKEN")

    if not client_id or not client_secret or not refresh_token:
        return None

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )

    if not creds.valid:
        creds.refresh(Request())

    return creds


def _service_account_credentials():
    """Fallback auth mode using a service account key file."""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(
            "Missing OAuth env vars and service account file. "
            "Set GOOGLE_OAUTH_CLIENT_ID/GOOGLE_OAUTH_CLIENT_SECRET/GOOGLE_OAUTH_REFRESH_TOKEN "
            f"or provide {SERVICE_ACCOUNT_FILE}."
        )

    return service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )


def get_authenticated_services():
    """Authenticate with OAuth (preferred) and fallback to service account if needed."""
    try:
        creds = _oauth_credentials_from_env()
        auth_mode = "OAuth"

        if creds is None:
            creds = _service_account_credentials()
            auth_mode = "Service Account"

        print(f"🔐 Google auth mode: {auth_mode}")
        form_service = build("forms", "v1", credentials=creds)
        drive_service = build("drive", "v3", credentials=creds)
        return form_service, drive_service

    except Exception as e:
        print(f"❌ Authentication Failed: {e}")
        raise e


def json_to_forms_requests(quiz_data):
    """Converts the AI's JSON into Google Forms batchUpdate requests."""
    requests = []

    requests.append(
        {
            "updateSettings": {
                "settings": {"quizSettings": {"isQuiz": True}},
                "updateMask": "quizSettings.isQuiz",
            }
        }
    )

    for index, q in enumerate(quiz_data):
        options = q.get("options", [])
        if len(options) < 2:
            # Skip malformed questions instead of crashing the entire publish flow.
            continue
        correct_answer_text = q.get("correct_answer", "")
        final_correct_value = options[0]

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
                                },
                            },
                            "choiceQuestion": {
                                "type": "RADIO",
                                "options": [{"value": opt} for opt in options],
                                "shuffle": True,
                            },
                        }
                    },
                },
                "location": {"index": index},
            }
        }
        requests.append(new_question)

    return requests


def create_quiz(title, questions):
    try:
        form_service, drive_service = get_authenticated_services()

        form_body = {"info": {"title": title, "documentTitle": title}}
        form = form_service.forms().create(body=form_body).execute()
        form_id = form["formId"]
        edit_url = f"https://docs.google.com/forms/d/{form_id}/edit"

        if FOLDER_ID:
            file = drive_service.files().get(fileId=form_id, fields="parents").execute()
            previous_parents = ",".join(file.get("parents", []))

            drive_service.files().update(
                fileId=form_id,
                addParents=FOLDER_ID,
                removeParents=previous_parents,
                fields="id, parents",
            ).execute()

        if USER_EMAIL:
            print(f"🤝 Sharing with {USER_EMAIL}...")
            drive_service.permissions().create(
                fileId=form_id,
                body={"type": "user", "role": "writer", "emailAddress": USER_EMAIL},
            ).execute()

        if questions:
            print(f"📝 Adding {len(questions)} questions...")
            update_requests = json_to_forms_requests(questions)
            form_service.forms().batchUpdate(
                formId=form_id,
                body={"requests": update_requests},
            ).execute()

        print("✅ Quiz created successfully!")
        return edit_url

    except Exception as e:
        print(f"❌ Error in create_quiz: {e}")
        raise e


if __name__ == "__main__":
    test_questions = [
        {
            "question": "What is the capital of France?",
            "options": ["Berlin", "Madrid", "Paris", "Rome"],
            "correct_answer": "Paris",
        }
    ]
    try:
        url = create_quiz("Test Quiz from Robot", test_questions)
        print(f"🔗 Access your quiz here: {url}")
    except Exception as e:
        print(f"Test Failed: {e}")
