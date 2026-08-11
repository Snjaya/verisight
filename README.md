# 🛡️ Verisight

> **Platform Verifikasi Informasi & Literasi Digital Berbasis AI**

Verisight adalah aplikasi berbasis **Kecerdasan Buatan (AI)** yang dirancang untuk membantu masyarakat memeriksa kebenaran klaim, berita, tautan, dan tangkapan layar digital.

Verisight tidak hanya berfokus pada hasil *fact-checking*, tetapi juga pada **literasi digital, transparansi proses analisis, dan keamanan AI**. Platform ini membantu pengguna memahami alasan sebuah informasi dinilai benar, meragukan, atau salah sehingga dapat mendorong kemampuan berpikir kritis dalam menghadapi misinformasi dan hoaks.

---

## ✨ Fitur Utama

### 🔎 1. Analisis Informasi Multimodal

Verisight dapat menganalisis berbagai jenis informasi:

* **Teks** — memeriksa klaim atau pernyataan yang diberikan pengguna.
* **URL** — mengambil dan menganalisis isi artikel dari tautan.
* **Gambar / Screenshot** — membaca teks pada gambar menggunakan kemampuan *Vision AI*.
* **Kombinasi input** — pengguna dapat memberikan informasi tambahan untuk membantu proses verifikasi.

### 🧠 2. AI Fact Checking

AI menganalisis klaim dengan mempertimbangkan:

* Isi informasi yang diberikan.
* Konteks klaim.
* Referensi dari sumber web.
* Indikasi informasi yang menyesatkan.
* Kesesuaian antara klaim dan bukti yang ditemukan.

Hasil analisis ditampilkan secara informatif agar mudah dipahami pengguna.

### 🌐 3. Pencarian Referensi Otomatis

Verisight menggunakan **DuckDuckGo Search** untuk mencari sumber informasi yang relevan di internet sebelum AI menghasilkan kesimpulan.

Alur sederhananya:

```text
Input Pengguna
      ↓
Ekstraksi Informasi
      ↓
Pencarian Referensi Web
      ↓
Analisis AI
      ↓
Evaluasi Klaim
      ↓
Hasil Verifikasi
```

### 🛡️ 4. Prompt Injection Protection

Verisight dirancang dengan mekanisme keamanan untuk mengurangi risiko manipulasi AI melalui *prompt injection*.

Pendekatan yang digunakan meliputi:

* System prompt yang membatasi ruang lingkup AI.
* Pemisahan instruksi sistem dan data pengguna.
* Pembatasan AI agar tetap berfokus pada proses verifikasi informasi.
* Pemanfaatan SDK resmi Google untuk menangani respons model.

> **Catatan:** Tidak ada sistem AI yang dapat menjamin perlindungan 100% terhadap seluruh bentuk *prompt injection*. Mekanisme keamanan perlu terus diuji dan diperbarui.

### 🧩 5. Reasoning Trace

Verisight dapat memanfaatkan metadata pemikiran model yang tersedia melalui SDK untuk kebutuhan **transparansi dan debugging**.

Informasi tersebut dipisahkan dari hasil akhir yang ditampilkan kepada pengguna sehingga aplikasi tidak perlu melakukan *regex parsing* terhadap respons AI.

> **Catatan:** *Reasoning trace* bukan berarti seluruh pemikiran internal model ditampilkan kepada pengguna. Implementasi sebaiknya hanya menampilkan informasi penjelasan atau ringkasan yang aman dan relevan.

### 📚 6. Literasi Digital

Selain melakukan verifikasi informasi, Verisight menyediakan materi edukasi yang membantu pengguna memahami:

* Cara mengenali hoaks.
* Cara memeriksa sumber informasi.
* Cara membandingkan beberapa sumber.
* Cara mengenali judul atau konten yang menyesatkan.
* Pentingnya memeriksa informasi sebelum membagikannya.

### 📝 7. Kuis Evaluasi

Fitur kuis digunakan untuk mengukur pemahaman pengguna setelah mempelajari materi literasi digital.

Kuis dapat digunakan untuk:

* Menguji kemampuan mengenali informasi palsu.
* Mengukur pemahaman pengguna.
* Memberikan pengalaman belajar yang interaktif.

---

# 🏗️ Arsitektur Sistem

Verisight menggunakan arsitektur sederhana dengan **Flask sebagai backend** dan **React sebagai frontend**.

