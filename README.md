# Telegram Job Bot - Automated Sarkari Job Updates

यह एक ऑटोमेटेड टेलीग्राम बॉट है जो **SarkariResult** और **FreeJobAlert** से लेटेस्ट सरकारी नौकरियों (Government Jobs) के अपडेट्स निकालकर सीधे टेलीग्राम चैनल **@divyacybercafe** पर पोस्ट करता है।

## विशेषताएं (Features)
- 🤖 **पूरी तरह से ऑटोमैटिक:** GitHub Actions द्वारा हर 30 मिनट में (दिन में 48 बार) स्वतः चलता है।
- 🚫 **नो डुप्लीकेट पोस्ट:** `sent_jobs.txt` की मदद से भेजी जा चुकी जॉब्स का रिकॉर्ड रखता है ताकि दोहराव न हो।
- ⚡ **फास्ट अलर्ट्स:** वेब-स्क्रैपिंग के माध्यम से नई वैकेंसी की तुरंत सूचना देता है।

## फाइल्स की जानकारी
- `bot.py`: डेटा स्क्रैप करने और Telegram API द्वारा संदेश भेजने की मुख्य स्क्रिप्ट।
- `requirements.txt`: प्रोजेक्ट के लिए आवश्यक Python पुस्तकालय (`requests`, `beautifulsoup4`)[cite: 1, 3]。
- `.github/workflows/scheduler.yml`: GitHub Actions के लिए ऑटो-शेड्यूलर[cite: 1, 4]。
- `sent_jobs.txt`: पोस्ट किए गए लिंक्स की हिस्ट्री[cite: 1, 16]।
