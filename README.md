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
