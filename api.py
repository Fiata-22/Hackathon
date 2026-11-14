# api.py
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from report_generator import generate_forensic_report, calculate_sha256
from database import SessionLocal, LaporanForensik, upload_file_ke_storage, s3_client, BUCKET_NAME, User
from ai_engine import DeepfakeAI
from metadata_analyzer import analyze_image_metadata
from auth import get_password_hash, verify_password, create_access_token
import shutil, os, uuid
import numpy as np
import cv2
import io

app = FastAPI(title="VeriFact Vision API")

# Izinkan akses dari Frontend (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inisialisasi Model AI
print("Sedang memuat model AI...")
ai_model = DeepfakeAI()
print("Siap menerima request!")

# --- SETUP AUTH ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- FUNGSI OTOMATIS MEMBUAT ADMIN SAAT SERVER NYALA ---
@app.on_event("startup")
def create_default_admin():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            hashed_pw = get_password_hash("rahasia123")
            new_admin = User(username="admin", hashed_password=hashed_pw, role="Admin")
            db.add(new_admin)
            db.commit()
            print("✅ Akun admin default berhasil dibuat (admin / rahasia123)")
    except Exception as e:
        print(f"❌ Gagal membuat admin default: {e}")
    finally:
        db.close()

# --- ENDPOINT REGISTER & LOGIN ---
@app.post("/register")
async def register_user(username: str, password: str):
    db = SessionLocal()
    user_exists = db.query(User).filter(User.username == username).first()
    if user_exists:
        db.close()
        return JSONResponse({"error": "Username sudah dipakai"}, status_code=400)
    
    new_user = User(username=username, hashed_password=get_password_hash(password))
    db.add(new_user)
    db.commit()
    db.close()
    return {"message": "User berhasil dibuat"}

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    user = db.query(User).filter(User.username == form_data.username).first()
    db.close()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau Password salah",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

