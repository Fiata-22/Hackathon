# report_generator.py
import os
import hashlib
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Frame
import cv2
import numpy as np

def calculate_sha256(file_path):
    """Menghitung Hash SHA-256 untuk membuktikan keaslian file yang diuji"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def generate_forensic_report(original_image_path, heatmap_array, result_data, output_pdf_path):
    """
    Membuat laporan PDF forensik lengkap dengan desain profesional.
    """
    # 1. Hitung Hash File
    file_hash = calculate_sha256(original_image_path)
    timestamp = datetime.now().strftime("%d %B %Y, %H:%M:%S WIB")
    
    # 2. Simpan heatmap sementara ke disk
    temp_heatmap_path = "temp_heatmap.jpg"
    cv2.imwrite(temp_heatmap_path, cv2.cvtColor(heatmap_array, cv2.COLOR_RGB2BGR))
    
    # 3. Setup Canvas PDF (Ukuran A4)
    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    width, height = A4

        # --- WATERMARK RAHASIA ---
    c.saveState()
    c.setFont("Helvetica-Bold", 60)
    c.setFillColor(colors.Color(0.8, 0.8, 0.8, alpha=0.3)) # Warna abu-abu transparan
    c.translate(width / 2, height / 2)
    c.rotate(45)
    c.drawCentredString(0, 0, "RAHASIA")
    c.restoreState()
    # -------------------------
    
    # --- KOP SURAT / HEADER ---
    # Kotak Biru di atas
    c.setFillColor(colors.HexColor("#1e3a8a")) # Warna Biru Gelap (Tailwind blue-900)
    c.rect(0, height - 100, width, 100, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(40, height - 50, "LAPORAN FORENSIK DIGITAL")
    
    c.setFont("Helvetica", 11)
    c.drawString(40, height - 70, "Sistem: VeriFact Vision // DeepGuard-XAI Engine")
    c.drawString(40, height - 85, f"Waktu Cetak: {timestamp}")
    
    # --- 1. INFORMASI BUKTI ---
    c.setFillColor(colors.HexColor("#0f172a")) # Warna Teks Gelap
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, height - 130, "1. Informasi Bukti (Chain of Custody)")
    
    c.setFont("Helvetica", 11)
    c.drawString(40, height - 150, f"Nama File Asli : {os.path.basename(original_image_path)}")
    
    # Kotak untuk Hash
    c.setFillColor(colors.HexColor("#f1f5f9")) # Latar abu-abu terang
    c.rect(40, height - 190, width - 80, 30, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Courier-Bold", 9)
    c.drawString(45, height - 180, f"SHA-256 HASH: {file_hash}")
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(45, height - 168, "Hash ini menjamin file tidak dimodifikasi sejak diunggah.")

    # --- 2. HASIL ANALISIS AI ---
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, height - 230, "2. Hasil Analisis Kecerdasan Buatan (Ensemble AI)")
    
    # Label hasil
    label = result_data.get('label', 'Unknown')
    confidence = result_data.get('confidence', 0)
    risk_score = result_data.get('risk_score', 0)
    verdict = result_data.get('verdict', '')
    
    # Warna dinamis untuk label (Merah jika PALSU, Hijau jika ASLI)
    if "PALSU" in label:
        c.setFillColor(colors.HexColor("#dc2626")) # Merah
    else:
        c.setFillColor(colors.HexColor("#16a34a")) # Hijau
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 255, f"KESIMPULAN: {label} (Confidence: {confidence}%)")
    
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica", 11)
    c.drawString(40, height - 275, f"Skor Risiko : {risk_score}/100")
    c.drawString(40, height - 290, f"Keterangan  : {verdict}")
    
    # Skor Masing-masing Model
    score_deepfake = result_data.get('score_deepfake', 0)
    score_ai_gen = result_data.get('score_ai_gen', 0)
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(40, height - 310, f"* Detail Skor: Model Deepfake (Wajah) = {score_deepfake}% | Model AI Generator = {score_ai_gen}%")

    # --- 3. VISUALISASI BUKTI ---
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, height - 350, "3. Visualisasi Bukti Manipulasi (XAI)")
    
    # Gambar Asli (Kiri)
    try:
        img_original = ImageReader(original_image_path)
        c.drawImage(img_original, 40, height - 550, width=230, height=180, preserveAspectRatio=True, anchor='c')
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.HexColor("#475569"))
        c.drawCentredString(155, height - 565, "Gambar Asli yang Diuji")
    except Exception:
        pass
        
    # Gambar Heatmap (Kanan)
    try:
        img_heatmap = ImageReader(temp_heatmap_path)
        c.drawImage(img_heatmap, 310, height - 550, width=230, height=180, preserveAspectRatio=True, anchor='c')
        c.setFont("Helvetica", 10)
        c.drawCentredString(425, height - 565, "Deteksi Area Manipulasi (Heatmap)")
    except Exception:
        pass

    # --- 4. PERINGATAN METADATA (Jika ada) ---
    forensic_note = result_data.get('forensic_note', '')
    if forensic_note and forensic_note != "Metadata valid.":
        c.setFillColor(colors.HexColor("#fef3c7")) # Latar kuning
        c.rect(40, height - 640, width - 80, 50, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#b45309")) # Teks kuning gelap
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, height - 610, "CATATAN FORENSIK METADATA:")
        c.setFont("Helvetica", 10)
        
        # Gunakan Paragraph agar teks panjang otomatis turun ke bawah
        styles = getSampleStyleSheet()
        style = ParagraphStyle('normal', parent=styles['Normal'], textColor=colors.HexColor("#92400e"), fontSize=9)
        p = Paragraph(forensic_note, style)
        p.wrapOn(c, width - 100, 50)
        p.drawOn(c, 50, height - 635)

    # --- FOOTER (DISCLAIMER) ---
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.line(40, 70, width - 40, 70)
    
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(40, 55, "DISCLAIMER: Laporan ini dihasilkan secara otomatis oleh sistem VeriFact Vision (AI).")
    c.drawString(40, 45, "Hasil analisis bersifat probabilitas dan TIDAK DAPAT dijadikan satu-satunya alat bukti mutlak.")
    c.drawString(40, 35, "Wajib divalidasi oleh Analis Forensik Digital Manusia sebelum digunakan dalam proses hukum.")
    
    # Simpan PDF
    c.save()
    
    # Hapus file heatmap sementara
    if os.path.exists(temp_heatmap_path):
        os.remove(temp_heatmap_path)
        
    return output_pdf_path
