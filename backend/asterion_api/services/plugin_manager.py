from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Mapping

from asterion_api.config import Settings
from asterion_api.harness import BaseHarness
from asterion_api.schemas import PluginManifest


class PluginManager(BaseHarness):
    privacy_level = "local"
    TRUST_LEVELS = {"verified", "local-only", "network", "file", "shell", "danger"}

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
                plugin_dir = manifest_path.parent
                sig_file = plugin_dir / "signature.sig"
                pub_file = plugin_dir / "public_key.pem"
                
                is_signed = sig_file.exists() and pub_file.exists()
                is_valid = False
                
                if is_signed:
                    is_valid = self._verify_signature(plugin_dir)
                    if not is_valid:
                        # Corrupted or invalid signature: skip loading entirely
                        continue
                
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                trust_level = data.get("trust_level", "local-only")
                
                if trust_level == "verified" and not (is_signed and is_valid):
                    trust_level = "danger"
                
                if not is_signed:
                    # Downgrade unsigned plugins seeking elevated access
                    if trust_level in ("shell", "network", "file", "danger"):
                        trust_level = "danger"
                    else:
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
                continue
        return manifests

    def _verify_signature(self, plugin_dir: Path) -> bool:
        manifest_file = plugin_dir / "manifest.json"
        sig_file = plugin_dir / "signature.sig"
        pub_file = plugin_dir / "public_key.pem"
        
        if not manifest_file.exists() or not sig_file.exists() or not pub_file.exists():
            return False
            
        try:
            from cryptography.hazmat.primitives.asymmetric import ed25519
            from cryptography.hazmat.primitives import serialization
            
            pub_bytes = pub_file.read_bytes()
            try:
                public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
            except Exception:
                public_key = serialization.load_pem_public_key(pub_bytes)
                
            sig_bytes = sig_file.read_bytes()
            if len(sig_bytes) != 64:
                try:
                    sig_bytes = bytes.fromhex(sig_bytes.decode('utf-8').strip())
                except Exception:
                    pass
                    
            manifest_bytes = manifest_file.read_bytes()
            public_key.verify(sig_bytes, manifest_bytes)
            return True
        except Exception:
            return False

    def start_watcher(self, interval: float = 5.0) -> None:
        self._watcher_active = True
        self._last_plugins: list[PluginManifest] = []
        def _watch() -> None:
            while self._watcher_active:
                current = self.load()
                current_dump = [p.model_dump() for p in current]
                last_dump = [p.model_dump() for p in self._last_plugins]
                if current_dump != last_dump:
                    self._last_plugins = current
                time.sleep(interval)
        self._watcher_thread = threading.Thread(target=_watch, daemon=True)
        self._watcher_thread.start()

    def stop_watcher(self) -> None:
        self._watcher_active = False

    def get_plugin_names(self) -> list[str]:
        return [p.name for p in self.load()]
