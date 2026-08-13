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
from google import genai
from google.genai import types
from duckduckgo_search import DDGS
from PIL import Image

# 1. MEMUAT KONFIGURASI
load_dotenv()
# CATATAN: Client AI tidak lagi diinisialisasi di sini. 
# Client akan dipanggil di dalam fungsi agar kompatibel dengan Vercel Serverless.

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
    """Memastikan warna badge status verifikasi sesuai dengan standar visual"""
    html_text = re.sub(
        r'class="[^"]*bg-amber-100[^"]*"(>\s*Fakta Valid)',
        r'class="px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800"\1',
        html_text,
        flags=re.IGNORECASE
    )
    html_text = re.sub(
        r'class="[^"]*bg-amber-100[^"]*"(>\s*Disinformasi[^\<]*)',
        r'class="px-3 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800"\1',
        html_text,
        flags=re.IGNORECASE
    )
    html_text = re.sub(
        r'class="[^"]*bg-amber-100[^"]*"(>\s*Perlu Verifikasi)',
        r'class="px-3 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-800"\1',
        html_text,
        flags=re.IGNORECASE
    )
    return html_text

def check_domain_security(url):
    social_domains = [
        'instagram.com', 'instagr.am', 'tiktok.com', 'vt.tiktok.com', 'vm.tiktok.com',
        'x.com', 'twitter.com', 'reddit.com', 'facebook.com', 'fb.watch',
        'youtube.com', 'youtu.be'
    ]
    try:
        domain = urllib.parse.urlparse(url).netloc.lower()
        if any(sd in domain for sd in social_domains):
            return True, 'SOCIAL_MEDIA'
        if domain and '.' in domain:
            return True, 'NEWS_OR_WEB'
        return False, 'INVALID'
    except:
        return False, 'INVALID'

def extract_keywords_from_url(url):
    try:
        path = urllib.parse.urlparse(url).path
        query = urllib.parse.urlparse(url).query
        raw_slug = path + ' ' + query
        raw_slug = re.sub(r'(comments|status|posts|videos|reels|reel|story\.php|fbid|photo\.php|watch|user|bisnis|amp|read|tren|news|berita|article|html|php|index)', ' ', raw_slug, flags=re.IGNORECASE)
        raw_slug = re.sub(r'[/_\-\d\?=&\.]', ' ', raw_slug)
        words = [w for w in raw_slug.split() if len(w) > 2 and w.lower() not in {
            'com', 'https', 'http', 'www', 'share', 'utm', 'source', 'medium', 'id', 'en'
        }]
        return " ".join(words[:8])
    except:
        return ""

