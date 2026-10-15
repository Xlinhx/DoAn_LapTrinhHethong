#!/usr/bin/env python3
"""
scripts/cutout_assets.py
Tách nền trắng phía sau (Background Removal) cho các vật thể 3D minh họa đã sinh,
giữ nguyên các chi tiết sáng bên trong vật thể nhờ thuật toán Border Flood-Fill +
Soft Alpha Feathering, xuất ra file PNG trong suốt (RGBA) dùng cho Slide & Báo cáo.
"""

from collections import deque
from pathlib import Path
from PIL import Image, ImageFilter

ARTIFACT_DIR = Path(r"C:\Users\ADMIN\.gemini\antigravity\brain\7b111724-2f70-48d1-9854-c000c2d46e50")
OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "assets" / "cutouts"

ASSETS = {
    "hero_inode_tree.png": "hero_inode_tree_1792089885428.jpg",
    "dentry_magnifier.png": "dentry_magnifier_1792089900780.jpg",
    "recursion_shield.png": "recursion_shield_1792089915808.jpg",
    "bitmask_decoder.png": "bitmask_decoder_1792089932667.jpg",
}


def remove_white_background_floodfill(img_path: Path, out_path: Path, threshold: int = 240):
    img = Image.open(img_path).convert("RGBA")
    w, h = img.size
    pixels = img.load()

    visited = bytearray(w * h)
    bg_mask = Image.new("L", (w, h), 255)
    mask_px = bg_mask.load()

    def is_bg_color(r: int, g: int, b: int) -> bool:
        # Nhận diện nền trắng hoặc bóng xám rất nhạt quanh viền ngoài
        max_c = max(r, g, b)
        min_c = min(r, g, b)
        chroma = max_c - min_c
        return (min_c >= threshold) or (min_c >= 226 and chroma <= 12)

    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            idx = y * w + x
            if not visited[idx]:
                visited[idx] = 1
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            idx = y * w + x
            if not visited[idx]:
                visited[idx] = 1
                q.append((x, y))

    while q:
        cx, cy = q.popleft()
        r, g, b, _ = pixels[cx, cy]
        if is_bg_color(r, g, b):
            mask_px[cx, cy] = 0
            for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                if 0 <= nx < w and 0 <= ny < h:
                    nidx = ny * w + nx
                    if not visited[nidx]:
                        visited[nidx] = 1
                        q.append((nx, ny))

    # Làm mượt biên cắt (Anti-alias feathering) để viền vật thể mịn màng trên nền slide
    smooth_alpha = bg_mask.filter(ImageFilter.GaussianBlur(radius=1.2))
    img.putalpha(smooth_alpha)

    # Cắt gọn khung (Auto-crop) quanh vật thể với lề 16px
    bbox = smooth_alpha.getbbox()
    if bbox:
        pad = 16
        left = max(0, bbox[0] - pad)
        top = max(0, bbox[1] - pad)
        right = min(w, bbox[2] + pad)
        bottom = min(h, bbox[3] + pad)
        img = img.crop((left, top, right, bottom))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", optimize=True)
    print(f"[OK] Cutout saved: {out_path} ({img.size[0]}x{img.size[1]} RGBA)")


def main():
    for out_name, src_name in ASSETS.items():
        src_path = ARTIFACT_DIR / src_name
        out_path = OUT_DIR / out_name
        remove_white_background_floodfill(src_path, out_path)


if __name__ == "__main__":
    main()
