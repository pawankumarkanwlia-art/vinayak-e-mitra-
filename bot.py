import os
import requests
from bs4 import BeautifulSoup

HISTORY_FILE = "sent_jobs.txt"

BOT_TOKEN = "8975425344:AAGASvNX15Wa6YweF1A-CrWTakY5io7JSSY"
CHAT_ID = "@divyacybercafe"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def load_sent_jobs():
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def mark_job_as_sent(job_url):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(job_url + "\n")

def fetch_from_sarkari_result_cm(sent_jobs):
    url = "https://sarkariresult.com.cm/"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.content, "html.parser")
        
        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            link = a["href"].strip()
            
            if len(title) > 10:
                if not link.startswith("http"):
                    link = "https://sarkariresult.com.cm" + ("/" if not link.startswith("/") else "") + link
                
                if link not in sent_jobs:
                    return {
                        "title": title,
                        "url": link,
                        "source": "SarkariResult.com.cm"
                    }
    except Exception as e:
        print(f"Error fetching from Sarkari Result: {e}")
    return None

def fetch_from_freejobalert(sent_jobs):
    url = "https://www.freejobalert.com/"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.content, "html.parser")
        
        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            link = a["href"].strip()
            
            if len(title) > 10:
                if not link.startswith("http"):
                    link = "https://www.freejobalert.com" + ("/" if not link.startswith("/") else "") + link
                
                if link not in sent_jobs:
                    return {
                        "title": title,
                        "url": link,
                        "source": "FreeJobAlert.com"
                    }
    except Exception as e:
        print(f"Error fetching from FreeJobAlert: {e}")
    return None

def get_job():
    sent_jobs = load_sent_jobs()
    job = fetch_from_sarkari_result_cm(sent_jobs)
    if not job:
        job = fetch_from_freejobalert(sent_jobs)
    return job

def send_to_telegram(job):
    message_text = f"""📣 <b>NEW JOB ALERT: सरकारी नौकरी की बड़ी भर्ती!</b> 📣

🔹 <b>पद/भर्ती का नाम:</b> {job['title']}
📌 <b>अपडेट स्रोत:</b> {job['source']}

🌐 <b>ऑनलाइन अप्लाई करने और पूरी डिटेल के लिए नीचे क्लिक करें:</b>
👇👇👇
👉 <a href="{job['url']}">ऑनलाइन अप्लाई और पूरी डिटेल लिंक</a>
👉 <a href="https://sarkariresult.com.cm/">Sarkari Result Portal</a>
👉 <a href="https://www.freejobalert.com/">FreeJobAlert Portal</a>"""

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    
    resp = requests.post(url, json=payload)
    print("Telegram Response Status:", resp.status_code)
    print("Telegram Response Text:", resp.text)
    return resp.status_code == 200

def main():
    job = get_job()
    if not job:
        print("दोनों वेबसाइटों पर कोई नई अनपोस्टेड जॉब नहीं मिली।")
        return
        
    print(f"नई जॉब मिली [{job['source']}]: {job['title']}")
    success = send_to_telegram(job)
    if success:
        mark_job_as_sent(job['url'])
        print("सफलतापूर्वक Telegram चैनल पर पोस्ट हो गया!")
    else:
        print("Telegram पर भेजने में एरर आया।")

if __name__ == "__main__":
    main()
    
