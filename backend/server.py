from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from io import BytesIO
from PIL import Image
from typing import List
import shutil
import os
import json

# Import your existing logic
from quiz_engine import extract_content_smart, generate_quiz_json
from create_quiz import get_credentials
from googleapiclient.discovery import build

app = FastAPI()

# Enable CORS (Allows your React Frontend to talk to this Python Backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, change this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- HELPER: The Logic from main.py ---
def json_to_forms_requests(quiz_data):
    requests = []
    requests.append({
        "updateSettings": {
            "settings": {"quizSettings": {"isQuiz": True}},
            "updateMask": "quizSettings.isQuiz"
        }
    })
    for index, q in enumerate(quiz_data):
        options = q.get("options", [])
        raw_correct = q.get("correct_answer", "")
        final_correct_answer = options[0] if options else "Error"
        
        if raw_correct in options:
            final_correct_answer = raw_correct
        else:
            for opt in options:
                if raw_correct.strip().lower() == opt.strip().lower():
                    final_correct_answer = opt
                    break

        question_item = {
            "createItem": {
                "item": {
                    "title": q["question"],
                    "questionItem": {
                        "question": {
                            "required": True,
                            "grading": {
                                "pointValue": 1,
                                "correctAnswers": {"answers": [{"value": final_correct_answer}]},
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
        requests.append(question_item)
    return requests

# --- ENDPOINT 1: Upload PDF & Generate Draft Questions ---
@app.post("/generate-quiz")
async def generate_quiz_endpoint(files: List[UploadFile] = File(...)):
    # 1. ENFORCE LIMITS
    pdf_count = sum(1 for f in files if f.content_type == "application/pdf")
    img_count = sum(1 for f in files if f.content_type.startswith("image/"))

    if pdf_count > 1:
        raise HTTPException(status_code=400, detail="Limit exceeded: Only 1 PDF allowed.")
    if img_count > 10:
        raise HTTPException(status_code=400, detail="Limit exceeded: Maximum 10 images allowed.")

    combined_content = []

    try:
        for file in files:
            file_content = await file.read()
            
            if file.content_type == "application/pdf":
                print(f"📄 Processing PDF: {file.filename}")
                temp_filename = f"temp_{file.filename}"
                with open(temp_filename, "wb") as f:
                    f.write(file_content)
                # Smart extraction handles text/images inside the PDF
                combined_content.extend(extract_content_smart(temp_filename))
                os.remove(temp_filename)

            elif file.content_type.startswith("image/"):
                print(f"📸 Processing Image: {file.filename}")
                img = Image.open(BytesIO(file_content))
                combined_content.append(img)
                combined_content.append(f"[Image Source: {file.filename}]")

        # 2. Pass the combined list (Text + Images) to Gemini
        quiz_data = generate_quiz_json(combined_content, num_questions=5)
        
        return {"status": "success", "quiz_data": quiz_data}
    
    except Exception as e:
        print(f"❌ Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- ENDPOINT 2: Publish to Google Forms ---
@app.post("/publish-quiz")
async def publish_quiz_endpoint(quiz_data: dict):
    # The frontend sends us the FINAL approved list of questions
    questions = quiz_data.get("questions", [])
    title = quiz_data.get("title", "Quiz")
    
    try:
        creds = get_credentials()
        form_service = build("forms", "v1", credentials=creds)

        # Create blank form
        form_info = {"info": {"title": title, "documentTitle": title}}
        form = form_service.forms().create(body=form_info).execute()
        form_id = form["formId"]
        form_url = f"https://docs.google.com/forms/d/{form_id}/edit"

        # Add questions
        if questions:
            update_requests = json_to_forms_requests(questions)
            form_service.forms().batchUpdate(formId=form_id, body={"requests": update_requests}).execute()
        
        return {"status": "success", "form_url": form_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Render assigns a port automatically in the environment variable "PORT"
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)