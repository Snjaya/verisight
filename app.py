import os
import requests
import datetime
import re
import io
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
# IMPORT SDK TERBARU
from google import genai
from google.genai import types
from duckduckgo_search import DDGS
from PIL import Image

# 1. MEMUAT KONFIGURASI DAN CLIENT AI TERBARU
load_dotenv()
# Menggunakan Client baru dari google-genai
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)

# 2. FUNGSI PEMBANTU: WEB SCRAPING & UTILITIES
def perbaiki_tautan_html(html_text):
    """Memastikan seluruh atribut href pada tag <a> diawali dengan https://"""
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
    input_pengguna = request.form.get('text', '').strip()
    file_gambar = request.files.get('image')

    if not input_pengguna and not file_gambar:
        return jsonify({"error": "Teks, link, atau gambar tidak boleh kosong"}), 400

    teks_untuk_dianalisis = input_pengguna
    referensi_internet = "Menganalisis data dari gambar atau tautan langsung."
    gambar_diproses = None

    if file_gambar and file_gambar.filename != '':
        try:
            image_bytes = file_gambar.read()
            gambar_diproses = Image.open(io.BytesIO(image_bytes))
            teks_untuk_dianalisis = input_pengguna if input_pengguna else "Tolong analisis gambar ini, baca teks di dalamnya, dan periksa fakta dari informasi tersebut."
        except Exception as e:
            return jsonify({"error": "Format gambar tidak didukung atau rusak."}), 400

    elif input_pengguna.startswith('http://') or input_pengguna.startswith('https://'):
        hasil_scraping = ambil_teks_dari_link(input_pengguna)
        if hasil_scraping == "ERROR_LINK":
            return jsonify({"error": "Gagal membaca isi link. Pastikan link aktif."}), 400
        teks_untuk_dianalisis = hasil_scraping
    else:
        referensi_internet = cari_referensi_internet(input_pengguna)

    waktu_sekarang = datetime.datetime.now().strftime("%d %B %Y")

    # PROMPT SEDERHANA TANPA ATURAN PEMOTONGAN KARENA SDK AKAN MENGURUSNYA
    prompt = f"""Tugasmu HANYA mengevaluasi apakah klaim ini FAKTA VALID, DISINFORMASI / HOAKS, atau MENYESATKAN.

[DATA]
Waktu: {waktu_sekarang}
Referensi Web: {referensi_internet}
Klaim Pengguna: "{teks_untuk_dianalisis}"

[ATURAN WAJIB OUTPUT]
Berikan HANYA kode HTML di bawah ini yang sudah diisi dengan analisis nyatamu. JANGAN gunakan tag markdown ```html.

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

    # 5. EKSEKUSI AI MENGGUNAKAN SDK BARU
    try:
        # Konfigurasi di SDK baru
        config = types.GenerateContentConfig(
            temperature=0.1,
        )

        # Menyiapkan konten untuk dikirim
        contents_to_send = []
        if gambar_diproses:
            contents_to_send.extend([gambar_diproses, prompt])
        else:
            contents_to_send.append(prompt)

        # Memanggil API dengan struktur baru
        response = client.models.generate_content(
            model='gemma-4-26b-a4b-it',
            contents=contents_to_send,
            config=config
        )

        # 6. LOGIKA PEMISAHAN AJAIB DARI SDK (part.thought)
        proses_berpikir = ""
        hasil_bersih = ""

        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                # SDK memisahkan secara otomatis!
                if hasattr(part, 'thought') and part.thought == True:
                    proses_berpikir += part.text + "\n"
                else:
                    hasil_bersih += part.text + "\n"

        # Cadangan keamanan super ringan jika model tidak mengembalikan tag thought
        if not proses_berpikir:
            match = re.search(r'<think>(.*?)</think>', hasil_bersih, flags=re.DOTALL | re.IGNORECASE)
            if match:
                proses_berpikir = match.group(1).strip()
                hasil_bersih = re.sub(r'<think>.*?</think>', '', hasil_bersih, flags=re.DOTALL | re.IGNORECASE).strip()
            else:
                proses_berpikir = "AI memproses data secara instan."

        # Pembersihan akhir untuk memastikan HTML siap tampil
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