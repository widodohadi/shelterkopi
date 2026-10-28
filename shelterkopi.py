import base64
from datetime import datetime, timedelta, timezone
import math
import sqlite3
import os
import zlib

import pandas as pd
import psycopg2
import requests
import streamlit as st

# ======================================================================
# KONFIGURASI
# ======================================================================
WIB = timezone(timedelta(hours=7))
OWNER_PIN = os.getenv("OWNER_PIN", "1234")  # ganti PIN pemilik di sini
DEFAULT_TOPIC = os.getenv("NTFY_TOPIC", "shelterkopi-7391")

NAMA_KEDAI = "Shelter Kopi"
HANDLE = "shelterkopi_"
JAM_BUKA = "16.00 - 00.00"
ALAMAT = "Jl. Pantai Labu, Emplasmen Kualanamu, Kec. Beringin, Kabupaten Deli Serdang, Sumatera Utara."
KATEGORI = ["Kopi Susu", "Kopi Hitam", "Bukan Kopi"]
STOK_AWAL = 50

st.set_page_config(page_title="shelterkopi_", page_icon="☕", layout="wide")

# Menu persis seperti lembar menu: (nama, kategori, harga panas, harga dingin) - 0 = tidak tersedia
MENU_AWAL = [
    ("Kopi Susu", "Kopi Susu", 13000, 15000),
    ("Cappuccino", "Kopi Susu", 15000, 18000),
    ("Kopster", "Kopi Susu", 0, 17000),
    ("Vietnam Drip", "Kopi Susu", 20000, 0),
    ("Espresso", "Kopi Hitam", 13000, 15000),
    ("Americano", "Kopi Hitam", 13000, 15000),
    ("Kopi Tubruk", "Kopi Hitam", 13000, 0),
    ("Kopi Klasik", "Kopi Hitam", 13000, 0),
    ("V60", "Kopi Hitam", 20000, 20000),
    ("Teh Lemon", "Bukan Kopi", 12000, 12000),
    ("Teh Hijau", "Bukan Kopi", 15000, 15000),
    ("Teh Tarik Om", "Bukan Kopi", 13000, 13000),
    ("Taro", "Bukan Kopi", 15000, 15000),
    ("Redvelvet", "Bukan Kopi", 15000, 15000),
    ("Coklat", "Bukan Kopi", 15000, 15000),
    ("Milo", "Bukan Kopi", 15000, 15000),
    ("Lemsu", "Bukan Kopi", 13000, 13000),
]


# ======================================================================
# DATABASE & HELPER
# ======================================================================
def db():
    if "DATABASE_URL" in st.secrets:
        url = st.secrets["DATABASE_URL"]
    else:
        url = "postgresql://postgres:ShelterKopi2026@db.eatbthzfktiplnugrewl.supabase.co:5432/postgres"
    return psycopg2.connect(url)

# ======================================================================
# KONFIGURASI
# ======================================================================
DB_FILE = "shelterkopi.db"
WIB = timezone(timedelta(hours=7))
OWNER_PIN = os.getenv("OWNER_PIN", "1234")  # ganti PIN pemilik di sini
DEFAULT_TOPIC = os.getenv("NTFY_TOPIC", "shelterkopi-7391")

NAMA_KEDAI = "Shelter Kopi"
HANDLE = "shelterkopi_"
JAM_BUKA = "16.00 - 00.00"
ALAMAT = "Jl. Pantai Labu, Emplasmen Kualanamu, Kec. Beringin, Kabupaten Deli Serdang, Sumatera Utara."
KATEGORI = ["Kopi Susu", "Kopi Hitam", "Bukan Kopi"]
STOK_AWAL = 50

st.set_page_config(page_title="shelterkopi_", page_icon="☕", layout="wide")

# Menu persis seperti lembar menu: (nama, kategori, harga panas, harga dingin) - 0 = tidak tersedia
MENU_AWAL = [
    ("Kopi Susu", "Kopi Susu", 13000, 15000),
    ("Cappuccino", "Kopi Susu", 15000, 18000),
    ("Kopster", "Kopi Susu", 0, 17000),
    ("Vietnam Drip", "Kopi Susu", 20000, 0),
    ("Espresso", "Kopi Hitam", 13000, 15000),
    ("Americano", "Kopi Hitam", 13000, 15000),
    ("Kopi Tubruk", "Kopi Hitam", 13000, 0),
    ("Kopi Klasik", "Kopi Hitam", 13000, 0),
    ("V60", "Kopi Hitam", 20000, 20000),
    ("Teh Lemon", "Bukan Kopi", 12000, 12000),
    ("Teh Hijau", "Bukan Kopi", 15000, 15000),
    ("Teh Tarik Om", "Bukan Kopi", 13000, 13000),
    ("Taro", "Bukan Kopi", 15000, 15000),
    ("Redvelvet", "Bukan Kopi", 15000, 15000),
    ("Coklat", "Bukan Kopi", 15000, 15000),
    ("Milo", "Bukan Kopi", 15000, 15000),
    ("Lemsu", "Bukan Kopi", 13000, 13000),
]


# ======================================================================
# DATABASE & HELPER
# ======================================================================
def db():
    return sqlite3.connect(DB_FILE)


