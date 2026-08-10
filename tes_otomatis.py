import os
import google.generativeai as genai
from dotenv import load_dotenv

# 1. Memuat API Key dari file .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print("Memulai pencarian model AI yang aktif untuk akunmu...")
print("Skrip ini akan mencoba mengirim pesan 'Halo' ke setiap model.\n")

# 2. Mengambil daftar semua model yang ada
try:
    models = genai.list_models()
    
    # 3. Melakukan perulangan untuk mengetes setiap model satu per satu
    for m in models:
        # Kita hanya mengetes model yang dirancang untuk menghasilkan teks
        if 'generateContent' in m.supported_generation_methods:
            # Menghilangkan teks "models/" di depannya agar rapi
            model_name = m.name.replace('models/', '')
            print(f"[*] Mencoba model: {model_name} ...", end=" ")
            
            try:
                # Mencoba mengirim pesan singkat ke model ini
                test_model = genai.GenerativeModel(model_name)
                response = test_model.generate_content("Halo")
                
                # Jika berhasil sampai ke baris ini, berarti modelnya aktif!
                print(f"BERHASIL! ✅")
                print(f"\n=======================================================")
                print(f"SELESAI! Silakan gunakan nama ini di file app.py kamu:")
                print(f"model = genai.GenerativeModel('{model_name}')")
                print(f"=======================================================\n")
                break # Menghentikan pencarian karena kita sudah menemukan yang berhasil
                
            except Exception as e:
                # Jika gagal/error, tampilkan pesan gagal dan lanjut ke model berikutnya
                print(f"Gagal ❌")
                
except Exception as e:
    print(f"Terjadi kesalahan utama: {e}")