# 🛡️ VERISIGHT: Platform Verifikasi Informasi & Literasi Digital

Verisight adalah aplikasi berbasis kecerdasan buatan (AI) yang dirancang untuk membantu masyarakat menguji kebenaran klaim, berita, dan tangkapan layar digital. Dibangun untuk mengedukasi nalar kritis dan memberantas misinformasi secara interaktif.

## ✨ Fitur Utama

- **Analisis Teks & Klaim (Anti-Bypass):** Mengevaluasi pernyataan teks dengan tingkat akurasi tinggi, dikawal oleh sistem *prompt* ketat yang tahan terhadap serangan *Prompt Injection*.
- **Web Scraping Tautan Artikel:** Secara otomatis membaca konten dari tautan URL publik menggunakan `BeautifulSoup` untuk memverifikasi isi berita.
- **Pencarian Referensi Otomatis:** Terintegrasi dengan `duckduckgo-search` untuk mencari fakta pembanding secara *real-time* di internet sebelum AI menarik kesimpulan.
- **Vision AI (Analisis Gambar):** Memanfaatkan model *Multimodal* untuk mengekstrak dan mengevaluasi teks dari unggahan tangkapan layar (*screenshot*) menggunakan pustaka `Pillow`.
- **Transparansi Nalar (Reasoning Trace):** Menampilkan pemikiran internal AI di balik layar menggunakan fitur pemisahan pintar (SDK `google-genai` terbaru dengan `part.thought`), memberikan transparansi penuh kepada pengguna.
- **Antarmuka React Modern:** Antarmuka interaktif dan responsif yang dibangun menggunakan React (CDN) dan Tailwind CSS.

## 🛠️ Teknologi yang Digunakan

**Backend:**
- Python 3
- Flask (Web Framework)
- `google-genai` (Google Gemini AI Official SDK)
- `BeautifulSoup4` & `requests` (Web Scraping)
- `duckduckgo-search` (Pencarian Internet)
- `Pillow` (Pemrosesan Gambar)

**Frontend:**
- HTML5 / JavaScript (ES6)
- React.js & Babel (Standalone via CDN)
- Tailwind CSS (Utility-first Styling)

## 🚀 Cara Menjalankan di Komputer Lokal (Local Setup)

Ikuti langkah-langkah ini untuk menjalankan Verisight di lingkungan pengembangan lokal Anda:

### 1. Prasyarat
Pastikan Anda telah menginstal **Python (versi 3.8 - 3.11 disarankan)** dan **Git**.

### 2. Kloning Repositori
```bash
git clone [https://github.com/](https://github.com/)[Username-Kamu]/verisight.git
cd verisight
