Email RAG — Python (FastAPI) + React

A Reference implementation of a Retrieval-Augmented Generation (RAG) style project that:
•Allows users to sign in only with Google (OAuth)
•Imports unread Gmail messages (subject, sender, date, and full message)
•Sends each email (subject + body) to an LLM (OpenAI) to classify urgency into Red / Yellow / Green
•Presents prioritized results in a React frontend
________________________________________

Architecture:-

Email RAG — Python (FastAPI) + React
A Reference implementation of a Retrieval-Augmented Generation (RAG) style project that:
•Allows users to sign in only with Google (OAuth)
•Imports unread Gmail messages (subject, sender, date, and full message)
•Sends each email (subject + body) to an LLM (OpenAI) to classify urgency into Red / Yellow / Green
•Presents prioritized results in a React frontend
This README describes architecture, setup, environment variables, important implementation notes and example prompts for the LLM classifier.

________________________________________

Prerequisites:-

•React frontend
•Python 3.10+ (recommended)
•Google Cloud account to create OAuth       credentials and enable Gmail API
•OpenAI account and API key 

__________________________________________

Google Cloud & Gmail API setup :-

1.Create a Google Cloud project or use an existing one.
2.Enable Gmail API for the project.
3.Create OAuth 2.0 Credentials (OAuth client ID) — choose Web application and add authorized redirect URIs (e.g. http://localhost:8000/auth/callback for backend).
4.Note these values:
	GOOGLE_CLIENT_ID
	GOOGLE_CLIENT_SECRET
5.OAuth scopes required (minimum):
    https://www.googleapis.com/auth/gmail.readonly (fetch messages)
	openid email profile (basic identity)
For production, you will need to configure OAuth consent screen and verify scopes as required by Google.
________________________________________

Environment variables (example .env):-

GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
REDIRECT_URI=http://localhost:8000/auth/callback

__________________________________________

Install dependencies :-

pip install fastapi uvicorn python-dotenv google-auth google-auth-oauthlib google-api-python-client requests openai

__________________________________________

Backend (Python) quickstart :-

c:\Users\HP\Desktop\email-priority\backend
>> .\venv\Scripts\Activate.ps1
>> python main.py

Frontend (React) quickstart :-

c:\Users\HP\Desktop\email-priority\frontend
>> npm install
>> npm start

OR

>> npm run dev

__________________________________________

