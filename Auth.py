"""Handles sign up / log in using Supabase Auth.

Uses the ANON key (not the service key Store.py uses) because auth
endpoints are designed to be called with the public key — Supabase
validates credentials and issues a session token itself.
"""
import os
from supabase import create_client

auth_client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])


def sign_up(email: str, password: str) -> dict:
    """Creates a new account. Returns {"id": ..., "email": ...} on success.
    Raises an exception (caught by the caller) on failure, e.g. email already used."""
    result = auth_client.auth.sign_up({"email": email, "password": password})
    return {"id": result.user.id, "email": result.user.email}


def sign_in(email: str, password: str) -> dict:
    """Logs in an existing user. Returns {"id": ..., "email": ...} on success.
    Raises an exception on wrong credentials."""
    result = auth_client.auth.sign_in_with_password({"email": email, "password": password})
    return {"id": result.user.id, "email": result.user.email}