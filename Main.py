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
    4: ("Springer IT", "https://www.springerprofessional.de/rss/rss-feeds/7097080")
}
CUSTOM_OPTION = 9
MAX_ITEMS = 10
DEFAULT_ITEMS = 5


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


def _collect_links(elements: List[ET.Element]) -> List[str]:
    """Collect link URLs from a list of XML elements."""
    links: List[str] = []
    seen = set()
    for elem in elements:
        href = (elem.text or "").strip()
        attr_href = elem.attrib.get("href", "").strip()
        url = href or attr_href
        if url and url not in seen:
            links.append(url)
            seen.add(url)
    return links


def extract_entries(root: ET.Element, limit: int = 5) -> List[Tuple[str, str, List[str]]]:
    """
    Extract (title, summary, links) tuples from either RSS or Atom feeds. Returns
    up to `limit` entries, skipping empty titles.
    """
    entries: List[Tuple[str, str, List[str]]] = []

    channel = root.find("channel")
    if channel is not None:
        for item in channel.findall("item"):
            title = (item.findtext("title") or "").strip()
            if not title:
                continue
            summary = (item.findtext("description") or "").strip()
            link_elements = item.findall("link")
            links = _collect_links(link_elements)
            if not links:
                link_text = (item.findtext("link") or "").strip()
                if link_text:
                    links = [link_text]
            entries.append((title, summary, links))
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
        link_elements = entry.findall(f"{atom_ns}link")
        links = _collect_links(link_elements)
        entries.append((title, summary, links))
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


def display_entries(entries: List[Tuple[str, str, List[str]]]) -> None:
    if not entries:
        print("Keine Eintraege fuer diesen Feed gefunden.")
        return

    for idx, (title, summary, links) in enumerate(entries, start=1):
        print(f"\n{idx}. {title}")
        if links:
            print("   Links:")
            for url in links:
                print(f"    - {url}")
        if summary:
            wrapped = textwrap.fill(summary, width=80, initial_indent="   ", subsequent_indent="   ")
            print(wrapped)


def prompt_for_item_count() -> int:
    hint = f"Wieviele Eintraege anzeigen (1-{MAX_ITEMS}, Enter fuer {DEFAULT_ITEMS}): "
    while True:
        try:
            user_input = input(hint).strip()
        except EOFError:
            return DEFAULT_ITEMS
        if not user_input:
            return DEFAULT_ITEMS
        if user_input.isdigit():
            count = int(user_input)
            if 1 <= count <= MAX_ITEMS:
                return count
        print("Bitte eine Zahl im gueltigen Bereich eingeben.")


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

    item_limit = prompt_for_item_count()

    print(f"\nLade '{name}'...")
    try:
        root = fetch_feed(url)
    except urllib.error.URLError as exc:
        print(f"Feed konnte nicht geladen werden: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except ET.ParseError as exc:
        print(f"Feed konnte nicht verarbeitet werden: {exc}", file=sys.stderr)
        raise SystemExit(1)

    entries = extract_entries(root, limit=item_limit)
    display_entries(entries)


if __name__ == "__main__":
    main()