```text
┌───────────────────────────────────────────┐
│                 USER                      │
│                                           │
│ Text / URL / Image / Screenshot           │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────┐
│              FRONTEND                     │
│                                           │
│ React.js + Tailwind CSS + JavaScript      │
└─────────────────────┬─────────────────────┘
                      │
                  REST API
                      │
                      ▼
┌───────────────────────────────────────────┐
│               BACKEND                     │
│                                           │
│ Flask + Python                            │
│                                           │
│ ┌───────────────────────────────────────┐ │
│ │ Input Processing                      │ │
│ │ - Text                                │ │
│ │ - URL                                 │ │
│ │ - Image                               │ │
│ └───────────────────┬───────────────────┘ │
│                     ▼                     │
│ ┌───────────────────────────────────────┐ │
│ │ Web Search                            │ │
│ │ DuckDuckGo                            │ │
│ └───────────────────┬───────────────────┘ │
│                     ▼                     │
│ ┌───────────────────────────────────────┐ │
│ │ AI Analysis                           │ │
│ │ Google GenAI                          │ │
│ └───────────────────┬───────────────────┘ │
│                     ▼                     │
│ ┌───────────────────────────────────────┐ │
│ │ Verification Result                   │ │
│ └───────────────────────────────────────┘ │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
              Hasil Verifikasi
```

---

# 🛠️ Teknologi yang Digunakan

## Backend

| Teknologi             | Fungsi                                    |
| --------------------- | ----------------------------------------- |
| **Python 3**          | Bahasa pemrograman backend                |
| **Flask**             | Framework untuk REST API dan web server   |
| **google-genai**      | SDK resmi Google untuk integrasi model AI |
| **BeautifulSoup4**    | Ekstraksi konten halaman web              |
| **Requests**          | Mengambil data dari URL                   |
| **DuckDuckGo Search** | Pencarian referensi web                   |
| **Pillow (PIL)**      | Pemrosesan gambar                         |
| **python-dotenv**     | Membaca variabel lingkungan dari `.env`   |

## Frontend

| Teknologi        | Fungsi                                |
| ---------------- | ------------------------------------- |
| **React.js**     | Membangun antarmuka berbasis komponen |
| **Babel**        | Menjalankan JSX React melalui browser |
| **Tailwind CSS** | Styling dan desain responsif          |
| **JavaScript**   | Pengelolaan state dan komunikasi API  |
| **HTML5**        | Struktur halaman aplikasi             |

---

# 📂 Struktur Direktori

```text
verisight/
│
├── app.py
│   └── Backend Flask, REST API, dan logika AI
│
├── .env
│   └── Variabel lingkungan dan API key
│
├── .gitignore
│   └── Daftar file yang tidak dikirim ke Git
│
├── README.md
│   └── Dokumentasi proyek
│
└── templates/
    └── index.html
        └── Frontend React + Tailwind CSS
```

> **Penting:** File `.env` **jangan pernah diunggah ke repository publik** karena dapat berisi API key.

Contoh `.gitignore`:

```gitignore
.env
env/
venv/
__pycache__/
*.pyc
```

---

# 🚀 Instalasi dan Menjalankan Proyek

## 1. Clone Repository

Clone repository Verisight ke komputer:

```bash
git clone https://github.com/[USERNAME]/verisight.git
cd verisight
```

Ganti `[USERNAME]` dengan username GitHub pemilik repository.

---

## 2. Membuat Virtual Environment

Virtual environment digunakan untuk mengisolasi dependency Python dari sistem utama.

### Windows

```bash
python -m venv env
env\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv env
source env/bin/activate
```

Jika berhasil, terminal biasanya akan menampilkan:

```text
(env)
```

---

## 3. Install Dependencies

Install seluruh library yang dibutuhkan:

```bash
pip install flask python-dotenv google-genai duckduckgo-search beautifulsoup4 requests pillow
```

Jika proyek memiliki file `requirements.txt`, lebih baik gunakan:

```bash
pip install -r requirements.txt
```

---

## 4. Konfigurasi API Key

Buat file `.env` di direktori utama proyek:

```text
verisight/
├── app.py
├── .env
└── templates/
```

Kemudian isi:

```env
GEMINI_API_KEY=MASUKKAN_API_KEY_ANDA
```

**Jangan memasukkan API key langsung ke dalam source code.**

---

## 5. Menjalankan Server

