from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
import hmac, json, time
from pathlib import Path
from typing import Optional

@dataclass
class ChainEntry:
    ts: str
    kind: str
    level: str
    message: str
    data: dict
    prev_hash: str
    hash: str
    sig: Optional[str] = None  # HMAC hex

class ChainLogger:
    """Append-only hash-chained JSONL logger with optional HMAC signature."""
    def __init__(self, path: str | Path, *, secret: str = "") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.secret = secret or ""

    def _last_hash(self) -> str:
        if not self.path.exists():
            return "0"*64
        last = None
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last = line
        if not last:
            return "0"*64
        try:
            obj = json.loads(last)
            return obj.get("hash", "0"*64)
        except Exception:
            return "0"*64

    def _now(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def log(self, kind: str, level: str, message: str, data: dict | None = None) -> ChainEntry:
        data = data or {}
        prev = self._last_hash()
        base = json.dumps({
            "ts": self._now(),
            "kind": kind, "level": level, "message": message,
            "data": data, "prev_hash": prev
        }, separators=(",", ":"), ensure_ascii=False)
        digest = sha256(base.encode("utf-8")).hexdigest()
        sig = None
        if self.secret:
            sig = hmac.new(self.secret.encode("utf-8"), digest.encode("utf-8"), sha256).hexdigest()
        entry = ChainEntry(json.loads(base)["ts"], kind, level, message, data, prev, digest, sig)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        return entry

    @staticmethod
    def verify(path: str | Path, *, secret: str = "") -> bool:
        """Verify the chain and HMAC (if secret provided)."""
        prev = "0"*64
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception:
                return False
            base_obj = {k: obj[k] for k in ("ts","kind","level","message","data")}
            base_obj["prev_hash"] = prev
            base = json.dumps(base_obj, separators=(",", ":"), ensure_ascii=False)
            digest = sha256(base.encode("utf-8")).hexdigest()
            if digest != obj.get("hash"):
                return False
            if secret:
                sig = hmac.new(secret.encode("utf-8"), digest.encode("utf-8"), sha256).hexdigest()
                if sig != obj.get("sig"):
                    return False
            prev = digest
        return True
