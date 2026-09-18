from datetime import datetime, timedelta, timezone
import hashlib
import jwt
from app.core.config import settings

try:
    import bcrypt

    def hash_password(p: str) -> str:
        # Bcrypt has a 72-byte max length limit
        p_bytes = p.encode("utf-8")[:72]
        return bcrypt.hashpw(p_bytes, bcrypt.gensalt()).decode("utf-8")

    def verify_password(p: str, h: str) -> bool:
        try:
            p_bytes = p.encode("utf-8")[:72]
            h_bytes = h.encode("utf-8")
            return bcrypt.checkpw(p_bytes, h_bytes)
        except Exception:
            return False

except ImportError:
    import hashlib
    import secrets

    def hash_password(p: str) -> str:
        salt = secrets.token_hex(8)
        hashed = hashlib.sha256((p + salt).encode("utf-8")).hexdigest()
        return f"sha256${salt}${hashed}"

    def verify_password(p: str, h: str) -> bool:
        try:
            parts = h.split("$")
            if len(parts) == 3 and parts[0] == "sha256":
                salt, expected = parts[1], parts[2]
                computed = hashlib.sha256((p + salt).encode("utf-8")).hexdigest()
                return computed == expected
            return False
        except Exception:
            return False

def get_password_hash(p: str) -> str:
    return hash_password(p)

def create_token(sub: str, role: str) -> str:
    payload = {
        "sub": str(sub),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24)
    }
    # Ensure key has minimum recommended length
    secret = settings.jwt_secret
    if len(secret) < 32:
        secret = (secret + "_secure_padding_key_32_bytes_min")[:32]
    return jwt.encode(payload, secret, algorithm="HS256")

def decode_token(t: str) -> dict:
    secret = settings.jwt_secret
    if len(secret) < 32:
        secret = (secret + "_secure_padding_key_32_bytes_min")[:32]
    return jwt.decode(t, secret, algorithms=["HS256"])
