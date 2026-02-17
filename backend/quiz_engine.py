import fitz  # PyMuPDF
import google.generativeai as genai
from dotenv import load_dotenv
import json
import os
from PIL import Image
import io

# --- CONFIGURATION ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("Gemini API Key not found. Make sure it's in the .env file.")

genai.configure(api_key=GEMINI_API_KEY)

def get_model():
    return genai.GenerativeModel('gemini-2.5-flash')

def pdf_page_to_image(page):
    """
    Converts a PDF page into a PIL Image object (for Gemini Vision).
    """
    pix = page.get_pixmap()
    img_data = pix.tobytes("png")
    return Image.open(io.BytesIO(img_data))

def extract_content_smart(pdf_path, max_pages=20):
    """
    Hybrid extraction:
    1. Tries to read text.
    2. If text is < 50 chars (scanned), converts page to image.
    3. Limits to 'max_pages' to prevent crashing the API.
    """
    doc = fitz.open(pdf_path)
    content_parts = []
    
    print(f"📄 Analyzing PDF ({len(doc)} pages)...")
    
    # Loop through pages (limit to max_pages to be safe)
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
            
        text = page.get_text()
        
        # LOGIC: If page has real text, use it. If not, use Vision.
        if len(text.strip()) > 50:
            content_parts.append(f"--- Page {i+1} ---\n{text}")
        else:
            print(f"📷 Page {i+1} looks scanned. Switching to Vision...")
            img = pdf_page_to_image(page)
            content_parts.append(img) # Add the actual Image object
            content_parts.append(f"--- End of Page {i+1} ---")
            
    return content_parts

def generate_quiz_json(content, num_questions=20):
    model = get_model()
    
    print("🧠 Sending data to Gemini... thinking...")
    
    # We construct a list of [Text, Image, Text, Image...] to send to Gemini
    prompt_instruction = f"""
    You are a teacher. Create a {num_questions}-question multiple choice quiz in RAW JSON format.
    
    RULES:
    1. Output strictly valid JSON.
    2. No Markdown. No ```json.
    3. Format:
    [
        {{
            "question": "Question text",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A"
        }}
    ]
    """
    
    # Gemini 1.5 Flash accepts a list of mixed content (Text + Images)
    request_content = [prompt_instruction] + content
    
    try:
        response = model.generate_content(request_content)
        
        clean_text = response.text.strip()
        clean_text = clean_text.replace("```json", "").replace("```", "")
        
        start = clean_text.find('[')
        end = clean_text.rfind(']') + 1
        if start != -1 and end != -1:
            clean_text = clean_text[start:end]
            
        return json.loads(clean_text)

    except Exception as e:
        print(f"❌ AI ERROR: {e}")
        return []