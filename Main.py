from __future__ import annotations

import ssl
import sys
import textwrap
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple


FEEDS: Dict[int, Tuple[str, str]] = {
    1: ("Haufe Nachrichten", "https://www.haufe.de/xml/rss_129128.xml"),
    2: ("Bundesregierung", "https://www.bundesregierung.de/service/rss/breg-de/1151244/feed.xml"),
    3: ("Handelsblatt Politik", "http://www.handelsblatt.com/contentexport/feed/politik"),
}
CUSTOM_OPTION = 9


def fetch_feed(url: str) -> ET.Element:
    """Download the RSS/Atom XML and return its parsed root element."""
    default_ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(url, timeout=15, context=default_ctx) as response:
            xml_text = response.read()
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLCertVerificationError):
            print(
                "Zertifikatspruefung fehlgeschlagen, versuche es ohne Pruefung erneut...",
                file=sys.stderr,
            )
            insecure_ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(url, timeout=15, context=insecure_ctx) as response:
                xml_text = response.read()
        else:
            raise
    return ET.fromstring(xml_text)


def extract_entries(root: ET.Element, limit: int = 5) -> List[Tuple[str, str, str]]:
    """
    Extract (title, summary, link) tuples from either RSS or Atom feeds. Returns
    up to `limit` entries, skipping empty titles.
    """
    entries: List[Tuple[str, str, str]] = []

    channel = root.find("channel")
    if channel is not None:
        for item in channel.findall("item"):
            title = (item.findtext("title") or "").strip()
            if not title:
                continue
            summary = (item.findtext("description") or "").strip()
            link = (item.findtext("link") or "").strip()
            entries.append((title, summary, link))
            if len(entries) >= limit:
                return entries
        return entries

    atom_ns = "{http://www.w3.org/2005/Atom}"
    for entry in root.findall(f".//{atom_ns}entry"):
        title = (entry.findtext(f"{atom_ns}title") or "").strip()
        if not title:
            continue
        summary = (
            entry.findtext(f"{atom_ns}summary")
            or entry.findtext(f"{atom_ns}content")
            or ""
        ).strip()
        link = entry.findtext(f"{atom_ns}link") or ""
        link = link.strip()
        if not link:
            link_elem = entry.find(f"{atom_ns}link")
            if link_elem is not None:
                link = link_elem.attrib.get("href", "").strip()
        entries.append((title, summary, link))
        if len(entries) >= limit:
            break
    return entries


def prompt_for_choice() -> int:
    """Prompt until the user selects one of the feed numbers."""
    while True:
        try:
            user_input = input("Waehlen Sie einen Feed per Nummer: ").strip()
        except EOFError:
            raise SystemExit("\nKeine Auswahl getroffen.")
        if not user_input:
            print("Bitte eine Nummer aus der Liste eingeben.")
            continue
        if user_input.isdigit():
            choice = int(user_input)
            if choice in FEEDS or choice == CUSTOM_OPTION:
                return choice
        print("Ungueltige Auswahl, bitte erneut versuchen.")


def display_entries(entries: List[Tuple[str, str, str]]) -> None:
    if not entries:
        print("Keine Eintraege fuer diesen Feed gefunden.")
        return

    for idx, (title, summary, link) in enumerate(entries, start=1):
        print(f"\n{idx}. {title}")
        if link:
            print(f"   Link: {link}")
        if summary:
            wrapped = textwrap.fill(summary, width=80, initial_indent="   ", subsequent_indent="   ")
            print(wrapped)


def main() -> None:
    print("Verfuegbare RSS-Feeds:")
    for key, (name, _) in FEEDS.items():
        print(f" {key}: {name}")
    print(f" {CUSTOM_OPTION}: Eigene Feed-URL")

    choice = prompt_for_choice()
    if choice == CUSTOM_OPTION:
        url = input("Bitte die RSS/Atom-URL eingeben: ").strip()
        if not url:
            raise SystemExit("Keine URL angegeben.")
        name = "Eigener Feed"
    else:
        name, url = FEEDS[choice]

    print(f"\nLade '{name}'...")
    try:
        root = fetch_feed(url)
    except urllib.error.URLError as exc:
        print(f"Feed konnte nicht geladen werden: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except ET.ParseError as exc:
        print(f"Feed konnte nicht verarbeitet werden: {exc}", file=sys.stderr)
        raise SystemExit(1)

    entries = extract_entries(root)
    display_entries(entries)


if __name__ == "__main__":
    main()
