import os
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image

# 1. Memuat konfigurasi API Key
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 2. Membuat gambar dummy 1x1 piksel warna hitam di memori
gambar_dummy = Image.new('RGB', (1, 1), color='black')

print("Memulai pencarian model AI yang bisa membaca gambar (Multimodal)...")
print("Skrip ini akan menguji setiap model. Harap tunggu...\n")

try:
    # Mengambil daftar model
    models = genai.list_models()
    
    for m in models:
        if 'generateContent' in m.supported_generation_methods:
            model_name = m.name.replace('models/', '')
            print(f"[*] Mengetes model: {model_name} ...", end=" ")
            
            try:
                # Mencoba mengirim teks DAN gambar secara bersamaan
                test_model = genai.GenerativeModel(model_name)
                response = test_model.generate_content(["Jawab dengan kata 'Ya' saja.", gambar_dummy])
                
                print(f"BERHASIL! ✅")
                print(f"\n=======================================================")
                print(f"SELESAI! Gunakan nama model ini untuk fitur gambar di app.py:")
                print(f"model_gambar = genai.GenerativeModel('{model_name}')")
                print(f"=======================================================\n")
                break # Berhenti mencari setelah menemukan yang berhasil
                
            except Exception as e:
                # Jika gagal (biasanya karena model hanya mendukung teks), lanjut ke berikutnya
                print(f"Gagal (Bukan model gambar) ❌")
                
except Exception as e:
    print(f"Terjadi kesalahan utama: {e}")