# ĐẶC TẢ KỸ THUẬT: HỆ THỐNG CƠ SỞ DỮ LIỆU QUẢN LÝ SỐ NHÀ 
**Mô hình:** Tích hợp API-First, Serverless & Lưu trữ Google Sheets  
**Nền tảng đích:** WebApp, Zalo Mini App "Tân Phú Số"

---

## I. KIẾN TRÚC TỔNG THỂ & STACK CÔNG NGHỆ (TECH STACK)

### 1. Frontend (Giao diện người dùng & Quản trị)
* **Framework:** Next.js (React) hoặc Nuxt 3 (Vue.js) để tối ưu tốc độ tải trang (SSR/SSG), SEO và thiết kế Mobile-first.
* **UI/UX:** Tailwind CSS + Radix UI / Shadcn UI cho giao diện hiện đại, tối giản và tốc độ phản hồi cực nhanh.
* **Bản đồ số:** Mapbox GL JS hoặc Leaflet. Tích hợp layer bản đồ vệ tinh, tối ưu việc hiển thị hàng ngàn điểm tọa độ nhà ở hoặc vẽ polygon lô đất mà không giật lag.

### 2. Backend & API (Khối xử lý logic)
* **Môi trường:** Next.js API Routes (Serverless Functions) triển khai trên Vercel.
* **Ngôn ngữ:** TypeScript nhằm kiểm soát kiểu dữ liệu chặt chẽ, dễ bảo trì khi mở rộng hệ thống.

### 3. Cơ sở dữ liệu (Database)
* **Lưu trữ chính (Master DB):** Google Sheets (Tài khoản Google Workspace/Ultra). Dữ liệu được cấu trúc thành các trang tính chuẩn hóa (Relational-like).
* **Bộ đệm (Caching - Bắt buộc):** Redis (thông qua Upstash). Xử lý Rate Limit của Google Sheets API bằng cách cache dữ liệu tra cứu. Thời gian phản hồi API < 0.01s, chịu tải hàng ngàn truy cập đồng thời từ Zalo Mini App.

### 4. Xác thực & Phân quyền (Authentication)
* **Công cụ:** NextAuth.js (Auth.js) hỗ trợ Single Sign-On (SSO):
  * **Google OAuth2:** Dành cho cán bộ quản trị (UBND xã, Ban quản lý dự án).
  * **Zalo Login:** Dành cho người dân truy cập thông qua Zalo Mini App.

---

## II. THIẾT KẾ CƠ SỞ DỮ LIỆU (GOOGLE SHEETS SCHEMA)

Hệ thống sử dụng 01 Spreadsheet cốt lõi, phân chia thành các Sheet:

1. **Sheet `TuyenDuong`:** `ID_Tuyen`, `TenDuong`, `ToaDo_BatDau`, `ToaDo_KetThuc`, `PhanLoai`.
2. **Sheet `SoNha` (Core):** `ID_Nha`, `SoNha_Moi`, `SoNha_Cu`, `TenChuHo`, `ToaDo_GPS`, `TrangThai` (Hiện hữu/Đất trống), `ID_TuyenDuong`, `ID_Hem_Ngach`.
3. **Sheet `HoSoCapMoi`:** `ID_YeuCau`, `ThongTin`, `HinhAnh_KhaoSat`, `TrangThai_Duyet`.
4. **Sheet `Log_HeThong`:** Lưu lịch sử thao tác (Audit trail) bao gồm người thực hiện, thời gian, trường dữ liệu thay đổi.

---

## III. GIẢI PHÁP KỸ THUẬT CHO CÁC BÀI TOÁN THỰC TẾ

### 1. Bài toán hẻm sâu, ngõ ngách chằng chịt
* **Thuật toán Path-based routing:** Áp dụng cấu trúc dạng cây (Tree). Ví dụ: `Hem_12` -> `Ngach_34` -> `SoNha_56`. Hệ thống tự động nối chuỗi tạo ra số nhà cuối cùng: `12/34/56 Đường X` và nối các node tọa độ để vẽ lộ trình chính xác trên bản đồ.

### 2. Bài toán "Khoảng đất trống" (Dự trữ số nhà)
* **Tính năng Virtual Node (Điểm ảo):** Thông qua dữ liệu khoảng cách mặt tiền cán bộ khảo sát nhập, thuật toán nội suy (Interpolation) trên tọa độ GPS sẽ sinh ra các `ID_Nha` ẩn (Đất dự trữ). Khi xây dựng mới, cán bộ chỉ cần chuyển trạng thái sang "Hiện hữu", đảm bảo logic chẵn/lẻ liên tục mà không vỡ cấu trúc đánh số.

### 3. Bài toán ánh xạ số cũ - số mới
* **Multi-Search (Tra cứu chéo):** Thuật toán tìm kiếm song song trên cả 2 trường `SoNha_Cu` và `SoNha_Moi`. Trả về kết quả duy nhất kèm vị trí ghim trên bản đồ.

### 4. Cấp giấy chứng nhận & Chữ ký số điện tử
* **Dynamic PDF Generation:** Tích hợp thư viện `pdf-lib`. Khi có lệnh "Duyệt", dữ liệu Google Sheets tự động fill vào phôi PDF Giấy chứng nhận biển số nhà.
* **Ký số:** Chèn ảnh chữ ký/con dấu định vị tọa độ sẵn trên PDF hoặc sinh mã Hash đẩy qua API của hệ thống chứng thực chữ ký số (VNPT-CA/Viettel-CA) chuẩn Nghị định 30/2020/NĐ-CP.

---

## IV. TÍCH HỢP ZALO MINI APP "TÂN PHÚ SỐ"

Hệ thống cung cấp RESTful API độc lập, phục vụ 4 luồng nghiệp vụ trên Zalo Mini App:

1. **Luồng Đăng nhập:** Mini App gọi Zalo API lấy Zalo ID cấp phiên làm việc, không yêu cầu tạo mật khẩu.
2. **Luồng Tra cứu bản đồ:** Mini App gửi `GET /api/sonha?address=...` -> Backend Redis trả JSON -> Hiển thị bản đồ mini ngay trên giao diện Zalo.
3. **Luồng Dịch vụ công (Cấp/Đổi số nhà):** Người dân điền form, chụp ảnh, đính kèm Zalo Location. Data POST về Backend -> Upload ảnh lên Google Drive -> Ghi dòng mới vào Sheet `HoSoCapMoi` -> n8n/GAS trigger gửi thông báo Telegram cho cán bộ phụ trách.
4. **Luồng Nhắc việc (Zalo ZNS):** Cán bộ duyệt cấp số trên WebApp -> Gọi Zalo OA API gửi tin nhắn ZNS trực tiếp cho người dân đến nhận kết quả.

---

## V. HIỆU QUẢ ĐẦU TƯ

* **Chi phí hạ tầng tối thiểu (Zero Server Cost):** Sử dụng hệ sinh thái Google Workspace sẵn có của đơn vị kết hợp các nền tảng Serverless miễn phí/giá rẻ.
* **Sở hữu dữ liệu 100%:** Dữ liệu nằm hoàn toàn trên Google Drive của cơ quan quản lý, không bị "khóa" bởi nhà cung cấp phần mềm, dễ dàng xuất/chia sẻ.
* **Khả năng mở rộng:** Kiến trúc API-First dễ dàng liên thông với Cổng dịch vụ công của Tỉnh hoặc Cơ sở dữ liệu Quốc gia khi có yêu cầu.