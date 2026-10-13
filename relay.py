import json
import os
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

CHANNEL = "prodigeekOfferte"
WEBHOOK = os.environ["DISCORD_WEBHOOK"]
SEEN_FILE = Path("seen.json")
URL = f"https://t.me/s/{CHANNEL}"
FIRST_RUN_LIMIT = 3
MAX_SEEN = 500


def load_seen():
    if SEEN_FILE.exists():
        return json.loads(SEEN_FILE.read_text(encoding="utf-8"))
    return None


def save_seen(seen):
    SEEN_FILE.write_text(json.dumps(seen[-MAX_SEEN:], indent=2), encoding="utf-8")


def get_posts():
    r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    posts = []
    for msg in soup.select(".tgme_widget_message"):
        post_id = msg.get("data-post")
        text_node = msg.select_one(".tgme_widget_message_text")
        if not post_id or not text_node:
            continue  # salta messaggi di servizio / vuoti
        text = text_node.get_text("\n", strip=True)
        link_node = msg.select_one("a.tgme_widget_message_date")
        link = link_node["href"] if link_node else URL
        image = None
        photo = msg.select_one("a.tgme_widget_message_photo_wrap")
        if photo:
            m = re.search(r"url\('(.*?)'\)", photo.get("style", ""))
            if m:
                image = m.group(1)
        posts.append({"id": post_id, "text": text, "link": link, "image": image})
    return posts


def send(post):
    embed = {
        "title": "Nuova offerta Prodigeek",
        "url": post["link"],
        "description": post["text"][:4000],
        "color": 0x2AABEE,
    }
    if post["image"]:
        embed["image"] = {"url": post["image"]}
    payload = {"username": "Prodigeek Offerte", "embeds": [embed]}
    for _ in range(5):
        r = requests.post(WEBHOOK, json=payload, timeout=20)
        if r.status_code == 429:
            time.sleep(float(r.json().get("retry_after", 2)) + 0.5)
            continue
        r.raise_for_status()
        return
    raise RuntimeError("Discord rate limit: troppi tentativi")


def main():
    seen = load_seen()
    first_run = seen is None
    seen = seen or []
    posts = get_posts()
    new = [p for p in posts if p["id"] not in seen]

    if first_run:
        for p in new[:-FIRST_RUN_LIMIT]:
            seen.append(p["id"])
        new = new[-FIRST_RUN_LIMIT:]

    for p in new:
        send(p)
        seen.append(p["id"])
        save_seen(seen)
        print(f"Inviato: {p['id']}")
        time.sleep(1.5)

    save_seen(seen)


if __name__ == "__main__":
    main()
