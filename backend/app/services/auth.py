from sqlalchemy import select

from app.models.models import User

from app.core.security import create_token, hash_password, verify_password


async def ensure_admin(db):
    user = (await db.execute(select(User).where(User.email == "admin@local"))).scalar_one_or_none()
    if not user:
        db.add(User(email="admin@local", password_hash=hash_password("admin123"), role="ADMIN"))
        await db.commit()


async def login(db, email, password):
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return None
    return create_token(str(user.id), user.role)
