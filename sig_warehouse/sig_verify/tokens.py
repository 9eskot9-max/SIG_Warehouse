"""Verification tokens: random, unguessable, URL-safe. Pure Python."""

import secrets

# No 0/O, 1/l/I: tokens are sometimes read aloud or retyped from a printout.
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
TOKEN_LENGTH = 20
MIN_TOKEN_LENGTH = 16
MAX_TOKEN_LENGTH = 64


def new_token(length=TOKEN_LENGTH):
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def is_plausible_token(value):
    """Cheap shape check before touching the database."""
    return (
        isinstance(value, str)
        and MIN_TOKEN_LENGTH <= len(value) <= MAX_TOKEN_LENGTH
        and all(ch in ALPHABET for ch in value)
    )


def verify_url(site_url, token):
    from .registry import VERIFY_PATH

    return f"{site_url.rstrip('/')}{VERIFY_PATH}?t={token}"
