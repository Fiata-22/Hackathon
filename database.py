# database.py
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import boto3
from botocore.client import Config

# ==========================================
# 1. SETUP DATABASE POSTGRESQL
# ==========================================
DATABASE_URL = "postgresql+psycopg2://verifact_admin:rahasia_negara@localhost:5432/verifact_forensic"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Tabel Laporan Forensik
class LaporanForensik(Base):
    __tablename__ = "laporan_forensik"

    id = Column(Integer, primary_key=True, index=True)
    nama_file_asli = Column(String, index=True)
    hash_sha256 = Column(String, unique=True, index=True)
    label_ai = Column(String)
    confidence = Column(Float)
    skor_risiko = Column(Float)
    
    url_file_asli = Column(String)
    url_heatmap = Column(String)
    url_pdf = Column(String)
    
    waktu_dibuat = Column(DateTime, default=datetime.utcnow)

# Tabel User (Penyidik/Admin)
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="Penyidik")

# Membuat semua tabel
Base.metadata.create_all(bind=engine)

# ==========================================
# 2. SETUP OBJECT STORAGE (LocalStack S3)
# ==========================================
s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:4566',
    aws_access_key_id='test', 
    aws_secret_access_key='test',
    region_name='us-east-1',
    config=Config(signature_version='s3v4')
)

BUCKET_NAME = "verifact-bukti"

def setup_storage():
    try:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
    except:
        s3_client.create_bucket(Bucket=BUCKET_NAME)
        print(f"Bucket '{BUCKET_NAME}' berhasil dibuat.")

setup_storage()

def upload_file_ke_storage(file_path, nama_di_storage):
    s3_client.upload_file(file_path, BUCKET_NAME, nama_di_storage)
    return f"http://localhost:4566/{BUCKET_NAME}/{nama_di_storage}"