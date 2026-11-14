# temporal_analyzer.py
import torch
import torch.nn as nn
import numpy as np
from PIL import Image
from torchvision import transforms

class TemporalLSTM(nn.Module):
    """
    Deteksi inkonsistensi antar-frame menggunakan Bi-GRU.
    Input: sequence of feature vectors dari tiap frame
    """
    def __init__(self, feature_dim=512, hidden_dim=256, num_layers=2):
        super().__init__()
        self.gru = nn.GRU(
            input_size=feature_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=0.3
        )
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim * 2, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 2)
        )
    
    def forward(self, x):
        # x: (batch, seq_len, feature_dim)
        out, _ = self.gru(x)
        # Ambil representasi terakhir (gabungan forward+backward)
        last = out[:, -1, :]
        return self.classifier(last)


def temporal_consistency_check(faces_list, model, backbone, device='cpu'):
    """
    Ekstrak fitur tiap frame, lalu analisis konsistensi temporalnya.
    Nilai tinggi = inkonsisten = mencurigakan.
    """
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225]),
    ])
    features = []
    for item in faces_list:
        face_img = Image.fromarray(item['face'])
        tensor = transform(face_img).unsqueeze(0).to(device)
        with torch.no_grad():
            feat = backbone.backbone.features(tensor)
            feat = backbone.backbone.avgpool(feat).flatten(1)
            features.append(feat.cpu().numpy())
    
    if len(features) < 2:
        return 0.0
    
    features = np.vstack(features)
    # Hitung variance antar frame (indikator ketidakstabilan)
    var = np.mean(np.var(features, axis=0))
    return float(var)