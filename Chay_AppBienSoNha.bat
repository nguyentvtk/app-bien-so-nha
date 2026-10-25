@echo off
REM ============================================================
REM  BỘ KHỞI ĐỘNG TỰ ĐỘNG - HỆ THỐNG QUẢN LÝ VÀ CẤP BIỂN SỐ NHÀ
REM  UBND XÃ TÂN PHÚ - TỈNH TÂY NINH  |  Bản Windows
REM  Tính năng: tự tạo/kích hoạt môi trường ảo - chạy FastAPI trên
REM  0.0.0.0:8000 - lấy IP mạng LAN - tự mở trình duyệt.
REM ============================================================
chcp 65001 >nul
title Hệ thống Quản lý và Cấp biển số nhà - Xã Tân Phú, Tây Ninh
cd /d "%~dp0backend"

echo ==========================================================
echo    KHỞI ĐỘNG HỆ THỐNG QUẢN LÝ VÀ CẤP BIỂN SỐ NHÀ
echo    UBND XÃ TÂN PHÚ - TỈNH TÂY NINH
echo ==========================================================
echo.

REM ---------- (a) KÍCH HOẠT MÔI TRƯỜNG ẢO ----------
if exist "venv\Scripts\activate.bat" call "venv\Scripts\activate.bat" >nul 2>&1 & goto :moi_truong_san_sang
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat" >nul 2>&1 & goto :moi_truong_san_sang

echo [!] Chưa có môi trường ảo — bắt đầu tự động tạo lần đầu chạy.
where python >nul 2>&1
if errorlevel 1 goto :loi_python
python -m venv venv
if not exist "venv\Scripts\activate.bat" goto :loi_venv
call "venv\Scripts\activate.bat" >nul 2>&1
echo [..] Đang cài đặt thư viện cần thiết — lần đầu có thể mất vài phút...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if errorlevel 1 goto :loi_pip
echo [OK] Đã tạo xong môi trường ảo và cài đặt thư viện.
goto :moi_truong_san_sang

:loi_python
echo.
echo [LỖI] Máy tính chưa cài Python.
echo        Vui lòng tải và cài Python 3.11 trở lên tại https://www.python.org/downloads/
echo        Khi cài nhớ tích chọn ô "Add Python to PATH" rồi chạy lại file này.
echo.
pause
exit /b 1

:loi_venv
echo.
echo [LỖI] Không tạo được môi trường ảo. Vui lòng kiểm tra lại phần cài đặt Python.
echo.
pause
exit /b 1

:loi_pip
echo.
echo [LỖI] Cài đặt thư viện thất bại — hãy kiểm tra kết nối Internet rồi chạy lại.
echo.
pause
exit /b 1

:moi_truong_san_sang
echo [OK] Môi trường Python đã sẵn sàng:
python --version
echo.

REM ---------- (b) LẤY ĐỊA CHỈ IP NỘI BỘ TRONG MẠNG LAN ----------
set "LAN_IP="
for /f "delims=" %%A in ('powershell -NoProfile -Command "Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*'} | Select-Object -ExpandProperty IPAddress -First 1" 2^>nul') do set "LAN_IP=%%A"
if not defined LAN_IP set "LAN_IP=127.0.0.1"

REM ---------- KIỂM TRA CỔNG 8000 CÓ BỊ CHIẾM ĐÓNG KHÔNG ----------
netstat -ano 2>nul | findstr /C:":8000 " | findstr /C:"LISTENING" >nul 2>&1
if errorlevel 1 goto :cong_trong
echo [CẢNH BÁO] Cổng 8000 đang có chương trình khác sử dụng.
echo             Nếu khởi động lỗi, hãy đóng ứng dụng đang chiếm cổng rồi chạy lại.
echo.
:cong_trong

REM ---------- HIỂN THỊ ĐƯỜNG LINK TRUY CẬP ----------
echo ----------------------------------------------------------
echo   ĐƯỜNG LINK TRUY CẬP HỆ THỐNG
echo ----------------------------------------------------------
echo   Trên chính máy này — khuyến nghị dùng:
echo       http://127.0.0.1:8000
echo.
if "%LAN_IP%"=="127.0.0.1" goto :khong_co_ip
echo   Trên điện thoại / máy tính khác trong CÙNG mạng Wi-Fi / LAN:
echo       http://%LAN_IP%:8000
echo.
echo   Tài liệu API dành cho cán bộ kỹ thuật:
echo       http://%LAN_IP%:8000/docs
goto :hien_thi_xong
:khong_co_ip
echo   [!] Không xác định được địa chỉ IP mạng LAN của máy.
echo       Hiện chỉ truy cập được ngay trên máy này.
:hien_thi_xong
echo.
echo ----------------------------------------------------------
echo   Máy chủ FastAPI sẽ chạy tại 0.0.0.0 cổng 8000
echo   — mọi thiết bị trong mạng nội bộ đều truy cập được.
echo ----------------------------------------------------------
echo.

REM ---------- (c) TỰ ĐỘNG MỞ TRÌNH DUYỆT TỚI GIAO DIỆN CHÍNH ----------
echo [OK] Trình duyệt sẽ tự động mở sau 5 giây tới giao diện hệ thống...
start "" /min powershell -NoProfile -Command "Start-Sleep -Seconds 5; Start-Process 'http://127.0.0.1:8000/'"
echo.

REM ---------- KHỞI CHẠY FASTAPI HOST 0.0.0.0 PORT 8000 ----------
echo [..] Đang khởi động máy chủ — nhấn tổ hợp phím Ctrl+C để dừng.
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo.
echo [!] Máy chủ đã dừng hoạt động. Nhấn phím bất kỳ để đóng cửa sổ...
pause >nul
