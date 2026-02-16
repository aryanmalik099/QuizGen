import os
import json
from quiz_engine import extract_text_from_pdf, generate_quiz_json
from create_quiz import get_credentials
from googleapiclient.discovery import build

def json_to_forms_requests(quiz_data):
    """
    Converts AI JSON into Google Forms API format with SAFETY CHECKS.
    """
    requests = []
    
    # 1. Set Quiz Settings (Make it a graded quiz)
    requests.append({
        "updateSettings": {
            "settings": {"quizSettings": {"isQuiz": True}},
            "updateMask": "quizSettings.isQuiz"
        }
    })

    # 2. Add Questions
    for index, q in enumerate(quiz_data):
        options = q.get("options", [])
        raw_correct = q.get("correct_answer", "")
        
        # --- THE FIX: SAFETY MATCHING ---
        # Google requires the correct answer to be an EXACT byte-for-byte string match.
        # We try to find the best match from the options list.
        
        final_correct_answer = options[0] # Default to Option A if match fails (prevents crash)
        
        if raw_correct in options:
            # Perfect match found
            final_correct_answer = raw_correct
        else:
            # Fuzzy match: Try ignoring case or whitespace
            print(f"⚠️ Warning: Exact match not found for Q{index+1}. Fuzzy matching '{raw_correct}'...")
            for opt in options:
                if raw_correct.strip().lower() == opt.strip().lower():
                    final_correct_answer = opt
                    break
        # --------------------------------

        # Create the question object
        question_item = {
            "createItem": {
                "item": {
                    "title": q["question"],
                    "questionItem": {
                        "question": {
                            "required": True,
                            "grading": {
                                "pointValue": 1,
                                "correctAnswers": {
                                    "answers": [{"value": final_correct_answer}]
                                },
                                "whenRight": {"text": "Correct!"},
                                "whenWrong": {"text": f"Explanation: {q.get('explanation', '')}"}
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

def main():
    # 1. Get Input
    pdf_path = "notes.pdf"
    if not os.path.exists(pdf_path):
        print("❌ Error: 'notes.pdf' not found. Please add a PDF file.")
        return

    # 2. Extract & Generate (The Brain)
    print("Step 1: Reading PDF...")
    text = extract_text_from_pdf(pdf_path)
    
    print("Step 2: Generating Questions with AI...")
    # We ask for a small batch to ensure speed/accuracy
    quiz_data = generate_quiz_json(text, num_questions=5) 
    
    if not quiz_data:
        print("❌ AI failed to generate questions.")
        return

    # 3. Create Form (The Hands)
    print("Step 3: Creating Google Form...")
    try:
        creds = get_credentials()
        form_service = build("forms", "v1", credentials=creds)

        # Create blank form
        form_info = {
            "info": {
                "title": "AI Generated Quiz",
                "documentTitle": "Notes Quiz",
            }
        }
        form = form_service.forms().create(body=form_info).execute()
        form_id = form["formId"]
        form_url = form["responderUri"]

        # 4. Populate Form
        print("Step 4: Adding Questions...")
        update_requests = json_to_forms_requests(quiz_data)
        form_service.forms().batchUpdate(formId=form_id, body={"requests": update_requests}).execute()

        print("\n" + "="*40)
        print(f"✅ SUCCESS! Quiz Ready: {form_url}")
        print("="*40)

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        # Print the data to see what went wrong
        print("Debug Data that failed:")
        print(json.dumps(quiz_data, indent=2))

if __name__ == "__main__":
    main()