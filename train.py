# train.py
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets
from detector import DeepfakeDetector, transform

def train_model(data_dir, epochs=10, batch_size=16, lr=1e-4):
    """
    Struktur folder:
    data_dir/
      ├── train/
      │    ├── asli/     (gambar asli)
      │    └── palsu/    (gambar deepfake)
      └── val/
           ├── asli/
           └── palsu/
    """
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    train_ds = datasets.ImageFolder(f'{data_dir}/train', transform=transform)
    val_ds = datasets.ImageFolder(f'{data_dir}/val', transform=transform)
    
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=4)
    val_loader = DataLoader(val_ds, batch_size=batch_size, num_workers=4)
    
    model = DeepfakeDetector(pretrained=True).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    
    for epoch in range(epochs):
        model.train()
        train_loss, correct, total = 0, 0, 0
        
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            out = model(imgs)
            loss = criterion(out, labels)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            correct += (out.argmax(1) == labels).sum().item()
            total += labels.size(0)
        
        # Validasi
        model.eval()
        val_correct, val_total = 0, 0
        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs, labels = imgs.to(device), labels.to(device)
                out = model(imgs)
                val_correct += (out.argmax(1) == labels).sum().item()
                val_total += labels.size(0)
        
        print(f"Epoch {epoch+1}/{epochs} | "
              f"Train Loss: {train_loss/len(train_loader):.4f} | "
              f"Train Acc: {100*correct/total:.2f}% | "
              f"Val Acc: {100*val_correct/val_total:.2f}%")
        
        scheduler.step()
    
    torch.save(model.state_dict(), 'weights/model.pth')
    print("Model disimpan di weights/model.pth")

if __name__ == '__main__':
    train_model('dataset/')