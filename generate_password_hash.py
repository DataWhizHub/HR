"""
Admin helper - run this locally to generate the PasswordHash value you
paste into the Users sheet when adding a new employee.

Usage:
    python generate_password_hash.py
"""
import getpass
import hashlib

if __name__ == "__main__":
    pwd = getpass.getpass("Enter the new user's password: ")
    print("\nPasswordHash (paste this into the Users sheet):")
    print(hashlib.sha256(pwd.encode("utf-8")).hexdigest())
