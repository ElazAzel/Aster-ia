from __future__ import annotations

import base64
import json
import os
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from asterion_api.dependencies import get_store
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore

router = APIRouter(prefix="/api/system", tags=["system"])


class BackupExportRequest(BaseModel):
    passphrase: str = Field(min_length=4, max_length=128)


class BackupImportRequest(BaseModel):
    backup: str
    passphrase: str = Field(min_length=4, max_length=128)


def _encrypt_dump(data: dict[str, Any], passphrase: str) -> str:
    json_bytes = json.dumps(data).encode("utf-8")
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))
    fernet = Fernet(key)
    encrypted_bytes = fernet.encrypt(json_bytes)
    combined = salt + encrypted_bytes
    return base64.b64encode(combined).decode("utf-8")


def _decrypt_dump(encrypted_base64: str, passphrase: str) -> dict[str, Any]:
    combined = base64.b64decode(encrypted_base64.encode("utf-8"))
    salt = combined[:16]
    ciphertext = combined[16:]
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))
    fernet = Fernet(key)
    decrypted_bytes = fernet.decrypt(ciphertext)
    return json.loads(decrypted_bytes.decode("utf-8"))


@router.post("/export")
async def export_backup(
    payload: BackupExportRequest,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> dict[str, str]:
    try:
        dump = await store.dump_all_data()
        encrypted_data = _encrypt_dump(dump, payload.passphrase)
        return {"backup": encrypted_data}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup export failed: {exc}",
        )


@router.post("/import")
async def import_backup(
    payload: BackupImportRequest,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> dict[str, bool]:
    try:
        dump = _decrypt_dump(payload.backup, payload.passphrase)
        await store.restore_all_data(dump)
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid passphrase or corrupted backup file: {exc}",
        )


@router.post("/wipe")
async def wipe_system(
    store: EncryptedSQLiteStore = Depends(get_store),
) -> dict[str, bool]:
    try:
        await store.wipe_all_data()
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Wipe operation failed: {exc}",
        )


@router.post("/expire-memories")
async def trigger_expire_memories(
    store: EncryptedSQLiteStore = Depends(get_store),
) -> dict[str, int]:
    try:
        count = await store.expire_memories()
        return {"expired_count": count}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Manual memory expiration failed: {exc}",
        )
