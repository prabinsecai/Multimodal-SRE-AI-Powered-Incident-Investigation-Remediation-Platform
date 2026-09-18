from app.core.security import create_token, decode_token, get_password_hash, verify_password

def test_jwt_token_flow():
    token = create_token("42", "ADMIN")
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "ADMIN"
    assert "exp" in payload

def test_password_hashing():
    pw = "sre-super-secret"
    h = get_password_hash(pw)
    assert h != pw
    assert verify_password(pw, h) is True
    assert verify_password("wrong-password", h) is False