def ambil_teks_dari_link(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    is_social_media = any(domain in url.lower() for domain in ['x.com', 'twitter.com', 'instagram.com', 'instagr.am', 'facebook.com', 'fb.watch', 'tiktok.com', 'reddit.com', 'youtube.com', 'youtu.be'])
    platform_name = "Media Sosial"
    if 'instagram.com' in url or 'instagr.am' in url: platform_name = "Instagram Reels/Video"
    elif 'tiktok.com' in url: platform_name = "TikTok Video"
    elif 'youtube.com' in url or 'youtu.be' in url: platform_name = "YouTube Video/Shorts"
    elif 'x.com' in url or 'twitter.com' in url: platform_name = "X (Twitter)"
    elif 'facebook.com' in url or 'fb.watch' in url: platform_name = "Facebook Video/Reels"
    elif 'reddit.com' in url: platform_name = "Reddit"

    try:
        respons = requests.get(url, headers=headers, timeout=5, verify=False)
        if respons.status_code == 200:
            soup = BeautifulSoup(respons.text, 'html.parser')
            
            og_title = soup.find('meta', attrs={'property': 'og:title'}) or soup.find('meta', attrs={'name': 'twitter:title'})
            og_desc = soup.find('meta', attrs={'property': 'og:description'}) or soup.find('meta', attrs={'name': 'twitter:description'}) or soup.find('meta', attrs={'name': 'description'})
            
            title_meta = og_title['content'].strip() if (og_title and 'content' in og_title.attrs) else ""
            desc_meta = og_desc['content'].strip() if (og_desc and 'content' in og_desc.attrs) else ""
            judul = soup.title.string.strip() if (soup.title and soup.title.string) else title_meta
            
            paragraphs = [p.get_text().strip() for p in soup.find_all('p') if len(p.get_text().strip()) > 30]
            body_teks = " ".join(paragraphs)[:3000] if paragraphs else soup.get_text(separator=' ', strip=True)[:3000]

            if is_social_media:
                slug_kw = extract_keywords_from_url(url)
                combined_social_text = f"[Konten {platform_name}]\nJudul / Meta Caption Video: {title_meta or judul}\nDeskripsi / Teks Unggahan: {desc_meta or body_teks[:1000]}\nKata Kunci Isu dari Slug: {slug_kw}"
                return judul or title_meta or f"Unggahan Video {platform_name}", combined_social_text
            
            return judul, body_teks
        return None, "ERROR_LINK"
    except Exception as e:
        print(f"Link scraping error: {e}")
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

def translate_to_english_keywords(text):
    dict_map = {
        'demo': 'protest', 'demonstrasi': 'protest', 'mahasiswa': 'student',
        'kebakaran': 'fire', 'terbakar': 'fire', 'karhutla': 'forest fire',
        'kabut': 'haze', 'asap': 'haze', 'pemilu': 'election', 'pilpres': 'election',
        'presiden': 'president', 'pemerintah': 'government', 'kebijakan': 'policy',
        'ekonomi': 'economic', 'korupsi': 'corruption', 'kecelakaan': 'accident',
        'kapal': 'ship ferry', 'polisi': 'police', 'banjir': 'flood', 'gempa': 'earthquake',
        'menteri': 'minister', 'rupiah': 'rupiah currency', 'ditutup': 'closed',
        'sekolah': 'school', 'korban': 'casualty', 'tewas': 'dead'
    }
    id_stopwords = {
        'terjadi', 'setiap', 'hari', 'di', 'pada', 'yang', 'saat', 'dini', 'dan', 'ke', 
        'dari', 'ini', 'itu', 'dalam', 'dengan', 'untuk', 'atau', 'oleh', 'karena', 
        'akan', 'telah', 'ada', 'bisa', 'juga', 'sudah', 'adalah', 'merupakan', 'tolong',
        'analisis', 'periksa', 'fakta'
    }
    
    clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
    words = clean_text.split()
    
    translated_words = []
    for w in words:
        if w in dict_map:
            translated_words.append(dict_map[w])
        elif w not in id_stopwords and len(w) > 2:
            translated_words.append(w)
            
    query_str = " ".join(translated_words[:7])
    if 'indonesia' not in query_str.lower() and 'jakarta' not in query_str.lower():
        query_str = f"Indonesia {query_str}"
    return query_str

def _fetch_gnews_id(query, exclude_url=None):
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
                if link and (not exclude_url or exclude_url not in link):
                    sumber = title.split(' - ')[-1] if ' - ' in title else 'Media Nasional'
                    referensi.append({
                        'title': title,
                        'href': link,
                        'body': f"[Kanal Berita Nasional] Dari {sumber}. Dipublikasikan: {pub_date}."
                    })
    except Exception as e:
        print(f"Google News RSS ID error: {e}")
    return referensi

def _fetch_gnews_int(query, exclude_url=None):
    referensi = []
    try:
        url_gnews = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-US&gl=US&ceid=US:en"
        r = requests.get(url_gnews, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}, timeout=4)
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            items = root.findall('.//item')
            for item in items[:6]:
                title = item.find('title').text if item.find('title') is not None else ''
                link = item.find('link').text if item.find('link') is not None else ''
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ''
                if link and (not exclude_url or exclude_url not in link):
                    sumber = title.split(' - ')[-1] if ' - ' in title else 'International Media'
                    referensi.append({
                        'title': title,
                        'href': link,
                        'body': f"[Kanal Berita Internasional / Global] Berita dari {sumber} (e.g. SCMP, BBC, CNN, Reuters, Al Jazeera, Japan Times). Dipublikasikan: {pub_date}."
                    })
    except Exception as e:
        print(f"Google News RSS International error: {e}")
    return referensi

def _fetch_ddg(query, exclude_url=None):
    referensi = []
    try:
        ddgs = DDGS()
        hasil_ddg = list(ddgs.text(query, max_results=5))
        for hasil in hasil_ddg:
            href = hasil.get('href', '')
            title = hasil.get('title', 'Sumber Berita')
            body = hasil.get('body', '')
            if href and (not exclude_url or exclude_url not in href):
                referensi.append({
                    'title': title,
                    'href': href,
                    'body': body
                })
    except Exception as e:
        print(f"DuckDuckGo error: {e}")
    return referensi

