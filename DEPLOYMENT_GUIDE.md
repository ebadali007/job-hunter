# 🌐 Global Job Hunter - 24/7 Cloud Hosting & Deployment Guide

## 📌 1. Hosting Par Upload Karne Ka Sach (Important Technical Reality)

Aapne poocha ke aapke paas hosting hai aur aap subdomain par upload karna chahte hain:

### A) Agar Aapke Paas **VPS (Linux / Ubuntu Server)** Hai:
* **Status:** 🟢 **100% PERFECT & FULLY SUPPORTED!**
* **Kyun:** Kyunki Job Hunter mein **Python 3**, **FastAPI**, aur **Playwright (Chromium Headless Browser Engine)** shamil hain jo direct websites par ja kar candidate forms fill karte hain. VPS par root access hoti hai jahan Playwright browser install ho sakta hai aur 24/7/365 background daemon run ho sakta hai.

### B) Agar Aapke Paas **Basic Shared Hosting (cPanel / Hostinger Shared / Namecheap PHP)** Hai:
* **Status:** 🔴 **Shared PHP Hosting Par Playwright Run Nahi Ho Sakta**
* **Kyun:** Shared hosting sirf static HTML/PHP websites (jaise WordPress) ke liye hoti hai. Wahan:
  1. Chromium browser aur OS libraries install karne ki permission nahi hoti.
  2. Long-running background Python daemons (jo har 1 ghante baad chalen) automatically kill ho jaate hain.

---

## 🚀 Option 1: VPS / Cloud Server Par Subdomain Setup (Docker Method - Recommended)

Agar aapke paas Ubuntu / Linux VPS hai (jaise DigitalOcean, Hetzner, AWS EC2, Contabo):

1. **Files upload karein:**
   ```bash
   scp -r job-hunter root@your-server-ip:/var/www/
   cd /var/www/job-hunter
   ```

2. **Docker Compose se 1 command mein start karein:**
   ```bash
   docker-compose up -d --build
   ```
   * Yeh automatically Python, Playwright Chromium, aur saare dependencies containerize kar dega aur `restart: always` ke sath 24/7 chala dega.

3. **Subdomain Nginx Setup (e.g. `jobs.yourdomain.com`):**
   * Apne DNS provider (Cloudflare, Namecheap, GoDaddy) par ek `A` record add karein:
     - Name: `jobs`
     - Value: `YOUR_SERVER_IP`
   * Server par `deploy/nginx.conf` ko copy karein:
     ```bash
     sudo cp deploy/nginx.conf /etc/nginx/sites-available/jobhunter
     sudo ln -s /etc/nginx/sites-available/jobhunter /etc/nginx/sites-enabled/
     sudo certbot --nginx -d jobs.yourdomain.com
     sudo systemctl restart nginx
     ```
   * Ab aapka dashboard poori duniya mein kahin se bhi **`https://jobs.yourdomain.com`** par bina PC on kiye live khulega!

---

## 🆓 Option 2: 100% Free 24/7 Cloud Hosting ($0 Cost)

Agar aapke paas VPS nahi hai aur aap PC bhi on nahi rakhna chahte:
* **Railway.app / Render.com:** Aap is repo ko GitHub par push kar ke **Railway** ya **Render** par connect kar sakte hain. Dockerfile already included hai.
* **Oracle Cloud Always Free Tier:** Oracle 24GB RAM aur 4 OCPU ka ARM VPS lifetime **$0 free** deta hai jahan aap apna subdomain connect kar ke 24/7 chala sakte hain.

---

## 💻 Option 3: Local PC Par 24/7 Silent Background Auto-Start (Without Touching Anything)

Agar aap apne PC par hi chalana chahte hain aur chahte hain ke:
1. **Rooz aa kar start na karna pare:** PC on hotay hi background mein khud chalu ho jaye.
2. **Koi Black Window / Terminal na khulay:** Bilkul silent background service ki tarah chalay.
3. **Din-raat har 1 ghante baad khud hunt aur apply kare.**

### Setup Kaise Karein (Sirf 1 Click):
1. Folder mein jayein: `c:\Users\User\Downloads\job-hunter\deploy\`
2. **`install_autostart_windows.bat`** par double click karein.
3. Yeh automatically Windows Startup mein silent runner attach kar dega.
4. Ab aapka PC jab bhi on hoga, Job Hunter background mein port 8050 par khud launch ho jayega aur har 60 minutes baad bina aapko bataye khud fresh jobs dhoond kar apply karta rahega!
