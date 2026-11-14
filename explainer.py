# explainer.py
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.image import show_cam_on_image
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
import numpy as np
from PIL import Image

def generate_heatmap(model, image_tensor, target_class=1):
    """
    Menghasilkan heatmap area yang dianggap palsu oleh model.
    target_class: 0=asli, 1=palsu
    """
    # Target layer terakhir di feature extractor
    target_layers = [model.backbone.features[-1]]
    
    cam = GradCAM(model=model, target_layers=target_layers)
    targets = [ClassifierOutputTarget(target_class)]
    
    grayscale_cam = cam(input_tensor=image_tensor, targets=targets)[0]
    
    # Overlay dengan gambar asli
    rgb_img = image_tensor[0].cpu().numpy().transpose(1, 2, 0)
    rgb_img = (rgb_img - rgb_img.min()) / (rgb_img.max() - rgb_img.min())
    visualization = show_cam_on_image(rgb_img, grayscale_cam, use_rgb=True)
    
    return visualization  # array HxWx3