def cari_referensi_internet(teks_input, exclude_url=None):
    hasil_referensi = []
    links_seen = set()
    query_id = extract_search_keywords(teks_input)
    query_en = translate_to_english_keywords(teks_input)
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_gnews_id = executor.submit(_fetch_gnews_id, query_id, exclude_url)
        future_gnews_int = executor.submit(_fetch_gnews_int, query_en, exclude_url)
        future_ddg = executor.submit(_fetch_ddg, query_id, exclude_url)
        
        gnews_id_res = future_gnews_id.result()
        gnews_int_res = future_gnews_int.result()
        ddg_res = future_ddg.result()

    all_combined = []
    max_len = max(len(gnews_id_res), len(gnews_int_res), len(ddg_res))
    for i in range(max_len):
        if i < len(gnews_id_res):
            all_combined.append(gnews_id_res[i])
        if i < len(gnews_int_res):
            all_combined.append(gnews_int_res[i])
        if i < len(ddg_res):
            all_combined.append(ddg_res[i])

    for item in all_combined:
        if item['href'] and item['href'] not in links_seen and (not exclude_url or exclude_url not in item['href']):
            links_seen.add(item['href'])
            hasil_referensi.append(item)

    if not hasil_referensi:
        words = [w for w in re.sub(r'[^\w\s]', ' ', teks_input).split() if len(w) > 3]
        query_broad = " ".join(words[:3]) if words else teks_input[:30]
        gnews_broad = _fetch_gnews_id(query_broad, exclude_url)
        for item in gnews_broad:
            if item['href'] and item['href'] not in links_seen and (not exclude_url or exclude_url not in item['href']):
                links_seen.add(item['href'])
                hasil_referensi.append(item)

    if not hasil_referensi:
        return "Tidak ditemukan referensi berita eksternal langsung di internet."

    hasil_pencarian_teks = ""
    for i, ref in enumerate(hasil_referensi[:8]):
        hasil_pencarian_teks += f"Referensi {i+1}:\n- Judul: {ref['title']}\n- Link: {ref['href']}\n- Ringkasan: {ref['body']}\n\n"
    
    return hasil_pencarian_teks

# 3. RUTE HALAMAN UTAMA
@app.route('/')
def home():
    return render_template('index.html')

