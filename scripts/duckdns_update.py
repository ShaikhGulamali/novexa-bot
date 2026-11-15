"""Push this machine's current public IPv4 to DuckDNS."""

from __future__ import annotations

import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"
LOG = ROOT / "logs" / "duckdns.log"


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV.exists():
        return values
    for line in ENV.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def log(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] {message}\n")


def main() -> int:
    env = load_env()
    token = env.get("DUCKDNS_TOKEN", "").strip()
    domain = env.get("DUCKDNS_DOMAIN", "").strip()

    if not token or not domain:
        log("missing DUCKDNS_TOKEN or DUCKDNS_DOMAIN in .env")
        return 1

    query = urllib.parse.urlencode(
        {"domains": domain, "token": token, "ip": "", "verbose": "true"}
    )
    request = urllib.request.Request(
        f"https://www.duckdns.org/update?{query}",
        headers={"User-Agent": "novexa-ddns/1.0"},
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8", "replace").strip()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        log(f"{domain}.duckdns.org update failed: {exc}")
        return 2

    lines = [line.strip() for line in body.splitlines() if line.strip()]
    status = lines[0].upper() if lines else ""
    resolved = lines[1] if len(lines) > 1 else "?"

    if status == "OK":
        log(f"{domain}.duckdns.org -> {resolved}")
        return 0

    log(f"{domain}.duckdns.org rejected: {body or 'empty response'}")
    return 3


if __name__ == "__main__":
    sys.exit(main())
