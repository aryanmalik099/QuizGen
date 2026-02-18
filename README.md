# QuizGen — Detailed Project Guide

This document is a full technical guide for QuizGen setup, architecture, API usage, OAuth configuration, deployment, and troubleshooting.

## Overview

QuizGen converts learning material (PDFs/images) into editable multiple-choice quizzes and publishes them to Google Forms.

### High-level flow

1. Upload study material in frontend.
2. Backend extracts text/images.
3. Gemini generates quiz JSON.
4. User edits/reorders questions.
5. Backend publishes to Google Forms.

## Architecture

### Frontend (`frontend/`)

- React + Vite + Tailwind.
- Main UI is `src/App.jsx` with a 3-step state flow:
  - Upload
  - Edit
  - Publish success
- Uses `axios` calls to backend endpoints.

### Backend (`backend/`)

- FastAPI app in `server.py`.
- Quiz extraction/generation in `quiz_engine.py`.
- Google auth + form creation in `create_quiz.py`.

## Backend endpoints

### `POST /generate-quiz`

Accepts multipart `files`.

- Max 1 PDF
- Max 10 images

Returns:

```json
{
  "status": "success",
  "quiz_data": [
    {
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "A"
    }
  ]
}
```

### `POST /publish-quiz`

Accepts:

```json
{
  "title": "Quiz Title",
  "questions": [
    {
      "question": "...",
      "options": ["...", "...", "...", "..."],
      "correct_answer": "..."
    }
  ]
}
```

Backend sanitizes payload and creates a Google Form quiz.

## Environment variables

Use `backend/.env.example` as template.

### Required

- `GEMINI_API_KEY`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`

### Optional

- `GOOGLE_ACCESS_TOKEN`
- `QUIZGEN_USER_EMAIL`
- `QUIZGEN_FOLDER_ID`

### Fallback

- `GOOGLE_SERVICE_ACCOUNT_FILE`

## Local setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env`:

```bash
VITE_API_URL=http://localhost:8000
```

Run:

```bash
npm run dev
```

## OAuth setup (recommended)

1. Enable Google Forms API + Drive API in Google Cloud.
2. Configure OAuth consent screen.
3. Create OAuth client **Web application**.
4. Add redirect URI:
   - `https://developers.google.com/oauthplayground`
5. In OAuth Playground, use your own credentials and request scopes:
   - `https://www.googleapis.com/auth/forms.body`
   - `https://www.googleapis.com/auth/drive`
   - `https://www.googleapis.com/auth/drive.file`
6. Exchange code and copy `refresh_token`.
7. Put values in backend env.

## Common issues

### `redirect_uri_mismatch`

- Wrong OAuth client type or missing redirect URI.
- Use a Web application client and add OAuth Playground URI.

### Publish 500

- Missing OAuth env vars
- Invalid token
- Malformed questions payload

### Gemini errors

- Missing/invalid `GEMINI_API_KEY`
- Source content too noisy or oversized

## Notes

- Generation is currently set to 20 questions in backend.
- PDF extraction currently processes up to ~20 pages.
- Upload limits are enforced in backend and frontend.
