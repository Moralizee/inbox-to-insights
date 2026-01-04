from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import email
from email import policy

app = FastAPI()

# ---- CORS FIX ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ping")
def ping():
    return {"message": "pong"}


@app.post("/parse-email")
async def parse_email(file: UploadFile = File(...)):
    contents = await file.read()

    msg = email.message_from_bytes(contents, policy=policy.default)

    subject = msg["subject"]
    sender = msg["from"]

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_content()
                break
    else:
        body = msg.get_content()

    preview = body[:200] if body else ""

    return {
        "subject": subject,
        "from": sender,
        "preview": preview,
    }
