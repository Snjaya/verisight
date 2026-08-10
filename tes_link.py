# Mengimpor library yang dibutuhkan
import requests
from bs4 import BeautifulSoup

def ambil_teks_dari_link(url):
    print(f"Mencoba membuka link: {url}")
    try:
        # Menambahkan 'User-Agent' agar web tidak mengira kita adalah bot spam
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # 1. Mengunduh halaman web
        respons = requests.get(url, headers=headers)
        
        # Jika berhasil dibuka (kode 200)
        if respons.status_code == 200:
            # 2. Mengurai kode HTML menggunakan BeautifulSoup
            soup = BeautifulSoup(respons.text, 'html.parser')
            
            # 3. Mengekstrak teksnya dan membuang kode HTML
            # soup.get_text() mengambil semua teks, separator=' ' memberi spasi antar paragraf
            teks_bersih = soup.get_text(separator=' ', strip=True)
            
            # Karena teks di web bisa sangat panjang, kita ambil misalnya 2000 karakter pertama saja
            # agar tidak kepanjangan saat dikirim ke AI
            return teks_bersih[:2000]
        else:
            return f"Gagal mengakses link. Kode error: {respons.status_code}"
            
    except Exception as e:
        return f"Terjadi kesalahan saat membuka link: {e}"

# --- Bagian untuk mencoba kodenya ---
if __name__ == "__main__":
    # Kamu bisa mengganti URL di bawah ini dengan link berita sungguhan!
    link_percobaan = "https://id.wikipedia.org/wiki/Literasi_digital"
    
    hasil_teks = ambil_teks_dari_link(link_percobaan)
    print("\n=== HASIL TEKS YANG DIAMBIL DARI LINK ===")
    print(hasil_teks)
    print("=========================================")