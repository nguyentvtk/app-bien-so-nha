@echo off
REM ============================================================
REM  ĐẨY MÃ NGUỒN WEBAPP BIỂN SỐ NHÀ LÊN GITHUB
REM  UBND XÃ TÂN PHÚ - TỈNH TÂY NINH  |  Bản Windows
REM
REM  Cách dùng:
REM    Cách 1:  nhấp đúp file, nhập địa chỉ GitHub khi được hỏi
REM    Cách 2:  Day_Len_Github.bat https://github.com/tai-khoan/repo.git
REM ============================================================
chcp 65001 >nul
title Đẩy mã nguồn WebApp Biển Số Nhà lên GitHub
cd /d "%~dp0"

echo ==========================================================
echo    ĐẨY MÃ NGUỒN LÊN GITHUB
echo    HỆ THỐNG QUẢN LÝ VÀ CẤP BIỂN SỐ NHÀ - XÃ TÂN PHÚ
echo ==========================================================
echo.

REM ---------- 0) KIỂM TRA GIT ĐÃ CÀI CHƯA ----------
where git >nul 2>&1
if errorlevel 1 goto :loi_git

REM ---------- KIỂM TRA DANH TÍNH GIT ----------
git config --global user.name >nul 2>&1
if not errorlevel 1 goto :danh_tinh_ok
echo [LỖI] Máy chưa cấu hình tên đăng ký Git — commit sẽ bị từ chối.
echo.
echo        Hãy chạy 2 lệnh sau thay thông tin của anh/chị rồi chạy lại file này:
echo            git config --global user.name "Ho Ten Cua Ban"
echo            git config --global user.email "email@example.com"
echo.
pause
exit /b 1
:danh_tinh_ok
set "GIT_TEN="
for /f "delims=" %%N in ('git config --global user.name') do set "GIT_TEN=%%N"
echo [OK] Git sẵn sàng - người commit: %GIT_TEN%
echo.

REM ---------- 1) TẠO FILE .gitignore CHUẨN ----------
if exist .gitignore goto :da_co_gitignore
echo [..] Đang tạo file .gitignore chuẩn...
(
echo # ==== Python ====
echo __pycache__/
echo *.py[cod]
echo *.egg-info/
echo .pytest_cache/
echo # ==== Môi trường ảo ====
echo venv/
echo .venv/
echo env/
echo # ==== Biến môi trường và thông tin mật ====
echo .env
echo .env.*
echo # ==== File tạm của hệ điều hành ====
echo .DS_Store
echo Thumbs.db
echo desktop.ini
echo *.log
echo *.swp
echo # ==== Dữ liệu ứng dụng sinh tự động ====
echo backend/data/certificates/
echo *.db-wal
echo *.db-shm
echo # ==== Vercel CLI ====
echo .vercel
) > .gitignore
echo [OK] Đã tạo .gitignore — bỏ qua __pycache__, .env, venv, file tạm hệ thống.
goto :gitignore_xong
:da_co_gitignore
echo [OK] Đã có sẵn file .gitignore — giữ nguyên không ghi đè.
:gitignore_xong
echo.

REM ---------- 2) KHỞI TẠO GIT + COMMIT ĐẦU TIÊN ----------
echo [..] Khởi tạo kho Git và đặt nhánh chính là main...
git init >nul 2>&1
git symbolic-ref HEAD refs/heads/main

echo [..] Đang thêm toàn bộ mã nguồn — git add .
git add .
if errorlevel 1 goto :loi_git

echo [..] Tạo commit đầu tiên...
git commit -m "Phat hanh WebApp Bien So Nha - Ban on dinh" >nul 2>&1
if errorlevel 1 goto :commit_bo_qua
echo [OK] Đã tạo commit: Phat hanh WebApp Bien So Nha - Ban on dinh
goto :sau_commit
:commit_bo_qua
echo [OK] Không có thay đổi mới cần commit — dùng commit sẵn có.
:sau_commit
echo.

REM ---------- 3) LIÊN KẾT REMOTE GITHUB ----------
set "REPO_URL=%~1"
if defined REPO_URL goto :kiem_tra_url
echo [!] Chưa truyền địa chỉ repository.
set /p "REPO_URL=Nhap dia chi GitHub (vi du https://github.com/tai-khoan/repo.git): "
if not defined REPO_URL goto :thieu_url

:kiem_tra_url
if "%REPO_URL:~0,4%"=="http" goto :url_hop_le
if "%REPO_URL:~0,5%"=="git@g" goto :url_hop_le
if "%REPO_URL:~0,6%"=="ssh://" goto :url_hop_le
echo [LỖI] Địa chỉ repository không hợp lệ: %REPO_URL%
echo        Địa chỉ phải bắt đầu bằng https:// hoặc git@github.com
echo.
pause
exit /b 1
:url_hop_le

git remote remove origin >nul 2>&1
echo [..] Liên kết remote origin tới: %REPO_URL%
git remote add origin "%REPO_URL%"
if errorlevel 1 goto :loi_git
echo [OK] Đã liên kết remote origin.
echo.

REM ---------- 4) ĐẨY MÃ LÊN GITHUB ----------
echo [..] Đang đẩy nhánh main lên GitHub — git push -u origin main
echo      Nếu lần đầu, cửa sổ đăng nhập GitHub có thể hiện ra — hãy hoàn tất đăng nhập.
echo.
git push -u origin main
if errorlevel 1 goto :loi_push

echo.
echo ==========================================================
echo    HOÀN TẤT! MÃ NGUỒN ĐÃ LÊN GITHUB
echo    Kho chứa: %REPO_URL%
echo    Nhánh    : main
echo ==========================================================
echo.
pause
exit /b 0

REM ============================================================
REM  CÁC NHÁN BÁO LỖI
REM ============================================================
:loi_git
echo.
echo [LỖI] Không tìm thấy Git trên máy hoặc lệnh Git bị lỗi.
echo        Vui lòng cài Git tai https://git-scm.com/download/win rồi chạy lại.
echo.
pause
exit /b 1

:thieu_url
echo.
echo [LỖI] Chưa nhập địa chỉ repository nên không thể đẩy lên GitHub.
echo        Tạo repository rỗng trên github.com rồi chạy lại file này.
echo.
pause
exit /b 1

:loi_push
echo.
echo [LỖI] Đẩy lên GitHub thất bại. Nguyên nhân thường gặp:
echo        1. Chưa đăng nhập GitHub — chạy lệnh: git credential-manager configure
echo        2. Địa chỉ repository sai hoặc chưa tạo kho trên GitHub
echo        3. Không có quyền đẩy — kiểm tra anh/chị là chủ kho hay được mời hợp tác
echo        4. Mất kết nối Internet
echo.
echo        Sau khi khắc phục, chỉ cần chạy lại file này.
echo.
pause
exit /b 1
