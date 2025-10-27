from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import base64

load_dotenv()

app = FastAPI(title="GPT Python Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

CLIENT_CONFIG = {
    "web": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [REDIRECT_URI],
    }
}

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
]

user_sessions = {}

@app.get("/")
async def root():
    return {"message": "GPT Python Backend API", "status": "running"}

@app.get("/login")
@app.get("/auth/google")
async def google_login():
    try:
        flow = Flow.from_client_config(
            CLIENT_CONFIG,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent"
        )
        
        return {"authorization_url": authorization_url, "state": state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initiating OAuth: {str(e)}")

@app.get("/oauth2callback")
async def oauth2callback(request: Request):
    try:
        code = request.query_params.get("code")
        
        if not code:
            raise HTTPException(status_code=400, detail="No authorization code received")
        
        flow = Flow.from_client_config(
            CLIENT_CONFIG,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
        
        user_info = {
            "email": id_info.get("email"),
            "name": id_info.get("name"),
            "picture": id_info.get("picture"),
            "sub": id_info.get("sub"),
        }
        
        user_sessions[user_info["sub"]] = {
            "credentials": {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes,
            },
            "user_info": user_info,
        }
        
        import urllib.parse
        user_data = urllib.parse.quote(json.dumps(user_info))
        frontend_url = f"http://localhost:5173/?user={user_data}"
        return RedirectResponse(url=frontend_url)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth callback error: {str(e)}")

@app.post("/api/fetch-emails")
async def fetch_emails(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
        
        if user_id not in user_sessions:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        session_data = user_sessions[user_id]
        creds_data = session_data["credentials"]
        
        creds = Credentials(
            token=creds_data["token"],
            refresh_token=creds_data.get("refresh_token"),
            token_uri=creds_data["token_uri"],
            client_id=creds_data["client_id"],
            client_secret=creds_data["client_secret"],
            scopes=creds_data["scopes"],
        )
        
        service = build("gmail", "v1", credentials=creds)
        
        results = service.users().messages().list(
            userId="me",
            q="is:unread",
            maxResults=10
        ).execute()
        
        messages = results.get("messages", [])
        
        if not messages:
            return {"success": True, "emails": [], "message": "No unread emails found"}
        
        def get_email_body(payload):
            body = ""
            
            if "parts" in payload:
                for part in payload["parts"]:
                    if part["mimeType"] == "text/plain":
                        if "data" in part["body"]:
                            body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                            break
                    elif "parts" in part:
                        body = get_email_body(part)
                        if body:
                            break
            elif "body" in payload and "data" in payload["body"]:
                body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
            
            return body
        
        email_list = []
        for msg in messages:
            msg_data = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="full"
            ).execute()
            
            headers = msg_data["payload"]["headers"]
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
            date = next((h["value"] for h in headers if h["name"] == "Date"), "Unknown")
            
            body = get_email_body(msg_data["payload"])
            snippet = msg_data.get("snippet", "")
            full_content = body if body else snippet
            
            email_list.append({
                "id": msg["id"],
                "subject": subject,
                "from": sender,
                "date": date,
                "snippet": snippet,
                "full_content": full_content[:2000],
            })
        
        return {
            "success": True,
            "emails": email_list,
            "count": len(email_list)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching emails: {str(e)}")

@app.post("/api/prioritize-emails")
async def prioritize_emails(request: Request):
    try:
        data = await request.json()
        emails = data.get("emails", [])
        
        if not emails:
            raise HTTPException(status_code=400, detail="No emails provided")
        
        prioritized_emails = []
        
        for email in emails:
            email_content = email.get('full_content', email.get('snippet', ''))
            
            prompt = f"""Analyze this email's SUBJECT and CONTENT to determine urgency level.

EMAIL SUBJECT: {email.get('subject', 'No Subject')}
FROM: {email.get('from', 'Unknown')}
EMAIL CONTENT: {email_content}

Specifically check for these urgency keywords in BOTH subject and content:

RED (URGENT) - Label as RED if ANY of these words/phrases are present:
- "urgent", "ASAP", "immediate", "critical", "emergency", "deadline today", "action required", "important", "time-sensitive", "overdue", "final notice"

YELLOW (LESS URGENT) - Label as YELLOW if these words are present:
- "reminder", "follow-up", "meeting", "review", "update", "please respond", "FYI", "scheduled", "upcoming"

GREEN (NON-URGENT) - Label as GREEN if it's:
- Newsletters, promotional emails, automated notifications, informational updates, social media notifications

First, check if any RED keywords are present in subject or content. If found, classify as RED.
If no RED keywords, check for YELLOW keywords. If found, classify as YELLOW.
If no RED or YELLOW keywords, classify as GREEN.

Respond with ONLY one word: RED, YELLOW, or GREEN."""
            
            summary_prompt = f"""Summarize the following email concisely. The summary should be 30-40% of the original email length, capturing only the key points and main message.

EMAIL SUBJECT: {email.get('subject', 'No Subject')}
EMAIL CONTENT: {email_content}

Provide a clear, concise summary that highlights:
- Main purpose of the email
- Key information or requests
- Important details or deadlines

Summary:"""
            
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an expert email priority classifier. You must check for specific urgency keywords in both subject and content. First look for RED keywords, then YELLOW, otherwise GREEN. Respond only with RED, YELLOW, or GREEN."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=10,
                    temperature=0.0,
                )
                
                urgency = response.choices[0].message.content.strip().upper() if response.choices[0].message.content else "YELLOW"
                
                if urgency not in ["RED", "YELLOW", "GREEN"]:
                    urgency = "YELLOW"
                
            except Exception as e:
                print(f"Error analyzing email: {str(e)}")
                urgency = "YELLOW"
            
            try:
                summary_response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an expert at summarizing emails concisely. Create summaries that are 30-40% of the original length."},
                        {"role": "user", "content": summary_prompt}
                    ],
                    max_tokens=200,
                    temperature=0.3,
                )
                
                summary = summary_response.choices[0].message.content.strip() if summary_response.choices[0].message.content else email.get('snippet', 'Summary not available')
                
            except Exception as e:
                print(f"Error summarizing email: {str(e)}")
                summary = email.get('snippet', 'Summary not available')
            
            prioritized_emails.append({
                **email,
                "urgency": urgency,
                "urgency_color": urgency.lower(),
                "summary": summary
            })
        
        urgency_order = {"RED": 0, "YELLOW": 1, "GREEN": 2}
        prioritized_emails.sort(key=lambda x: urgency_order.get(x["urgency"], 1))
        
        return {
            "success": True,
            "emails": prioritized_emails,
            "summary": {
                "red": sum(1 for e in prioritized_emails if e["urgency"] == "RED"),
                "yellow": sum(1 for e in prioritized_emails if e["urgency"] == "YELLOW"),
                "green": sum(1 for e in prioritized_emails if e["urgency"] == "GREEN"),
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error prioritizing emails: {str(e)}")

@app.post("/api/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        message = data.get("message")
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": message}
            ],
            max_tokens=1000,
            temperature=0.7,
        )
        
        reply = response.choices[0].message.content
        
        return {
            "success": True,
            "reply": reply,
            "model": "gpt-3.5-turbo"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "google_oauth": "configured" if GOOGLE_CLIENT_ID else "not configured",
        "openai": "configured" if OPENAI_API_KEY else "not configured"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)