# --- ENDPOINT ANALISIS GAMBAR ---
@app.post("/analyze/image")
async def analyze_image(file: UploadFile = File(...)):
    db = SessionLocal()
    tmp_file = f"temp_{uuid.uuid4()}_{file.filename}"
    
    try:
        with open(tmp_file, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        
        file_hash = calculate_sha256(tmp_file)
        
        # ==========================================
        # 1. JALANKAN AI, METADATA, DAN ELA
        # ==========================================
        result = ai_model.predict(tmp_file)
        meta_result = analyze_image_metadata(tmp_file)
        
        # ==========================================
        # 2. SISTEM POIN DOSA (VERSI MEDIA SOSIAL)
        # ==========================================
        skor_dosa = 0
        alasan = []

        # A. CEK AI VISUAL (Hakim Utama - Bobot Terbesar)
        if result['score_ai_gen'] > 80:
            skor_dosa += 80
            alasan.append("Pola Gambar AI Sangat Kuat")
        elif result['score_ai_gen'] > 50:
            skor_dosa += 40
            alasan.append("Pola Gambar AI Terdeteksi")
            
        # Cek Deepfake Wajah (Hanya jika ada wajah)
        if result.get('has_face', False) and result['score_deepfake'] > 70:
            skor_dosa += 70
            alasan.append("Manipulasi Wajah Kuat")

        # B. CEK METADATA (Hanya Poin Tambahan)
        if not meta_result["has_exif"]:
            skor_dosa += 10
            alasan.append("Metadata Hilang (Sosmed/Web)")
        
        if meta_result["is_edited"]:
            skor_dosa += 90
            alasan.append(f"Diedit dgn {meta_result['software_used']}")
            
        if meta_result["has_exif"] and not meta_result["is_edited"]:
            skor_dosa -= 20 # Bonus jika metadata valid
            alasan.append(f"Metadata Valid ({meta_result['camera_make']})")

        # C. CEK ELA (Error Level Analysis)
        if result['ela_score'] > 70:
            skor_dosa += 30
            alasan.append("Anomali Kompresi Tinggi")
            
        # Pastikan skor tidak minus
        skor_dosa = max(0, skor_dosa)

        # ==========================================
        # 3. TENTUKAN KEPUTUSAN AKHIR
        # ==========================================
        if skor_dosa >= 60:
            final_label = "PALSU (AI)"
            final_confidence = min(100.0, skor_dosa + 10)
            final_verdict = " | ".join(alasan)
        elif skor_dosa >= 30:
            final_label = "TIDAK TERVERIFIKASI"
            final_confidence = skor_dosa
            final_verdict = "Wajib Verifikasi: " + " | ".join(alasan)
        else:
            final_label = "ASLI"
            final_confidence = 100 - skor_dosa
            final_verdict = "Tidak ada indikasi manipulasi AI. " + " | ".join(alasan)

        # Update result untuk PDF dan Frontend
        result['label'] = final_label
        result['confidence'] = final_confidence
        result['verdict'] = final_verdict
        result['forensic_note'] = meta_result['warning']
            
        # ==========================================
        # 4. BUAT LAPORAN PDF & UPLOAD STORAGE
        # ==========================================
        file_id = str(uuid.uuid4())
        tmp_pdf = f"Laporan_{file_id}.pdf"
        generate_forensic_report(tmp_file, result['heatmap'], result, tmp_pdf)
        
        pdf_filename = f"{file_id}_laporan.pdf"
        url_asli = upload_file_ke_storage(tmp_file, f"{file_id}_asli.jpg")
        url_pdf = upload_file_ke_storage(tmp_pdf, pdf_filename)
        
        temp_heatmap = f"temp_{file_id}_heatmap.jpg"
        cv2.imwrite(temp_heatmap, cv2.cvtColor(result['heatmap'], cv2.COLOR_RGB2BGR))
        url_heatmap = upload_file_ke_storage(temp_heatmap, f"{file_id}_heatmap.jpg")
        
        # ==========================================
        # 5. SIMPAN KE DATABASE
        # ==========================================
        laporan_baru = LaporanForensik(
            nama_file_asli=file.filename,
            hash_sha256=file_hash,
            label_ai=result['label'],
            confidence=result['confidence'],
            skor_risiko=result['risk_score'] if 'risk_score' in result else skor_dosa,
            url_file_asli=url_asli,
            url_heatmap=url_heatmap,
            url_pdf=url_pdf
        )
        db.add(laporan_baru)
        db.commit()
        db.refresh(laporan_baru)
        
        # ==========================================
        # 6. RETURN RESPONSE KE FRONTEND
        # ==========================================
        response_data = {
            "id_laporan": laporan_baru.id,
            "label": result['label'],
            "confidence": result['confidence'],
            "verdict": result['verdict'],
            "hash_sha256": file_hash,
            "file_url": url_asli,
            "heatmap_url": url_heatmap,
            "pdf_filename": pdf_filename,
            "pdf_url": url_pdf,
            "forensic_note": result['forensic_note'],
            "camera_make": meta_result.get("camera_make", "Tidak diketahui"),
            "score_deepfake": result.get('score_deepfake', 0),
            "score_ai_gen": result.get('score_ai_gen', 0)
        }
        
        # Cleanup file temporary
        os.remove(tmp_file)
        os.remove(tmp_pdf)
        os.remove(temp_heatmap)
        
        return JSONResponse(response_data)
        
    except Exception as e:
        db.rollback()
        if "duplicate key" in str(e):
             return JSONResponse({"error": "Gambar ini sudah pernah dianalisis sebelumnya."}, status_code=400)
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        db.close()

# --- ENDPOINT LAINNYA ---
@app.get("/download-report/{filename}")
async def download_report(filename: str):
    try:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=filename)
        pdf_content = response['Body'].read()
        return StreamingResponse(
            io.BytesIO(pdf_content), 
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        return JSONResponse({"error": f"File tidak ditemukan: {str(e)}"}, status_code=404)

@app.get("/riwayat")
async def get_riwayat():
    db = SessionLocal()
    try:
        riwayat = db.query(LaporanForensik).order_by(LaporanForensik.waktu_dibuat.desc()).all()
        hasil = []
        for r in riwayat:
            hasil.append({
                "id": r.id,
                "nama_file": r.nama_file_asli,
                "label": r.label_ai,
                "confidence": r.confidence,
                "waktu": r.waktu_dibuat.strftime("%Y-%m-%d %H:%M"),
                "pdf_url": r.url_pdf
            })
        return JSONResponse(hasil)
    finally:
        db.close()

@app.get("/statistik")
async def get_statistik():
    db = SessionLocal()
    try:
        total_kasus = db.query(LaporanForensik).count()
        total_palsu = db.query(LaporanForensik).filter(LaporanForensik.label_ai.contains("PALSU")).count()
        total_asli = total_kasus - total_palsu
        return JSONResponse({
            "total_kasus": total_kasus,
            "total_palsu": total_palsu,
            "total_asli": total_asli
        })
    finally:
        db.close()

@app.delete("/riwayat/{laporan_id}")
async def hapus_riwayat(laporan_id: int):
    db = SessionLocal()
    try:
        laporan = db.query(LaporanForensik).filter(LaporanForensik.id == laporan_id).first()
        if not laporan:
            return JSONResponse({"error": "Data tidak ditemukan"}, status_code=404)
        db.delete(laporan)
        db.commit()
        return JSONResponse({"message": "Data berhasil dihapus"})
    finally:
        db.close()