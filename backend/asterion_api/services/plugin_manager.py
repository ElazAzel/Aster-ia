from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any, Mapping

from asterion_api.config import Settings
from asterion_api.harness import BaseHarness
from asterion_api.schemas import PluginManifest


class PluginManager(BaseHarness):
    privacy_level = "local"
    TRUST_LEVELS = {"verified", "local-only", "network", "file", "shell", "danger"}

    # Built-in trusted RSA-2048 public key generated during Phase 3
    TRUSTED_RSA_N = 24786168142965038805805814738973577365230724014991198524999230993652690727099805243243020791886529650571373806622633264011787331944147051840841278215707285485143196798502353209946235020449255511840696862557581530753054030710013146657132628145390633493672604787991185323112910496585929833315602434606770407253410998695383668507444789997720795336001675346442818105191157751186991845081012172275143104883171889501874022910334112769300763234695715425306272107040530767104979933337787004639933311314754112570507491920764932622678040210918428140619141275553333659421237141134327187794202164055388551247094540517261266425987
    TRUSTED_RSA_E = 65537

    def __init__(self, settings: Settings) -> None:
        self.plugins_dir = settings.data_dir / "plugins"
        self._watcher_active: bool = False
        self._watcher_thread: threading.Thread | None = None

    async def execute(self, payload: Mapping[str, Any] | None = None) -> list[PluginManifest]:
        return self.load()

    def get_state(self) -> dict[str, Any]:
        return {"plugins_dir": str(self.plugins_dir)}

    def set_state(self, state: Mapping[str, Any]) -> None:
        if state.get("plugins_dir"):
            self.plugins_dir = Path(str(state["plugins_dir"]))

    def load(self) -> list[PluginManifest]:
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        manifests: list[PluginManifest] = []
        for manifest_path in self.plugins_dir.glob("*/manifest.json"):
            try:
                manifest_bytes = manifest_path.read_bytes()
                data = json.loads(manifest_bytes.decode("utf-8"))

                # Cryptographic signature check
                sig_path = manifest_path.parent / "signature.sig"
                if not sig_path.exists():
                    sig_path = manifest_path.with_name("manifest.json.sig")
                pem_path = manifest_path.parent / "public_key.pem"
                is_verified = False
                if sig_path.exists():
                    try:
                        raw = sig_path.read_bytes()
                        try:
                            sig_bytes = bytes.fromhex(raw.decode("utf-8").strip())
                        except (ValueError, UnicodeDecodeError):
                            sig_bytes = raw
                        if pem_path.exists():
                            is_verified = self._verify_signature_pem(manifest_bytes, sig_bytes, pem_path)
                        else:
                            is_verified = self._verify_signature(manifest_bytes, sig_bytes)
                    except Exception:
                        is_verified = False

                trust_level = data.get("trust_level", "local-only")
                if is_verified:
                    trust_level = "verified"
                elif trust_level == "verified":
                    if sig_path.exists():
                        # Had a signature file but it was invalid -> skip plugin
                        continue
                    # No sig file, just claiming verified -> demote to local-only
                    trust_level = "local-only"

                if trust_level not in self.TRUST_LEVELS:
                    trust_level = "danger"

                manifests.append(
                    PluginManifest(
                        name=str(data.get("name") or manifest_path.parent.name),
                        trust_level=trust_level,
                        path=str(manifest_path.parent),
                        description=data.get("description"),
                    )
                )
            except Exception:
                # Skip invalid manifests
                continue
        return manifests

    def _verify_signature_pem(self, data: bytes, signature_bytes: bytes, pem_path: Path) -> bool:
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            from cryptography.hazmat.primitives.serialization import load_pem_public_key
            pem_data = pem_path.read_bytes()
            public_key = load_pem_public_key(pem_data)
            if isinstance(public_key, Ed25519PublicKey):
                public_key.verify(signature_bytes, data)
                return True
        except Exception:
            pass
        return self._verify_signature(data, signature_bytes)

    def _verify_signature(self, data: bytes, signature_bytes: bytes) -> bool:
        if len(signature_bytes) != 256:
            return False
        try:
            s = int.from_bytes(signature_bytes, "big")
            m = pow(s, self.TRUSTED_RSA_E, self.TRUSTED_RSA_N)
            decrypted = m.to_bytes(256, "big")

            h = hashlib.sha256(data).digest()
            asn1_prefix = b"\x30\x31\x30\x0d\x06\x09\x60\x86\x48\x01\x65\x03\x04\x02\x01\x05\x00\x04\x20"
            expected_suffix = asn1_prefix + h

            if decrypted[0:2] != b"\x00\x01" or not decrypted.endswith(expected_suffix):
                return False

            pad_len = 256 - len(expected_suffix) - 3
            if pad_len < 8:
                return False
            if decrypted[2 : 2 + pad_len] != b"\xff" * pad_len:
                return False
            if decrypted[2 + pad_len] != 0x00:
                return False
            return True
        except Exception:
            return False
