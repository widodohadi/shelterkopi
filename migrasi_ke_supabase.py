"""Salin data dari shelterkopi.db (SQLite lokal) ke Supabase.

Cara pakai:
  1. Jalankan aplikasi SEKALI dengan DATABASE_URL terisi (agar tabel dibuat di Supabase), lalu hentikan.
  2. Jalankan:  python migrasi_ke_supabase.py
     (membaca DATABASE_URL dari .streamlit/secrets.toml atau variabel lingkungan)
PERHATIAN: isi tabel menu & transaksi di Supabase akan DIGANTI dengan isi shelterkopi.db.
"""
import os
import re
import sqlite3
import sys

import psycopg2

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "shelterkopi.db")


def baca_url():
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"].strip()
    path = os.path.join(BASE, ".streamlit", "secrets.toml")
    if os.path.exists(path):
        m = re.search(r'DATABASE_URL\s*=\s*"([^"]+)"', open(path, encoding="utf-8").read())
        if m:
            return m.group(1).strip()
    return ""


url = baca_url()
if not url:
    sys.exit("DATABASE_URL tidak ditemukan. Isi .streamlit/secrets.toml terlebih dahulu.")
if not os.path.exists(SRC):
    sys.exit(f"File {SRC} tidak ditemukan.")

lite = sqlite3.connect(SRC)
menu = lite.execute(
    "SELECT id, nama, kategori, harga_panas, harga_dingin, stok, gambar FROM menu ORDER BY id"
).fetchall()
trx = lite.execute(
    "SELECT id, nama_pembeli, menu, ukuran, jumlah, total_harga, metode_bayar, "
    "CAST(waktu AS TEXT), uang_diterima, kembalian FROM transaksi ORDER BY id"
).fetchall()
lite.close()
print(f"Akan menyalin {len(menu)} menu dan {len(trx)} transaksi ke Supabase.")
if input("Data lama di Supabase akan DIHAPUS & diganti. Ketik YA untuk lanjut: ").strip() != "YA":
    sys.exit("Dibatalkan.")

with psycopg2.connect(url, connect_timeout=10) as pg:
    with pg.cursor() as cur:
        cur.execute("TRUNCATE menu, transaksi RESTART IDENTITY")
        cur.executemany("INSERT INTO menu VALUES (%s,%s,%s,%s,%s,%s,%s)", menu)
        cur.executemany("INSERT INTO transaksi VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", trx)
        for tabel in ("menu", "transaksi"):  # lanjutkan nomor urut id agar tidak bentrok
            cur.execute(
                f"SELECT setval(pg_get_serial_sequence('{tabel}','id'), "
                f"(SELECT COALESCE(MAX(id),1) FROM {tabel}), (SELECT COUNT(*) > 0 FROM {tabel}))"
            )
print("Selesai. Buka aplikasi dan cek menu serta riwayat transaksinya.")
