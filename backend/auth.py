import os
import random
from datetime import datetime, timedelta

import jwt
import resend
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlmodel import Session, select

from database import get_session
from models import User, VerificationCode

load_dotenv()

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer()


def generate_code() -> str:
    return f"{random.randint(0, 999999):06d}"


def send_code(email: str, code: str) -> None:
    api_key = os.getenv("RESEND_API_KEY", "")
    if api_key:
        resend.api_key = api_key
        resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": [email],
            "subject": "Ваш код входа FinTrack",
            "html": f"<h1 style='font-size:48px;letter-spacing:8px'>{code}</h1><p>Код действителен 10 минут.</p>",
        })
    else:
        print(f"=== CODE for {email}: {code} ===")


def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(days=30),
    }
    return jwt.encode(payload, os.getenv("JWT_SECRET"), algorithm="HS256")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    session: Session = Depends(get_session),
) -> User:
    try:
        payload = jwt.decode(
            credentials.credentials,
            os.getenv("JWT_SECRET"),
            algorithms=["HS256"],
        )
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Недействительный токен")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user


def _user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "surname": user.surname or "",
        "date_of_birth": user.date_of_birth or "",
        "currency": user.currency or "UZS",
    }


class RequestCodeBody(BaseModel):
    email: str


class VerifyCodeBody(BaseModel):
    email: str
    code: str


class ProfileUpdate(BaseModel):
    name: str
    surname: str
    date_of_birth: str
    currency: str = "UZS"


@router.post("/request-code")
def request_code(body: RequestCodeBody, session: Session = Depends(get_session)):
    code = generate_code()
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    verification = VerificationCode(
        email=body.email,
        code=code,
        expires_at=expires_at,
        is_used=False,
    )
    session.add(verification)
    session.commit()
    send_code(body.email, code)
    return {"message": "code sent"}


@router.post("/verify-code")
def verify_code(body: VerifyCodeBody, session: Session = Depends(get_session)):
    now = datetime.utcnow()
    statement = (
        select(VerificationCode)
        .where(VerificationCode.email == body.email)
        .where(VerificationCode.code == body.code)
        .where(VerificationCode.is_used == False)
        .where(VerificationCode.expires_at > now)
        .order_by(VerificationCode.expires_at.desc())
    )
    verification = session.exec(statement).first()
    if not verification:
        raise HTTPException(status_code=400, detail="Неверный или истёкший код")

    verification.is_used = True
    session.add(verification)

    user = session.exec(select(User).where(User.email == body.email)).first()
    if not user:
        user = User(email=body.email, name=body.email.split("@")[0])
        session.add(user)

    session.commit()
    session.refresh(user)

    return {"token": create_token(user.id), "user": _user_dict(user)}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return _user_dict(current_user)


@router.put("/me")
def update_me(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    current_user.name = body.name
    current_user.surname = body.surname
    current_user.date_of_birth = body.date_of_birth
    current_user.currency = body.currency
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return _user_dict(current_user)
