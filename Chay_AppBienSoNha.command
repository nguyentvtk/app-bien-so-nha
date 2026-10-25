#!/bin/bash
# ============================================================
#  BỘ KHỞI ĐỘNG TỰ ĐỘNG — HỆ THỐNG QUẢN LÝ VÀ CẤP BIỂN SỐ NHÀ
#  UBND XÃ TÂN PHÚ — TỈNH TÂY NINH  |  Bản macOS
#  Tính năng: tự tạo/kích hoạt môi trường ảo — chạy FastAPI trên
#  0.0.0.0:8000 — lấy IP mạng LAN — tự mở trình duyệt.
# ============================================================
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/backend"

echo "=========================================================="
echo "   KHỞI ĐỘNG HỆ THỐNG QUẢN LÝ VÀ CẤP BIỂN SỐ NHÀ"
echo "   UBND XÃ TÂN PHÚ — TỈNH TÂY NINH"
echo "=========================================================="
echo

# ---------- (a) KÍCH HOẠT MÔI TRƯỜNG ẢO ----------
if [ -f "venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "venv/bin/activate"
    echo "[OK] Đã kích hoạt môi trường ảo: venv"
elif [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
    echo "[OK] Đã kích hoạt môi trường ảo: .venv"
else
    echo "[!] Chưa có môi trường ảo — bắt đầu tự động tạo lần đầu chạy."
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[LỖI] Máy chưa cài Python 3. Hãy cài qua App Store hoặc https://www.python.org"
        read -r -p "Nhấn phím bất kỳ để đóng..." _
        exit 1
    fi
    python3 -m venv venv
    # shellcheck disable=SC1091
    source "venv/bin/activate"
    echo "[..] Đang cài đặt thư viện cần thiết — lần đầu có thể mất vài phút..."
    python3 -m pip install --quiet --upgrade pip
    python3 -m pip install --quiet -r requirements.txt || {
        echo "[LỖI] Cài đặt thư viện thất bại — hãy kiểm tra kết nối Internet rồi chạy lại."
        read -r -p "Nhấn phím bất kỳ để đóng..." _
        exit 1
    }
    echo "[OK] Đã tạo xong môi trường ảo và cài đặt thư viện."
fi
echo "[OK] Môi trường Python đã sẵn sàng: $(python3 --version 2>&1)"
echo

# ---------- (b) LẤY ĐỊA CHỈ IP NỘI BỘ TRONG MẠNG LAN ----------
LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
if [ -z "$LAN_IP" ]; then
    LAN_IP="127.0.0.1"
    echo "[!] Không xác định được địa chỉ IP mạng LAN — hiện chỉ truy cập được trên chính máy này."
    echo
fi

# ---------- HIỂN THỊ ĐƯỜNG LINK TRUY CẬP ----------
echo "----------------------------------------------------------"
echo "  ĐƯỜNG LINK TRUY CẬP HỆ THỐNG"
echo "----------------------------------------------------------"
echo "  Trên chính máy này — khuyến nghị dùng:"
echo "      http://127.0.0.1:8000"
echo
if [ "$LAN_IP" != "127.0.0.1" ]; then
    echo "  Trên điện thoại / máy tính khác trong CÙNG mạng Wi-Fi / LAN:"
    echo "      http://${LAN_IP}:8000"
    echo
    echo "  Tài liệu API dành cho cán bộ kỹ thuật:"
    echo "      http://${LAN_IP}:8000/docs"
fi
echo
echo "----------------------------------------------------------"
echo "  Máy chủ FastAPI sẽ chạy tại 0.0.0.0 cổng 8000"
echo "  — mọi thiết bị trong mạng nội bộ đều truy cập được."
echo "----------------------------------------------------------"
echo

# ---------- (c) TỰ ĐỘNG MỞ TRÌNH DUYỆT TỚI GIAO DIỆN CHÍNH ----------
echo "[OK] Trình duyệt sẽ tự động mở sau 3 giây tới giao diện hệ thống..."
( sleep 3 && open "http://127.0.0.1:8000" ) &

# ---------- KHỞI CHẠY FASTAPI HOST 0.0.0.0 PORT 8000 ----------
echo "[..] Đang khởi động máy chủ — nhấn tổ hợp phím Ctrl+C để dừng."
echo
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo
echo "[!] Máy chủ đã dừng hoạt động."
read -r -p "Nhấn phím bất kỳ để đóng..." _
