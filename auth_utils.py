"""
Simple username/password authentication backed by the Users sheet.
Passwords are never stored in plain text - only their SHA-256 hash.
Use generate_password_hash.py to create the hash for a new user.
"""
import hashlib

from gsheet_utils import get_users_df


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def authenticate(username: str, password: str):
    """Returns the matching user row as a dict if credentials are valid, else None."""
    users = get_users_df()
    if users.empty:
        return None
    users["Username"] = users["Username"].astype(str).str.strip()
    match = users[users["Username"].str.lower() == username.strip().lower()]
    if match.empty:
        return None
    user = match.iloc[0].to_dict()
    if str(user.get("PasswordHash", "")) == hash_password(password):
        return user
    return None