def init_db():
    conn = db()
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT, kategori TEXT,
            harga_panas INTEGER, harga_dingin INTEGER,
            stok INTEGER, gambar TEXT)"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS transaksi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_pembeli TEXT, menu TEXT, ukuran TEXT,
            jumlah INTEGER, total_harga INTEGER, metode_bayar TEXT,
            waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uang_diterima INTEGER DEFAULT 0, kembalian INTEGER DEFAULT 0)"""
    )
    if c.execute("SELECT COUNT(*) FROM menu").fetchone()[0] == 0:
        c.executemany(
            "INSERT INTO menu (nama, kategori, harga_panas, harga_dingin, stok, gambar) VALUES (?,?,?,?,?,'')",
            [(n, k, p, d, STOK_AWAL) for n, k, p, d in MENU_AWAL],
        )
    conn.commit()
    conn.close()


init_db()


def rupiah(x):
    return "Rp " + f"{int(x):,}".replace(",", ".")


def rb(x):
    return f"{int(x) / 1000:g}rb"


def angka_menu(x):
    return f"{int(x) / 1000:g}" if int(x) > 0 else ""


def now_wib():
    return datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S")


def file_ke_uri(f):
    mime = f.type or "image/png"
    return f"data:{mime};base64," + base64.b64encode(f.getvalue()).decode()


# ======================================================================
# ILUSTRASI MINUMAN (SVG vektor - tajam di layar apa pun / HD)
# ======================================================================
LATAR = {
    "Kopi Susu": ("#FFEFB5", "#F8D45C"),
    "Kopi Hitam": ("#FFE6A3", "#F1BC3A"),
    "Bukan Kopi": ("#FFF4C9", "#F9DE6E"),
}

ES = [(146, 146, 50, -12), (208, 134, 52, 10), (160, 214, 54, 8),
      (222, 222, 48, -9), (146, 282, 50, 14), (210, 290, 52, -6), (176, 100, 50, -8)]


def _spec(nama):
    """Warna lapisan (atas -> bawah), topping, dan aksesori tiap minuman."""
    n = nama.lower()
    if "vietnam" in n:
        return dict(layers=[("#3a1f0e", 1), ("#8a5a34", 1), ("#f1dcb8", 1.6)], extra="phin")
    if "cappuccino" in n:
        return dict(layers=[("#d9b38a", 1.3), ("#a86f43", 1.4), ("#5a3219", 1)], top="art")
    if "kopster" in n:
        return dict(layers=[("#caa27a", 1), ("#8a5530", 1.4), ("#f0dcc0", 1)])
    if "kopi susu" in n:
        return dict(layers=[("#4a2813", 1), ("#a2693a", 1.2), ("#f4e4c8", 1.6)])
    if "espresso" in n:
        return dict(layers=[("#b9773a", .4), ("#3a1d0d", 1.4), ("#2a1408", 1)])
    if "americano" in n:
        return dict(layers=[("#3a1e0e", 1), ("#24120a", 1.5)])
    if "tubruk" in n:
        return dict(layers=[("#2e1709", 1.2), ("#1b0e06", 1.6)], extra="ampas")
    if "klasik" in n:
        return dict(layers=[("#4a2813", 1), ("#2d1609", 1.4)])
    if "v60" in n:
        return dict(layers=[("#6a3b1a", 1), ("#3b200e", 1.4)], extra="v60")
    if "lemsu" in n:
        return dict(layers=[("#fbefb2", 1), ("#f4d86a", 1.5)], extra="lemon")
    if "lemon" in n:
        return dict(layers=[("#f3c24a", 1), ("#e29a2a", 1.6)], extra="lemon")
    if "hijau" in n:
        return dict(layers=[("#b7d56a", 1), ("#8fb83c", 1.6)])
    if "tarik" in n:
        return dict(layers=[("#c58f55", 1.3), ("#a96d3a", 1.2)], top="foam")
    if "taro" in n:
        return dict(layers=[("#cdb4ee", 1), ("#a782d6", 1.5)], top="cream")
    if "redvelvet" in n or "red velvet" in n:
        return dict(layers=[("#f8dfe0", .7), ("#d4333f", 1.2), ("#a31524", 1.4)], top="cream")
    if "coklat" in n or "cokelat" in n:
        return dict(layers=[("#8a5030", 1), ("#4a2412", 1.6)], top="cream")
    if "milo" in n:
        return dict(layers=[("#6b4423", 1), ("#3d2411", 1.6)], top="bubuk")
    return dict(layers=[("#a86f43", 1), ("#5a3219", 1.5)])


def _grad_cair(uid, layers):
    total = sum(w for _, w in layers)
    stops, acc = [], 0.0
    for i, (c, w) in enumerate(layers):
        a, b = acc / total, (acc + w) / total
        acc += w
        pad = min(0.08, (b - a) / 3)
        s = 0 if i == 0 else a + pad
        e = 1 if i == len(layers) - 1 else b - pad
        stops.append(f'<stop offset="{s:.3f}" stop-color="{c}"/><stop offset="{e:.3f}" stop-color="{c}"/>')
    return f'<linearGradient id="l{uid}" x1="0" y1="0" x2="0" y2="1">{"".join(stops)}</linearGradient>'


def _bunga(cx, cy, r, op):
    petals = "".join(
        f'<ellipse cx="0" cy="{-r * .62:.1f}" rx="{r * .16:.1f}" ry="{r * .4:.1f}" fill="#fff" transform="rotate({a})"/>'
        for a in range(0, 360, 45)
    )
    return f'<g transform="translate({cx} {cy})" opacity="{op}">{petals}<circle r="{r * .12:.1f}" fill="#fff"/></g>'


def _lemon(cx, cy, r):
    seg = "".join(
        f'<line x1="{cx}" y1="{cy}" x2="{cx + (r - 7) * math.cos(a * 0.01745):.1f}" '
        f'y2="{cy + (r - 7) * math.sin(a * 0.01745):.1f}" stroke="#fff6c2" stroke-width="2.5"/>'
        for a in range(0, 360, 45)
    )
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#F7D33F" stroke="#E8B923" stroke-width="3"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r - 5}" fill="#FFF0A0"/>{seg}'
        f'<circle cx="{cx}" cy="{cy}" r="4" fill="#fff6c2"/>'
    )


def _phin(rim, uid, cx=200, h=92):
    y0 = rim - h
    return (
        f'<ellipse cx="{cx}" cy="{rim - 6}" rx="104" ry="12" fill="#b7bcc4" stroke="#8d939c" stroke-width="2"/>'
        f'<rect x="{cx - 62}" y="{y0 + 22}" width="124" height="{rim - y0 - 28}" rx="8" fill="url(#mt{uid})"/>'
        f'<rect x="{cx - 70}" y="{y0 + 12}" width="140" height="14" rx="7" fill="#c9ced6"/>'
        f'<rect x="{cx - 52}" y="{y0}" width="104" height="14" rx="7" fill="#aab0b9"/>'
        f'<circle cx="{cx}" cy="{y0 - 6}" r="8" fill="#8d939c"/>'
        f'<ellipse cx="{cx}" cy="{rim + 12}" rx="5" ry="8" fill="#4a2813"/>'
    )


def _v60(rim, uid, cx=200, h=96):
    return (
        f'<path d="M{cx - 88} {rim - h} L{cx + 88} {rim - h} L{cx + 24} {rim - 6} L{cx - 24} {rim - 6} Z" '
        f'fill="#F6F1E4" stroke="#c9bfa8" stroke-width="3" stroke-linejoin="round"/>'
        f'<ellipse cx="{cx}" cy="{rim - h}" rx="88" ry="11" fill="#3b200e" stroke="#c9bfa8" stroke-width="3"/>'
        f'<path d="M{cx - 60} {rim - h + 8} L{cx - 16} {rim - 8} M{cx - 20} {rim - h + 10} L{cx - 6} {rim - 8} '
        f'M{cx + 20} {rim - h + 10} L{cx + 6} {rim - 8} M{cx + 60} {rim - h + 8} L{cx + 16} {rim - 8}" '
        f'stroke="#d8cfba" stroke-width="2.5" fill="none"/>'
        f'<path d="M{cx + 86} {rim - h + 12} Q{cx + 128} {rim - h + 12} {cx + 124} {rim - h + 44}" fill="none" '
        f'stroke="#F6F1E4" stroke-width="12" stroke-linecap="round"/>'
        f'<ellipse cx="{cx}" cy="{rim + 12}" rx="5" ry="8" fill="#4a2813"/>'
    )


def _cream(cx, base, r):
    """Whipped cream bertingkat."""
    return (
        f'<ellipse cx="{cx}" cy="{base}" rx="{r}" ry="{r * .3:.1f}" fill="#FFFAF0" stroke="#EADBC0" stroke-width="2"/>'
        f'<ellipse cx="{cx}" cy="{base - r * .32:.1f}" rx="{r * .74:.1f}" ry="{r * .26:.1f}" fill="#FFFAF0" stroke="#EADBC0" stroke-width="2"/>'
        f'<ellipse cx="{cx}" cy="{base - r * .6:.1f}" rx="{r * .46:.1f}" ry="{r * .22:.1f}" fill="#FFFAF0" stroke="#EADBC0" stroke-width="2"/>'
        f'<path d="M{cx - 8} {base - r * .74:.1f} Q{cx} {base - r * 1.08:.1f} {cx + 8} {base - r * .74:.1f} Z" fill="#FFFAF0" stroke="#EADBC0" stroke-width="2"/>'
    )


def _bagian_dingin(uid, sp):
    glass = "M112 84 L288 84 L266 324 Q264 342 246 342 L154 342 Q136 342 134 324 Z"
    top = sp.get("top")
    ext = sp.get("extra", "")
    p = ['<ellipse cx="200" cy="356" rx="108" ry="12" fill="#2B2118" opacity=".16"/>',
         f'<path d="{glass}" fill="#fff" fill-opacity=".32"/>']
    isi = [f'<rect x="100" y="122" width="200" height="230" fill="url(#l{uid})"/>']
    for x, y, s, r in ES:
        isi.append(
            f'<g transform="rotate({r} {x + s / 2} {y + s / 2})">'
            f'<rect x="{x}" y="{y}" width="{s}" height="{s}" rx="9" fill="#fff" fill-opacity=".26" '
            f'stroke="#fff" stroke-opacity=".75" stroke-width="2.5"/>'
            f'<path d="M{x + 9} {y + 14} L{x + 9} {y + s - 16}" stroke="#fff" stroke-opacity=".7" '
            f'stroke-width="3" stroke-linecap="round"/></g>'
        )
    if top in ("foam", "art"):
        isi.append('<ellipse cx="200" cy="122" rx="92" ry="20" fill="#FFF3DF"/>')
        for cx, cy, r in [(150, 118, 9), (176, 112, 11), (206, 116, 10), (236, 112, 11), (258, 120, 8)]:
            isi.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#FFF8EC"/>')
    if top == "bubuk":
        for cx, cy in [(150, 124), (168, 120), (186, 126), (204, 121), (222, 127), (240, 122), (256, 126), (176, 132), (232, 134)]:
            isi.append(f'<circle cx="{cx}" cy="{cy}" r="4.5" fill="#6b3f1d" opacity=".9"/>')
    if ext == "ampas":
        for cx, cy in [(160, 320), (178, 328), (198, 322), (218, 330), (238, 322), (190, 312), (226, 314), (170, 334)]:
            isi.append(f'<circle cx="{cx}" cy="{cy}" r="3.6" fill="#120a04"/>')
    p.append(f'<g clip-path="url(#k{uid})">{"".join(isi)}</g>')
    if ext not in ("phin", "v60"):
        p.append('<line x1="252" y1="26" x2="214" y2="268" stroke="#F2A93B" stroke-width="12" stroke-linecap="round"/>')
        p.append('<line x1="252" y1="26" x2="214" y2="268" stroke="#fff" stroke-width="12" stroke-dasharray="9 13" opacity=".55"/>')
    p.append(f'<path d="{glass}" fill="none" stroke="#fff" stroke-width="4" stroke-opacity=".95"/>')
    p.append('<path d="M127 112 L142 318" stroke="#fff" stroke-width="8" stroke-linecap="round" opacity=".5"/>')
    p.append('<path d="M268 120 L260 250" stroke="#fff" stroke-width="4" stroke-linecap="round" opacity=".35"/>')
    p.append('<rect x="106" y="78" width="188" height="11" rx="5.5" fill="#fff" opacity=".96"/>')
    for cx, cy in [(158, 160), (166, 226), (250, 190), (244, 268), (176, 296)]:
        p.append(f'<ellipse cx="{cx}" cy="{cy}" rx="3.4" ry="4.6" fill="#fff" opacity=".55"/>')
    if top == "cream":
        p.append(_cream(200, 82, 78))
    if ext == "phin":
        p.append(_phin(84, uid, h=62))
    if ext == "v60":
        p.append(_v60(84, uid, h=64))
    if ext == "lemon":
        p.append(_lemon(292, 92, 34))
    return "".join(p)


def _bagian_panas(uid, sp, skala=1.0):
    top = sp.get("top")
    ext = sp.get("extra", "")
    permukaan = sp["layers"][0][0]
    badan = "M112 196 L288 196 L278 318 Q275 346 248 346 L152 346 Q125 346 122 318 Z"
    p = ['<ellipse cx="200" cy="366" rx="156" ry="12" fill="#2B2118" opacity=".16"/>',
         '<ellipse cx="200" cy="354" rx="146" ry="20" fill="#FFF6DA" stroke="#E6CF93" stroke-width="3"/>',
         '<ellipse cx="200" cy="350" rx="108" ry="12" fill="#F0DDA6" opacity=".7"/>']
    # gagang
    p.append(f'<path d="M284 222 Q350 222 344 272 Q338 316 274 312" fill="none" stroke="url(#mg{uid})" stroke-width="20" stroke-linecap="round"/>')
    p.append(f'<path d="{badan}" fill="url(#mg{uid})"/>')
    p.append(f'<clipPath id="k{uid}"><path d="{badan}"/></clipPath>')
    p.append(
        f'<g clip-path="url(#k{uid})"><rect x="100" y="262" width="200" height="32" fill="#2B2118"/>'
        '<text x="200" y="284" text-anchor="middle" font-family="Georgia,serif" font-weight="bold" '
        'font-size="17" letter-spacing="5" fill="#F6D95B">SHELTER</text></g>'
    )
    p.append('<path d="M128 214 L134 318" stroke="#fff" stroke-width="8" stroke-linecap="round" opacity=".7"/>')
    # permukaan minuman
    p.append('<ellipse cx="200" cy="196" rx="90" ry="19" fill="#FFF6DA" stroke="#E6CF93" stroke-width="3"/>')
    p.append(f'<ellipse cx="200" cy="198" rx="82" ry="14.5" fill="{permukaan}"/>')
    if len(sp["layers"]) > 1 and top not in ("foam", "art"):
        p.append(f'<ellipse cx="200" cy="199" rx="52" ry="8" fill="{sp["layers"][1][0]}" opacity=".75"/>')
    if top == "art":
        p.append('<ellipse cx="200" cy="198" rx="80" ry="13.5" fill="#F4E2C4"/>')
        p.append('<path d="M200 206 C186 190 170 200 180 208 C186 214 200 220 200 220 C200 220 214 214 220 208 C230 200 214 190 200 206 Z" fill="#8a5530"/>')
    if top == "foam":
        p.append('<ellipse cx="200" cy="197" rx="80" ry="13.5" fill="#FFF3DF"/>')
        for cx, cy, r in [(160, 197, 6), (180, 192, 7), (204, 196, 7), (228, 192, 7), (244, 198, 5)]:
            p.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#FFF9EE"/>')
    if top == "bubuk":
        for cx, cy in [(156, 198), (172, 192), (190, 200), (208, 194), (226, 200), (244, 196), (200, 206)]:
            p.append(f'<circle cx="{cx}" cy="{cy}" r="3.6" fill="#6b3f1d"/>')
    if ext == "ampas":
        for cx, cy in [(164, 200), (182, 194), (202, 203), (224, 196), (240, 201)]:
            p.append(f'<circle cx="{cx}" cy="{cy}" r="3.2" fill="#120a04"/>')
    # uap
    for dx, ph in [(-34, 0), (6, 12), (44, 4)]:
        x = 200 + dx
        p.append(
            f'<path d="M{x} {170 - ph} Q{x - 20} {140 - ph} {x} {118 - ph} Q{x + 20} {96 - ph} {x} {70 - ph}" '
            'fill="none" stroke="#fff" stroke-width="9" stroke-linecap="round" opacity=".8"/>'
        )
    if top == "cream":
        p.append(_cream(200, 194, 62))
    if ext == "phin":
        p.append(_phin(196, uid))
    if ext == "v60":
        p.append(_v60(196, uid))
    if ext == "lemon":
        p.append(_lemon(296, 204, 30))
    isi = "".join(p)
    if skala != 1.0:
        tx, ty = 200 * (1 - skala), 366 * (1 - skala)
        return f'<g transform="translate({tx:.1f} {ty:.1f}) scale({skala})">{isi}</g>'
    return isi


def gambar_svg(nama, suhu="Dingin", kategori="Kopi Susu", lebar=None):
    """Ilustrasi minuman vektor (HD, tajam di semua ukuran layar)."""
    sp = _spec(nama)
    uid = zlib.crc32(f"{nama}{suhu}".encode()) & 0xFFFFFF
    b1, b2 = LATAR.get(kategori, LATAR["Kopi Susu"])
    panas = suhu == "Panas"
    skala = 0.78 if (panas and "espresso" in str(nama).lower()) else 1.0
    glass = "M112 84 L288 84 L266 324 Q264 342 246 342 L154 342 Q136 342 134 324 Z"
    defs = (
        f'<linearGradient id="bg{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{b1}"/>'
        f'<stop offset="1" stop-color="{b2}"/></linearGradient>'
        f'<radialGradient id="gl{uid}" cx=".5" cy=".42" r=".6"><stop offset="0" stop-color="#fff" stop-opacity=".75"/>'
        f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="mt{uid}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#9aa0a9"/>'
        f'<stop offset=".35" stop-color="#eceff3"/><stop offset=".7" stop-color="#c3c8d0"/>'
        f'<stop offset="1" stop-color="#8b919a"/></linearGradient>'
        f'<linearGradient id="mg{uid}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#FFFDF2"/>'
        f'<stop offset=".6" stop-color="#FBEFC4"/><stop offset="1" stop-color="#E8D08A"/></linearGradient>'
        f'{_grad_cair(uid, sp["layers"])}'
        f'<clipPath id="k{uid}"><path d="{glass}"/></clipPath>'
    )
    # clipPath mug dibuat ulang di dalam _bagian_panas dengan id sama; hindari duplikat
    if panas:
        defs = defs.replace(f'<clipPath id="k{uid}"><path d="{glass}"/></clipPath>', "")
    isi = _bagian_panas(uid, sp, skala) if panas else _bagian_dingin(uid, sp)
    badge = "🔥" if panas else "❄️"
    svg = (
        f'<svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg" style="display:block;width:100%;height:auto" '
        f'role="img" aria-label="{nama} {suhu}"><defs>{defs}</defs>'
        f'<rect width="400" height="400" fill="url(#bg{uid})"/>'
        f'<circle cx="200" cy="190" r="190" fill="url(#gl{uid})"/>'
        f'{_bunga(46, 52, 34, .55)}{_bunga(356, 340, 40, .45)}{_bunga(362, 62, 20, .5)}{_bunga(40, 350, 22, .4)}'
        f'{isi}'
        '</svg>'
    )
    maxw = f"max-width:{lebar}px;" if lebar else ""
    return f'<div class="foto" style="{maxw}">{svg}<span class="foto-tag">{badge} {suhu}</span></div>'


def foto_html(m, suhu, lebar=None):
    """Pakai foto asli jika ada (URL / unggahan), jika tidak pakai ilustrasi."""
    g = str(m.gambar or "")
    if g.startswith("http") or g.startswith("data:image"):
        maxw = f"max-width:{lebar}px;" if lebar else ""
        badge = "🔥" if suhu == "Panas" else "❄️"
        return f'<div class="foto" style="{maxw}"><img src="{g}" alt="{m.nama}"/><span class="foto-tag">{badge} {suhu}</span></div>'
    return gambar_svg(m.nama, suhu, m.kategori, lebar)


def suhu_utama(m):
    return "Dingin" if int(m.harga_dingin) > 0 else "Panas"


def chip_harga(m):
    def c(ikon, h):
        if int(h) > 0:
            return f'<span class="chip">{ikon} {rb(h)}</span>'
        return f'<span class="chip chip-off">{ikon} -</span>'
    return c("🔥", m.harga_panas) + c("❄️", m.harga_dingin)


# ======================================================================
# STRUK & NOTIFIKASI
# ======================================================================
def get_trx(trx_id):
    conn = db()
    query = text("SELECT * FROM transaksi WHERE id = :id")
    df = pd.read_sql(query, conn, params={"id": int(trx_id)})
    conn.close()
    return df.iloc[0].to_dict() if not df.empty else None

def _angka(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def buat_struk(t):
    """Teks struk (lebar 34 karakter, cocok untuk printer thermal)."""
    w = 34
    garis = "-" * w
    jumlah = int(t["jumlah"])
    satuan = int(t["total_harga"]) // max(jumlah, 1)
    rincian = f"{jumlah} x {rupiah(satuan)}"
    total = rupiah(t["total_harga"])
    diterima = _angka(t.get("uang_diterima"))
    extra = []
    if diterima > 0:
        dt, kb = rupiah(diterima), rupiah(_angka(t.get("kembalian")))
        extra = ["DITERIMA".ljust(w - len(dt)) + dt, "KEMBALI".ljust(w - len(kb)) + kb]
    baris = [
        "S H E L T E R   K O P I".center(w),
        f"@{HANDLE}".center(w),
        f"Buka {JAM_BUKA}".center(w),
        garis,
        f"No    : #{int(t['id']):05d}",
        f"Waktu : {t['waktu']}",
        f"Nama  : {t['nama_pembeli']}",
        f"Bayar : {t['metode_bayar']}",
        garis,
        f"{t['menu']} ({t['ukuran']})",
        rincian.ljust(w - len(total)) + total,
        garis,
        "TOTAL".ljust(w - len(total)) + total,
        *extra,
        garis,
        "Terima kasih sudah mampir di".center(w),
        "Shelter. Sampai jumpa lagi!".center(w),
    ]
    return "\n".join(baris)


def tampil_struk(t, key):
    teks = buat_struk(t)
    st.markdown(f'<div class="struk">{teks}</div>', unsafe_allow_html=True)
    st.download_button(
        "⬇️ Unduh Struk (.txt)",
        data=teks,
        file_name=f"struk_{int(t['id']):05d}.txt",
        mime="text/plain",
        key=f"dl_{key}",
        use_container_width=True,
    )


def kirim_notif(topik, judul, pesan):
    """Push notification ke HP lewat ntfy.sh (gratis, tanpa akun)."""
    st.session_state.notif_error = ""
    if not topik.strip():
        st.session_state.notif_error = "nama topik kosong"
        return False
    judul = judul.encode("ascii", "ignore").decode().strip() or "Kasir"
    try:
        r = requests.post(
            f"https://ntfy.sh/{topik.strip()}",
            data=pesan.encode("utf-8"),
            headers={"Title": judul, "Priority": "high", "Tags": "coffee,moneybag"},
            timeout=8,
        )
        if not r.ok:
            st.session_state.notif_error = f"server menolak (HTTP {r.status_code})"
        return r.ok
    except Exception as e:
        st.session_state.notif_error = f"{type(e).__name__}: {str(e)[:80]}"
        return False


# ======================================================================
# STYLING
# ======================================================================
LOGO = (
    '<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" class="logo-svg">'
    '<path d="M18 46 L50 14 L82 46 V90 H18 Z" fill="none" stroke="#2B2118" stroke-width="5.5" stroke-linejoin="round"/>'
    '<path d="M65 41 C65 27 35 27 35 42 C35 57 66 53 66 68 C66 82 37 82 37 68" fill="none" stroke="#2B2118" '
    'stroke-width="8" stroke-linecap="round"/></svg>'
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Gloock&family=Quicksand:wght@500;600;700&display=swap');
:root{--kopi:#2B2118;--kuning:#F6D95B;--emas:#E8B923;--krem:#FFFBEA;--krem2:#FFF1B8;}
html, body, .stApp, [class*="css"]{font-family:'Quicksand',system-ui,sans-serif;}
.stApp{background:var(--krem);}
.block-container{padding-top:1.2rem;max-width:1250px;}
[data-testid="stSidebar"]{background:var(--krem2);border-right:3px solid var(--kopi);}
h1,h2,h3{font-family:'Gloock',Georgia,serif !important;color:var(--kopi);letter-spacing:.2px;}

/* Header */
.hero{border-radius:22px;overflow:hidden;box-shadow:0 12px 30px rgba(43,33,24,.22);margin-bottom:22px;background:#fff;}
.hero-bar{height:34px;background:repeating-linear-gradient(90deg,#2B2118 0 7px,#3a2e22 7px 8px);}
.hero-body{display:flex;align-items:center;gap:20px;padding:20px 26px;flex-wrap:wrap;
  background:radial-gradient(circle at 12% 20%,#FFF1B8 0,#F6D95B 70%);}
.logo-svg{width:78px;height:78px;flex:none;}
.hero-tx{flex:1;min-width:230px;}
.brand{font-family:'Gloock',serif;font-size:2.5rem;letter-spacing:.42em;color:var(--kopi);line-height:1;}
.handle{font-weight:700;color:#5a4630;margin-top:6px;font-size:1.02rem;}
.alamat{font-size:.82rem;color:#4a3a28;margin-top:4px;max-width:560px;}
.buka{background:var(--kopi);color:var(--kuning);padding:9px 20px;border-radius:999px;font-weight:700;
  font-size:.95rem;white-space:nowrap;box-shadow:0 4px 0 rgba(0,0,0,.18);}

/* Foto minuman */
.foto{position:relative;border-radius:18px;overflow:hidden;box-shadow:0 8px 20px rgba(43,33,24,.18);margin:0 auto 8px;}
.foto img{display:block;width:100%;aspect-ratio:1/1;object-fit:cover;}
.foto-tag{position:absolute;left:10px;bottom:10px;background:rgba(43,33,24,.88);color:var(--kuning);
  padding:3px 11px;border-radius:999px;font-size:.74rem;font-weight:700;}

/* Kartu & chip */
div[data-testid="stVerticalBlockBorderWrapper"]{border-radius:20px !important;border-color:#EBD37A !important;background:#fff;}
.nm{font-family:'Gloock',serif;font-size:1.12rem;color:var(--kopi);margin:2px 0 6px;}
.chip{display:inline-block;background:var(--kuning);color:var(--kopi);padding:2px 11px;border-radius:999px;
  font-size:.8rem;font-weight:700;margin-right:6px;border:1.5px solid var(--kopi);}
.chip-off{background:#eee;color:#9a9a9a;border-color:#ccc;}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.74rem;font-weight:700;}
.badge-ok{background:#dcfce7;color:#166534;}
.badge-low{background:#fef3c7;color:#92400e;}
.badge-out{background:#fee2e2;color:#991b1b;}

/* Tombol */
div.stButton > button[kind="primary"], div[data-testid="stDownloadButton"] > button{
  background:var(--kopi);color:var(--kuning);border:none;border-radius:12px;font-weight:700;}
div.stButton > button[kind="primary"]:hover{background:#44342a;color:#fff;}
div.stButton > button[kind="secondary"]{border:2px solid var(--kopi);border-radius:12px;font-weight:700;color:var(--kopi);background:#fff;}
div.stButton > button[kind="secondary"]:hover{background:var(--kuning);}
div[data-testid="stMetric"]{background:#fff;border:2px solid var(--kopi);border-radius:16px;padding:14px 18px;
  box-shadow:5px 5px 0 var(--kuning);}

/* Struk */
.struk{font-family:'Courier New',monospace;white-space:pre;font-size:.85rem;background:#fffef7;color:#222;
  padding:18px 20px;border-radius:6px;border:1px dashed #bbb;box-shadow:0 4px 14px rgba(0,0,0,.12);
  margin-bottom:10px;overflow-x:auto;}

/* Lembar menu (replika menu cetak) */
.lembar{background:#fff;border-radius:22px;overflow:hidden;box-shadow:0 12px 30px rgba(43,33,24,.2);}
.lembar-top{height:30px;background:repeating-linear-gradient(90deg,#2B2118 0 7px,#3a2e22 7px 8px);}
.lembar-in{padding:22px 26px 28px;}
.ljudul{text-align:center;}
.ljudul .big{font-family:'Gloock',serif;font-size:4.6rem;line-height:1;color:var(--kopi);}
.ljudul .al{font-size:.82rem;color:#4a3a28;margin-top:4px;}
.lgrid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:20px;}
@media (max-width:820px){.lgrid{grid-template-columns:1fr;}.brand{font-size:1.7rem;}.ljudul .big{font-size:3.4rem;}}
.panel{background:var(--kuning);border-radius:22px;padding:16px 16px 12px;display:flex;flex-direction:column;gap:12px;}
.mhead{display:grid;grid-template-columns:1fr 62px 62px;background:var(--kopi);color:var(--kuning);
  font-family:'Gloock',serif;border-radius:999px;padding:7px 18px;font-size:.95rem;}
.mhead span:nth-child(n+2){text-align:center;}
.mrow{display:grid;grid-template-columns:1fr 62px 62px;padding:5px 18px;font-weight:600;color:var(--kopi);
  border-bottom:1px dashed rgba(43,33,24,.18);}
.mrow:last-child{border-bottom:none;}
.mrow span:nth-child(n+2){text-align:center;font-weight:700;}
.lpill{align-self:flex-end;border:2px solid var(--kopi);background:#fff;border-radius:999px;padding:5px 20px;
  font-family:'Gloock',serif;font-size:.9rem;color:var(--kopi);}
.lfoot{display:flex;justify-content:space-between;align-items:center;margin-top:18px;}
.lfoot .ig{border:2px solid var(--kopi);border-radius:999px;padding:6px 26px;font-family:'Gloock',serif;color:var(--kopi);}
.lfoot .logo-svg{width:64px;height:64px;}
.catatan{font-size:.78rem;color:#6b5a45;text-align:center;margin-top:8px;}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)
st.markdown(
    '<div class="hero"><div class="hero-bar"></div><div class="hero-body">'
    + LOGO
    + f'<div class="hero-tx"><div class="brand">SHELTER</div><div class="handle">@{HANDLE} · Kasir &amp; Menu Digital</div>'
    f'<div class="alamat">{ALAMAT}</div></div>'
    f'<div class="buka">🕓 Buka {JAM_BUKA}</div></div></div>',
    unsafe_allow_html=True,
)

# ======================================================================
# SIDEBAR
# ======================================================================
st.sidebar.markdown("### ⚙️ Pengaturan & Navigasi")
role = st.sidebar.radio("Akses Pengguna", ["Kasir", "Pemilik (Owner)"])

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔔 Notifikasi HP")
st.sidebar.text_input(
    "Nama topik ntfy",
    value=DEFAULT_TOPIC,
    key="ntfy_topic",
    help="Pasang aplikasi ntfy di HP, lalu subscribe ke topik yang sama.",
)
if st.sidebar.button("Kirim notifikasi tes", use_container_width=True):
    ok = kirim_notif(st.session_state.ntfy_topic, "Tes Kasir", "Notifikasi dari Shelter Kopi berhasil! 🎉")
    st.sidebar.success("Terkirim ✅") if ok else st.sidebar.error(
        f"Gagal kirim: {st.session_state.get('notif_error', '')}"
    )


# ======================================================================
# CALLBACK
# ======================================================================
def set_uang(nominal):
    st.session_state.uang = int(nominal)


def pilih_menu(mid):
    st.session_state.menu_id = int(mid)


def proses_pesanan():
    s = st.session_state
    nama = s.get("nama", "").strip()
    menu_id = s.get("menu_id")
    suhu = s.get("suhu", "Dingin")
    jumlah = int(s.get("jumlah", 1))
    metode = s.get("metode", "Tunai (Cash)")
    uang = int(s.get("uang", 0))

    if not nama:
        s.flash = ("error", "Nama pembeli / No. Meja wajib diisi!")
        return
    conn = db()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT nama, harga_panas, harga_dingin, stok FROM menu WHERE id = ?", (menu_id,)
    ).fetchone()
    if not row:
        s.flash = ("error", "Menu tidak ditemukan.")
        conn.close()
        return
    nama_menu, h_panas, h_dingin, stok = row
    harga = h_panas if suhu == "Panas" else h_dingin
    if int(harga) <= 0:
        s.flash = ("error", f"{nama_menu} tidak tersedia dalam versi {suhu}.")
        conn.close()
        return
    if stok < jumlah:
        s.flash = ("error", f"Stok tidak mencukupi! Sisa stok: {stok}")
        conn.close()
        return

    total = int(harga) * jumlah
    if metode.startswith("Tunai"):
        if uang < total:
            s.flash = ("error", f"Uang diterima kurang {rupiah(total - uang)}!")
            conn.close()
            return
        kembalian = uang - total
    else:  # QRIS: dibayar pas
        uang, kembalian = total, 0
    cur.execute("UPDATE menu SET stok = stok - ? WHERE id = ?", (jumlah, menu_id))
    cur.execute(
        """INSERT INTO transaksi (nama_pembeli, menu, ukuran, jumlah, total_harga, metode_bayar,
                                 waktu, uang_diterima, kembalian)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (nama, nama_menu, suhu, jumlah, total, metode, now_wib(), uang, kembalian),
    )
    trx_id = cur.lastrowid
    conn.commit()
    conn.close()

    terkirim = kirim_notif(
        s.get("ntfy_topic", ""),
        "Pesanan Baru!",
        f"{nama} pesan {jumlah}x {nama_menu} ({suhu})\nTotal {rupiah(total)} via {metode}",
    )
    s.struk_id = trx_id
    s.flash = (
        "success",
        f"🎉 Pesanan atas nama {nama} berhasil disimpan!"
        + (f" 💵 Kembalian: {rupiah(kembalian)}." if metode.startswith("Tunai") else "")
        + ("  📲 Notifikasi terkirim." if terkirim else f"  (notifikasi HP gagal: {s.get('notif_error', '')})"),
    )
    s.nama = ""
    s.jumlah = 1
    s.uang = 0


