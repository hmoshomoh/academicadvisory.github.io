"""Tracking references.

A reference is a bearer token: whoever holds it can read the complaint's status.
It is generated from `secrets`, so it is neither sequential nor derived from the
submitter, and it cannot be walked or guessed from another complaint's reference.
"""

import secrets

PREFIX = "ACS"
# Crockford-style alphabet: no I, L, O, U, so references survive being read aloud.
ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
TOKEN_LENGTH = 10


def new_reference():
    token = "".join(secrets.choice(ALPHABET) for _ in range(TOKEN_LENGTH))
    return "{}-{}".format(PREFIX, token)


def normalise(raw):
    """Accept a reference the way a human retypes it: spaces, case, missing dash."""
    cleaned = "".join(ch for ch in (raw or "").upper() if ch.isalnum())
    if cleaned.startswith(PREFIX):
        cleaned = cleaned[len(PREFIX):]
    return "{}-{}".format(PREFIX, cleaned) if cleaned else ""
