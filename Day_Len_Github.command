#!/bin/bash
# ============================================================
#  ĐẨY MÃ NGUỒN WEBAPP BIỂN SỐ NHÀ LÊN GITHUB — Bản macOS
#
#  Cách dùng:
#    Cách 1:  nhấp đôi file, nhập địa chỉ GitHub khi được hỏi
#    Cách 2:  ./Day_Len_Github.command https://github.com/tai-khoan/repo.git
# ============================================================
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR" || exit 1

echo "=========================================================="
echo "   ĐẨY MÃ NGUỒN LÊN GITHUB"
echo "   HỆ THỐNG QUẢN LÝ VÀ CẤP BIỂN SỐ NHÀ — XÃ TÂN PHÚ"
echo "=========================================================="
echo

# ---------- 0) KIỂM TRA GIT ----------
if ! command -v git >/dev/null 2>&1; then
    echo "[LỖI] Máy chưa cài Git. Hãy cài qua: xcode-select --install"
    read -r -p "Nhấn phím bất kỳ để đóng..." _
    exit 1
fi
if [ -z "$(git config --global user.name)" ]; then
    echo "[LỖI] Máy chưa cấu hình tên đăng ký Git — commit sẽ bị từ chối."
    echo
    echo "Hãy chạy 2 lệnh sau thay thông tin của anh/chị rồi chạy lại file này:"
    echo "    git config --global user.name \"Họ Tên Của Bạn\""
    echo "    git config --global user.email \"email@example.com\""
    echo
    read -r -p "Nhấn phím bất kỳ để đóng..." _
    exit 1
fi
echo "[OK] Git sẵn sàng — người commit: $(git config --global user.name)"
echo

# ---------- 1) TẠO FILE .gitignore CHUẨN ----------
if [ -f .gitignore ]; then
    echo "[OK] Đã có sẵn file .gitignore — giữ nguyên không ghi đè."
else
    echo "[..] Đang tạo file .gitignore chuẩn..."
    cat > .gitignore <<'EOF'
# ==== Python ====
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/

# ==== Môi trường ảo ====
venv/
.venv/
env/

# ==== Biến môi trường và thông tin mật ====
.env
.env.*

# ==== File tạm của hệ điều hành ====
.DS_Store
Thumbs.db
desktop.ini
*.log
*.swp

# ==== Dữ liệu ứng dụng sinh tự động ====
backend/data/certificates/
*.db-wal
*.db-shm

# ==== Vercel CLI ====
.vercel
EOF
    echo "[OK] Đã tạo .gitignore — bỏ qua __pycache__, .env, venv, file tạm hệ thống."
fi
echo

# ---------- 2) KHỞI TẠO GIT + COMMIT ĐẦU TIÊN ----------
echo "[..] Khởi tạo kho Git và đặt nhánh chính là main..."
git init --initial-branch=main >/dev/null 2>&1 || { git init >/dev/null 2>&1; git symbolic-ref HEAD refs/heads/main; }

echo "[..] Đang thêm toàn bộ mã nguồn — git add ."
git add . || { echo "[LỖI] git add thất bại."; read -r -p "Nhấn phím bất kỳ để đóng..." _; exit 1; }

echo "[..] Tạo commit đầu tiên..."
if git commit -m "Phat hanh WebApp Bien So Nha - Ban on dinh" >/dev/null 2>&1; then
    echo "[OK] Đã tạo commit: Phat hanh WebApp Bien So Nha - Ban on dinh"
else
    echo "[OK] Không có thay đổi mới cần commit — dùng commit sẵn có."
fi
echo

# ---------- 3) LIÊN KẾT REMOTE GITHUB ----------
REPO_URL="${1:-}"
if [ -z "$REPO_URL" ]; then
    echo "[!] Chưa truyền địa chỉ repository."
    read -r -p "Nhập địa chỉ GitHub (ví dụ https://github.com/tai-khoan/repo.git): " REPO_URL
fi
if [ -z "$REPO_URL" ]; then
    echo "[LỖI] Chưa nhập địa chỉ repository nên không thể đẩy lên GitHub."
    echo "      Hãy tạo repository rỗng trên github.com rồi chạy lại file này."
    read -r -p "Nhấn phím bất kỳ để đóng..." _
    exit 1
fi
case "$REPO_URL" in
    http*|git@*|ssh://*|/*) ;;
    *)
        echo "[LỖI] Địa chỉ repository không hợp lệ: $REPO_URL"
        echo "      Địa chỉ phải bắt đầu bằng https:// hoặc git@github.com"
        read -r -p "Nhấn phím bất kỳ để đóng..." _
        exit 1
        ;;
esac

git remote remove origin >/dev/null 2>&1
echo "[..] Liên kết remote origin tới: $REPO_URL"
git remote add origin "$REPO_URL"
echo "[OK] Đã liên kết remote origin."
echo

# ---------- 4) ĐẨY MÃ LÊN GITHUB ----------
echo "[..] Đang đẩy nhánh main lên GitHub — git push -u origin main"
echo "     Nếu lần đầu, cửa sổ đăng nhập GitHub có thể hiện ra — hãy hoàn tất đăng nhập."
echo
if git push -u origin main; then
    echo
    echo "=========================================================="
    echo "   HOÀN TẤT! MÃ NGUỒN ĐÃ LÊN GITHUB"
    echo "   Kho chứa: $REPO_URL"
    echo "   Nhánh    : main"
    echo "=========================================================="
else
    echo
    echo "[LỖI] Đẩy lên GitHub thất bại. Nguyên nhân thường gặp:"
    echo "      1. Chưa đăng nhập GitHub — thử: gh auth login hoặc git credential-manager"
    echo "      2. Địa chỉ repository sai hoặc chưa tạo kho trên GitHub"
    echo "      3. Không có quyền đẩy — kiểm tra quyền hợp tác trên kho"
    echo "      4. Mất kết nối Internet"
    echo
    echo "      Sau khi khắc phục, chỉ cần chạy lại file này."
fi
echo
read -r -p "Nhấn phím bất kỳ để đóng..." _
