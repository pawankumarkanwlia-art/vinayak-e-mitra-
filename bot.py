import os
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urldefrag, urlparse
from html import escape

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = "@divyacybercafe"
HISTORY_FILE = "sent_jobs.txt"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    )
}

SOURCES = [
    {
        "name": "SarkariResult.com.cm",
        "url": "https://sarkariresult.com.cm/",
        "host": "sarkariresult.com.cm",
    },
    {
        "name": "FreeJobAlert.com",
        "url": "https://www.freejobalert.com/",
        "host": "www.freejobalert.com",
    },
]

# केवल भर्ती/आवेदन वाले शीर्षक स्वीकार करें
JOB_WORDS = (
    "recruitment", "online form", "apply online",
    "vacancy", "vacancies", "bharti", "भर्ती",
    "apprentice", "job notification",
)

IGNORE_WORDS = (
    "privacy policy", "disclaimer", "contact us",
    "about us", "terms and conditions", "cookie policy",
    "answer key", "admit card", "result", "syllabus",
    "exam city", "cut off", "cutoff", "merit list",
    "scholarship", "meditation", "login", "register",
    "document verification",
)

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return set()

    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def save_history(url):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")


def fetch_soup(url):
    response = SESSION.get(url, timeout=20)
    response.raise_for_status()
    return BeautifulSoup(response.content, "html.parser")


def clean_text(text):
    return " ".join(text.split()).strip()


def is_job_title(title):
    low = title.lower()

    if len(title) < 10:
        return False

    if any(word in low for word in IGNORE_WORDS):
        return False

    return any(word in low for word in JOB_WORDS)


def get_listing_jobs(source, history):
    found = []
    seen = set()

    try:
        soup = fetch_soup(source["url"])

        for a in soup.find_all("a", href=True):
            title = clean_text(a.get_text(" ", strip=True))
            link = urljoin(source["url"], a["href"].strip())
            link, _ = urldefrag(link)

            parsed = urlparse(link)
            host = (parsed.hostname or "").lower()

            if host != source["host"]:
                continue

            if parsed.scheme not in ("http", "https"):
                continue

            if not is_job_title(title):
                continue

            if link in history or link in seen:
                continue

            if any(x in parsed.path.lower() for x in (
                "/category/", "/tag/", "/author/", "/page/"
            )):
                continue

            seen.add(link)
            found.append({
                "title": title,
                "url": link,
                "source": source["name"],
                "source_url": source["url"],
            })

            # हर वेबसाइट से सीमित उम्मीदवार जाँचें
            if len(found) >= 20:
                break

    except requests.RequestException as exc:
        print(f"Listing error [{source['name']}]: {exc}")

    return found


def extract_labeled_value(text, labels):
    lines = [clean_text(x) for x in text.splitlines()]
    lines = [x for x in lines if x]

    for i, line in enumerate(lines):
        low = line.lower()

        if any(label in low for label in labels):
            # उसी लाइन में ':' या '-' के बाद की जानकारी
            parts = re.split(r"[:：]\s*", line, maxsplit=1)

            if len(parts) == 2 and len(parts[1]) > 2:
                return parts[1][:220]

            # अगली लाइन में जानकारी होने की संभावना
            if i + 1 < len(lines):
                candidate = lines[i + 1]
                if len(candidate) > 2:
                    return candidate[:220]

    return None


