import hashlib
import os
import hmac
import base64

PBKDF2_ITERATIONS = 200_000


def hash_pin(pin: str, salt: bytes | None = None):
    if salt is None:
        salt = os.urandom(16)

    pin_hash = hashlib.pbkdf2_hmac(
        "sha256",
        pin.encode(),
        salt,
        PBKDF2_ITERATIONS
    )

    return {
        "salt": base64.b64encode(salt).decode(),
        "hash": base64.b64encode(pin_hash).decode()
    }


def verify_pin(pin: str, stored_salt: str, stored_hash: str):
    salt = base64.b64decode(stored_salt)
    expected_hash = base64.b64decode(stored_hash)

    calculated_hash = hashlib.pbkdf2_hmac(
        "sha256",
        pin.encode(),
        salt,
        PBKDF2_ITERATIONS
    )

    return hmac.compare_digest(
        calculated_hash,
        expected_hash
    )