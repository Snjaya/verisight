import os
import requests
import datetime
import re
import io # Modul bawaan untuk menangani input/output data
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai
from duckduckgo_search import DDGS
from PIL import Image # Modul baru untuk membaca gambar

# 1. MEMUAT KONFIGURASI DAN AI
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Menyiapkan dua model: satu untuk teks, satu untuk gambar (multimodal)
model_teks = genai.GenerativeModel('gemma-4-26b-a4b-it')
model_gambar = genai.GenerativeModel('gemma-4-26b-a4b-it')

app = Flask(__name__)

def ambil_teks_dari_link(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
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
        if not hasil_ddg: return "Tidak ditemukan referensi langsung di internet."
        
        hasil_pencarian_teks = ""
        for i, hasil in enumerate(hasil_ddg):
            hasil_pencarian_teks += f"Referensi {i+1}:\n- Judul: {hasil['title']}\n- Link: {hasil['href']}\n- Ringkasan: {hasil['body']}\n\n"
        return hasil_pencarian_teks
    except:
        return "Gagal mengambil data dari mesin pencari."

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_text():
    # Karena kita menerima FormData, cara mengambil datanya berubah menggunakan request.form dan request.files
    input_pengguna = request.form.get('text', '').strip()
    file_gambar = request.files.get('image')

    if not input_pengguna and not file_gambar:
        return jsonify({"error": "Teks, link, atau gambar tidak boleh kosong"}), 400

    teks_untuk_dianalisis = input_pengguna
    referensi_internet = "Menganalisis data dari gambar atau tautan langsung."
    gambar_diproses = None

    # 1. CEK JIKA ADA GAMBAR YANG DIUNGGAH
    if file_gambar and file_gambar.filename != '':
        try:
            # Membaca file gambar ke dalam memori
            image_bytes = file_gambar.read()
            gambar_diproses = Image.open(io.BytesIO(image_bytes))
            teks_untuk_dianalisis = input_pengguna if input_pengguna else "Tolong analisis gambar ini, baca teks di dalamnya, dan periksa fakta dari informasi tersebut."
        except Exception as e:
            return jsonify({"error": "Format gambar tidak didukung atau rusak."}), 400

    # 2. JIKA TIDAK ADA GAMBAR, CEK LINK ATAU TEKS BIASA
    elif input_pengguna.startswith('http://') or input_pengguna.startswith('https://'):
        hasil_scraping = ambil_teks_dari_link(input_pengguna)
        if hasil_scraping == "ERROR_LINK":
            return jsonify({"error": "Gagal membaca isi link."}), 400
        teks_untuk_dianalisis = hasil_scraping
    else:
        referensi_internet = cari_referensi_internet(input_pengguna)

    waktu_sekarang = datetime.datetime.now().strftime("%d %B %Y")

    prompt = f"""
    Kamu adalah asisten literasi digital di aplikasi Verisight. 
    Tugasmu mengajari pengguna cara berpikir kritis dalam memverifikasi informasi.

    [KONTEKS WAKTU PENTING]: 
    Saat ini adalah tanggal {waktu_sekarang}.
    
    [REFERENSI DARI INTERNET]:
    {referensi_internet}
    
    Analisis data berikut ini:
    "{teks_untuk_dianalisis}"
    
    ATURAN:
    Berikan hasil akhir menggunakan format HTML di bawah ini.
    
    <p class="mb-4">Halo! Saya asisten literasi digital Anda dari <strong>Verisight</strong>. Mari kita bedah informasi tersebut bersama-sama:</p>
    
    <ul class="list-disc pl-5 space-y-3 mb-6">
        <li><strong>Inti Informasi:</strong> <br> [Jelaskan singkat isinya]</li>
        <li><strong>Sumber:</strong> <br> [Sebutkan sumbernya berdasarkan teks ATAU Referensi Internet]</li>
        <li><strong>Tingkat Kredibilitas:</strong> <br> <span class="font-bold text-blue-600">[Tinggi / Sedang / Rendah]</span></li>
        <li><strong>Analisis Kritis:</strong> <br> [Jelaskan mengapa ini mencurigakan atau patut dipercaya.]</li>
    </ul>

    <div class="bg-blue-100 p-4 rounded-lg border-l-4 border-blue-500">
        <strong>💡 Tips Verisight:</strong> [Tips menghindari hoaks terkait topik ini]
    </div>
    """

    try:
        # LOGIKA PEMILIHAN MODEL
        if gambar_diproses:
            # Jika ada gambar, gunakan model flash dan kirim teks + gambar
            response = model_gambar.generate_content([prompt, gambar_diproses])
        else:
            # Jika hanya teks, gunakan model gemma
            response = model_teks.generate_content(prompt)
            
        hasil_mentah = response.text
        
        # Memisahkan thinking process
        thinking_match = re.search(r'<think>(.*?)</think>', hasil_mentah, flags=re.DOTALL)
        proses_berpikir = thinking_match.group(1).strip() if thinking_match else "Analisis langsung diproses oleh model penglihatan (vision) atau tanpa catatan internal."
        
        hasil_bersih = re.sub(r'<think>.*?</think>', '', hasil_mentah, flags=re.DOTALL)
        
        if '<p' in hasil_bersih:
            hasil_bersih = hasil_bersih[hasil_bersih.find('<p'):]

        return jsonify({
            "result": hasil_bersih.strip(),
            "thinking": proses_berpikir
        })
        
    except Exception as e:
        return jsonify({"error": f"Kesalahan AI: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)