def muat_menu():
    conn = db()
    df = pd.read_sql("SELECT * FROM menu ORDER BY id", conn)
    conn.close()
    df["kategori"] = pd.Categorical(df["kategori"], KATEGORI + [k for k in df["kategori"].unique() if k not in KATEGORI], ordered=True)
    return df.sort_values(["kategori", "id"]).reset_index(drop=True)


# ======================================================================
# HALAMAN KASIR
# ======================================================================
def halaman_pos():
    st.subheader("🛒 Katalog & Pemesanan")
    df = muat_menu()
    if df.empty:
        st.warning("Belum ada menu. Tambahkan dulu di halaman 'Kelola Menu'.")
        return

    kategori = ["Semua"] + [k for k in KATEGORI if k in df["kategori"].astype(str).unique()]
    pilih_kat = st.radio("Kategori:", kategori, horizontal=True)
    df_tampil = df if pilih_kat == "Semua" else df[df["kategori"].astype(str) == pilih_kat]

    if "menu_id" not in st.session_state or st.session_state.menu_id not in df["id"].values:
        st.session_state.menu_id = int(df["id"].iloc[0])

    kiri, kanan = st.columns([3, 2], gap="large")

    # ---- Katalog kartu menu ----
    with kiri:
        kolom = 3
        rows = list(df_tampil.itertuples())
        for i in range(0, len(rows), kolom):
            cols = st.columns(kolom)
            for col, m in zip(cols, rows[i : i + kolom]):
                with col, st.container(border=True):
                    st.markdown(foto_html(m, suhu_utama(m)), unsafe_allow_html=True)
                    st.markdown(f'<div class="nm">{m.nama}</div>', unsafe_allow_html=True)
                    st.markdown(chip_harga(m), unsafe_allow_html=True)
                    if m.stok <= 0:
                        badge = '<span class="badge badge-out">Habis</span>'
                    elif m.stok <= 5:
                        badge = f'<span class="badge badge-low">Sisa {m.stok}</span>'
                    else:
                        badge = f'<span class="badge badge-ok">Stok {m.stok}</span>'
                    st.markdown(badge, unsafe_allow_html=True)
                    dipilih = st.session_state.menu_id == m.id
                    st.button(
                        "✅ Dipilih" if dipilih else "Pilih",
                        key=f"pilih_{m.id}",
                        use_container_width=True,
                        type="primary" if dipilih else "secondary",
                        disabled=m.stok <= 0 or (m.harga_panas <= 0 and m.harga_dingin <= 0),
                        on_click=pilih_menu,
                        args=(m.id,),
                    )

    # ---- Panel pesanan ----
    with kanan:
        terpilih = df[df["id"] == st.session_state.menu_id].iloc[0]
        opsi_suhu = [s for s, k in (("Panas", "harga_panas"), ("Dingin", "harga_dingin")) if int(terpilih[k]) > 0]
        if not opsi_suhu:
            st.warning("Menu ini belum punya harga. Atur di 'Kelola Menu'.")
            return
        if st.session_state.get("suhu") not in opsi_suhu:
            st.session_state.suhu = opsi_suhu[0] if len(opsi_suhu) == 1 else "Dingin"
        with st.container(border=True):
            st.markdown("### 📝 Pesanan Baru")
            st.markdown(foto_html(terpilih, st.session_state.suhu, 340), unsafe_allow_html=True)
            st.markdown(f"Menu: **{terpilih['nama']}** · {terpilih['kategori']}")
            st.text_input("Nama Pembeli / No. Meja", key="nama", placeholder="Contoh: Kak Siti / Meja 03")
            c1, c2 = st.columns(2)
            with c1:
                suhu = st.radio(
                    "Pilihan",
                    opsi_suhu,
                    key="suhu",
                    horizontal=True,
                    format_func=lambda s: "🔥 Panas" if s == "Panas" else "❄️ Dingin",
                )
            maks = max(int(terpilih["stok"]), 1)
            c2.number_input("Jumlah", min_value=1, max_value=maks, value=1, key="jumlah")
            metode = st.selectbox("Metode Pembayaran", ["Tunai (Cash)", "QRIS"], key="metode")

            harga = terpilih["harga_panas"] if suhu == "Panas" else terpilih["harga_dingin"]
            total = int(harga) * int(st.session_state.get("jumlah", 1))
            st.info(f"💰 Total Harga: **{rupiah(total)}**")
            if metode.startswith("Tunai"):
                st.number_input("💵 Uang Diterima (Rp)", min_value=0, step=1000, key="uang")
                q = st.columns(4)
                q[0].button("Pas", on_click=set_uang, args=(total,), use_container_width=True)
                q[1].button("20rb", on_click=set_uang, args=(20000,), use_container_width=True)
                q[2].button("50rb", on_click=set_uang, args=(50000,), use_container_width=True)
                q[3].button("100rb", on_click=set_uang, args=(100000,), use_container_width=True)
                uang_now = int(st.session_state.get("uang", 0))
                if uang_now >= total and uang_now > 0:
                    st.success(f"Kembalian: **{rupiah(uang_now - total)}**")
                elif uang_now > 0:
                    st.warning(f"Uang kurang {rupiah(total - uang_now)}")
            st.button(
                "Proses Pembayaran & Cetak Struk",
                type="primary",
                use_container_width=True,
                on_click=proses_pesanan,
            )

            flash = st.session_state.pop("flash", None)
            if flash:
                (st.success if flash[0] == "success" else st.error)(flash[1])

        if st.session_state.get("struk_id"):
            t = get_trx(st.session_state.struk_id)
            if t:
                st.markdown("#### 🧾 Struk Terakhir")
                tampil_struk(t, "terakhir")