# 4. RUTE API UNTUK ANALISIS AI
@app.route('/api/analyze', methods=['POST'])
def analyze_text():
    
    # === PEMBARUAN PENTING UNTUK VERCEL ===
    # Inisialisasi client Gemini diletakkan secara dinamis di dalam fungsi request.
    # Ini menjamin Vercel membaca kunci rahasia secara real-time.
    api_key_server = os.environ.get("GEMINI_API_KEY")
    if not api_key_server:
        return jsonify({"error": "Sistem gagal menemukan Kunci API Gemini di pengaturan Vercel."}), 500
    
    client = genai.Client(api_key=api_key_server)
    # =======================================

    input_teks = request.form.get('text', '').strip()
    input_url = request.form.get('url', '').strip()
    file_gambar = request.files.get('image')

    if not input_url and input_teks and (input_teks.startswith('http://') or input_teks.startswith('https://') or input_teks.startswith('www.')):
        input_url = input_teks
        input_teks = ""

    if not input_teks and not input_url and not file_gambar:
        return jsonify({"error": "Input tidak boleh kosong"}), 400

    teks_untuk_dianalisis = ""
    referensi_internet = "Menganalisis data dari gambar atau tautan langsung."
    gambar_diproses = None

    pola_url = re.compile(r'^(https?://|www\.)[^\s/$.?#].[^\s]*$', re.IGNORECASE)

    # A. TAB GAMBAR / SCREENSHOT
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
        url_target = input_url
        if not url_target.startswith('http'):
            url_target = 'https://' + url_target

        is_valid_url, url_type = check_domain_security(url_target)
        
        if not is_valid_url or not pola_url.match(url_target):
            html_bukan_link = """
            <div class="bg-rose-50 p-6 rounded-xl border border-rose-200 text-center mb-6">
                <div class="w-12 h-12 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center mx-auto mb-3">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                </div>
                <h4 class="font-bold text-rose-900 text-lg mb-2">Input Tidak Valid</h4>
                <p class="text-rose-700 text-sm">Tautan yang Anda masukkan bukan merupakan platform media sosial resmi (Instagram, TikTok, X, Reddit, Facebook, YouTube) atau portal berita resmi yang dapat diverifikasi faktanya.</p>
            </div>
            """
            return jsonify({"result": html_bukan_link, "thinking": "Input ditolak oleh sistem penjaga keamanan domain. Format atau domain tidak dikenal."})

        judul_halaman, hasil_scraping = ambil_teks_dari_link(url_target)
        slug_kw = extract_keywords_from_url(url_target)

        if url_type == 'SOCIAL_MEDIA':
            platform_name = "Media Sosial (Instagram Reels / TikTok / X / Reddit / Facebook / YouTube)"
            if 'instagram.com' in url_target or 'instagr.am' in url_target: platform_name = "Instagram Reels Video"
            elif 'tiktok.com' in url_target: platform_name = "TikTok Video"
            elif 'youtube.com' in url_target or 'youtu.be' in url_target: platform_name = "YouTube Video / Shorts"
            elif 'x.com' in url_target or 'twitter.com' in url_target: platform_name = "X (Twitter) Video / Post"
            elif 'reddit.com' in url_target: platform_name = "Reddit Post / Video"
            elif 'facebook.com' in url_target or 'fb.watch' in url_target: platform_name = "Facebook Reels / Video"

            teks_untuk_dianalisis = f"URL Tautan {platform_name}: {url_target}\n"
            if judul_halaman and len(judul_halaman) > 5 and judul_halaman.lower() not in {'instagram', 'tiktok', 'youtube', 'reddit', 'facebook'}:
                teks_untuk_dianalisis += f"Judul / Meta Caption Video: {judul_halaman}\n"
            if hasil_scraping and hasil_scraping != "ERROR_LINK" and len(hasil_scraping) > 20:
                teks_untuk_dianalisis += f"Teks Meta Unggahan: {hasil_scraping}\n"
            if slug_kw:
                teks_untuk_dianalisis += f"Kata Kunci Isu dari Slug: {slug_kw}\n"
            if input_teks:
                teks_untuk_dianalisis += f"Catatan Teks Pengguna Mengenai Video: {input_teks}\n"

            teks_untuk_dianalisis += f"\nCatatan Penting: Tautan di atas ADALAH konten video pendek/Reels/unggahan media sosial dari {platform_name}. Analisis fakta atau klaim isu yang dibahas di balik video viral ini."

            if judul_halaman and len(judul_halaman) > 10 and judul_halaman.lower() not in {'instagram', 'tiktok', 'youtube', 'reddit', 'facebook'}:
                query_search = judul_halaman
            elif slug_kw and len(slug_kw) > 3:
                query_search = slug_kw
            elif input_teks:
                query_search = input_teks
            else:
                query_search = "berita viral video media sosial indonesia"

        else:
            if hasil_scraping != "ERROR_LINK" and len(hasil_scraping) > 30:
                teks_untuk_dianalisis = f"URL Tautan Artikel Pengguna: {url_target}\n" + (f"Judul Artikel: {judul_halaman}\n" if judul_halaman else "") + f"Isi Teks Artikel:\n{hasil_scraping}"
                query_search = judul_halaman if (judul_halaman and len(judul_halaman) > 10) else slug_kw
            else:
                teks_untuk_dianalisis = f"URL Tautan Pengguna: {url_target}\nTopik Isu (dikategori dari Slug): {slug_kw}"
                query_search = slug_kw if slug_kw else url_target

        referensi_internet = cari_referensi_internet(query_search, exclude_url=url_target)

    # C. TAB TEKS BIASA
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

