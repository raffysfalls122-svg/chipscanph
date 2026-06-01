# 📱 ChipScan PH — Mobile Testing Guide

This guide walks you through connecting your mobile device (smartphone or tablet) directly to the **ChipScan PH** system running on your development machine. 

This enables you to test live camera auto-scanning, OCR, and the mobile-friendly user interface directly on real hardware.

---

## ⚡ Prerequisite Check: HTTPS & Camera Access
Modern mobile browsers (iOS Safari and Android Chrome) **restrict camera access (getUserMedia)** to secure contexts:
1. `localhost` / `127.0.0.1` (Always secure, but only accessible on your laptop).
2. `https://` secure domains (Required for remote network connections).

Below are the **3 robust options** to run and test ChipScan PH on your mobile device.

---

## 🌐 Option A: Local WiFi Network (Fastest & Simplest)
If both your laptop and mobile device are connected to the **same local WiFi network**, you can access the server directly.

### 1. Bind Django Server to All Interface IPs
By default, `runserver` only listens on localhost. To allow external network connections, run:
```bash
python manage.py runserver 0.0.0.0:8000
```

### 2. Find Your Laptop's Local IP Address
- **Windows**: Open PowerShell/CMD and type:
  ```powershell
  ipconfig
  ```
  Look for `IPv4 Address` under your wireless adapter (e.g., `192.168.1.15`).
- **Mac/Linux**: Open terminal and type:
  ```bash
  ifconfig | grep "inet "
  ```

### 3. Access on Mobile
Open your mobile browser and navigate to:
```
http://<YOUR-LAPTOP-IP>:8000
```
*(e.g., `http://192.168.1.15:8000`)*

> [!NOTE]
> **Mobile Camera Permissions on HTTP:**
> Chrome and Safari will block camera access over insecure `http://` local IP connections. To bypass this on Android Chrome:
> 1. Open `chrome://flags/#unsafely-treat-insecure-origin-as-secure` on your mobile Chrome browser.
> 2. Enable the flag and enter `http://<YOUR-LAPTOP-IP>:8000` in the input text area.
> 3. Relaunch Chrome. Now the camera permission will be allowed!
>
> On **iOS Safari**, you MUST use **Option B (ngrok)** for secure `https://` access.

---

## 🔒 Option B: Ngrok Tunneling (Recommended for iOS/Safari)
Ngrok provides a secure public `https://` tunnel to your local server, satisfying all browser security guidelines out-of-the-box.

### 1. Start Django Server
```bash
python manage.py runserver 8000
```

### 2. Create Public Tunnel via Ngrok
If you have ngrok installed, open a new terminal window and run:
```bash
ngrok http 8000
```

### 3. Open Secure Link on Mobile
Ngrok will display a public URL forwarding traffic to your machine:
```
https://<random-id>.ngrok-free.app
```
Open this secure **`https://`** URL on your iPhone Safari or Android Chrome browser. Camera access will work instantly!

---

## 🔗 Option C: Custom Local Area Connection (Ad-hoc Hotspot)
If you don't have active internet access or a router:
1. Turn on your **Mobile Hotspot** on your smartphone.
2. Connect your laptop to your smartphone's hotspot network.
3. Find your laptop IP using `ipconfig` (the hotspot gate IP).
4. Run Django via `python manage.py runserver 0.0.0.0:8000`.
5. Open your browser on mobile and enter `http://<YOUR-LAPTOP-IP>:8000`.

---

## 🛠️ Troubleshooting Mobile Access
- **Connection Timed Out?** Your Windows Defender or system firewall is likely blocking port 8000. 
  - On Windows, open PowerShell as Admin and run this command to temporarily allow port 8000:
    ```powershell
    New-NetFirewallRule -DisplayName "Django Port 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
    ```
- **"Origin Not Allowed"?** `ALLOWED_HOSTS = ['*']` is already set in `settings.py`, so you will not face any Django host blocking issues.
