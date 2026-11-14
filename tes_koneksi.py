# tes_koneksi.py
import sys
try:
    from database import SessionLocal, engine, setup_storage, BUCKET_NAME
    from sqlalchemy import text
    print("1. Berhasil meng-import modul database...")
except Exception as e:
    print(f"❌ Gagal meng-import database.py: {e}")
    sys.exit()

print("2. Menguji koneksi ke PostgreSQL (Docker)...")
try:
    db = SessionLocal()
    db.execute(text("SELECT 1"))
    db.close()
    print("✅ KONEKSI POSTGRESQL BERHASIL! (Python <-> Docker DB)")
except Exception as e:
    print(f"❌ KONEKSI POSTGRESQL GAGAL: {e}")

print("3. Menguji koneksi ke Object Storage (LocalStack)...")
try:
    setup_storage()
    print(f"✅ KONEKSI STORAGE BERHASIL! (Bucket '{BUCKET_NAME}' siap)")
except Exception as e:
    print(f"❌ KONEKSI STORAGE GAGAL: {e}")

print("\nSelesai!")