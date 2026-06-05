from datetime import datetime, timedelta
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from sqlalchemy.orm import Session
from jose import jwt

from database import SessionLocal
from auth import require_admin
from models import User
from utils.email_service import send_invitation_email

router = APIRouter()

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class InviteUserRequest(BaseModel):
    email: EmailStr
    role: str


@router.post("/invite-user")
def invite_user(
    payload: InviteUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):

    role = payload.role.lower()

    if role not in ["admin", "analyst"]:
        raise HTTPException(
            status_code=400,
            detail="Role must be admin or analyst"
        )

    existing_user = (
        db.query(User)
        .filter(
            User.email == payload.email.lower(),
            User.is_deleted == False
        )
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="User already exists"
        )

    invite_token = jwt.encode(
        {
            "email": payload.email.lower(),
            "role": role,
            "company_id": current_user.company_id,
            "type": "invite",
            "exp": datetime.utcnow() + timedelta(days=7)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    invite_link = f"{FRONTEND_URL}/accept-invitation?token={invite_token}"

    # Send email
    success = send_invitation_email(
        recipient_email=payload.email,
        recipient_name=payload.email.split("@")[0].title(),   # Better name formatting
        invite_link=invite_link
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send invitation email")

    return {
        "message": "Invitation sent successfully",
        "email": payload.email,
        "role": role,
        "invite_link": invite_link,
        "invite_token": invite_token
    }


@router.get("/test-email")
def test_email():
    success = send_invitation_email(
        recipient_email="hirakzenydata@gmail.com",
        recipient_name="Hirak",                    # ← Fixed: Added recipient name
        invite_link="https://example.com/invite"
    )

    return {
        "message": "Test email sent successfully" if success else "Failed to send test email"
    }