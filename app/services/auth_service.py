import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import GOOGLE_CLIENT_ID, JWT_ACCESS_TOKEN_EXPIRE_MINUTES, JWT_ALGORITHM, JWT_SECRET_KEY
from app.database import get_db
from app.models.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def _require_google_client_id() -> str:
    client_id = GOOGLE_CLIENT_ID
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth is not configured on the server.",
        )
    return client_id


def verify_google_credential(credential: str) -> Dict[str, Any]:
    if not credential or not credential.strip():
        raise ValueError("Google credential is required.")

    if not GOOGLE_CLIENT_ID:
        raise ValueError("Google OAuth is not configured on the server.")

    try:
        payload = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            clock_skew_in_seconds=10,
            audience=GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        raise ValueError("Invalid Google credential.") from exc
    except Exception as exc:
        raise ValueError("Unable to verify Google credential.") from exc

    if payload.get("email_verified") is False:
        raise ValueError("Google email is not verified.")

    email = payload.get("email")
    if not email:
        raise ValueError("Google account email is missing.")

    google_sub = payload.get("sub")
    if not google_sub:
        raise ValueError("Google account identifier is missing.")

    return {
        "sub": google_sub,
        "email": email,
        "name": payload.get("name"),
        "picture": payload.get("picture"),
    }


def create_access_token(subject: str) -> str:
    if not JWT_SECRET_KEY:
        raise ValueError("JWT secret is not configured.")

    payload = {
        "sub": str(subject),
        "exp": datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    if not token:
        raise ValueError("Missing authentication token.")
    if not JWT_SECRET_KEY:
        raise ValueError("JWT secret is not configured.")

    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token.") from exc


def get_or_create_user_from_google(db: Session, google_payload: Dict[str, Any]) -> User:
    email = (google_payload.get("email") or "").strip().lower()
    if not email:
        raise ValueError("Google email is required to create a user.")

    google_id = str(google_payload.get("sub") or "").strip()
    if not google_id:
        raise ValueError("Google account identifier is required.")

    user = db.query(User).filter((User.google_id == google_id) | (User.email == email)).first()
    if user:
        if user.google_id is None:
            user.google_id = google_id
        if not user.email:
            user.email = email
        if user.name is None and google_payload.get("name"):
            user.name = google_payload.get("name")
        if user.profile_picture is None and google_payload.get("picture"):
            user.profile_picture = google_payload.get("picture")
        user.last_login = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user

    user = User(
        google_id=google_id,
        email=email,
        name=google_payload.get("name"),
        profile_picture=google_payload.get("picture"),
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise ValueError("Token payload missing subject.")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    return user
