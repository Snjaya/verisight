import os
import requests
import datetime
import re
import io
import urllib.parse
import xml.etree.ElementTree as ET
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

def extract_keywords_from_url(url):
    try:
        path = urllib.parse.urlparse(url).path
        slug = re.sub(r'[/_\-\d]', ' ', path)
        words = [w for w in slug.split() if len(w) > 2 and w.lower() not in {'read', 'tren', 'news', 'berita', 'article', 'html', 'php', 'index'}]
        return " ".join(words[:8])
    except:
        return ""

def ambil_teks_dari_link(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        respons = requests.get(url, headers=headers, timeout=10, verify=False)
        if respons.status_code == 200:
            soup = BeautifulSoup(respons.text, 'html.parser')
            judul = soup.title.string.strip() if soup.title and soup.title.string else ""
            paragraphs = [p.get_text().strip() for p in soup.find_all('p') if len(p.get_text().strip()) > 30]
            if paragraphs:
                teks = " ".join(paragraphs)[:3000]
            else:
                teks = soup.get_text(separator=' ', strip=True)[:3000]
            return judul, teks
        return None, "ERROR_LINK"
    except:
        return None, "ERROR_LINK"

def extract_search_keywords(teks_input):
    stopwords = {
        'di', 'pada', 'yang', 'saat', 'melintas', 'dini', 'hari', 'dan', 'ke', 'dari', 
        'ini', 'itu', 'terjadi', 'dalam', 'dengan', 'untuk', 'atau', 'oleh', 'karena', 
        'akan', 'telah', 'ada', 'bisa', 'juga', 'sudah', 'merupakan', 'adalah', 'rabu', 
        'kamis', 'senin', 'selasa', 'jumat', 'sabtu', 'minggu', 'januari', 'februari', 
        'maret', 'april', 'mei', 'juni', 'juli', 'agustus', 'september', 'oktober', 
        'november', 'desember', 'tolong', 'analisis', 'periksa', 'fakta', 'kompas', 
        'detik', 'antara', 'berita', 'terbaru', 'baca', 'halaman'
    }
    clean_text = re.sub(r'[^\w\s]', ' ', teks_input)
    words = clean_text.split()
    filtered = [w for w in words if w.lower() not in stopwords]
    if len(filtered) >= 3:
        return " ".join(filtered[:8])
    return " ".join(words[:8]) if words else teks_input[:60]

def cari_referensi_internet(teks_input):
    hasil_referensi = []
    links_seen = set()
    
    query = extract_search_keywords(teks_input)
    
    # 1. UTAMA: GOOGLE NEWS RSS (Super cepat, kebal blokir ISP Indonesia, media nasional & lokal)
    try:
        url_gnews = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=id&gl=ID&ceid=ID:id"
        r = requests.get(url_gnews, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}, timeout=6)
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            items = root.findall('.//item')
            for item in items[:6]:
                title = item.find('title').text if item.find('title') is not None else ''
                link = item.find('link').text if item.find('link') is not None else ''
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ''
                if link and link not in links_seen:
                    links_seen.add(link)
                    sumber = title.split(' - ')[-1] if ' - ' in title else 'Media Berita'
                    hasil_referensi.append({
                        'title': title,
                        'href': link,
                        'body': f"Berita resmi dari {sumber}. Dipublikasikan pada {pub_date}."
                    })
    except Exception as e:
        print(f"Google News RSS error: {e}")

    # 2. SEKUNDER: DUCKDUCKGO (Handling SSL/DNS Exception jika diblokir ISP)
    try:
        ddgs = DDGS()
        hasil_ddg = list(ddgs.text(query, max_results=5))
        for hasil in hasil_ddg:
            href = hasil.get('href', '')
            title = hasil.get('title', 'Sumber Berita')
            body = hasil.get('body', '')
            if href and href not in links_seen:
                links_seen.add(href)
                hasil_referensi.append({
                    'title': title,
                    'href': href,
                    'body': body
                })
    except Exception as e:
        print(f"DuckDuckGo error: {e}")

    # 3. FALLBACK BROADER QUERY (3 kata entitas kunci utama)
    if not hasil_referensi:
        try:
            words = [w for w in re.sub(r'[^\w\s]', ' ', teks_input).split() if len(w) > 3]
            query_broad = " ".join(words[:3]) if words else teks_input[:30]
            url_broad = f"https://news.google.com/rss/search?q={urllib.parse.quote(query_broad)}&hl=id&gl=ID&ceid=ID:id"
            r = requests.get(url_broad, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}, timeout=6)
            if r.status_code == 200:
                root = ET.fromstring(r.text)
                items = root.findall('.//item')
                for item in items[:5]:
                    title = item.find('title').text if item.find('title') is not None else ''
                    link = item.find('link').text if item.find('link') is not None else ''
                    pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ''
                    if link and link not in links_seen:
                        links_seen.add(link)
                        sumber = title.split(' - ')[-1] if ' - ' in title else 'Media Berita'
                        hasil_referensi.append({
                            'title': title,
                            'href': link,
                            'body': f"Laporan berita terkait topik {query_broad} dari {sumber}. Dipublikasikan: {pub_date}"
                        })
        except Exception as e:
            print(f"Broad search error: {e}")

    if not hasil_referensi:
        return "Tidak ditemukan referensi langsung di internet."

    hasil_pencarian_teks = ""
    for i, ref in enumerate(hasil_referensi[:6]):
        hasil_pencarian_teks += f"Referensi {i+1}:\n- Judul: {ref['title']}\n- Link: {ref['href']}\n- Ringkasan: {ref['body']}\n\n"
    
    return hasil_pencarian_teks

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
            if input_pengguna:
                referensi_internet = cari_referensi_internet(input_pengguna)
            else:
                referensi_internet = "Menganalisis data dari gambar langsung."
        except Exception as e:
            return jsonify({"error": "Format gambar tidak didukung atau rusak."}), 400

    elif input_pengguna.startswith('http://') or input_pengguna.startswith('https://'):
        judul_halaman, hasil_scraping = ambil_teks_dari_link(input_pengguna)
        
        if hasil_scraping != "ERROR_LINK" and len(hasil_scraping) > 50:
            teks_untuk_dianalisis = f"URL Tautan Artikel Pengguna: {input_pengguna}\n" + (f"Judul Artikel: {judul_halaman}\n" if judul_halaman else "") + f"Isi Teks Artikel:\n{hasil_scraping}"
            query_search = judul_halaman if judul_halaman else hasil_scraping[:200]
        else:
            url_keywords = extract_keywords_from_url(input_pengguna)
            teks_untuk_dianalisis = f"URL Tautan Pengguna: {input_pengguna}\nTopik Artikel (dikategori dari Tautan): {url_keywords}"
            query_search = url_keywords if url_keywords else input_pengguna

        # MULTI-ENGINE RELATED NEWS SEARCH FOR LINK MODE
        referensi_terkait = cari_referensi_internet(query_search)
        
        referensi_utama = f"Referensi Utama (Tautan Pengguna):\n- Judul: {judul_halaman if (judul_halaman and hasil_scraping != 'ERROR_LINK') else 'Artikel Tautan Pengguna'}\n- Link: {input_pengguna}\n- Ringkasan: Halaman artikel berita spesifik yang dikirim oleh pengguna.\n\n"
        referensi_internet = referensi_utama + referensi_terkait
    else:
        referensi_internet = cari_referensi_internet(input_pengguna)

    now = datetime.datetime.now()
    bulan_indo = {
        1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
        5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
        9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
    }
    waktu_iso = now.strftime("%Y-%m-%d")
    waktu_en = now.strftime("%d %B %Y")
    waktu_id = f"{now.day} {bulan_indo[now.month]} {now.year}"
    waktu_sekarang_universal = f"{waktu_id} / {waktu_en} (ISO: {waktu_iso})"

    # PROMPT DENGAN UNIVERSAL TEMPORAL ANCHOR & DEDICATED LINK INJECTION DIRECTIVES
    prompt = f"""Tugasmu HANYA mengevaluasi apakah klaim ini FAKTA VALID, DISINFORMASI / HOAKS, atau MENYESATKAN.

[ACUAN WAKTU SEKARANG / UNIVERSAL TEMPORAL ANCHOR WAJIB]
- HARI INI / WAKTU SEKARANG ADALAH: {waktu_sekarang_universal} (Tahun {now.year}).
- PENTING: Pahami dan adaptasi berbagai format tanggal secara universal dalam bahasa apa pun (Bahasa Indonesia, English, format ISO: {waktu_iso}, dsb.) sebagai MASA KINI (PRESENT TIME / WAKTU SEKARANG).
- Setiap kejadian atau klaim bertanggal {now.year} atau sebelum/sama dengan {waktu_iso} ADALAH MASA KINI ATAU MASA LALU (PRESENT/PAST), BUKAN MASA DEPAN.
- JANGAN PERNAH menyimpulkan bahwa tanggal dalam format apapun (misal: "{waktu_en}", "{waktu_id}", "{waktu_iso}") yang sesuai dengan waktu sekarang adalah "masa depan" atau menganggap klaim sebagai hoaks/disinformasi hanya karena bertanggal hari ini/tahun {now.year}.

[PETUNJUK ANALISIS SUNGGUH-SUNGGUH & PENCARIAN MANDIRI]
- Jangan langsung menyimpulkan klaim "Rendah" atau "Tidak Ada Referensi" secara terburu-buru. Analisis subjek utama, lokasi, dan latar belakang klaim secara mendalam.
- Gunakan data [Referensi Web] secara optimal untuk memverifikasi kebenaran klaim, atau untuk memberikan informasi relevan terkini tentang topik tersebut.

[ATURAN WAJIB REFERENSI URL & LINK ASLI]
1. Pada bagian HTML `Referensi Berita & Kanal Cek Fakta Resmi`, kamu WAJIB menyalin URL HTTPS artikel berita spesifik dan lengkap (`Link`) dari data [Referensi Web] ke dalam tag `<a href="URL_ASLI" target="_blank" rel="noopener noreferrer" class="font-semibold underline hover:text-primary-900">Judul Artikel Asli</a>`.
2. DILARANG KERAS mencantumkan link ke Halaman Utama / Domain Utama media berita umum saja (seperti `https://kompas.com`, `https://detik.com`, `https://news.kompas.com`, `https://antara.id`). Kamu HARUS menggunakan URL artikel spesifik dan lengkap!
3. Tampilkan 2 hingga 4 tautan referensi berita/sumber artikel spesifik dari data Referensi Web (termasuk artikel tautan utama pengguna dan berita pembanding/berita terkait dari media lain).

[DATA]
Waktu Acuan Hari Ini: {waktu_sekarang_universal}
Referensi Web: {referensi_internet}
Klaim / Artikel Pengguna: "{teks_untuk_dianalisis}"

[ATURAN WAJIB OUTPUT]
Berikan HANYA kode HTML di bawah ini yang sudah diisi dengan analisis nyatamu. JANGAN gunakan tag markdown ```html.

<p class="mb-4 text-slate-800 text-sm leading-relaxed">Halo! Saya asisten literasi digital Anda dari <strong>Verisight</strong>. Berikut adalah hasil penelusuran fakta terhadap klaim tersebut:</p>

<div class="space-y-4 mb-6">
    <div class="bg-white p-4 rounded-xl border border-slate-200">
        <h4 class="font-bold text-navy-900 text-sm mb-1">Ringkasan Klaim & Subjek Utama</h4>
        <p class="text-slate-600 text-xs leading-relaxed">[Jelaskan klaim utama dengan padat dan teliti]</p>
    </div>

    <div class="bg-white p-4 rounded-xl border border-slate-200">
        <h4 class="font-bold text-navy-900 text-sm mb-1">Status Verifikasi</h4>
        <div class="flex items-center gap-2 mt-1 mb-2">
            <span class="px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800">[Pilih: Fakta Valid / Disinformasi / Menyesatkan / Perlu Verifikasi]</span>
        </div>
        <p class="text-slate-600 text-xs leading-relaxed">[Alasan komprehensif penentuan status]</p>
    </div>

    <div class="bg-white p-4 rounded-xl border border-slate-200">
        <h4 class="font-bold text-navy-900 text-sm mb-1">Analisis Mendalam & Pembuktian Fakta</h4>
        <p class="text-slate-600 text-xs leading-relaxed mb-2">[Penjelasan mendalam, pembuktian fakta, dan konteks latar belakang topik]</p>
    </div>

    <div class="bg-blue-50/70 p-4 rounded-xl border border-blue-200">
        <h4 class="font-bold text-primary-900 text-sm mb-2">Referensi Berita & Kanal Cek Fakta Resmi</h4>
        <ul class="list-disc pl-5 space-y-1.5 text-xs text-primary-700">
            <li><a href="URL_ASLI_DARI_REFERENSI_WEB" target="_blank" rel="noopener noreferrer" class="font-semibold underline hover:text-primary-900">Judul Referensi Asli</a></li>
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