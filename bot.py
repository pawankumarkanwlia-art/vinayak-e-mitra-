
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urldefrag
from html import escape

HISTORY_FILE = "sent_jobs.txt"
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = "@divyacybercafe"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

SOURCES = [
    {
        "name": "SarkariResult.com.cm",
        "url": "https://sarkariresult.com.cm/",
    },
    {
        "name": "FreeJobAlert.com",
        "url": "https://www.freejobalert.com/",
    },
]

KEYWORDS = (
    "recruitment", "vacancy", "vacancies", "apply online",
    "admit card", "result", "answer key", "government job",
    "सरकारी नौकरी", "भर्ती", "रिक्ति", "आवेदन",
    "प्रवेश पत्र", "उत्तर कुंजी",
)


def load_sent_jobs():
    if not os.path.exists(HISTORY_FILE):
        return set()

    with open(HISTORY_FILE, "r", encoding="utf-8") as file:
        return {line.strip() for line in file if line.strip()}


def mark_job_as_sent(url):
    with open(HISTORY_FILE, "a", encoding="utf-8") as file:
        file.write(url + "\n")


def fetch_jobs(source, sent_jobs):
    jobs = []

    try:
        response = requests.get(
            source["url"],
            headers=HEADERS,
            timeout=20,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        for anchor in soup.find_all("a", href=True):
            title = " ".join(anchor.get_text(" ", strip=True).split())
            link = urljoin(source["url"], anchor["href"].strip())
            link, _ = urldefrag(link)

            if len(title) < 12:
                continue

            if not any(
                keyword in (title + " " + link).lower()
                for keyword in KEYWORDS
            ):
                continue

            # केवल उसी वेबसाइट के लिंक स्वीकार करें।
            source_host = source["url"].split("/")[2].lower()
            link_host = (requests.utils.urlparse(link).hostname or "").lower()

            if link_host != source_host:
                continue

            if link.rstrip("/") == source["url"].rstrip("/"):
                continue

            if link in sent_jobs:
                continue

            jobs.append({
                "title": title,
                "url": link,
                "source": source["name"],
            })

    except requests.RequestException as error:
        print(f"Website error [{source['name']}]: {error}")

    return jobs


def get_job():
    sent_jobs = load_sent_jobs()

    for source in SOURCES:
        jobs = fetch_jobs(source, sent_jobs)

        if jobs:
            return jobs[0]

    return None


def send_to_telegram(job):
    message = (
        "📣 <b>सरकारी नौकरी अलर्ट</b> 📣\n\n"
        f"🔹 <b>भर्ती / अपडेट:</b> {escape(job['title'])}\n"
        f"📌 <b>स्रोत:</b> {escape(job['source'])}\n\n"
        "🌐 <b>पूरी जानकारी के लिए:</b>\n"
        f'👉 <a href="{escape(job["url"], quote=True)}">'
        "यहाँ क्लिक करें</a>\n\n"
        "⚠️ आवेदन से पहले आधिकारिक नोटिफिकेशन, "
        "योग्यता और अंतिम तिथि जाँचें।"
    )

    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        response = requests.post(
            api_url,
            json={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=20,
        )

        try:
            result = response.json()
        except ValueError:
            print("Telegram ने मान्य JSON response नहीं दिया।")
            return False

        if response.ok and result.get("ok") is True:
            print("Telegram पर संदेश सफलतापूर्वक भेजा गया।")
            return True

        print("Telegram API error:", result.get("description", "Unknown error"))
        return False

    except requests.RequestException as error:
        print("Telegram network error:", error)
        return False


def main():
    if not BOT_TOKEN.strip():
        raise RuntimeError("GitHub Secret BOT_TOKEN खाली है।")

    job = get_job()

    if not job:
        print("कोई नई matching job link नहीं मिली।")
        return

    print(f"नई matching link: {job['title']} [{job['source']}]")

    if send_to_telegram(job):
        mark_job_as_sent(job["url"])
        print("लिंक sent_jobs.txt में सेव कर दी गई।")
    else:
        raise RuntimeError("Telegram पर संदेश भेजने में विफलता।")


if __name__ == "__main__":
    main()