[ATURAN PENJAGA GERBANG / GATEKEEPER INPUT TRIVIAL WAJIB]
1. Evaluasi apakah input pengguna benar-benar sebuah klaim, berita, atau informasi yang masuk akal untuk diverifikasi faktanya.
2. PERHATIAN KHUSUS UNTUK TAUTAN MEDIA SOSIAL & REELS/VIDEO: Jika input berupa Tautan URL Video/Reels/Unggahan Media Sosial (seperti Instagram Reels, TikTok, YouTube Shorts, X/Twitter, Facebook, Reddit), TAUTAN TERSEBUT ADALAH SANGAT VALID DAN HARUS DIANALISIS! DILARANG KERAS mengembalikan "Input Tidak Valid" untuk tautan video/Reels media sosial. Evaluasi fakta atau klaim di balik video viral tersebut berdasarkan data [Referensi Web].
3. JIKA input HANYA berupa teks acak/asal-asalan tanpa makna (contoh: "asdfgh", "qwerty", "sasasasa"), kata sapaan/uji coba tanpa konteks (contoh: "halo", "hai", "hello", "tes", "test", "hahaha"), MAKA BERHENTI dan HANYA keluarkan kode HTML Input Tidak Valid ini tanpa markdown ```html:

<div class="bg-rose-50 p-6 rounded-xl border border-rose-200 text-center mb-6">
    <div class="w-12 h-12 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center mx-auto mb-3">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
    </div>
    <h4 class="font-bold text-rose-900 text-lg mb-2">Input Tidak Valid</h4>
    <p class="text-rose-700 text-sm">Teks atau tautan yang Anda masukkan tidak terdeteksi sebagai klaim atau informasi berita yang dapat diverifikasi faktanya. Mohon masukkan klaim, berita, atau tautan yang spesifik.</p>
</div>

[PETUNJUK ANALISIS SUNGGUH-SUNGGUH & MULTI-PERSPEKTIF MEDIA NASIONAL DAN INTERNASIONAL]
- Jangan langsung menyimpulkan klaim "Rendah" atau "Tidak Ada Referensi" secara terburu-buru. Analisis subjek utama, lokasi, dan latar belakang klaim secara mendalam.
- Verisight menggunakan acuan dari **Kanal Berita Nasional** (Kompas, Detik, Antara, CNN Indonesia, Suara, dll.) DAN **Kanal Berita Internasional / Global** (seperti South China Morning Post, BBC, Reuters, Al Jazeera, CNN International, Japan Times, AP News, Bloomberg).
- Gunakan data [Referensi Web] secara optimal untuk menyajikan evaluasi independen yang bebas dari pembatasan atau sensor media lokal.

[ATURAN WAJIB REFERENSI URL & LINK ASLI]
1. Pada bagian HTML `Referensi Berita & Kanal Cek Fakta Resmi`, kamu WAJIB menyalin URL HTTPS artikel berita spesifik dan lengkap (`Link`) dari data [Referensi Web] di bawah ke dalam tag `<a href="URL_ASLI" target="_blank" rel="noopener noreferrer" class="font-semibold underline hover:text-primary-900">Judul Artikel Asli</a>`.
2. DILARANG KERAS mencantumkan link ke Halaman Utama / Domain Utama media berita umum saja (seperti `[https://kompas.com](https://kompas.com)`, `[https://detik.com](https://detik.com)`, `[https://news.kompas.com](https://news.kompas.com)`, `[https://antara.id](https://antara.id)`). Kamu HARUS menggunakan URL artikel berita spesifik dan lengkap dari data Referensi Web!
3. DILARANG KERAS memasukkan kembali tautan URL yang dikirim pengguna ke dalam daftar `Referensi Berita & Kanal Cek Fakta Resmi`. Tampilkan 2 hingga 4 tautan referensi berita/sumber artikel EKSTERNAL pembanding dari media massa resmi!

[ATURAN WARNA STYLING STATUS VERIFIKASI WAJIB]
Gunakan kelas Tailwind CSS yang tepat untuk span Status Verifikasi:
- Jika "Fakta Valid": Gunakan `<span class="px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">Fakta Valid</span>` (HIJAU / EMERALD)
- Jika "Disinformasi" / "Disinformasi / Hoaks": Gunakan `<span class="px-3 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800">Disinformasi / Hoaks</span>` (MERAH / ROSE)
- Jika "Menyesatkan": Gunakan `<span class="px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800">Menyesatkan</span>` (KUNING / AMBER)
- Jika "Perlu Verifikasi": Gunakan `<span class="px-3 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-800">Perlu Verifikasi</span>` (BIRU / BLUE)

[DATA]
Waktu Acuan Hari Ini: {waktu_sekarang_universal}
Referensi Web Eksternal Pembanding: {referensi_internet}
Klaim / Artikel / Unggahan Video Pengguna: "{teks_untuk_dianalisis}"

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
            <li><a href="URL_ASLI_DARI_REFERENSI_WEB" target="_blank" rel="noopener noreferrer" class="font-semibold underline hover:text-primary-900">Judul Referensi Asli (Sertakan Berita Eksternal Pembanding)</a></li>
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
            "thinking": "" 
        })
        
    except Exception as e:
        return jsonify({"error": f"Kesalahan AI: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)