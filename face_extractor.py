# face_extractor.py
from facenet_pytorch import MTCNN
import cv2
import numpy as np

class FaceExtractor:
    """Deteksi & crop wajah dari gambar/video menggunakan MTCNN"""
    def __init__(self, device='cpu'):
        self.mtcnn = MTCNN(
            keep_all=False,
            margin=20,
            min_face_size=80,
            device=device
        )
    
    def extract_from_image(self, image_path):
        img = cv2.imread(image_path)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        boxes, probs = self.mtcnn.detect(img_rgb)
        if boxes is None:
            return None
        
        # Ambil wajah dengan confidence tertinggi
        best_idx = np.argmax(probs)
        x1, y1, x2, y2 = [int(v) for v in boxes[best_idx]]
        face = img_rgb[max(0,y1):y2, max(0,x1):x2]
        return face
    
    def extract_from_video(self, video_path, max_frames=30):
        """Ambil sampel frame dari video"""
        cap = cv2.VideoCapture(video_path)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        step = max(1, total // max_frames)
        
        faces = []
        for i in range(0, total, step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if not ret:
                break
            
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            boxes, probs = self.mtcnn.detect(rgb)
            if boxes is not None:
                x1, y1, x2, y2 = [int(v) for v in boxes[0]]
                faces.append({
                    'frame_idx': i,
                    'face': rgb[max(0,y1):y2, max(0,x1):x2],
                    'bbox': (x1, y1, x2, y2)
                })
        
        cap.release()
        return faces