# ======================================================================
# HALAMAN MENU DIGITAL (replika menu cetak + galeri)
# ======================================================================
def _tabel_menu(df, judul):
    sub = df[df["kategori"].astype(str) == judul]
    baris = "".join(
        f'<div class="mrow"><span>• {r.nama}</span><span>{angka_menu(r.harga_panas)}</span>'
        f'<span>{angka_menu(r.harga_dingin)}</span></div>'
        for r in sub.itertuples()
    )
    return (
        f'<div class="panel"><div><div class="mhead"><span>{judul}</span><span>Panas</span><span>Dingin</span></div>'
        f'{baris}</div></div>'
    )


def html_lembar_menu(df):
    kiri = _tabel_menu(df, "Kopi Susu") + _tabel_menu(df, "Kopi Hitam")
    kanan = _tabel_menu(df, "Bukan Kopi")
    extra = [k for k in df["kategori"].astype(str).unique() if k not in KATEGORI]
    kanan += "".join(_tabel_menu(df, k) for k in extra)
    return (
        '<div class="lembar"><div class="lembar-top"></div><div class="lembar-in">'
        f'<div class="ljudul"><div class="big">Menu</div><div class="al">Shelter Kopi {ALAMAT}</div></div>'
        '<div class="lgrid">'
        f'<div style="display:flex;flex-direction:column;gap:14px">{kiri}</div>'
        f'<div style="display:flex;flex-direction:column;gap:14px"><div class="lpill">Buka {JAM_BUKA}</div>{kanan}</div>'
        '</div>'
        f'<div class="lfoot"><div class="ig">{HANDLE}</div>{LOGO}</div>'
        '</div></div>'
        '<div class="catatan">Harga dalam ribuan rupiah (13 = Rp 13.000)</div>'
    )


