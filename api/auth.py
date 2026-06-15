import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
from jose import JWTError, jwt

SECRET_KEY = "08c4a52ffcef44ea2f6406e91b48b6bd01c25736fc7f73a524255109dc09fc32"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8

_USERS_FILE = Path(__file__).parent / "users.json"


def _load_users() -> dict[str, str]:
    users = json.loads(_USERS_FILE.read_text())
    return {u["username"]: u["hashed_password"] for u in users}


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def authenticate(username: str, password: str) -> bool:
    users = _load_users()
    if username not in users:
        return False
    return bcrypt.checkpw(password.encode(), users[username].encode())


def create_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if not username:
            raise ValueError("Missing subject")
        return username
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
