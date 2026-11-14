# pipeline.py
import torch
from detector import DeepfakeDetector, predict_image
from face_extractor import FaceExtractor
from explainer import generate_heatmap
from temporal_analyzer import temporal_consistency_check
import numpy as np

class ForensicPipeline:
    def __init__(self, model_path=None, device='cpu'):
        self.device = device
        self.model = DeepfakeDetector(pretrained=False).to(device)
        
        if model_path:
            self.model.load_state_dict(torch.load(model_path, map_location=device))
        self.model.eval()
        
        self.face_extractor = FaceExtractor(device=device)
    
    def analyze_image(self, image_path):
        """Analisis lengkap satu gambar"""
        # 1. Ekstrak wajah
        face = self.face_extractor.extract_from_image(image_path)
        if face is None:
            return {'error': 'Wajah tidak terdeteksi'}
        
        # 2. Preprocess
        from PIL import Image
        from detector import transform
        face_img = Image.fromarray(face)
        tensor = transform(face_img).unsqueeze(0).to(self.device)
        
        # 3. Klasifikasi
        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
        
        label = 'PALSU' if probs[1] > probs[0] else 'ASLI'
        confidence = float(max(probs))
        
        # 4. Generate heatmap penjelasan
        heatmap = generate_heatmap(self.model, tensor, target_class=1)
        
        # 5. Skor risiko
        risk_score = self._compute_risk(probs[1], confidence)
        
        return {
            'label': label,
            'confidence': round(confidence * 100, 2),
            'probabilities': {
                'asli': round(float(probs[0]) * 100, 2),
                'palsu': round(float(probs[1]) * 100, 2)
            },
            'risk_score': risk_score,
            'heatmap': heatmap,  # array untuk disimpan/ditampilkan
            'verdict': self._verdict(probs[1])
        }
    
    def analyze_video(self, video_path):
        """Analisis video dengan temporal consistency"""
        faces = self.face_extractor.extract_from_video(video_path, max_frames=20)
        if not faces:
            return {'error': 'Tidak ada wajah terdeteksi di video'}
        
        # Analisis per-frame
        per_frame_scores = []
        from PIL import Image
        from detector import transform
        
        for item in faces:
            face_img = Image.fromarray(item['face'])
            tensor = transform(face_img).unsqueeze(0).to(self.device)
            with torch.no_grad():
                probs = torch.softmax(self.model(tensor), dim=1)[0].cpu().numpy()
            per_frame_scores.append(float(probs[1]))
        
        avg_fake_prob = float(np.mean(per_frame_scores))
        consistency = temporal_consistency_check(faces, self.model, self.model, self.device)
        
        return {
            'frames_analyzed': len(faces),
            'avg_fake_probability': round(avg_fake_prob * 100, 2),
            'temporal_inconsistency': round(consistency, 4),
            'label': 'PALSU' if avg_fake_prob > 0.5 else 'ASLI',
            'verdict': self._verdict(avg_fake_prob)
        }
    
    @staticmethod
    def _compute_risk(fake_prob, confidence):
        """Skor risiko sederhana 0-100"""
        return round((fake_prob * 0.7 + confidence * 0.3) * 100, 2)
    
    @staticmethod
    def _verdict(fake_prob):
        if fake_prob > 0.85:
            return 'SANGAT TINGGI — indikasi kuat deepfake'
        elif fake_prob > 0.65:
            return 'TINGGI — kemungkinan besar dimanipulasi'
        elif fake_prob > 0.5:
            return 'SEDANG — perlu verifikasi manual'
        elif fake_prob > 0.3:
            return 'RENDAH — kemungkinan asli'
        return 'SANGAT RENDAH — hampir pasti asli'


# ===== Contoh Penggunaan =====
if __name__ == '__main__':
    pipeline = ForensicPipeline(model_path=None, device='cpu')
    
    # Analisis gambar
    result = pipeline.analyze_image('test.jpg')
    print(f"Label     : {result['label']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"Risiko    : {result['risk_score']}/100")
    print(f"Verdict   : {result['verdict']}")