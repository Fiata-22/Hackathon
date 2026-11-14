# detector.py
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np

class DeepfakeDetector(nn.Module):
    """
    Model deteksi deepfake berbasis EfficientNet-B4.
    Output: probabilitas [asli, palsu]
    """
    def __init__(self, pretrained=True):
        super().__init__()
        # Backbone EfficientNet-B4
        self.backbone = models.efficientnet_b4(weights='IMAGENET1K_V1' if pretrained else None)
        
        # Ganti classifier head
        in_features = self.backbone.classifier[1].in_features
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(0.4),
            nn.Linear(in_features, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 2)  # [asli, palsu]
        )
    
    def forward(self, x):
        return self.backbone(x)


# Preprocessing standar
transform = transforms.Compose([
    transforms.Resize((380, 380)),  # ukuran input EfficientNet-B4
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])

def predict_image(model, image_path, device='cpu'):
    """Prediksi satu gambar: return (label, confidence, probabilitas)"""
    model.eval()
    img = Image.open(image_path).convert('RGB')
    tensor = transform(img).unsqueeze(0).to(device)
    
    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)[0]
    
    labels = ['ASLI', 'PALSU (AI)']
    idx = probs.argmax().item()
    return labels[idx], probs[idx].item(), probs.cpu().numpy()