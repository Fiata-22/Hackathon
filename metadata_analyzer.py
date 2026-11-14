# metadata_analyzer.py
from PIL import Image
from PIL.ExifTags import TAGS
import os

def analyze_image_metadata(image_path):
    metadata_info = {
        "has_exif": False,
        "camera_make": "Tidak diketahui",
        "is_compressed": False,
        "is_edited": False,
        "software_used": "Tidak ada",
        "metadata_score": 0, 
        "warning": "Metadata valid."
    }
    
    try:
        file_size_kb = os.path.getsize(image_path) / 1024
        if file_size_kb < 100:
            metadata_info["is_compressed"] = True
            metadata_info["metadata_score"] += 20 

        image = Image.open(image_path)
        exifdata = image.getexif()
        
        if not exifdata:
            metadata_info["has_exif"] = False
            metadata_info["metadata_score"] += 50 
            metadata_info["warning"] = "Metadata EXIF tidak ditemukan (Kemungkinan Screenshot/WhatsApp/Web)."
            return metadata_info
            
        metadata_info["has_exif"] = True
        
        for tag_id, value in exifdata.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "Make":
                metadata_info["camera_make"] = str(value)
            elif tag == "Software":
                metadata_info["software_used"] = str(value)
                if any(sw in str(value).lower() for sw in ["photoshop", "canva", "lightroom", "snapseed", "picsart"]):
                    metadata_info["is_edited"] = True
                    metadata_info["metadata_score"] += 80
                    metadata_info["warning"] = f"Gambar terindikasi diedit menggunakan software: {value}"
                elif any(ai in str(value).lower() for ai in ["midjourney", "dall-e", "stable diffusion"]):
                    metadata_info["is_edited"] = True
                    metadata_info["metadata_score"] += 100
                    metadata_info["warning"] = f"Gambar dihasilkan oleh AI: {value}"
                     
        return metadata_info
    except Exception as e:
        metadata_info["warning"] = f"Error membaca metadata: {str(e)}"
        return metadata_info