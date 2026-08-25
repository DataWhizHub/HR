"""
Simple username/password authentication backed by the Users sheet.
Passwords are never stored in plain text - only their SHA-256 hash.
Use generate_password_hash.py to create the hash for a new user,
or let people create their own account via the app's Create Account tab.
"""
import hashlib

from config import ROLE_USER
from gsheet_utils import append_user, get_users_df


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


def username_exists(username: str) -> bool:
    users = get_users_df()
    if users.empty:
        return False
    users["Username"] = users["Username"].astype(str).str.strip()
    return (users["Username"].str.lower() == username.strip().lower()).any()


def register_user(username: str, password: str, emp_no: str, name: str, designation: str, email: str):
    """Creates a new 'User' account. Returns (True, '') on success or (False, error_message)."""
    username = username.strip()
    if not all([username, password, emp_no, name, designation, email]):
        return False, "Please fill in every field."
    if username_exists(username):
        return False, "That username is already taken. Please choose another."
    append_user({
        "Username": username,
        "PasswordHash": hash_password(password),
        "EmpNo": emp_no.strip(),
        "Name": name.strip(),
        "Designation": designation.strip(),
        "Email": email.strip(),
        "Role": ROLE_USER,
    })
    return True, ""