Jalankan:

```bash
python app.py
```

Jika server berhasil berjalan, buka browser dan akses:

```text
http://127.0.0.1:5000
```

atau:

```text
http://localhost:5000
```

---

# 🔄 Alur Kerja Verisight

Proses utama Verisight dapat digambarkan sebagai berikut:

```text
                    ┌──────────────┐
                    │    Pengguna  │
                    └──────┬───────┘
                           │
                           ▼
                ┌────────────────────┐
                │ Masukkan Informasi │
                │ Text / URL / Image │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │ Input Processing   │
                └─────────┬──────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
           Text          URL        Image
              │           │           │
              │           ▼           ▼
              │      Web Scraping   Vision AI
              │           │           │
              └───────────┼───────────┘
                          ▼
                ┌────────────────────┐
                │ Web Search         │
                │ DuckDuckGo         │
                └─────────┬──────────┘
                          ▼
                ┌────────────────────┐
                │ AI Fact Checking   │
                │ Google GenAI       │
                └─────────┬──────────┘
                          ▼
                ┌────────────────────┐
                │ Evaluasi Klaim     │
                └─────────┬──────────┘
                          ▼
                ┌────────────────────┐
                │ Hasil Verifikasi   │
                │ + Referensi        │
                └────────────────────┘
```

---

# 📡 API

Endpoint utama backend:

```text
POST /api/analyze
```

Endpoint tersebut digunakan frontend untuk mengirim data yang akan dianalisis oleh backend.

Secara umum:

```text
Frontend
   │
   │ POST /api/analyze
   ▼
Flask Backend
   │
   ├── Validasi input
   ├── Proses URL / gambar
   ├── Pencarian referensi
   ├── Analisis AI
   └── Membuat hasil
   │
   ▼
JSON Response
   │
   ▼
Frontend
```

Contoh struktur request:

```text
FormData
├── text
├── url
└── image
```

Struktur tersebut dapat disesuaikan dengan implementasi aktual pada `app.py`.

---

# 🔐 Keamanan

Keamanan menjadi salah satu bagian penting dalam pengembangan Verisight.

## Perlindungan API Key

API key disimpan menggunakan environment variable:

```env
GEMINI_API_KEY=********
```

Bukan:

```python
GEMINI_API_KEY = "AIza..."
```

## Perlindungan Prompt Injection

Input pengguna diperlakukan sebagai **data yang akan dianalisis**, bukan sebagai instruksi sistem.

Konsepnya:

```text
System Instruction
        │
        ▼
   Aturan Verisight
        │
        ▼
User Input ──► Data untuk dianalisis
        │
        ▼
    AI Analysis
```

Pengguna tidak seharusnya dapat mengubah aturan utama AI hanya dengan memasukkan instruksi tertentu ke dalam teks yang diperiksa.

## Validasi Input

Backend sebaiknya melakukan validasi terhadap:

* Ukuran file.
* Format gambar.
* URL.
* Panjang teks.
* Input kosong.
* Respons dari layanan eksternal.

---

# ⚠️ Keterbatasan Sistem

Verisight merupakan alat bantu verifikasi dan **bukan pengganti pemeriksa fakta profesional**.

Beberapa keterbatasan yang perlu diperhatikan:

1. Hasil AI dapat mengandung kesalahan.
2. Informasi di internet dapat berubah.
3. Tidak semua sumber web memiliki kredibilitas yang sama.
4. Hasil pencarian mesin pencari dapat berbeda dari waktu ke waktu.
5. Artikel tertentu mungkin tidak dapat diakses karena *paywall* atau pembatasan website.
6. Gambar dengan kualitas rendah dapat menyebabkan kesalahan pembacaan teks.
7. Perlindungan terhadap *prompt injection* perlu terus diuji.
8. Keputusan akhir tetap memerlukan penilaian manusia untuk kasus yang kompleks.

Karena itu, pengguna tetap disarankan memeriksa sumber asli sebelum menyebarkan informasi penting.

---

# 🧪 Pengujian yang Disarankan

Sebelum digunakan dalam demonstrasi atau kompetisi, lakukan pengujian berikut.

## Functional Testing

* [ ] Analisis teks berhasil.
* [ ] Analisis URL berhasil.
* [ ] Upload gambar berhasil.
* [ ] Gambar tidak valid ditolak.
* [ ] URL tidak valid ditangani.
* [ ] Input kosong ditangani.
* [ ] Hasil analisis tampil di frontend.
* [ ] Referensi sumber ditampilkan dengan benar.

