"""Download configured RSS/Atom feeds into local XML files for static hosting."""

from __future__ import annotations

import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Tuple

from Main import FEEDS

OUTPUT_FILES: Dict[int, str] = {
    1: "feeds/haufe.xml",
    2: "feeds/bundesregierung.xml",
    3: "feeds/handelsblatt.xml",
}


def download_bytes(url: str) -> bytes:
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(url, timeout=20, context=ctx) as response:
            return response.read()
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLCertVerificationError):
            print("Warnung: Zertifikatsproblem, lade mit deaktivierter Pruefung...")
            insecure = ssl._create_unverified_context()
            with urllib.request.urlopen(url, timeout=20, context=insecure) as response:
                return response.read()
        raise


def main() -> None:
    repo_root = Path(__file__).parent
    for feed_id, (name, url) in FEEDS.items():
        rel_path = OUTPUT_FILES.get(feed_id, f"feeds/feed_{feed_id}.xml")
        target = repo_root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        print(f"Lade {name} ({url}) ...")
        data = download_bytes(url)
        target.write_bytes(data)
        print(f" -> gespeichert in {rel_path} ({len(data)} Bytes)")


if __name__ == "__main__":
    main()
