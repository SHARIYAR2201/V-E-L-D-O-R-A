import hashlib, secrets, uuid
import time
from datetime import datetime, timedelta, timezone
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from . import cache, models as m
from .config import settings
from .db import get_db

bearer = HTTPBearer(auto_error=False)


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str | None) -> bool:
    return bool(hashed) and bcrypt.checkpw(pw.encode()[:72], hashed.encode())


def create_token(user: m.User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub": str(user.id), "role": user.role, "jti": uuid.uuid4().hex, "exp": exp}, settings.jwt_secret, settings.jwt_algorithm)


def revoke(token: str):
    try:
        p = jwt.decode(token, settings.jwt_secret, [settings.jwt_algorithm])
    except JWTError:
        return
    ttl = max(int(p["exp"] - time.time()), 1)
    cache.set(f"revoked:{p['jti']}", 1, ttl)


def one_time_token(db: Session, user_id: int, purpose: str, minutes: int) -> str:
    raw = secrets.token_urlsafe(32)
    db.add(m.AuthToken(user_id=user_id, purpose=purpose, token_hash=hashlib.sha256(raw.encode()).hexdigest(),
                       expires_at=m.now() + timedelta(minutes=minutes)))
    db.commit()
    return raw


def consume_token(db: Session, raw: str, purpose: str) -> m.AuthToken | None:
    row = db.query(m.AuthToken).filter_by(token_hash=hashlib.sha256(raw.encode()).hexdigest(), purpose=purpose, used=False).first()
    if not row or row.expires_at < m.now():
        return None
    row.used = True
    db.commit()
    return row


def current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> m.User:
    err = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    if not cred:
        raise err
    try:
        p = jwt.decode(cred.credentials, settings.jwt_secret, [settings.jwt_algorithm])
    except JWTError:
        raise err
    if cache.get(f"revoked:{p.get('jti')}"):
        raise err
    user = db.get(m.User, int(p["sub"]))
    if not user or not user.is_active:
        raise err
    return user


def admin_only(user: m.User = Depends(current_user)) -> m.User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    return user
