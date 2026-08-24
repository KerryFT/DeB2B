from __future__ import annotations

import base64
import json
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

GMAIL_SCOPES = (
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
)


class CredentialCipher:
    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError("credential encryption key must be 32 bytes")
        self._cipher = AESGCM(key)

    def encrypt(self, payload: dict[str, Any], *, tenant_id: str) -> str:
        nonce = os.urandom(12)
        plaintext = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ciphertext = self._cipher.encrypt(nonce, plaintext, tenant_id.encode())
        return base64.urlsafe_b64encode(nonce + ciphertext).decode()

    def decrypt(self, token: str, *, tenant_id: str) -> dict[str, Any]:
        raw = base64.urlsafe_b64decode(token)
        plaintext = self._cipher.decrypt(raw[:12], raw[12:], tenant_id.encode())
        value = json.loads(plaintext)
        if not isinstance(value, dict):
            raise ValueError("credential payload must be an object")
        return value