def halaman_menu_digital():
    st.subheader("📋 Menu Digital")
    df = muat_menu()
    tab1, tab2 = st.tabs(["📋 Lembar Menu", "🖼️ Galeri Foto"])
    with tab1:
        st.markdown(html_lembar_menu(df), unsafe_allow_html=True)
    with tab2:
        suhu = st.radio(
            "Tampilkan versi:", ["Dingin", "Panas"], horizontal=True, key="galeri_suhu",
            format_func=lambda s: "🔥 Panas" if s == "Panas" else "❄️ Dingin",
        )
        kol = "harga_panas" if suhu == "Panas" else "harga_dingin"
        sub = df[df[kol] > 0]
        rows = list(sub.itertuples())
        for i in range(0, len(rows), 3):
            cols = st.columns(3)
            for col, m in zip(cols, rows[i : i + 3]):
                with col, st.container(border=True):
                    st.markdown(foto_html(m, suhu), unsafe_allow_html=True)
                    st.markdown(f'<div class="nm">{m.nama}</div>', unsafe_allow_html=True)
                    st.markdown(f'<span class="chip">{rupiah(getattr(m, kol))}</span>', unsafe_allow_html=True)


# ======================================================================
# KELOLA MENU
# ======================================================================
def halaman_kelola_menu():
    st.subheader("📦 Kelola Menu Minuman")
    with st.form("tambah_menu_form", clear_on_submit=True):
        st.markdown("##### ➕ Tambah Menu Baru")
        c1, c2 = st.columns(2)
        nama_menu = c1.text_input("Nama Menu")
        kategori = c2.selectbox("Kategori", KATEGORI)
        c3, c4, c5 = st.columns(3)
        h_panas = c3.number_input("Harga Panas (Rp)", min_value=0, step=500, help="Isi 0 jika tidak ada versi panas")
        h_dingin = c4.number_input("Harga Dingin (Rp)", min_value=0, step=500, help="Isi 0 jika tidak ada versi dingin")
        stok = c5.number_input("Stok Awal", min_value=0, value=STOK_AWAL)
        up = st.file_uploader("Foto asli (opsional, JPG/PNG)", type=["jpg", "jpeg", "png", "webp"])
        img_url = st.text_input("atau URL Gambar (opsional)", placeholder="https://...")
        if st.form_submit_button("Simpan Menu Baru", type="primary"):
            if not nama_menu.strip():
                st.error("Nama menu wajib diisi.")
            elif h_panas <= 0 and h_dingin <= 0:
                st.error("Isi minimal satu harga (panas atau dingin).")
            else:
                gambar = file_ke_uri(up) if up else img_url.strip()
                conn = db()
                conn.execute(
                    "INSERT INTO menu (nama, kategori, harga_panas, harga_dingin, stok, gambar) VALUES (?,?,?,?,?,?)",
                    (nama_menu.strip(), kategori, int(h_panas), int(h_dingin), int(stok), gambar),
                )
                conn.commit()
                conn.close()
                st.success(f"Menu '{nama_menu}' berhasil ditambahkan!")
                st.rerun()

    df = muat_menu()
    st.markdown("---")
    st.markdown("##### 📋 Daftar Menu Saat Ini")
    tabel = df.drop(columns=["gambar"]).rename(
        columns={"nama": "Menu", "kategori": "Kategori", "harga_panas": "Panas", "harga_dingin": "Dingin", "stok": "Stok"}
    )
    st.dataframe(tabel, use_container_width=True, hide_index=True)

    if df.empty:
        return
    st.markdown("##### 🔧 Ubah Menu")
    opsi = {f"{r.nama} (stok {r.stok})": int(r.id) for r in df.itertuples()}
    label = st.selectbox("Pilih menu", list(opsi.keys()))
    mid = opsi[label]
    row = df[df["id"] == mid].iloc[0]

    c1, c2, c3 = st.columns([2, 1, 1])
    tambah = c1.number_input("Tambah stok sebanyak", min_value=1, value=10, key="tambah_stok")
    if c2.button("➕ Tambah Stok", use_container_width=True):
        conn = db()
        conn.execute("UPDATE menu SET stok = stok + ? WHERE id = ?", (int(tambah), mid))
        conn.commit()
        conn.close()
        st.rerun()
    if c3.button("🗑️ Hapus Menu", use_container_width=True):
        conn = db()
        conn.execute("DELETE FROM menu WHERE id = ?", (mid,))
        conn.commit()
        conn.close()
        st.rerun()

    with st.expander("💲 Ubah harga & 📷 ganti foto"):
        e1, e2 = st.columns(2)
        np_ = e1.number_input("Harga Panas (Rp)", min_value=0, step=500, value=int(row["harga_panas"]), key=f"ep_{mid}")
        nd_ = e2.number_input("Harga Dingin (Rp)", min_value=0, step=500, value=int(row["harga_dingin"]), key=f"ed_{mid}")
        up2 = st.file_uploader("Foto baru (JPG/PNG)", type=["jpg", "jpeg", "png", "webp"], key=f"up_{mid}")
        reset_foto = st.checkbox("Kembalikan ke ilustrasi bawaan", key=f"rf_{mid}")
        if st.button("💾 Simpan Perubahan", type="primary", key=f"sv_{mid}"):
            gambar = row["gambar"]
            if reset_foto:
                gambar = ""
            elif up2:
                gambar = file_ke_uri(up2)
            conn = db()
            conn.execute(
                "UPDATE menu SET harga_panas=?, harga_dingin=?, gambar=? WHERE id=?",
                (int(np_), int(nd_), gambar, mid),
            )
            conn.commit()
            conn.close()
            st.toast("Perubahan disimpan", icon="✅")
            st.rerun()


