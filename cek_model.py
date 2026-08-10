import os
import google.generativeai as genai
from dotenv import load_dotenv

# Memuat API Key dari file .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print("Berhasil terhubung! Mencari model teks yang tersedia untuk akunmu...\n")

# Mengambil daftar semua model dan menampilkannya
try:
    for m in genai.list_models():
        # Kita hanya mencari model yang bisa menghasilkan teks (generateContent)
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
            
    print("\nSelesai! Silakan pilih salah satu nama model di atas (misalnya: models/gemini-1.5-flash) untuk dimasukkan ke app.py")
except Exception as e:
    print(f"Terjadi kesalahan saat mengecek model: {e}")