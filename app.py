import os
import requests
import datetime
import re
import io
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
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

def perbaiki_warna_status_badge(html_text):
    """Memastikan warna badge status verifikasi sesuai dengan standar visual:
    - Fakta Valid -> Emerald Green (bg-emerald-100 text-emerald-800)
    - Disinformasi / Hoaks -> Rose Red (bg-rose-100 text-rose-800)
    - Menyesatkan -> Amber Yellow (bg-amber-100 text-amber-800)
    - Perlu Verifikasi -> Blue (bg-blue-100 text-blue-800)
    """
    # Fakta Valid -> Emerald Green
    html_text = re.sub(
        r'class="[^"]*bg-amber-100[^"]*"(>\s*Fakta Valid)',
        r'class="px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800"\1',
        html_text,
        flags=re.IGNORECASE
    )
    # Disinformasi / Hoaks -> Rose Red
    html_text = re.sub(
        r'class="[^"]*bg-amber-100[^"]*"(>\s*Disinformasi[^\<]*)',
        r'class="px-3 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800"\1',
        html_text,
        flags=re.IGNORECASE
    )
    # Perlu Verifikasi -> Blue
    html_text = re.sub(
        r'class="[^"]*bg-amber-100[^"]*"(>\s*Perlu Verifikasi)',
        r'class="px-3 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-800"\1',
        html_text,
        flags=re.IGNORECASE
    )
    return html_text

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
        respons = requests.get(url, headers=headers, timeout=5, verify=False)
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

def _fetch_gnews(query):
    referensi = []
    try:
        url_gnews = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=id&gl=ID&ceid=ID:id"
        r = requests.get(url_gnews, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}, timeout=4)
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            items = root.findall('.//item')
            for item in items[:6]:
                title = item.find('title').text if item.find('title') is not None else ''
                link = item.find('link').text if item.find('link') is not None else ''
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ''
                if link:
                    sumber = title.split(' - ')[-1] if ' - ' in title else 'Media Berita'
                    referensi.append({
                        'title': title,
                        'href': link,
                        'body': f"Berita resmi dari {sumber}. Dipublikasikan pada {pub_date}."
                    })
    except Exception as e:
        print(f"Google News RSS error: {e}")
    return referensi

def _fetch_ddg(query):
    referensi = []
    try:
        ddgs = DDGS()
        hasil_ddg = list(ddgs.text(query, max_results=5))
        for hasil in hasil_ddg:
            href = hasil.get('href', '')
            title = hasil.get('title', 'Sumber Berita')
            body = hasil.get('body', '')
            if href:
                referensi.append({
                    'title': title,
                    'href': href,
                    'body': body
                })
    except Exception as e:
        print(f"DuckDuckGo error: {e}")
    return referensi

