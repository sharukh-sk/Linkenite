import os
import re
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import heapq
from transformers import pipeline
import openai

# Initialize OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise Exception("OPENAI_API_KEY environment variable not set")

app = FastAPI()

# Load dataset CSV
DATASET_PATH = "MultipleFiles/68b1acd44f393_Sample_Support_Emails_Dataset.csv"
df = pd.read_csv(DATASET_PATH)

# Initialize sentiment pipeline (Hugging Face)
sentiment_pipeline = pipeline("sentiment-analysis")

# Urgency keywords
URGENT_KEYWORDS = ['immediately', 'critical', 'cannot access', 'urgent', 'asap', 'blocked', 'down', 'error']

# Regex for phone and email extraction
PHONE_REGEX = r'(\+?\d{1,3}[-.\s]?)?(\$?\d{3}\$?[-.\s]?)?\d{3}[-.\s]?\d{4}'
EMAIL_REGEX = r'[\w\.-]+@[\w\.-]+'

# Pydantic models for API responses
class Email(BaseModel):
    id: int
    sender: str
    subject: str
    body: str
    sent_date: str
    sentiment: str
    priority: str
    phone_numbers: List[str]
    alternate_emails: List[str]
    customer_requests: List[str]
    ai_response: Optional[str] = None

class ResponseUpdate(BaseModel):
    ai_response: str

# Helper functions
def is_urgent(text: str) -> bool:
    text_lower = text.lower()
    return any(word in text_lower for word in URGENT_KEYWORDS)

def analyze_sentiment(text: str) -> str:
    truncated = text[:512]
    result = sentiment_pipeline(truncated)[0]
    label = result['label']
    if label == 'NEGATIVE':
        return 'Negative'
    elif label == 'POSITIVE':
        return 'Positive'
    else:
        return 'Neutral'

def extract_info(text: str):
    phones = re.findall(PHONE_REGEX, text)
    phones = [''.join(p) for p in phones if ''.join(p).strip() != '']
    emails = re.findall(EMAIL_REGEX, text)
    requests = []
    lowered = text.lower()
    if 'refund' in lowered:
        requests.append('Refund request')
    if 'cancel' in lowered:
        requests.append('Cancellation request')
    if 'billing error' in lowered or 'charged twice' in lowered:
        requests.append('Billing error')
    if 'password' in lowered and 'reset' in lowered:
        requests.append('Password reset issue')
    if 'login' in lowered or 'log into' in lowered:
        requests.append('Login issue')
    if 'servers are down' in lowered or 'downtime' in lowered:
        requests.append('Downtime / Server issue')
    if 'integration' in lowered:
        requests.append('Integration query')
    return phones, emails, requests

def generate_ai_response(email_body: str, sentiment: str, requests: List[str]) -> str:
    # Compose prompt for OpenAI GPT-4
    prompt = f"""
You are a professional customer support assistant.

Customer email:
\"\"\"{email_body}\"\"\"

Customer sentiment: {sentiment}
Customer requests/issues: {', '.join(requests) if requests else 'None'}

Write a professional, friendly, and empathetic response. If the customer is frustrated, acknowledge their feelings. Reference any mentioned products or issues.
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        # Fallback response on error
        return "Dear Customer,\n\nThank you for contacting us. We are reviewing your request and will get back to you shortly.\n\nBest regards,\nSupport Team"

# Load and process emails
def load_and_process_emails():
    emails = []
    for idx, row in df.iterrows():
        subject = str(row['subject'])
        # Filter by subject keywords
        if any(k.lower() in subject.lower() for k in ['support', 'query', 'request', 'help']):
            body = str(row['body'])
            combined_text = subject + " " + body
            priority = 'Urgent' if is_urgent(combined_text) else 'Not urgent'
            sentiment = analyze_sentiment(body)
            phones, alt_emails, requests = extract_info(body)
            ai_response = generate_ai_response(body, sentiment, requests)
            emails.append(Email(
                id=idx,
                sender=row['sender'],
                subject=subject,
                body=body,
                sent_date=row['sent_date'],
                sentiment=sentiment,
                priority=priority,
                phone_numbers=phones,
                alternate_emails=alt_emails,
                customer_requests=requests,
                ai_response=ai_response
            ))
    # Sort emails by priority (Urgent first)
    emails.sort(key=lambda e: 0 if e.priority == 'Urgent' else 1)
    return emails

# Cache emails on startup
EMAILS_CACHE = load_and_process_emails()

@app.get("/emails", response_model=List[Email])
def get_emails():
    return EMAILS_CACHE

@app.post("/emails/{email_id}/response")
def update_response(email_id: int, response_update: ResponseUpdate):
    for email in EMAILS_CACHE:
        if email.id == email_id:
            email.ai_response = response_update.ai_response
            return {"message": "Response updated"}
    raise HTTPException(status_code=404, detail="Email not found")