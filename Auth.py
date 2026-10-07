"""Handles sign up / log in using Supabase Auth.

Uses the ANON key (not the service key Store.py uses) because auth
endpoints are designed to be called with the public key — Supabase
validates credentials and issues a session token itself.
"""
import os
from typing import Optional

from supabase import create_client

auth_client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])


def sign_up(email: str, password: str) -> Optional[dict]:
    """Create an account; return None when email confirmation is still required."""
    result = auth_client.auth.sign_up({"email": email.strip(), "password": password})
    if result.session is None:
        return None
    return {"id": result.user.id, "email": result.user.email}


def sign_in(email: str, password: str) -> dict:
    """Logs in an existing user. Returns {"id": ..., "email": ...} on success.
    Raises an exception on wrong credentials."""
    result = auth_client.auth.sign_in_with_password(
        {"email": email.strip(), "password": password}
    )
    return {"id": result.user.id, "email": result.user.email}