import os
import requests
import datetime
import re
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

# 1. MEMUAT KONFIGURASI DAN AI
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Menggunakan model yang teruji aktif dengan fallback
PRIMARY_MODEL_NAME = 'gemini-flash-latest'
FALLBACK_MODEL_NAME = 'gemma-4-26b-a4b-it'

def get_ai_model():
    try:
        return genai.GenerativeModel(PRIMARY_MODEL_NAME)
    except Exception:
        return genai.GenerativeModel(FALLBACK_MODEL_NAME)

model = get_ai_model()

app = Flask(__name__)

# 2. FUNGSI PEMBANTU: WEB SCRAPING
def perbaiki_tautan_html(html_text):
    """Memastikan seluruh atribut href pada tag <a> diawali dengan https://"""
    def sanitize_url(match):
        url = match.group(1).strip()
        if url and not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
        return f'href="{url}"'

    return re.sub(r'href=["\']([^"\']+)["\']', sanitize_url, html_text)

def ambil_teks_dari_link(url):
    """Membaca isi teks dari sebuah halaman web."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        respons = requests.get(url, headers=headers, timeout=10)
        
        if respons.status_code == 200:
            soup = BeautifulSoup(respons.text, 'html.parser')
            teks_bersih = soup.get_text(separator=' ', strip=True)
            return teks_bersih[:3000]
        else:
            return "ERROR_LINK"
    except Exception as e:
        return "ERROR_LINK"

# 3. RUTE HALAMAN UTAMA
@app.route('/')
def home():
    return render_template('index.html')

# 4. RUTE API UNTUK ANALISIS AI
@app.route('/api/analyze', methods=['POST'])
def analyze_text():
    data = request.json
    input_pengguna = data.get('text', '').strip()

    if not input_pengguna:
        return jsonify({"error": "Teks atau link tidak boleh kosong"}), 400

    teks_untuk_dianalisis = input_pengguna

    if input_pengguna.startswith('http://') or input_pengguna.startswith('https://'):
        print(f"[*] Mengambil data dari link: {input_pengguna}")
        hasil_scraping = ambil_teks_dari_link(input_pengguna)
        
        if hasil_scraping == "ERROR_LINK":
            return jsonify({"error": "Gagal membaca isi link. Pastikan link aktif."}), 400
        
        teks_untuk_dianalisis = hasil_scraping

    waktu_sekarang = datetime.datetime.now().strftime("%d %B %Y")

    prompt = f"""
    Kamu adalah analis fakta terpercaya dan asisten literasi digital senior di aplikasi Verisight. 
    Berikan analisis mendalam, obyektif, dan menyeluruh mengenai klaim berikut ini:

    [KONTEN UNTUK DIANALISIS]:
    "{teks_untuk_dianalisis}"

    [KONTEKS WAKTU HARI INI]:
    {waktu_sekarang}.

    TUGAS UTAMA:
    1. Bedah klaim ini secara kritis dan mendalam. Jangan hanya memberikan jawaban singkat. Berikan pembuktian fakta yang kuat berdasarkan data/fakta yang diketahui hingga saat ini.
    2. Identifikasi apakah klaim ini merupakan: FAKTA VALID, DISINFORMASI / HOAKS, MENYESATKAN (MISLEADING), atau PERLU KONFIRMASI SUMBER RESMI.
    3. Sangat Penting: Sediakan TAUTAN REFERENSI BERITA BUKTI REAL / REFERENSI RESMI (seperti ke https://turnbackhoax.id, https://www.kompas.com, https://www.detik.com, https://www.antaranews.com, https://www.cnnindonesia.com, https://www.cnbcindonesia.com, atau situs kementerian/lembaga resmi .go.id) yang relevan dengan topik klaim ini. SETIAP ALAMAT HREF SAAT MENULIS TAG <a href="..."> WAJIB DIAWALI DENGAN PROTOKOL LENGKAP "https://" (misal: href="https://www.cnbcindonesia.com/..." atau href="https://www.google.com/search?q=..."). DILARANG KERAS MENULIS href="www.domain.com" TANPA HTTPS://.
    4. JANGAN GUNAKAN EMOTICON ATAU EMOJI APAPUN. Gunakan teks baku dan rapi.
    5. Gunakan format HTML yang rapi di bawah ini tanpa tag markdown ```html:

    <p class="mb-4 text-slate-800 text-sm leading-relaxed">Halo! Saya asisten literasi digital Anda dari <strong>Verisight</strong>. Berikut adalah hasil penelusuran mendalam dan analisis fakta terhadap klaim yang Anda kirimkan:</p>

    <div class="space-y-4 mb-6">
        <div class="bg-white p-4 rounded-xl border border-slate-200">
            <h4 class="font-bold text-navy-900 text-sm mb-1">Ringkasan Klaim & Subjek Utama</h4>
            <p class="text-slate-600 text-xs leading-relaxed">[Jelaskan klaim utama yang diuji secara jernih dan mendalam]</p>
        </div>

        <div class="bg-white p-4 rounded-xl border border-slate-200">
            <h4 class="font-bold text-navy-900 text-sm mb-1">Tingkat Kredibilitas & Status Verifikasi</h4>
            <div class="flex items-center gap-2 mt-1">
                <span class="px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800">[Label Kredibilitas: Fakta Valid / Disinformasi / Menyesatkan / Perlu Verifikasi]</span>
            </div>
            <p class="text-slate-600 text-xs leading-relaxed mt-2">[Penjelasan mengapa kredibilitas tersebut diberikan]</p>
        </div>

        <div class="bg-white p-4 rounded-xl border border-slate-200">
            <h4 class="font-bold text-navy-900 text-sm mb-1">Analisis Mendalam & Pembuktian Fakta</h4>
            <p class="text-slate-600 text-xs leading-relaxed mb-2">[Sajikan kronologi, fakta sebenarnya, atau bantahan ilmiah/jurnalistik secara detail]</p>
        </div>

        <div class="bg-blue-50/70 p-4 rounded-xl border border-blue-200">
            <h4 class="font-bold text-primary-900 text-sm mb-2">Referensi Berita & Kanal Cek Fakta Resmi</h4>
            <p class="text-xs text-slate-600 mb-2">Berikut adalah tautan rujukan berita dan kanal verifikasi resmi terkait isu ini:</p>
            <ul class="list-disc pl-5 space-y-1.5 text-xs text-primary-700">
                <li><a href="[URL_RELEVAN_1]" target="_blank" rel="noopener noreferrer" class="font-semibold underline hover:text-primary-900">[Judul Artikel Berita / Laporan Cek Fakta 1]</a> - [Keterangan singkat]</li>
                <li><a href="[URL_RELEVAN_2]" target="_blank" rel="noopener noreferrer" class="font-semibold underline hover:text-primary-900">[Judul Artikel Berita / Laporan Cek Fakta 2]</a> - [Keterangan singkat]</li>
            </ul>
        </div>
    </div>

    <div class="bg-primary-50 p-4 rounded-xl border-l-4 border-primary-600 text-xs text-primary-900">
        <strong>Tips Nalar Kritis Verisight:</strong> [Berikan saran spesifik bagi pengguna saat menemui klaim sejenis]
    </div>
    """

    try:
        try:
            response = model.generate_content(prompt)
        except Exception as primary_err:
            print(f"[*] Primary model failed: {primary_err}. Trying fallback model...")
            fallback = genai.GenerativeModel(FALLBACK_MODEL_NAME)
            response = fallback.generate_content(prompt)

        hasil_mentah = response.text

        # --- LOGIKA BARU: MEMISAHKAN THINKING PROCESS ---
        
        # 1. Mencari teks di dalam tag <think> menggunakan Regex
        thinking_match = re.search(r'<think>(.*?)</think>', hasil_mentah, flags=re.DOTALL)
        
        # Jika ketemu, ambil teksnya. Jika tidak ada, kosongkan.
        proses_berpikir = thinking_match.group(1).strip() if thinking_match else "AI langsung memberikan jawaban tanpa catatan internal."

        # 2. Menghapus bagian <think> dari teks utama agar bersih
        hasil_bersih = re.sub(r'<think>.*?</think>', '', hasil_mentah, flags=re.DOTALL)
        
        # 3. Memastikan teks dimulai dari tag HTML (jika ada pengantar yang bocor)
        if '<p' in hasil_bersih:
            hasil_bersih = hasil_bersih[hasil_bersih.find('<p'):]

        hasil_bersih = hasil_bersih.strip()
        hasil_bersih = perbaiki_tautan_html(hasil_bersih)

        # 4. Mengirimkan KEDUA data tersebut ke halaman web
        return jsonify({
            "result": hasil_bersih,
            "thinking": proses_berpikir
        })
        
    except Exception as e:
        return jsonify({"error": f"Kesalahan AI: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)