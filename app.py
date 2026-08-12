import os
import requests
import datetime
import re
import io
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google import genai
from google.genai import types
from duckduckgo_search import DDGS
from PIL import Image

# 1. MEMUAT KONFIGURASI DAN CLIENT AI TERBARU
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)

# 2. FUNGSI PEMBANTU: WEB SCRAPING & UTILITIES
def perbaiki_tautan_html(html_text):
    def sanitize_url(match):
        url = match.group(1).strip()
        if url and not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
        return f'href="{url}"'
    return re.sub(r'href=["\']([^"\']+)["\']', sanitize_url, html_text)

def ambil_teks_dari_link(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        respons = requests.get(url, headers=headers, timeout=10)
        if respons.status_code == 200:
            soup = BeautifulSoup(respons.text, 'html.parser')
            return soup.get_text(separator=' ', strip=True)[:3000]
        return "ERROR_LINK"
    except:
        return "ERROR_LINK"

def cari_referensi_internet(teks_input):
    try:
        kata_kunci = teks_input[:100]
        hasil_ddg = DDGS().text(kata_kunci, max_results=3)
        if not hasil_ddg: 
            return "Tidak ditemukan referensi langsung di internet."
        
        hasil_pencarian_teks = ""
        for i, hasil in enumerate(hasil_ddg):
            hasil_pencarian_teks += f"Referensi {i+1}:\n- Judul: {hasil['title']}\n- Link: {hasil['href']}\n- Ringkasan: {hasil['body']}\n\n"
        return hasil_pencarian_teks
    except:
        return "Gagal mengambil data dari mesin pencari."

# 3. RUTE HALAMAN UTAMA
@app.route('/')
def home():
    return render_template('index.html')

# 4. RUTE API UNTUK ANALISIS AI
@app.route('/api/analyze', methods=['POST'])
def analyze_text():
    # Mengambil data berdasarkan tab yang digunakan pengguna
    input_teks = request.form.get('text', '').strip()
    input_url = request.form.get('url', '').strip()
    file_gambar = request.files.get('image')

    if not input_teks and not input_url and not file_gambar:
        return jsonify({"error": "Input tidak boleh kosong"}), 400

    teks_untuk_dianalisis = ""
    referensi_internet = "Menganalisis data dari gambar atau tautan langsung."
    gambar_diproses = None

    # Pola Regex untuk mendeteksi struktur URL
    pola_url = re.compile(r'^(https?://|www\.)[^\s/$.?#].[^\s]*$', re.IGNORECASE)

    # A. LOGIKA JIKA TAB GAMBAR
    if file_gambar and file_gambar.filename != '':
        try:
            image_bytes = file_gambar.read()
            gambar_diproses = Image.open(io.BytesIO(image_bytes))
            teks_untuk_dianalisis = "Tolong analisis gambar ini, baca teks di dalamnya, dan periksa fakta dari informasi tersebut."
        except Exception as e:
            return jsonify({"error": "Format gambar tidak didukung."}), 400

    # B. LOGIKA JIKA TAB URL (CEGATAN ANTI-LINK PALSU)
    elif input_url:
        # CEK: Apakah teks yang diketik benar-benar sebuah link?
        if not pola_url.match(input_url) and not input_url.startswith('http'):
            # Jika BUKAN link, kembalikan error instan tanpa memanggil AI!
            html_bukan_link = """
            <div class="bg-rose-50 p-6 rounded-xl border border-rose-200 text-center mb-6">
                <div class="w-12 h-12 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center mx-auto mb-3">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                </div>
                <h4 class="font-bold text-rose-900 text-lg mb-2">Bukan Tautan Berita</h4>
                <p class="text-rose-700 text-sm">Teks yang Anda masukkan di kolom URL tidak memiliki format tautan yang valid (seperti http:// atau www.). Harap gunakan kolom 'Teks Klaim' jika Anda ingin mengetik pernyataan biasa.</p>
            </div>
            """
            return jsonify({"result": html_bukan_link, "thinking": "Input ditolak oleh sistem penjaga. Format tidak menyerupai tautan web."})

        # Jika link valid, lanjutkan Scraping
        url_target = input_url
        if not url_target.startswith('http'):
            url_target = 'https://' + url_target
            
        hasil_scraping = ambil_teks_dari_link(url_target)
        if hasil_scraping == "ERROR_LINK":
            html_link_rusak = """
            <div class="bg-rose-50 p-6 rounded-xl border border-rose-200 text-center mb-6">
                <div class="w-12 h-12 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center mx-auto mb-3">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                </div>
                <h4 class="font-bold text-rose-900 text-lg mb-2">Tautan Tidak Dapat Diakses</h4>
                <p class="text-rose-700 text-sm">Sistem gagal membaca isi dari tautan tersebut. Kemungkinan tautan rusak, diblokir keamanan website, atau artikel telah dihapus.</p>
            </div>
            """
            return jsonify({"result": html_link_rusak, "thinking": "Gagal scraping konten dari URL yang diberikan."})
            
        teks_untuk_dianalisis = hasil_scraping

    # C. LOGIKA JIKA TAB TEKS BIASA
    elif input_teks:
        teks_untuk_dianalisis = input_teks
        referensi_internet = cari_referensi_internet(input_teks)

    waktu_sekarang = datetime.datetime.now().strftime("%d %B %Y")

    # PROMPT AI PENJAGA GERBANG TEKS
    prompt = f"""Tugasmu adalah mengevaluasi input pengguna.

[DATA]
Waktu: {waktu_sekarang}
Referensi Web: {referensi_internet}
Klaim: "{teks_untuk_dianalisis}"

[ATURAN PENJAGA GERBANG]
Pertama, evaluasi apakah "Klaim" di atas benar-benar sebuah klaim, berita, atau informasi yang masuk akal. 
JIKA input HANYA berupa teks acak (contoh: "asdfgh"), suara tawa ("hahaha"), sapaan ringan ("halo"), atau kalimat tanpa makna, MAKA BERHENTI dan HANYA keluarkan kode HTML ini tanpa markdown ```html:

<div class="bg-rose-50 p-6 rounded-xl border border-rose-200 text-center mb-6">
    <div class="w-12 h-12 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center mx-auto mb-3">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
    </div>
    <h4 class="font-bold text-rose-900 text-lg mb-2">Input Tidak Valid</h4>
    <p class="text-rose-700 text-sm">Teks ini tidak terdeteksi sebagai pernyataan yang dapat diverifikasi faktanya. Mohon masukkan klaim yang spesifik.</p>
</div>

[ATURAN WAJIB OUTPUT JIKA INPUT VALID]
JIKA valid, berikan HANYA kode HTML di bawah ini yang sudah diisi dengan analisis nyatamu. JANGAN gunakan tag markdown ```html.

<p class="mb-4 text-slate-800 text-sm leading-relaxed">Halo! Saya asisten literasi digital Anda dari <strong>Verisight</strong>. Berikut adalah hasil penelusuran fakta terhadap klaim tersebut:</p>

<div class="space-y-4 mb-6">
    <div class="bg-white p-4 rounded-xl border border-slate-200">
        <h4 class="font-bold text-navy-900 text-sm mb-1">Ringkasan Klaim & Subjek Utama</h4>
        <p class="text-slate-600 text-xs leading-relaxed">[Jelaskan klaim utama dengan padat]</p>
    </div>

    <div class="bg-white p-4 rounded-xl border border-slate-200">
        <h4 class="font-bold text-navy-900 text-sm mb-1">Status Verifikasi</h4>
        <div class="flex items-center gap-2 mt-1 mb-2">
            <span class="px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800">[Pilih: Fakta Valid / Disinformasi / Menyesatkan / Perlu Verifikasi]</span>
        </div>
        <p class="text-slate-600 text-xs leading-relaxed">[Alasan singkat penentuan status]</p>
    </div>

    <div class="bg-white p-4 rounded-xl border border-slate-200">
        <h4 class="font-bold text-navy-900 text-sm mb-1">Analisis Mendalam & Pembuktian Fakta</h4>
        <p class="text-slate-600 text-xs leading-relaxed mb-2">[Bantahan atau konfirmasi berdasarkan bukti nyata]</p>
    </div>

    <div class="bg-blue-50/70 p-4 rounded-xl border border-blue-200">
        <h4 class="font-bold text-primary-900 text-sm mb-2">Referensi Berita & Kanal Cek Fakta Resmi</h4>
        <ul class="list-disc pl-5 space-y-1.5 text-xs text-primary-700">
            <li><a href="[URL_HTTPS]" target="_blank" rel="noopener noreferrer" class="font-semibold underline hover:text-primary-900">[Judul Referensi]</a></li>
        </ul>
    </div>
</div>

<div class="bg-primary-50 p-4 rounded-xl border-l-4 border-primary-600 text-xs text-primary-900">
    <strong>Tips Nalar Kritis Verisight:</strong> [Saran edukasi literasi spesifik]
</div>"""

    # 5. EKSEKUSI AI
    try:
        config = types.GenerateContentConfig(
            temperature=0.1,
        )

        contents_to_send = []
        if gambar_diproses:
            contents_to_send.extend([gambar_diproses, prompt])
        else:
            contents_to_send.append(prompt)

        response = client.models.generate_content(
            model='gemma-4-26b-a4b-it',
            contents=contents_to_send,
            config=config
        )

        proses_berpikir = ""
        hasil_bersih = ""

        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'thought') and part.thought == True:
                    proses_berpikir += part.text + "\n"
                else:
                    hasil_bersih += part.text + "\n"

        if not proses_berpikir:
            match = re.search(r'<think>(.*?)</think>', hasil_bersih, flags=re.DOTALL | re.IGNORECASE)
            if match:
                proses_berpikir = match.group(1).strip()
                hasil_bersih = re.sub(r'<think>.*?</think>', '', hasil_bersih, flags=re.DOTALL | re.IGNORECASE).strip()
            else:
                proses_berpikir = "AI memproses data secara instan."

        hasil_bersih = hasil_bersih.replace('```html', '').replace('```', '').strip()
        hasil_bersih = perbaiki_tautan_html(hasil_bersih)

        return jsonify({
            "result": hasil_bersih,
            "thinking": proses_berpikir.strip()
        })
        
    except Exception as e:
        return jsonify({"error": f"Kesalahan AI: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)