def extract_job_details(job):
    details = {
        "qualification": None,
        "posts": None,
        "last_date": None,
        "apply_url": None,
    }

    try:
        soup = fetch_soup(job["url"])
    except requests.RequestException as exc:
        print(f"Detail error [{job['title']}]: {exc}")
        return details

    # अनावश्यक HTML हटाएँ
    for tag in soup(["script", "style", "noscript", "header", "footer"]):
        tag.decompose()

    text = soup.get_text("\n", strip=True)
    text = text.replace("\xa0", " ")

    # 1. योग्यता
    qualification = extract_labeled_value(text, (
        "educational qualification", "qualification",
        "eligibility criteria", "education qualification",
        "शैक्षणिक योग्यता", "योग्यता",
    ))

    if qualification and len(qualification) <= 220:
        details["qualification"] = qualification

    # 2. कुल पद — पहले शीर्षक में स्पष्ट संख्या खोजें
    match = re.search(
        r"([\d,]+)\s*(?:posts?|vacancies|पद)",
        job["title"],
        re.IGNORECASE,
    )

    if match:
        details["posts"] = match.group(1)
    else:
        posts = extract_labeled_value(text, (
            "total vacancies", "total posts", "number of posts",
            "vacancy details", "no. of posts", "total vacancy",
            "कुल पद", "कुल रिक्तियां",
        ))

        if posts and len(posts) <= 100:
            details["posts"] = posts

    # 3. आवेदन की अंतिम तिथि
    date_line = extract_labeled_value(text, (
        "last date to apply", "last date for application",
        "closing date", "application last date",
        "last date", "apply online last date",
        "अंतिम तिथि", "आवेदन की अंतिम तिथि",
    ))

    if date_line:
        date_match = re.search(
            r"\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b"
            r"|\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b"
            r"|\b[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}\b",
            date_line,
        )

        if date_match:
            details["last_date"] = date_match.group(0)

    # 4. आवेदन लिंक — भर्ती पेज के लिंक में से खोजें
    for a in soup.find_all("a", href=True):
        label = clean_text(a.get_text(" ", strip=True)).lower()
        href = urljoin(job["url"], a["href"].strip())

        if any(word in label for word in (
            "apply online", "apply now", "official website",
            "online application", "आवेदन करें",
        )):
            if urlparse(href).scheme in ("http", "https"):
                if href != job["url"]:
                    details["apply_url"] = href
                    break

    return details


def make_message(job, details):
    qualification = (
        details["qualification"] or "आधिकारिक नोटिफिकेशन देखें"
    )
    posts = details["posts"] or "आधिकारिक नोटिफिकेशन देखें"
    last_date = details["last_date"] or "आधिकारिक नोटिफिकेशन देखें"

    apply_url = details["apply_url"] or job["url"]

    return (
        "📢 <b>नई सरकारी नौकरी भर्ती</b>\n\n"
        f"🏢 <b>भर्ती:</b> {escape(job['title'])}\n\n"
        f"🎓 <b>योग्यता:</b> {escape(qualification)}\n"
        f"👥 <b>कुल पद:</b> {escape(posts)}\n"
        f"📅 <b>अंतिम तिथि:</b> {escape(last_date)}\n\n"
        f"🌐 <b>स्रोत:</b> "
        f'<a href="{escape(job["url"], quote=True)}">'
        f'{escape(job["source"])}</a>\n'
        f'📝 <b>आवेदन लिंक:</b> '
        f'<a href="{escape(apply_url, quote=True)}">'
        "यहाँ क्लिक करें</a>\n\n"
        "⚠️ योग्यता, पद और अंतिम तिथि आधिकारिक "
        "नोटिफिकेशन से अवश्य जाँचें।"
    )


def send_to_telegram(message):
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        response = SESSION.post(
            api_url,
            json={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=20,
        )

        result = response.json()

        if response.ok and result.get("ok") is True:
            return True

        print("Telegram error:", result.get("description", result))
        return False

    except (requests.RequestException, ValueError) as exc:
        print("Telegram request failed:", exc)
        return False


def main():
    if not BOT_TOKEN.strip():
        raise RuntimeError("BOT_TOKEN GitHub Secret खाली है।")

    history = load_history()
    new_count = 0

    for source in SOURCES:
        jobs = get_listing_jobs(source, history)

        for job in jobs:
            print("Checking:", job["title"])

            details = extract_job_details(job)
            message = make_message(job, details)

            if send_to_telegram(message):
                save_history(job["url"])
                history.add(job["url"])
                new_count += 1
                print("Sent:", job["title"])

                # Telegram/API पर अनावश्यक तेजी से अनुरोध न हों
                time.sleep(2)
            else:
                print("Not saved; will retry next run:", job["url"])

    print(f"काम पूरा। भेजे गए नए मैसेज: {new_count}")


if __name__ == "__main__":
    main()
