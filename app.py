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

# Menggunakan model yang sudah teruji aktif
model = genai.GenerativeModel('gemma-4-26b-a4b-it')

app = Flask(__name__)

# 2. FUNGSI PEMBANTU: WEB SCRAPING
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
    Kamu adalah asisten literasi digital di aplikasi Verisight. 
    Tugasmu mengajari pengguna cara berpikir kritis dalam memverifikasi informasi.

    [KONTEKS WAKTU PENTING]: 
    Saat ini adalah tanggal {waktu_sekarang}. Jadikan tanggal ini sebagai acuan realitas mutlakmu.
    
    Analisis klaim atau teks berikut ini:
    "{teks_untuk_dianalisis}"
    
    ATURAN:
    Berikan hasil akhir menggunakan format HTML di bawah ini.
    
    <p class="mb-4">Halo! Saya asisten literasi digital Anda dari <strong>Verisight</strong>. Mari kita bedah informasi tersebut bersama-sama:</p>
    
    <ul class="list-disc pl-5 space-y-3 mb-6">
        <li><strong>Inti Informasi:</strong> <br> [Jelaskan singkat isinya]</li>
        <li><strong>Sumber:</strong> <br> [Sebutkan sumbernya]</li>
        <li><strong>Tingkat Kredibilitas:</strong> <br> <span class="font-bold text-blue-600">[Tinggi / Sedang / Rendah]</span></li>
        <li><strong>Analisis Kritis:</strong> <br> [Jelaskan mengapa ini mencurigakan atau patut dipercaya berdasarkan logika]</li>
    </ul>

    <div class="bg-blue-100 p-4 rounded-lg border-l-4 border-blue-500">
        <strong>💡 Tips Verisight:</strong> [Tips menghindari hoaks terkait topik ini]
    </div>
    """

    try:
        response = model.generate_content(prompt)
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

        # 4. Mengirimkan KEDUA data tersebut ke halaman web
        return jsonify({
            "result": hasil_bersih,
            "thinking": proses_berpikir
        })
        
    except Exception as e:
        return jsonify({"error": f"Kesalahan AI: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)