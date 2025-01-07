import pg8000

DATABASE_URL = "postgresql://postgres:wrAeHQzqeeTpoDSauXvWyWnfOTxCqnYt@monorail.proxy.rlwy.net:47382/railway"

try:
    conn = pg8000.connect(DATABASE_URL)
    print("Veritabanı bağlantısı başarılı!")
    conn.close()
except Exception as e:
    print(f"Veritabanı bağlantı hatası: {e}")