def cari_referensi_internet(teks_input):
    hasil_referensi = []
    links_seen = set()
    query = extract_search_keywords(teks_input)
    
    # PERCEPATAN EKSEKUSI: PANGGIL GOOGLE NEWS & DUCKDUCKGO PARALEL MENGGUNAKAN THREADPOOLEXECUTOR
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_gnews = executor.submit(_fetch_gnews, query)
        future_ddg = executor.submit(_fetch_ddg, query)
        
        gnews_res = future_gnews.result()
        ddg_res = future_ddg.result()

    for item in gnews_res + ddg_res:
        if item['href'] and item['href'] not in links_seen:
            links_seen.add(item['href'])
            hasil_referensi.append(item)

    # FALLBACK BROADER QUERY jika tidak ada hasil
    if not hasil_referensi:
        words = [w for w in re.sub(r'[^\w\s]', ' ', teks_input).split() if len(w) > 3]
        query_broad = " ".join(words[:3]) if words else teks_input[:30]
        gnews_broad = _fetch_gnews(query_broad)
        for item in gnews_broad:
            if item['href'] and item['href'] not in links_seen:
                links_seen.add(item['href'])
                hasil_referensi.append(item)

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
    # Mengambil data berdasarkan input pengguna (text, url, atau image)
    input_teks = request.form.get('text', '').strip()
    input_url = request.form.get('url', '').strip()
    file_gambar = request.files.get('image')

    # Fallback: jika input_teks adalah URL
    if not input_url and input_teks and (input_teks.startswith('http://') or input_teks.startswith('https://') or input_teks.startswith('www.')):
        input_url = input_teks
        input_teks = ""

    if not input_teks and not input_url and not file_gambar:
        return jsonify({"error": "Input tidak boleh kosong"}), 400

    teks_untuk_dianalisis = ""
    referensi_internet = "Menganalisis data dari gambar atau tautan langsung."
    gambar_diproses = None

    pola_url = re.compile(r'^(https?://|www\.)[^\s/$.?#].[^\s]*$', re.IGNORECASE)

    # A. TAB GAMBAR / SCREENSHOT (VISION AI)
    if file_gambar and file_gambar.filename != '':
        try:
            image_bytes = file_gambar.read()
            gambar_diproses = Image.open(io.BytesIO(image_bytes))
            teks_untuk_dianalisis = input_teks if input_teks else "Tolong analisis gambar ini, baca teks di dalamnya, dan periksa fakta dari informasi tersebut."
            if input_teks:
                referensi_internet = cari_referensi_internet(input_teks)
            else:
                referensi_internet = "Menganalisis data dari gambar langsung menggunakan Vision AI."
        except Exception as e:
            return jsonify({"error": "Format gambar tidak didukung."}), 400

    # B. TAB URL / LINK MODE
    elif input_url:
        if not pola_url.match(input_url) and not input_url.startswith('http'):
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

        url_target = input_url
        if not url_target.startswith('http'):
            url_target = 'https://' + url_target
            
        judul_halaman, hasil_scraping = ambil_teks_dari_link(url_target)
        
        if hasil_scraping != "ERROR_LINK" and len(hasil_scraping) > 50:
            teks_untuk_dianalisis = f"URL Tautan Artikel Pengguna: {url_target}\n" + (f"Judul Artikel: {judul_halaman}\n" if judul_halaman else "") + f"Isi Teks Artikel:\n{hasil_scraping}"
            query_search = judul_halaman if judul_halaman else hasil_scraping[:200]
        else:
            url_keywords = extract_keywords_from_url(url_target)
            teks_untuk_dianalisis = f"URL Tautan Pengguna: {url_target}\nTopik Artikel (dikategori dari Tautan): {url_keywords}"
            query_search = url_keywords if url_keywords else url_target

        referensi_terkait = cari_referensi_internet(query_search)
        referensi_utama = f"Referensi Utama (Tautan Pengguna):\n- Judul: {judul_halaman if (judul_halaman and hasil_scraping != 'ERROR_LINK') else 'Artikel Tautan Pengguna'}\n- Link: {url_target}\n- Ringkasan: Halaman artikel berita spesifik yang dikirim oleh pengguna.\n\n"
        referensi_internet = referensi_utama + referensi_terkait

    # C. TAB TEKS BIASA / TEXT STATEMENT MODE
    elif input_teks:
        teks_untuk_dianalisis = input_teks
        referensi_internet = cari_referensi_internet(input_teks)

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

    prompt = f"""Tugasmu adalah mengevaluasi klaim/informasi pengguna.

[ACUAN WAKTU SEKARANG / UNIVERSAL TEMPORAL ANCHOR WAJIB]
- HARI INI / WAKTU SEKARANG ADALAH: {waktu_sekarang_universal} (Tahun {now.year}).
- PENTING: Pahami dan adaptasi berbagai format tanggal secara universal dalam bahasa apa pun (Bahasa Indonesia, English, format ISO: {waktu_iso}, dsb.) sebagai MASA KINI (PRESENT TIME / WAKTU SEKARANG).
- Setiap kejadian atau klaim bertanggal {now.year} atau sebelum/sama dengan {waktu_iso} ADALAH MASA KINI ATAU MASA LALU (PRESENT/PAST), BUKAN MASA DEPAN.
- JANGAN PERNAH menyimpulkan bahwa tanggal dalam format apapun (misal: "{waktu_en}", "{waktu_id}", "{waktu_iso}") yang sesuai dengan waktu sekarang adalah "masa depan" atau menganggap klaim sebagai hoaks/disinformasi hanya karena bertanggal hari ini/tahun {now.year}.

[ATURAN PENJAGA GERBANG / GATEKEEPER INPUT TRIVIAL]
Pertama, evaluasi apakah "Klaim" di atas benar-benar sebuah klaim, berita, atau informasi yang masuk akal untuk diverifikasi faktanya.
JIKA input HANYA berupa teks acak/asal-asalan (contoh: "asdfgh", "qwerty", "sasasasa"), kata sapaan/uji coba tanpa konteks (contoh: "halo", "hai", "hello", "tes", "test", "hahaha"), MAKA BERHENTI dan HANYA keluarkan kode HTML ini tanpa markdown ```html:

<div class="bg-rose-50 p-6 rounded-xl border border-rose-200 text-center mb-6">
    <div class="w-12 h-12 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center mx-auto mb-3">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
    </div>
    <h4 class="font-bold text-rose-900 text-lg mb-2">Input Tidak Valid</h4>
    <p class="text-rose-700 text-sm">Teks yang Anda masukkan tidak terdeteksi sebagai klaim atau informasi berita yang dapat diverifikasi faktanya. Mohon masukkan klaim atau berita yang spesifik.</p>
</div>

[PETUNJUK ANALISIS SUNGGUH-SUNGGUH & PENCARIAN MANDIRI]
- Jangan langsung menyimpulkan klaim "Rendah" atau "Tidak Ada Referensi" secara terburu-buru. Analisis subjek utama, lokasi, dan latar belakang klaim secara mendalam.
- Gunakan data [Referensi Web] secara optimal untuk memverifikasi kebenaran klaim, atau untuk memberikan informasi relevan terkini tentang topik tersebut.

[ATURAN WAJIB REFERENSI URL & LINK ASLI]
1. Pada bagian HTML `Referensi Berita & Kanal Cek Fakta Resmi`, kamu WAJIB menyalin URL HTTPS artikel berita spesifik dan lengkap (`Link`) dari data [Referensi Web] di bawah ke dalam tag `<a href="URL_ASLI" target="_blank" rel="noopener noreferrer" class="font-semibold underline hover:text-primary-900">Judul Artikel Asli</a>`.
2. DILARANG KERAS mencantumkan link ke Halaman Utama / Domain Utama media berita umum saja (seperti `https://kompas.com`, `https://detik.com`, `https://news.kompas.com`, `https://antara.id`). Kamu HARUS menggunakan URL artikel berita spesifik dan lengkap dari data Referensi Web!
3. Tampilkan 2 hingga 4 tautan referensi berita/sumber artikel spesifik dari data Referensi Web (termasuk artikel tautan utama pengguna dan berita pembanding/berita terkait dari media lain).

[ATURAN WARNA STYLING STATUS VERIFIKASI WAJIB]
Gunakan kelas Tailwind CSS yang tepat untuk span Status Verifikasi:
- Jika "Fakta Valid": Gunakan `<span class="px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">Fakta Valid</span>` (HIJAU / EMERALD)
- Jika "Disinformasi" / "Disinformasi / Hoaks": Gunakan `<span class="px-3 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800">Disinformasi / Hoaks</span>` (MERAH / ROSE)
- Jika "Menyesatkan": Gunakan `<span class="px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800">Menyesatkan</span>` (KUNING / AMBER)
- Jika "Perlu Verifikasi": Gunakan `<span class="px-3 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-800">Perlu Verifikasi</span>` (BIRU / BLUE)

[DATA]
Waktu Acuan Hari Ini: {waktu_sekarang_universal}
Referensi Web: {referensi_internet}
Klaim / Artikel Pengguna: "{teks_untuk_dianalisis}"

[ATURAN WAJIB OUTPUT JIKA INPUT VALID]
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
            <span class="px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">[PILIH WARNA STATUS KELAS TAILWIND:
            - Fakta Valid: bg-emerald-100 text-emerald-800
            - Disinformasi: bg-rose-100 text-rose-800
            - Menyesatkan: bg-amber-100 text-amber-800
            - Perlu Verifikasi: bg-blue-100 text-blue-800]</span>
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
        hasil_bersih = perbaiki_warna_status_badge(hasil_bersih)

        return jsonify({
            "result": hasil_bersih,
            "thinking": ""  # AI Reasoning Trace disembunyikan sementara sesuai permintaan
        })
        
    except Exception as e:
        return jsonify({"error": f"Kesalahan AI: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)