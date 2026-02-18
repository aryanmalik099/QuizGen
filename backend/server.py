import os
import shutil
import uvicorn
from typing import List
from io import BytesIO
from PIL import Image

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv

# Your custom modules
from quiz_engine import extract_content_smart, generate_quiz_json
from create_quiz import create_quiz 

# Load environment variables
load_dotenv()

app = FastAPI()

# --- 1. CONFIGURATION & MIDDLEWARE ---

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

app.add_middleware(
    SessionMiddleware, 
    secret_key=os.getenv("SECRET_KEY", "random_string"),
    same_site="none",      
    https_only=True        
)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "https://quizgen-web.vercel.app", 
    os.getenv("FRONTEND_URL")         
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAUTH CONFIGURATION
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile https://www.googleapis.com/auth/forms.body https://www.googleapis.com/auth/drive.file'
    }
)

# --- 2. HELPER FUNCTIONS ---

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

        sanitized.append({
            "question": title,
            "options": options,
            "correct_answer": correct_answer,
        })

    if not sanitized:
        raise HTTPException(status_code=400, detail="At least one valid question is required.")

    return sanitized


@app.get("/")
def health_check():
    return {"status": "awake", "message": "I am ready to work!"}

# --- 3. AUTH ROUTES ---

@app.get("/login")
async def login(request: Request):
    current_backend_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{current_backend_url}/auth/callback"
    print(f"🔀 Redirecting Google to: {redirect_uri}")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/callback")
async def auth_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        user = token.get('userinfo')
        
        # Save User & Token in Session Cookie
        request.session['user'] = user
        request.session['token'] = token 
        
        # Redirect back to Frontend
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        return RedirectResponse(url=frontend_url)
    except Exception as e:
        return {"error": f"Auth failed: {str(e)}"}

@app.get("/user")
async def get_current_user(request: Request):
    # Frontend calls this to check "Am I logged in?"
    return request.session.get('user')

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out"}

# --- 4. CORE APP ROUTES ---

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
                # Save temp file for PyMuPDF
                temp_filename = f"temp_{file.filename}"
                with open(temp_filename, "wb") as f:
                    f.write(file_content)
                
                # Extract text/images
                combined_content.extend(extract_content_smart(temp_filename))
                
                # Clean up
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

            elif file.content_type.startswith("image/"):
                print(f"📸 Processing Image: {file.filename}")
                img = Image.open(BytesIO(file_content))
                combined_content.append(img)
                combined_content.append(f"[Image Source: {file.filename}]")

        # 2. Pass to Gemini
        quiz_data = generate_quiz_json(combined_content, num_questions=20)
        
        return {"status": "success", "quiz_data": quiz_data}
    
    except Exception as e:
        print(f"❌ Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/publish-quiz")
async def publish_quiz_endpoint(quiz_data: dict, request: Request):
    # 1. Sanitize Data (Prevent Crashes)
    title = str(quiz_data.get("title", "AI Generated Quiz")).strip() or "AI Generated Quiz"
    questions = sanitize_questions(quiz_data.get("questions", []))
    
    # 2. Check Auth (Are we User or Robot?)
    user_token = request.session.get('token')
    user_creds = None

    if user_token:
        print(f"👤 Publishing as User: {request.session.get('user')['email']}")
        user_creds = {
            "token": user_token["access_token"],
            "refresh_token": user_token.get("refresh_token"),
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "scopes": ["https://www.googleapis.com/auth/forms.body", "https://www.googleapis.com/auth/drive.file"]
        }
    else:
        print("🤖 No User found. Publishing as Robot.")

    try:
        # 3. Create the Form
        form_url = create_quiz(title, questions, user_creds_dict=user_creds)
        return {"status": "success", "form_url": form_url}

    except Exception as e:
        print(f"❌ Publish Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)