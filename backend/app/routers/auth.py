from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Role, User
from ..schemas import LoginIn, PasswordChangeIn, ProfileIn, RegisterIn, TokenOut, UserOut
from ..security import create_token, get_current_user, hash_password, password_policy, verify_password
from ..services.ratelimit import client_ip, limit
from ..services.records import log

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    limit(f"register:{client_ip(request)}", 10, 3600)
    password_policy(body.password)
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    # The very first account becomes administrator so a fresh install is manageable; later accounts are standard users.
    first = (db.scalar(select(func.count(User.id))) or 0) == 0
    role = db.scalar(select(Role).where(Role.name == ("admin" if first else "user")))
    user = User(email=email, full_name=body.full_name, password_hash=hash_password(body.password), role_id=role.id)
    db.add(user)
    db.flush()
    log(db, user, "auth.register", "user", user.id, role=role.name)
    db.commit()
    db.refresh(user)
    token, exp = create_token(user)
    return TokenOut(access_token=token, expires_at=exp, user=UserOut.of(user))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    limit(f"login:{client_ip(request)}", 20, 300)
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    log(db, user, "auth.login", "user", user.id)
    db.commit()
    token, exp = create_token(user)
    return TokenOut(access_token=token, expires_at=exp, user=UserOut.of(user))


@router.post("/logout", status_code=204)
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.token_version += 1  # revokes every token issued so far
    log(db, user, "auth.logout", "user", user.id)
    db.commit()


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.of(user)


@router.patch("/me", response_model=UserOut, summary="Update your own profile (display name)")
def update_me(body: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.full_name = body.full_name.strip()
    log(db, user, "auth.profile_update", "user", user.id)
    db.commit()
    db.refresh(user)
    return UserOut.of(user)


@router.post("/change-password", response_model=TokenOut, summary="Change your password (signs out every other session)")
def change_password(body: PasswordChangeIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    limit(f"pwchange:{user.id}:{client_ip(request)}", 10, 3600)
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    if body.new_password == body.current_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "New password must differ from the current one")
    password_policy(body.new_password)
    user.password_hash = hash_password(body.new_password)
    user.token_version += 1  # revoke every existing token; the caller gets a fresh one below
    log(db, user, "auth.password_change", "user", user.id)
    db.commit()
    db.refresh(user)
    token, exp = create_token(user)
    return TokenOut(access_token=token, expires_at=exp, user=UserOut.of(user))