## Security Testing

* [ ] API key tidak berada di source code.
* [ ] `.env` masuk `.gitignore`.
* [ ] Prompt injection dasar diuji.
* [ ] Input berbahaya diuji.
* [ ] File dengan format tidak sesuai diuji.
* [ ] Ukuran upload dibatasi.
* [ ] Error dari API eksternal ditangani.

## Usability Testing

* [ ] Tampilan desktop responsif.
* [ ] Tampilan mobile dapat digunakan.
* [ ] Informasi hasil mudah dipahami.
* [ ] Tombol dan form mudah digunakan.
* [ ] Pesan error jelas bagi pengguna.

---

# 📈 Pengembangan Selanjutnya

Beberapa pengembangan yang dapat dilakukan:

* [ ] Sistem kredibilitas sumber.
* [ ] Riwayat pemeriksaan pengguna.
* [ ] Login dan profil pengguna.
* [ ] Dashboard literasi digital.
* [ ] Sistem skor literasi pengguna.
* [ ] Database artikel dan hasil verifikasi.
* [ ] Integrasi lebih banyak sumber *fact-checking*.
* [ ] Dukungan bahasa daerah.
* [ ] Peningkatan OCR untuk screenshot.
* [ ] Peningkatan keamanan terhadap prompt injection.
* [ ] Unit testing dan integration testing.
* [ ] Deployment ke cloud server.
* [ ] Monitoring penggunaan API.
* [ ] Rate limiting untuk endpoint API.

---

# 🎯 Tujuan Proyek

Verisight dikembangkan dengan tiga tujuan utama:

### 1. Membantu Verifikasi Informasi

Membantu pengguna memeriksa klaim dan informasi digital secara lebih cepat dengan bantuan AI dan sumber web.

### 2. Meningkatkan Literasi Digital

Tidak hanya memberikan hasil benar atau salah, tetapi membantu pengguna memahami **mengapa suatu informasi perlu dipercaya atau diragukan**.

### 3. Mendorong Penggunaan AI yang Bertanggung Jawab

Mengembangkan aplikasi AI yang memperhatikan aspek:

* Transparansi.
* Keamanan.
* Validasi informasi.
* Perlindungan terhadap manipulasi AI.
* Pengambilan keputusan yang tetap melibatkan manusia.

---

# 🏆 Konteks Kompetisi

Verisight dikembangkan sebagai proyek yang relevan dengan tema:

> **Literasi Digital dan Anti-Hoaks**

Proyek ini dapat dikembangkan lebih lanjut untuk kebutuhan demonstrasi dan kompetisi **GEMASTIK XIX 2026**, khususnya pada bidang **Software Development**.

Fokus utama proyek adalah menggabungkan:

```text
AI
+
Fact Checking
+
Literasi Digital
+
Keamanan AI
+
User Education
```

sehingga Verisight tidak hanya berfungsi sebagai alat pendeteksi informasi, tetapi juga sebagai media pembelajaran literasi digital.

---

# 🤝 Kontribusi

Kontribusi terhadap proyek dapat dilakukan melalui:

1. Fork repository.
2. Buat branch baru.
3. Lakukan perubahan.
4. Uji perubahan.
5. Buat Pull Request.

Contoh:

```bash
git checkout -b feature/nama-fitur
git add .
git commit -m "feat: menambahkan fitur baru"
git push origin feature/nama-fitur
```

---

# 📜 Lisensi

Tambahkan lisensi proyek sesuai kebutuhan tim dan ketentuan kompetisi.

Contoh:

```text
Copyright © 2026 Verisight Team
```

---

# 👥 Tim

**Verisight Team**

> 🛡️ **Verisight — Verify Before You Share.**

---

# 📌 Git Workflow

Setelah melakukan perubahan dokumentasi:

```bash
git status
git add README.md
git commit -m "docs: memperbarui README"
git push origin main
```

Pastikan tidak ada file rahasia seperti `.env` yang ikut ter-*commit*:

```bash
git status
```

Jika `.env` masih muncul sebagai file yang akan diunggah, periksa kembali `.gitignore` sebelum melakukan `git push`.

---

# ⭐ Prinsip Verisight

> **Jangan hanya percaya pada informasi. Periksa, pahami, lalu bagikan.**
