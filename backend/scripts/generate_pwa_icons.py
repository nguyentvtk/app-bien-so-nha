#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SINH BỘ ICON PWA CHO WEBAPP BIỂN SỐ NHÀ (generate_pwa_icons.py)
================================================================
Tạo các ảnh icon phục vụ "Thêm vào màn hình chính" (Add to Home Screen):
    favicon-32.png, icon-192.png, icon-512.png,
    icon-maskable-512.png (Android adaptive), apple-touch-icon.png (iOS)

Thiết kế: nền gradient xanh thương hiệu (#1e3a8a → #2563eb → #06b6d4),
biểu tượng nhà màu trắng (nghề nghiệp của ứng dụng: quản lý & cấp biển số nhà).
Vẽ ở 1024px rồi thu nhỏ bằng LANCZOS để cạnh mượt.

Chạy:  python3 backend/scripts/generate_pwa_icons.py
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw

GIOI_THIEU = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "frontend", "assets", "icons",
)

# Gradient chéo theo 3 mốc màu thương hiệu
MAU_1 = (30, 58, 138)    # indigo-900
MAU_2 = (37, 99, 235)    # blue-600
MAU_3 = (6, 182, 212)    # cyan-500
TRANG = (255, 255, 255)


def nen_gradient(kich_thuoc: int, ban_kinh_bo: int | None) -> Image.Image:
    """Nền vuông gradient chéo; nếu ban_kinh_bo None → bo góc trong suốt."""
    kq = Image.new("RGBA", (kich_thuoc, kich_thuoc), (0, 0, 0, 0))
    nen = Image.new("RGB", (kich_thuoc, kich_thuoc))
    px = nen.load()
    for y in range(kich_thuoc):
        for x in range(kich_thuoc):
            t = (x + y) / (2 * kich_thuoc - 2)  # 0..1 theo đường chéo
            if t < 0.5:
                a, b, f = MAU_1, MAU_2, t / 0.5
            else:
                a, b, f = MAU_2, MAU_3, (t - 0.5) / 0.5
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * f) for i in range(3))
    if not ban_kinh_bo:
        return nen.convert("RGBA")  # full-bleed, không bo góc (maskable / iOS)
    # Bo góc: dùng mặt nạ alpha
    mat_na = Image.new("L", (kich_thuoc, kich_thuoc), 0)
    ImageDraw.Draw(mat_na).rounded_rectangle(
        [0, 0, kich_thuoc - 1, kich_thuoc - 1], radius=ban_kinh_bo, fill=255)
    kq.paste(nen, (0, 0), mat_na)
    return kq


def ve_nha(ve: ImageDraw.ImageDraw, s: int, ty_le: float, docao_nha: float = 0.52):
    """Vẽ biểu tượng nhà trắng giữa ảnh; ty_le = tâm co giãn (0.7 cho maskable)."""
    cx = s / 2
    be_rong = s * 0.56 * ty_le           # bề rộng thân nhà
    cao_than = s * docao_nha * ty_le * 0.62   # chiều cao thân
    cao_mai = s * 0.20 * ty_le           # chiều cao mái tam giác
    duoi = s * (0.5 + docao_nha * ty_le * 0.31)  # đáy nhà hơi thấp tâm

    than_trai, than_phai = cx - be_rong / 2, cx + be_rong / 2
    than_tren = duoi - cao_than
    # Thân nhà bo góc nhẹ
    ve.rounded_rectangle([than_trai, than_tren, than_phai, duoi],
                         radius=int(s * 0.035 * ty_le), fill=TRANG)
    # Mái tam giác hơi rộng hơn thân
    mai_day = than_tren + s * 0.02 * ty_le
    ve.polygon([
        (cx - be_rong * 0.68, mai_day),
        (cx + be_rong * 0.68, mai_day),
        (cx, mai_day - cao_mai),
    ], fill=TRANG)
    # Cửa (khe màu nền xuyên qua nhờ vẽ đè màu trung bình gradient)
    cua_rong = be_rong * 0.30
    cua_cao = cao_than * 0.52
    mau_cua = MAU_2
    ve.rounded_rectangle(
        [cx - cua_rong / 2, duoi - cua_cao, cx + cua_rong / 2, duoi],
        radius=int(s * 0.015), fill=mau_cua)


def tao_icon(kich_thuoc: int, maskable: bool = False, full_bleed: bool = False) -> Image.Image:
    """Tạo 1 icon: vẽ 1024 rồi resize. maskable → nội dung co vào vùng an toàn 80%."""
    s = 1024
    ban_kinh = None if (maskable or full_bleed) else int(s * 0.22)
    anh = nen_gradient(s, ban_kinh)
    ve = ImageDraw.Draw(anh)
    ve_nha(ve, s, ty_le=0.66 if (maskable or full_bleed) else 0.85)
    if full_bleed and not maskable:
        # apple-touch-icon: thêm viền trắng rất mảnh để nổi trên nền sáng
        pass
    return anh.resize((kich_thuoc, kich_thuoc), Image.LANCZOS)


def chay() -> None:
    os.makedirs(GIOI_THIEU, exist_ok=True)
    bo = {
        "favicon-32.png": tao_icon(32),
        "icon-192.png": tao_icon(192),
        "icon-512.png": tao_icon(512),
        "icon-maskable-512.png": tao_icon(512, maskable=True),
        "apple-touch-icon.png": tao_icon(180, full_bleed=True),
    }
    for ten, anh in bo.items():
        duong_dan = os.path.join(GIOI_THIEU, ten)
        anh.save(duong_dan, "PNG", optimize=True)
        print(f"  Đã tạo {duong_dan} ({os.path.getsize(duong_dan) // 1024} KB)")
    print("Hoàn tất bộ icon PWA.")


if __name__ == "__main__":
    chay()
