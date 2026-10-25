import pandas as pd
import psycopg2

# Masukkan DATABASE_URL Supabase milikmu di sini
URL_SUPABASE = "postgresql://postgres:ShelterKopi2026@db.eatbthzfktiplnugrewl.supabase.co:5432/postgres"

conn = psycopg2.connect(URL_SUPABASE)

print("\n=== 5 TRANSAKSI TERAKHIR ===")
df_trx = pd.read_sql("SELECT * FROM transaksi ORDER BY id DESC LIMIT 5", conn)
print(df_trx)

print("\n=== STOK MENU SAAT INI ===")
df_menu = pd.read_sql("SELECT id, nama, stok FROM menu ORDER BY id", conn)
print(df_menu)

conn.close()