## 📦 requirements.txt

annotated-types==0.7.0
anyio==4.9.0
attrs==25.3.0
beautifulsoup4==4.13.4
certifi==2025.4.26
charset-normalizer==3.4.2
distro==1.9.0
greenlet==3.2.3
h11==0.14.0
httpcore==0.17.3
httpx==0.24.1
idna==3.10
iniconfig==2.1.0
markdown-it-py==2.2.0
mdurl==0.1.2
numpy==1.26.4
openai==1.11.0
outcome==1.3.0.post0
packaging==25.0
pillow==11.2.1
playwright==1.52.0
playwright-stealth==1.0.6
pluggy==1.6.0
pydantic==2.0.2
pydantic_core==2.1.2
pyee==13.0.0
Pygments==2.19.1
PySocks==1.7.1
pytest==7.3.1
python-dotenv==1.0.0
python-telegram-bot==20.3
requests==2.31.0
rich==13.3.5
scipy==1.15.3
selenium==4.33.0
sniffio==1.3.1
sortedcontainers==2.4.0
soupsieve==2.7
tenacity==8.2.2
tqdm==4.65.0
trio==0.30.0
trio-websocket==0.12.2
typing_extensions==4.13.2
urllib3==2.4.0
websocket-client==1.8.0
wsproto==1.2.0
yt-dlp==2025.6.9

---

## 📖 README.md (дополнение)

### ⚙️ Поточне стабільне оточення

- Python 3.11.13
- Playwright 1.52.0
- playwright-stealth 1.0.6
- Chromium 136.0.7103.25 (playwright build 1169)

---

### 🛠 Інструкція Recovery (якщо все зламається)

1. Встановити Python 3.11.13 (рекомендується Homebrew + Pyenv)

2. Створити віртуальне оточення:

```bash
python3.11 -m venv venv
source venv/bin/activate
```

3. Встановити залежності:

```bash
pip install -r requirements.txt
```

4. Встановити Playwright-браузери:

```bash
playwright install
```

✅ Бот буде готовий до роботи!

