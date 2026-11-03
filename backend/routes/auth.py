from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from schemas.user import UserCreate, UserLogin, UserResponse
from models.user import User
from models.revoked_token import RevokedToken
from database import get_db
from utils.auth import get_password_hash, verify_password, create_access_token
from utils.common import generate_id

router = APIRouter(prefix="/auth", tags=["auth"])


def get_current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    credential_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise credential_exception
    from utils.auth import decode_token
    payload = decode_token(token)
    user_id = payload.get("sub") if payload else None
    jti = payload.get("jti") if payload else None
    if not user_id or not jti:
        raise credential_exception
    if db.query(RevokedToken).filter(RevokedToken.jti == jti).first():
        raise credential_exception
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credential_exception
    return user


@router.post("/signup", response_model=dict)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    new_user = User(id=generate_id(), email=user.email, first_name=user.first_name, last_name=user.last_name, hashed_password=get_password_hash(user.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    access_token = create_access_token(data={"sub": new_user.id})
    return {"access_token": access_token, "token_type": "bearer", "user": {"id": new_user.id, "email": new_user.email, "firstName": new_user.first_name, "lastName": new_user.last_name, "createdAt": new_user.created_at.isoformat()}}


@router.post("/login", response_model=dict)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer", "user": {"id": user.id, "email": user.email, "firstName": user.first_name, "lastName": user.last_name, "createdAt": user.created_at.isoformat()}}


@router.post("/logout")
def logout(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    from utils.auth import decode_token
    payload = decode_token(token)
    if not payload or not payload.get("sub") or not payload.get("jti") or not payload.get("exp"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    if expires_at > datetime.now(timezone.utc):
        db.merge(RevokedToken(jti=payload["jti"], user_id=payload["sub"], expires_at=expires_at))
        db.commit()
    return {"message": "Logged out successfully"}
