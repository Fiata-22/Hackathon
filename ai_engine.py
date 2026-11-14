# ai_engine.py
from transformers import pipeline
from facenet_pytorch import MTCNN
import numpy as np
import cv2
from PIL import Image
import io

class DeepfakeAI:
    def __init__(self):
        print("Memuat Model A (Deepfake Detector)...")
        self.model_deepfake = pipeline("image-classification", model="prithivMLmods/deepfake-detector-model-v1")
        print("Memuat Model B (AI-Generated Image Detector)...")
        self.model_ai_generated = pipeline("image-classification", model="umm-maybe/AI-image-detector")
        print("Memuat Face Detector (MTCNN)...")
        self.face_detector = MTCNN(keep_all=False, device='cpu')
        print("Semua Model AI dan Face Detector berhasil dimuat!")

    def perform_ela(self, image_path):
        """Fitur 3: Error Level Analysis (Deteksi perbedaan kompresi akibat editan)"""
        try:
            original = cv2.imread(image_path)
            # Kompres ulang gambar dengan kualitas 90%
            cv2.imwrite("temp_ela.jpg", original, [cv2.IMWRITE_JPEG_QUALITY, 90])
            compressed = cv2.imread("temp_ela.jpg")
            
            # Hitung perbedaan (Absolute Difference)
            diff = cv2.absdiff(original, compressed)
            # Perbesar perbedaannya agar terlihat
            diff_scaled = diff * 15 
            
            # Hitung skor keanehan (semakin tinggi perbedaannya, semakin mencurigakan)
            ela_score = np.mean(diff_scaled)
            import os
            os.remove("temp_ela.jpg")
            
            # Normalisasi skor (0-100)
            normalized_score = min(100, (ela_score / 20) * 100) 
            return normalized_score
        except Exception as e:
            print(f"ELA Error: {e}")
            return 0

    def predict(self, image_path):
        # --- FITUR 2: Face Consistency ---
        img = Image.open(image_path).convert('RGB')
        boxes, _ = self.face_detector.detect(img)
        has_face = boxes is not None
        
        # Jalankan AI Gen
        res_ai_gen = self.model_ai_generated(image_path)
        score_ai_gen_fake = 0.0
        for res in res_ai_gen:
            if 'artificial' in res['label'].lower() or 'ai' in res['label'].lower():
                score_ai_gen_fake = res['score']

        # Jalankan AI Deepfake HANYA jika ada wajah
        score_deepfake_fake = 0.0
        if has_face:
            res_deepfake = self.model_deepfake(image_path)
            for res in res_deepfake:
                if 'fake' in res['label'].lower():
                    score_deepfake_fake = res['score']
        
        # --- FITUR 3: ELA Score ---
        ela_score = self.perform_ela(image_path)

        # --- FITUR 1: Total Poin Dosa (Akan diproses lebih lanjut di api.py) ---
        # Di sini kita hanya mengembalikan data mentahnya
        if not has_face:
            verdict_ai = "Gambar Sintetis AI (Tanpa Wajah)"
        else:
            verdict_ai = "Manipulasi Wajah Deepfake" if score_deepfake_fake > score_ai_gen_fake else "Gambar Sintetis AI"

        # Heatmap sederhana
        h, w, _ = cv2.imread(image_path).shape
        heatmap = np.zeros((h, w, 3), dtype=np.uint8)
        cv2.circle(heatmap, (w // 2, h // 2), int(w * 0.2), (0, 0, 255), -1)

        return {
            'has_face': has_face,
            'score_deepfake': round(score_deepfake_fake * 100, 2),
            'score_ai_gen': round(score_ai_gen_fake * 100, 2),
            'ela_score': round(ela_score, 2),
            'ai_verdict': verdict_ai,
            'heatmap': heatmap
        }