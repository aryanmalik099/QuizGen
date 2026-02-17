from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import shutil
import os
import uvicorn
from io import BytesIO
from PIL import Image

# ✅ NEW IMPORT: We only need the main function now
from quiz_engine import extract_content_smart, generate_quiz_json
from create_quiz import create_quiz 

app = FastAPI()


def sanitize_questions(raw_questions):
    """Normalize client payload so publish never crashes on malformed questions."""
    sanitized = []

    for index, question in enumerate(raw_questions):
        if not isinstance(question, dict):
            raise HTTPException(status_code=400, detail=f"Question {index + 1} is invalid.")

        title = str(question.get("question", "")).strip()
        options = [str(option).strip() for option in question.get("options", []) if str(option).strip()]

        if not title:
            raise HTTPException(status_code=400, detail=f"Question {index + 1} is missing text.")
        if len(options) < 2:
            raise HTTPException(status_code=400, detail=f"Question {index + 1} needs at least 2 options.")

        correct_answer = str(question.get("correct_answer", "")).strip()
        if correct_answer not in options:
            correct_answer = options[0]

        sanitized.append(
            {
                "question": title,
                "options": options,
                "correct_answer": correct_answer,
            }
        )

    if not sanitized:
        raise HTTPException(status_code=400, detail="At least one valid question is required.")

    return sanitized

# Allow CORS for Vercel/Localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
                combined_content.extend(extract_content_smart(temp_filename))
                os.remove(temp_filename)

            elif file.content_type.startswith("image/"):
                print(f"📸 Processing Image: {file.filename}")
                img = Image.open(BytesIO(file_content))
                combined_content.append(img)
                combined_content.append(f"[Image Source: {file.filename}]")

        # 2. Pass to Gemini
        quiz_data = generate_quiz_json(combined_content, num_questions=5)
        
        return {"status": "success", "quiz_data": quiz_data}
    
    except Exception as e:
        print(f"❌ Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/publish-quiz")
async def publish_quiz_endpoint(quiz_data: dict):
    # ✅ SIMPLIFIED: The Robot handles all the auth logic now
    title = str(quiz_data.get("title", "AI Generated Quiz")).strip() or "AI Generated Quiz"
    questions = sanitize_questions(quiz_data.get("questions", []))
    
    try:
        # This function now does: Auth -> Create Form -> Share with You -> Add Questions
        form_url = create_quiz(title, questions)
        
        return {"status": "success", "form_url": form_url}

    except Exception as e:
        print(f"❌ Publish Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Render assigns a port automatically
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
