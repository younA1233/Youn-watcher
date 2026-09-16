#!/usr/bin/env python3
"""
CROUS Watcher — surveille trouverunlogement.lescrous.fr et notifie
via ntfy.sh dès qu'un nouveau logement apparaît dans la zone choisie.

Variables d'environnement requises :
  CROUS_SEARCH_URL   URL de recherche CROUS (avec les bounds de ta zone)
  NTFY_TOPIC         Nom de topic ntfy (long et aléatoire, voir README)

Variable optionnelle :
  MAX_RUNTIME_MIN    Durée max d'exécution en minutes (défaut 55, pensé
                      pour un cron GitHub Actions horaire)
"""

import os
import re
import sys
import json
import time
import requests
from bs4 import BeautifulSoup

STATE_FILE = "seen.json"
POLL_INTERVAL_SEC = 30
DEFAULT_MAX_RUNTIME_MIN = 55

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def load_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=2)


def fetch_listings(search_url):
    """
    Récupère la page de recherche et en extrait les logements.
    Le site utilise le référentiel DSFR (classe 'fr-card' stable) pour
    chaque carte de logement, donc on s'appuie là-dessus plutôt que sur
    des classes générées (susceptibles de changer à chaque déploiement).
    """
    resp = requests.get(search_url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    listings = []
    cards = soup.select("[class*='fr-card']")
    for card in cards:
        text = card.get_text(" ", strip=True)
        if not text:
            continue

        # Une carte de logement contient typiquement un prix (€) et une
        # surface (m²) — ça permet de filtrer le bruit (cartes de nav, etc.)
        if "€" not in text or "m²" not in text:
            continue

        link_tag = card.find("a", href=True)
        href = link_tag["href"] if link_tag else None
        if href and href.startswith("/"):
            href = "https://trouverunlogement.lescrous.fr" + href

        # Identifiant unique : on privilégie l'URL de la fiche si dispo,
        # sinon le texte complet de la carte
        listing_id = href or text

        title_match = re.search(r"^[^\d€]+", text)
        title = title_match.group(0).strip() if title_match else text[:60]

        listings.append({
            "id": listing_id,
            "title": title,
            "text": text,
            "url": href or search_url,
        })

    return listings


def notify(ntfy_topic, listing):
    url = f"https://ntfy.sh/{ntfy_topic}"
    body = listing["text"][:200]
    try:
        requests.post(
            url,
            data=body.encode("utf-8"),
            headers={
                "Title": f"🏠 Nouveau logement : {listing['title'][:80]}".encode("utf-8"),
                "Click": listing["url"],
                "Priority": "high",
                "Tags": "house",
            },
            timeout=10,
        )
    except requests.RequestException as e:
        print(f"[!] Échec notification ntfy : {e}", file=sys.stderr)


def notify_summary(ntfy_topic, count):
    url = f"https://ntfy.sh/{ntfy_topic}"
    try:
        requests.post(
            url,
            data=f"{count} nouveaux logements détectés d'un coup. Va voir le site directement.".encode("utf-8"),
            headers={
                "Title": "🏠 Plusieurs nouveaux logements CROUS".encode("utf-8"),
                "Priority": "high",
                "Tags": "house",
            },
            timeout=10,
        )
    except requests.RequestException as e:
        print(f"[!] Échec notification résumé ntfy : {e}", file=sys.stderr)


def notify_startup(ntfy_topic):
    url = f"https://ntfy.sh/{ntfy_topic}"
    try:
        requests.post(
            url,
            data="La surveillance des logements CROUS est active.".encode("utf-8"),
            headers={"Title": "✅ Surveillance active".encode("utf-8")},
            timeout=10,
        )
    except requests.RequestException:
        pass


def run_once(search_url, ntfy_topic, seen, first_run):
    try:
        listings = fetch_listings(search_url)
    except requests.RequestException as e:
        print(f"[!] Erreur de récupération : {e}", file=sys.stderr)
        return seen

    current_ids = {l["id"] for l in listings}
    new_ids = current_ids - seen

    if new_ids and not first_run:
        new_listings = [l for l in listings if l["id"] in new_ids]
        print(f"[+] {len(new_listings)} nouveau(x) logement(s) détecté(s)")
        if len(new_listings) > 8:
            notify_summary(ntfy_topic, len(new_listings))
        else:
            for listing in new_listings:
                notify(ntfy_topic, listing)
    elif first_run:
        print(f"[i] Premier passage : {len(current_ids)} logement(s) déjà en ligne, enregistrés silencieusement")

    seen |= current_ids
    save_seen(seen)
    return seen


def main():
    search_url = os.environ.get("CROUS_SEARCH_URL")
    ntfy_topic = os.environ.get("NTFY_TOPIC")
    max_runtime_min = float(os.environ.get("MAX_RUNTIME_MIN", DEFAULT_MAX_RUNTIME_MIN))

    if not search_url or not ntfy_topic:
        print("[!] CROUS_SEARCH_URL et NTFY_TOPIC doivent être définis (variables d'env ou secrets GitHub).", file=sys.stderr)
        sys.exit(1)

    seen = load_seen()
    first_run = len(seen) == 0
    if first_run:
        notify_startup(ntfy_topic)

    deadline = time.time() + max_runtime_min * 60
    iteration = 0

    while time.time() < deadline:
        seen = run_once(search_url, ntfy_topic, seen, first_run and iteration == 0)
        iteration += 1
        time.sleep(POLL_INTERVAL_SEC)

    print("[i] Fin de session (relais pris par le prochain déclenchement planifié).")


if __name__ == "__main__":
    main()
