import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from .. import mailer, models as m, security
from ..config import settings
from ..db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class Creds(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _new_user(db: Session, email: str, password: str | None = None, google_sub: str | None = None, verified=False) -> m.User:
    role = "admin" if email.lower() in [e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()] else "user"
    u = m.User(email=email.lower(), password_hash=security.hash_password(password) if password else None, role=role,
               google_sub=google_sub, email_verified=verified)
    u.profile = m.Profile()
    db.add(u); db.commit()
    return u


@router.post("/register", response_model=Token, status_code=201)
def register(c: Creds, db: Session = Depends(get_db)):
    if db.query(m.User).filter_by(email=c.email.lower()).first():
        raise HTTPException(409, "Email already registered")
    u = _new_user(db, c.email, c.password)
    tok = security.one_time_token(db, u.id, "verify", 60 * 48)
    mailer.send(u.email, "Verify your V-E-L-D-O-R-A email", f"Verification token: {tok}")
    return Token(access_token=security.create_token(u))


@router.post("/login", response_model=Token)
def login(c: Creds, db: Session = Depends(get_db)):
    u = db.query(m.User).filter_by(email=c.email.lower()).first()
    if not u or not security.verify_password(c.password, u.password_hash) or not u.is_active:
        raise HTTPException(401, "Incorrect email or password")
    return Token(access_token=security.create_token(u))


@router.post("/logout", status_code=204)
def logout(cred: HTTPAuthorizationCredentials = Depends(security.bearer), _=Depends(security.current_user)):
    security.revoke(cred.credentials)


class TokenIn(BaseModel):
    token: str


@router.post("/verify-email")
def verify_email(b: TokenIn, db: Session = Depends(get_db)):
    row = security.consume_token(db, b.token, "verify")
    if not row:
        raise HTTPException(400, "Invalid or expired token")
    db.get(m.User, row.user_id).email_verified = True
    db.commit()
    return {"verified": True}


class Email(BaseModel):
    email: EmailStr


@router.post("/forgot-password")
def forgot(b: Email, db: Session = Depends(get_db)):
    u = db.query(m.User).filter_by(email=b.email.lower()).first()
    if u:  # same response either way so accounts cannot be enumerated
        mailer.send(u.email, "Reset your V-E-L-D-O-R-A password", f"Reset token: {security.one_time_token(db, u.id, 'reset', 30)}")
    return {"message": "If that email exists, a reset link has been sent."}


class Reset(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/reset-password")
def reset(b: Reset, db: Session = Depends(get_db)):
    row = security.consume_token(db, b.token, "reset")
    if not row:
        raise HTTPException(400, "Invalid or expired token")
    db.get(m.User, row.user_id).password_hash = security.hash_password(b.new_password)
    db.commit()
    return {"reset": True}


class GoogleIn(BaseModel):
    id_token: str


@router.post("/google", response_model=Token)
def google(b: GoogleIn, db: Session = Depends(get_db)):
    if not settings.google_client_id:
        raise HTTPException(501, "Google sign-in is not configured (VELDORA_GOOGLE_CLIENT_ID)")
    r = httpx.get("https://oauth2.googleapis.com/tokeninfo", params={"id_token": b.id_token}, timeout=10)
    info = r.json() if r.status_code == 200 else {}
    if info.get("aud") != settings.google_client_id or info.get("email_verified") not in ("true", True):
        raise HTTPException(401, "Invalid Google token")
    u = db.query(m.User).filter_by(google_sub=info["sub"]).first() or db.query(m.User).filter_by(email=info["email"].lower()).first()
    if not u:
        u = _new_user(db, info["email"], google_sub=info["sub"], verified=True)
    elif not u.google_sub:
        u.google_sub, u.email_verified = info["sub"], True
        db.commit()
    return Token(access_token=security.create_token(u))
