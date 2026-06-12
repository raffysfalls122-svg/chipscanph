# ChipScan PH 🇵🇭

A premium mobile-responsive smartphone storage chip grading and pricing application built with **Python, Django, and SQLite**.

---

## 📱 How to Open on Your Phone Using the Same WiFi
You can open this grading system on your mobile phone to use your phone's camera as a real-time scanner. To make it work across devices on the same WiFi network, follow these simple steps:

### 1. Identify Your Computer's Local IP
When you run the server, the terminal will automatically detect and print your network IP (e.g. `192.168.1.10`).

### 2. Start the Django Server (Bind to All Interfaces)
Launch the server binding to `0.0.0.0` (all network interfaces) so other devices on your WiFi can connect:
```bash
python manage.py runserver 0.0.0.0:8000
```

### 3. Open the Link on Your Phone
On your phone (connected to the **same WiFi** network as your computer), open your browser and navigate to:
👉 **`http://<YOUR_COMPUTER_IP>:8000`** (e.g., `http://192.168.1.10:8000`)

---

## 📸 Enabling Camera Scanner on Your Phone (Crucial Browser Security Setup)
Modern mobile browsers (Chrome, Safari, Edge) block the live camera stream (`getUserMedia`) on local HTTP connections for security (they require HTTPS). Since you are running locally on your WiFi (`http://...`), you must tell your mobile browser to trust this connection:

### For Android (Google Chrome)
1. Open Google Chrome on your mobile phone.
2. In the URL address bar, type exactly:
   👉 **`chrome://flags/#unsafely-treat-insecure-origin-as-secure`**
3. Tap Enter. In the flags page:
   - Find the **"Insecure origins treated as secure"** text box.
   - Enter your computer's local IP link exactly: **`http://<YOUR_COMPUTER_IP>:8000`** (e.g., `http://192.168.1.10:8000`).
   - Change the dropdown next to it from **Disabled** to **Enabled**.
4. Tap the **Relaunch** button at the bottom of Chrome.
5. Re-open `http://<YOUR_COMPUTER_IP>:8000` on your phone, navigate to **SCAN**, tap **START**, and your real live camera viewfinder will work flawlessly!

### For iOS (Safari)
iOS allows local camera access on standard local networks automatically. Simply connect your iPhone to the same WiFi, open Safari, navigate to `http://<YOUR_COMPUTER_IP>:8000`, tap **START**, and tap **Allow** when prompted for camera access.

---

## 🚀 Server Installation & Configuration

### Prerequisites
Make sure you have **Python 3.10+** installed on your computer.

### 1. Install Dependencies
Open your command line and run:
```bash
pip install -r requirements.txt
```

### 2. Run Database Migrations
Create and execute migrations to initialize the local SQLite database (`db.sqlite3`):
```bash
python manage.py makemigrations
python manage.py migrate
```

*Note: On your first page load, ChipScan PH's lazy pre-seeder will automatically populate the database with the default credentials, standard buy rates, and 28 built-in eMMC/UFS storage chips!*

---

## 🔐 Default Login Credentials

| Role | Username | Password |
|---|---|---|
| **IT Admin** | `admin` | `admin123` |
| **Technician** | `tech1` | `tech123` |

*IT Admins have full privileges to register new technician accounts, delete users, reset logs, and download DB backups in the **ADMIN** tab.*

---

## ⚙️ Tesseract-OCR Setup (Required for Local OCR Scanner)
The local image scanner runs using **Tesseract-OCR**. To enable text extraction from chip images, you need to install Tesseract on your host system:

### 1. Windows Installation
1. Download the Tesseract installer from [UB Mannheim's GitHub](https://github.com/UB-Mannheim/tesseract/wiki) (e.g., `tesseract-ocr-w64-setup-v5.3.0.exe`).
2. Run the installer. The default path is `C:\Program Files\Tesseract-OCR`.
3. Add `C:\Program Files\Tesseract-OCR` to your Windows System Environment Variables `PATH`.
4. Restart your terminal or command prompt to apply changes.

*(The Django backend automatically attempts to locate Tesseract at its default installation path: `C:\Program Files\Tesseract-OCR\tesseract.exe`).*

### 2. macOS Installation
Install via Homebrew:
```bash
brew install tesseract
```

### 3. Linux (Ubuntu/Debian) Installation
Install via apt-get:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

---

## 🤖 OpenRouter AI-Assisted Chip Scanning & Database Verification

This application uses an optional extra extraction layer powered by **OpenRouter Vision AI**. When you scan/upload a chip image, the system executes two steps:
1. **Local OCR (Tesseract)** reads text if available.
2. **OpenRouter Vision AI** reads the uploaded image to extract visible markings/codes.

The backend combines all extracted possibilities, normalizes them, and queries the **local database**. Final chip verification, pricing, grades, storage, and status **always come from the local database**—never from the AI's guesses, ensuring total data integrity.

### Environment Configuration (.env)

Create a `.env` file in the project root based on `.env.example` and set your credentials:

```bash
# OpenRouter AI Scanning Settings
OPENROUTER_API_KEY=your-openrouter-api-key-here
OPENROUTER_MODEL=your-vision-capable-openrouter-model
OPENROUTER_SITE_URL=http://127.0.0.1:8000
OPENROUTER_APP_NAME=ChipScanPH

# Database Settings
DATABASE_ENGINE=sqlite
DATABASE_NAME=db.sqlite3
```

- **OpenRouter Fallback**: If `OPENROUTER_API_KEY` is missing, or if OpenRouter returns a 404/failure, the system automatically falls back to local OCR-only scanner mode without crashing.
- **Model Configuration (404 / Safety Error)**: The model to use is loaded dynamically from the `OPENROUTER_MODEL` variable in your `.env` file (it is not hardcoded in the codebase). If you receive an **"AI model unavailable (404)"** note, it means the model is either not found or not active on your OpenRouter account. In this case, please edit your `.env` file and replace `OPENROUTER_MODEL` with another active, vision-capable model from OpenRouter (e.g. `google/gemini-2.5-flash` or similar). Do not use content-safety, audio, embedding, image-generation, or text-only models for chip image scanning. Use only a vision-capable model that accepts image input and can return text JSON. If the model returns content like `User Safety: safe.`, the selected model is likely not suitable for chip scanning and should be changed in `.env`.
- **Database Engine Support**: Supports SQLite (default) and PostgreSQL by setting `DATABASE_ENGINE=postgresql` and populating connection details.

