"""
ĐIỂM VÀO TRIỂN KHAI VERCEL (backend/main.py)
=============================================

File này tồn tại để thoả mãn cấu hình `builds` trong vercel.json:
runtime `@vercel/python` trỏ tới `backend/main.py` và tự động nhận diện
biến toàn cục `app` (thể hiện FastAPI/ASGI) làm entry point.

Ứng dụng thật nằm ở `backend/app/main.py` (app = FastAPI(...)).
File này chỉ làm 2 việc trước khi nhúng app:

1. Chuyển thư mục dữ liệu sang /tmp khi chạy trên Vercel — filesystem của
   serverless function là CHỈ ĐỌC trừ /tmp, nên SQLite (sonha.db,
   sonha_database.db) và PDF chứng nhận phải ghi vào /tmp.
2. Sao chép tệp CSDL gốc đi kèm bộ triển khai (includeFiles trong
   vercel.json) vào /tmp làm dữ liệu hạt giống — bản deploy hiển thị ngay
   7.409 hồ sơ hộ dân/thửa đất; dữ liệu ghi thêm là tạm thời theo vòng đời
   lambda (muốn dữ liệu bền vững cần chuyển sang CSDL đám mây).

Chạy local vẫn dùng backend/run.py hoặc Chay_AppBienSoNha như cũ.
"""

import os
import sys

# Đảm bảo package `app` nằm trong đường dẫn import (mô phỏng run.py)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Trên Vercel: filesystem chỉ ghi được trong /tmp
if os.environ.get("VERCEL"):
    data_dir = os.environ.setdefault("SONHA_DATA_DIR", "/tmp/sonha_data")
    os.makedirs(data_dir, exist_ok=True)

    # Sao chép CSDL hạt giống đi kèm bundle vào /tmp (chỉ lần đầu của mỗi lambda)
    nguon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    if os.path.isdir(nguon):
        import shutil
        for tep in os.listdir(nguon):
            if tep.endswith(".db"):
                dich = os.path.join(data_dir, tep)
                if not os.path.exists(dich):
                    try:
                        shutil.copy2(os.path.join(nguon, tep), dich)
                    except OSError:
                        pass  # không có hạt giống → hệ thống tự tạo CSDL rỗng

# Entry point ASGI cho Vercel: app = FastAPI() từ backend/app/main.py
from app.main import app  # noqa: E402,F401