# ======================================================================
# HALAMAN PEMILIK
# ======================================================================
def halaman_owner():
    if not st.session_state.get("owner_ok"):
        st.subheader("🔐 Masuk sebagai Pemilik")
        pin = st.text_input("Masukkan PIN", type="password")
        if st.button("Masuk", type="primary"):
            if pin == OWNER_PIN:
                st.session_state.owner_ok = True
                st.rerun()
            else:
                st.error("PIN salah.")
        return

    st.subheader("📊 Laporan Omset & Riwayat Transaksi")
    conn = db()
    df = pd.read_sql("SELECT * FROM transaksi ORDER BY id DESC", conn)
    conn.close()

    if df.empty:
        st.info("Belum ada data transaksi yang tercatat.")
        if st.sidebar.button("Keluar (Logout Pemilik)", use_container_width=True):
            st.session_state.owner_ok = False
            st.rerun()
        return

    hari_ini = datetime.now(WIB).strftime("%Y-%m-%d")
    df_hari = df[df["waktu"].astype(str).str.startswith(hari_ini)]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Omset", rupiah(df["total_harga"].sum()))
    c2.metric("Omset Hari Ini", rupiah(df_hari["total_harga"].sum()))
    c3.metric("Jumlah Transaksi", f"{len(df)}")
    c4.metric("Gelas Terjual", f"{int(df['jumlah'].sum())}")

    g1, g2, g3 = st.columns(3)
    with g1:
        st.markdown("##### 🏆 Omset per Menu")
        st.bar_chart(df.groupby("menu")["total_harga"].sum())
    with g2:
        st.markdown("##### 🔥❄️ Panas vs Dingin")
        st.bar_chart(df.groupby("ukuran")["jumlah"].sum())
    with g3:
        st.markdown("##### 💳 Metode Pembayaran")
        st.bar_chart(df.groupby("metode_bayar")["total_harga"].sum())

    st.markdown("---")
    st.markdown("##### 📋 Riwayat Transaksi")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("##### 🧾 Lihat Struk / 🗑️ Hapus Pemesan")
    opsi = {
        f"#{int(r.id):05d} · {r.nama_pembeli} · {r.menu} · {rupiah(r.total_harga)}": int(r.id)
        for r in df.itertuples()
    }
    label = st.selectbox("Pilih transaksi", list(opsi.keys()))
    trx_id = opsi[label]
    t = get_trx(trx_id)

    kiri, kanan = st.columns(2, gap="large")
    with kiri:
        tampil_struk(t, f"owner_{trx_id}")
    with kanan:
        with st.container(border=True):
            st.markdown(f"**Hapus pesanan atas nama:** {t['nama_pembeli']}")
            st.caption("Menghapus transaksi akan menghapus nama pemesan, data pesanan, dan struknya.")
            kembalikan = st.checkbox("Kembalikan stok menu", value=True)
            yakin = st.checkbox("Saya yakin ingin menghapus")
            if st.button("🗑️ Hapus Pemesan & Struk", type="primary", disabled=not yakin, use_container_width=True):
                conn = db()
                if kembalikan:
                    conn.execute("UPDATE menu SET stok = stok + ? WHERE nama = ?", (int(t["jumlah"]), t["menu"]))
                conn.execute("DELETE FROM transaksi WHERE id = ?", (trx_id,))
                conn.commit()
                conn.close()
                if st.session_state.get("struk_id") == trx_id:
                    st.session_state.struk_id = None
                st.toast(f"Pesanan {t['nama_pembeli']} dan struknya dihapus", icon="🗑️")
                st.rerun()

    if st.sidebar.button("Keluar (Logout Pemilik)", use_container_width=True):
        st.session_state.owner_ok = False
        st.rerun()


# ======================================================================
# ROUTING
# ======================================================================
if role == "Kasir":
    halaman = st.sidebar.selectbox("Pilih Modul Halaman", ["Kasir & POS", "Menu Digital", "Kelola Menu"])
    if halaman == "Kasir & POS":
        halaman_pos()
    elif halaman == "Menu Digital":
        halaman_menu_digital()
    else:
        halaman_kelola_menu()
else:
    halaman_owner()
