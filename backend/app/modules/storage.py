"""
Module Storage & Database Layer - UBND XÃ TÂN PHÚ, TỈNH TÂY NINH
Không sử dụng dữ liệu mẫu - Toàn bộ tuyến đường được đồng bộ trực tiếp từ Google Sheets chính thức:
https://docs.google.com/spreadsheets/d/1LYgA4jQQ9VgCZFpfKT4KyMQzlzg2jaB2jXlP1E870NM/edit?gid=1984523791
"""

import sqlite3
import json
import os
import csv
import io
import httpx
import logging
from typing import List, Optional, Dict, Any
from app.models.schemas import TuyenDuong, SoNha, HoSoCapMoi, TrangThaiSoNha, TrangThaiHoSo, MucDichSuDungDat, HienTrangXayDung

logger = logging.getLogger(__name__)

# Thư mục dữ liệu: mặc định backend/data; trên serverless (Vercel) chuyển sang
# /tmp qua biến môi trường SONHA_DATA_DIR vì filesystem chỉ đọc được ghi trong /tmp
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.environ.get("SONHA_DATA_DIR") or os.path.join(BACKEND_DIR, "data")
DB_FILE = os.path.join(DATA_DIR, "sonha.db")
DEFAULT_GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1LYgA4jQQ9VgCZFpfKT4KyMQzlzg2jaB2jXlP1E870NM/export?format=csv&gid=1984523791"

class StorageService:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._cache: Dict[str, Any] = {}
        self.init_database()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 1. Bảng Tuyến Đường (WGS84)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tuyen_duong (
                id_tuyen TEXT PRIMARY KEY,
                ten_duong TEXT NOT NULL,
                vi_tri TEXT,
                toado_batdau TEXT NOT NULL,
                toado_kethuc TEXT NOT NULL,
                phan_loai TEXT DEFAULT 'Đường xã',
                diem_dau TEXT,
                diem_cuoi TEXT,
                chieu_dai_m REAL DEFAULT 0.0,
                be_rong_m TEXT,
                ket_cau TEXT,
                tong_so_nha INTEGER DEFAULT 0,
                quy_tac_danh_so TEXT DEFAULT 'Tả Chẵn - Hữu Lẻ',
                nguon_du_lieu TEXT DEFAULT 'Google Sheets'
            )
            """)

            # 2. Bảng Số Nhà & Hiện Trạng Đất Đai
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS so_nha (
                id_nha TEXT PRIMARY KEY,
                so_nha_moi TEXT NOT NULL,
                so_nha_cu TEXT,
                ten_chu_ho TEXT NOT NULL,
                cccd TEXT,
                sdt TEXT,
                toado_gps TEXT NOT NULL,
                trang_thai TEXT NOT NULL,
                muc_dich_su_dung_dat TEXT DEFAULT 'DAT_O_THO_CU',
                hien_trang_xay_dung TEXT DEFAULT 'DA_XAY_NHA',
                so_to_thua TEXT,
                id_tuyen_duong TEXT NOT NULL,
                id_hem_ngach TEXT,
                loai_nha TEXT DEFAULT 'Nhà ở riêng lẻ',
                dien_tich_mat_tien REAL DEFAULT 5.0,
                ngay_cap TEXT,
                so_giay_phep TEXT,
                ghi_chu TEXT,
                FOREIGN KEY (id_tuyen_duong) REFERENCES tuyen_duong (id_tuyen)
            )
            """)

            # 3. Bảng Hồ Sơ & Khảo Sát Thực Địa Của Điều Tra Viên
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ho_so (
                id_yeu_cau TEXT PRIMARY KEY,
                ho_ten_nguoi_nop TEXT NOT NULL,
                cccd TEXT NOT NULL,
                sdt TEXT NOT NULL,
                email TEXT,
                dia_chi_khao_sat TEXT NOT NULL,
                id_tuyen_duong TEXT NOT NULL,
                hem_ngach TEXT,
                muc_dich_su_dung_dat TEXT DEFAULT 'DAT_O_THO_CU',
                hien_trang_xay_dung TEXT DEFAULT 'DA_XAY_NHA',
                so_to_thua TEXT,
                khoang_cach_mat_tien REAL DEFAULT 5.0,
                toado_gps TEXT NOT NULL,
                hinh_anh_khao_sat TEXT,
                giay_to_phap_ly TEXT,
                loai_yeu_cau TEXT DEFAULT 'KHAO_SAT_THUC_DIA',
                trang_thai TEXT DEFAULT 'CHO_TIEP_NHAN',
                so_nha_de_xuat TEXT,
                ai_risk_score REAL,
                ai_feedback TEXT,
                ngay_tao TEXT,
                dieu_tra_vien TEXT,
                can_bo_duyet TEXT
            )
            """)

            # 4. Bảng Thửa Đất Địa Chính (Kế hoạch 2959/KH-BNNMT-BCA)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS thua_dat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                so_to TEXT NOT NULL,
                so_thua TEXT NOT NULL,
                ten_chu TEXT,
                ma_loai_dat TEXT,
                dien_tich REAL DEFAULT 0.0,
                so_gcn TEXT,
                nhom_phan_loai TEXT,
                da_xuat_so_dien_tu INTEGER DEFAULT 0,
                dong_bo_3_khoi INTEGER DEFAULT 0,
                lam_sach_csdl_dan_cu INTEGER DEFAULT 0,
                van_hanh_24_7 INTEGER DEFAULT 0,
                da_dinh_danh_thua INTEGER DEFAULT 0,
                thong_tin_thieu TEXT,
                co_dat_o INTEGER DEFAULT 0,
                nguon_du_lieu TEXT DEFAULT 'KH2959_BCA',
                UNIQUE(so_to, so_thua)
            )
            """)

            # 5. Bảng Hộ Dân Thực Tế (Điều tra thu nhập năm 2026)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ho_dan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stt_nha INTEGER,
                stt_ho INTEGER,
                ten_chu_ho TEXT NOT NULL,
                dia_chi TEXT,
                ap TEXT NOT NULL,
                so_nhan_khau INTEGER DEFAULT 0,
                ghi_chu TEXT,
                dieu_tra_vien TEXT,
                sdt_dieu_tra_vien TEXT,
                thua_dat_lien_ket TEXT,
                phan_loai_phap_ly TEXT DEFAULT 'CHUA_DOI_SOAT',
                nguon_du_lieu TEXT DEFAULT 'DS_Nha_thuc_te.xlsx'
            )
            """)

            # 6. Audit Log
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS log_hethong (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hanh_dong TEXT NOT NULL,
                doi_tuong TEXT NOT NULL,
                nguoi_thuc_hien TEXT DEFAULT 'Hệ thống',
                thoi_gian TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                chi_tiet TEXT
            )
            """)

            # Migration nhẹ: bổ sung cột chế độ đánh số (Đô thị/Nông thôn)
            # cho bảng so_nha nếu phiên bản CSDL cũ chưa có
            cot_da_co = {r["name"] for r in cursor.execute("PRAGMA table_info(so_nha)").fetchall()}
            if "che_do_danh_so" not in cot_da_co:
                cursor.execute("ALTER TABLE so_nha ADD COLUMN che_do_danh_so TEXT")

            conn.commit()

    def clear_mock_data(self):
        """Xóa sạch số nhà và hồ sơ mẫu, giữ nguyên danh mục tuyến đường thật đã đồng bộ"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM so_nha")
            cursor.execute("DELETE FROM ho_so")
            cursor.execute("INSERT INTO log_hethong (hanh_dong, doi_tuong, chi_tiet) VALUES (?, ?, ?)",
                           ("XÓA DỮ LIỆU MẪU", "SYSTEM", "Đã xóa toàn bộ số nhà và hồ sơ mẫu. Bảo lưu danh mục tuyến đường thực tế."))
            conn.commit()
            self._cache.clear()

    def clear_all_data(self):
        """Xóa sạch toàn bộ bao gồm cả tuyến đường (dùng khi reset toàn hệ thống)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM so_nha")
            cursor.execute("DELETE FROM ho_so")
            cursor.execute("DELETE FROM tuyen_duong")
            cursor.execute("INSERT INTO log_hethong (hanh_dong, doi_tuong, chi_tiet) VALUES (?, ?, ?)",
                           ("RESET TOÀN BỘ", "SYSTEM", "Đã reset sạch toàn bộ cơ sở dữ liệu."))
            conn.commit()
            self._cache.clear()

    # --- Query Methods ---
    def get_all_tuyen_duong(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tuyen_duong ORDER BY id_tuyen ASC")
            rows = cursor.fetchall()
            result = []
            for r in rows:
                item = dict(r)
                item["toado_batdau"] = json.loads(item["toado_batdau"])
                item["toado_kethuc"] = json.loads(item["toado_kethuc"])
                result.append(item)
            return result

    def get_all_so_nha(self, id_tuyen: Optional[str] = None, trang_thai: Optional[str] = None) -> List[Dict[str, Any]]:
        cache_key = f"so_nha_{id_tuyen}_{trang_thai}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM so_nha WHERE 1=1"
            params = []
            if id_tuyen:
                query += " AND id_tuyen_duong = ?"
                params.append(id_tuyen)
            if trang_thai:
                query += " AND trang_thai = ?"
                params.append(trang_thai)
            query += " ORDER BY id_nha ASC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            result = []
            for r in rows:
                item = dict(r)
                item["toado_gps"] = json.loads(item["toado_gps"])
                result.append(item)
            self._cache[cache_key] = result
            return result

    def get_so_nha_by_id(self, id_nha: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM so_nha WHERE id_nha = ?", (id_nha,))
            row = cursor.fetchone()
            if not row:
                return None
            item = dict(row)
            item["toado_gps"] = json.loads(item["toado_gps"])
            return item

    def search_so_nha(self, query: str) -> List[Dict[str, Any]]:
        clean_q = f"%{query.strip().lower()}%"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM so_nha 
            WHERE LOWER(so_nha_moi) LIKE ? 
               OR LOWER(COALESCE(so_nha_cu, '')) LIKE ? 
               OR LOWER(ten_chu_ho) LIKE ?
               OR LOWER(COALESCE(so_to_thua, '')) LIKE ?
               OR LOWER(COALESCE(so_gcn, '')) LIKE ?
               OR LOWER(COALESCE(cccd, '')) LIKE ?
               OR LOWER(COALESCE(ap, '')) LIKE ?
               OR LOWER(COALESCE(dia_chi_day_du, '')) LIKE ?
               OR LOWER(COALESCE(ma_loai_dat_goc, '')) LIKE ?
            """, (clean_q, clean_q, clean_q, clean_q, clean_q, clean_q, clean_q, clean_q, clean_q))
            rows = cursor.fetchall()
            result = []
            for r in rows:
                item = dict(r)
                item["toado_gps"] = json.loads(item["toado_gps"])
                result.append(item)
            return result

    def insert_so_nha(self, so_nha: SoNha) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO so_nha (
                id_nha, so_nha_moi, so_nha_cu, ten_chu_ho, cccd, sdt,
                toado_gps, trang_thai, muc_dich_su_dung_dat, hien_trang_xay_dung,
                so_to_thua, id_tuyen_duong, id_hem_ngach, loai_nha, dien_tich_mat_tien,
                ngay_cap, so_giay_phep, ghi_chu, che_do_danh_so
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                so_nha.id_nha, so_nha.so_nha_moi, so_nha.so_nha_cu,
                so_nha.ten_chu_ho, so_nha.cccd, so_nha.sdt,
                json.dumps(so_nha.toado_gps.dict()), so_nha.trang_thai.value,
                so_nha.muc_dich_su_dung_dat.value, so_nha.hien_trang_xay_dung.value,
                so_nha.so_to_thua, so_nha.id_tuyen_duong, so_nha.id_hem_ngach,
                so_nha.loai_nha, so_nha.dien_tich_mat_tien,
                so_nha.ngay_cap, so_nha.so_giay_phep, so_nha.ghi_chu,
                getattr(so_nha, "che_do_danh_so", None)
            ))
            cursor.execute("UPDATE tuyen_duong SET tong_so_nha = tong_so_nha + 1 WHERE id_tuyen = ?", (so_nha.id_tuyen_duong,))
            cursor.execute("INSERT INTO log_hethong (hanh_dong, doi_tuong, chi_tiet) VALUES (?, ?, ?)",
                           ("CẤP BIỂN SỐ NHÀ", so_nha.id_nha, f"UBND Xã Tân Phú cấp biển {so_nha.so_nha_moi} cho {so_nha.ten_chu_ho}"))
            conn.commit()
            self._cache.clear()
            return True

    def get_all_ho_so(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ho_so ORDER BY ngay_tao DESC")
            rows = cursor.fetchall()
            result = []
            for r in rows:
                item = dict(r)
                item["toado_gps"] = json.loads(item["toado_gps"])
                item["hinh_anh_khao_sat"] = json.loads(item["hinh_anh_khao_sat"] or "[]")
                item["giay_to_phap_ly"] = json.loads(item["giay_to_phap_ly"] or "[]")
                result.append(item)
            return result

    def get_ho_so_by_id(self, id_yeu_cau: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ho_so WHERE id_yeu_cau = ?", (id_yeu_cau,))
            row = cursor.fetchone()
            if not row:
                return None
            item = dict(row)
            item["toado_gps"] = json.loads(item["toado_gps"])
            item["hinh_anh_khao_sat"] = json.loads(item["hinh_anh_khao_sat"] or "[]")
            item["giay_to_phap_ly"] = json.loads(item["giay_to_phap_ly"] or "[]")
            return item

    def insert_ho_so(self, ho_so: HoSoCapMoi) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO ho_so (
                id_yeu_cau, ho_ten_nguoi_nop, cccd, sdt, email,
                dia_chi_khao_sat, id_tuyen_duong, hem_ngach, muc_dich_su_dung_dat,
                hien_trang_xay_dung, so_to_thua, khoang_cach_mat_tien, toado_gps,
                hinh_anh_khao_sat, giay_to_phap_ly, loai_yeu_cau, trang_thai,
                so_nha_de_xuat, ai_risk_score, ai_feedback, ngay_tao, dieu_tra_vien, can_bo_duyet
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ho_so.id_yeu_cau, ho_so.ho_ten_nguoi_nop, ho_so.cccd, ho_so.sdt, ho_so.email,
                ho_so.dia_chi_khao_sat, ho_so.id_tuyen_duong, ho_so.hem_ngach,
                ho_so.muc_dich_su_dung_dat.value, ho_so.hien_trang_xay_dung.value, ho_so.so_to_thua,
                ho_so.khoang_cach_mat_tien, json.dumps(ho_so.toado_gps.dict()),
                json.dumps(ho_so.hinh_anh_khao_sat), json.dumps(ho_so.giay_to_phap_ly),
                ho_so.loai_yeu_cau, ho_so.trang_thai.value, ho_so.so_nha_de_xuat,
                ho_so.ai_risk_score, ho_so.ai_feedback, ho_so.ngay_tao,
                ho_so.dieu_tra_vien, ho_so.can_bo_duyet
            ))
            cursor.execute("INSERT INTO log_hethong (hanh_dong, doi_tuong, chi_tiet) VALUES (?, ?, ?)",
                           ("KHẢO SÁT / NỘP HỒ SƠ", ho_so.id_yeu_cau, f"Tiếp nhận hồ sơ {ho_so.id_yeu_cau} tại {ho_so.dia_chi_khao_sat}"))
            conn.commit()
            return True

    def update_ho_so_status(self, id_yeu_cau: str, trang_thai: str, can_bo: str, so_nha_cap: Optional[str] = None) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE ho_so 
            SET trang_thai = ?, can_bo_duyet = ?, so_nha_de_xuat = COALESCE(?, so_nha_de_xuat)
            WHERE id_yeu_cau = ?
            """, (trang_thai, can_bo, so_nha_cap, id_yeu_cau))
            cursor.execute("INSERT INTO log_hethong (hanh_dong, doi_tuong, chi_tiet) VALUES (?, ?, ?)",
                           ("DUYỆT HỒ SƠ", id_yeu_cau, f"Cán bộ {can_bo} phê duyệt cấp số: {so_nha_cap}"))
            conn.commit()
            return True

    def get_thong_ke_dat_dai(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM so_nha WHERE trang_thai = 'HIEN_HUU'")
            da_cap_so = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM so_nha WHERE trang_thai = 'NHA_CHUA_DU_DIEU_KIEN' OR muc_dich_su_dung_dat = 'DAT_CHUA_CHUYEN_MUC_DICH'")
            chua_du_dieu_kien = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM so_nha WHERE trang_thai = 'DAT_THO_CU_CHUA_XAY' OR (muc_dich_su_dung_dat = 'DAT_O_THO_CU' AND hien_trang_xay_dung = 'DAT_TRONG')")
            tho_cu_chua_xay = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM tuyen_duong")
            tong_tuyen = cursor.fetchone()[0]

            return {
                "da_cap_so": da_cap_so,
                "nha_chua_du_dieu_kien": chua_du_dieu_kien,
                "dat_tho_cu_chua_xay_du_tru": tho_cu_chua_xay,
                "tong_tuyen_duong": tong_tuyen,
                "ghi_chu": "Báo cáo thống kê quản lý số nhà & đất đai xã Tân Phú, tỉnh Tây Ninh"
            }

    def sync_tuyen_duong_from_csv(self, csv_content: str) -> Dict[str, Any]:
        """
        Phân tích chính xác cấu trúc Google Sheets tuyến đường của Xã Tân Phú, Tây Ninh:
        Cột 0: STT (1, 2, I, II...)
        Cột 1: Tên đường (TP.01, TP.02...)
        Cột 2: Vị trí (Ấp Tân Hòa, Tân Tiến...)
        Cột 4: Điểm đầu
        Cột 5: Điểm cuối
        Cột 6: Chiều dài (km)
        Cột 8: Bề rộng mặt đường (m)
        Cột 10: Kết cấu mặt đường
        """
        f = io.StringIO(csv_content.strip())
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return {"success": False, "message": "Nội dung CSV rỗng"}

        current_category = "Đường xã"
        count_updated = 0
        base_lat = 11.6050
        base_lng = 106.1850

        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Xóa các tuyến cũ để cập nhật danh mục chuẩn từ Sheets
            cursor.execute("DELETE FROM tuyen_duong")

            for row in reader:
                if not row or not any(row):
                    continue

                stt = row[0].strip() if len(row) > 0 else ""
                col1 = row[1].strip() if len(row) > 1 else ""

                # Nhận diện dòng phân loại mục (I. Đường xã, II. Đường ấp, III. Đường ngõ xóm...)
                if stt in ["I", "II", "III", "IV", "V", "VI", "VII"] and col1:
                    current_category = col1
                    continue

                if not col1:
                    continue

                ten_duong = col1
                vi_tri = row[2].strip() if len(row) > 2 else ""
                diem_dau = row[4].strip() if len(row) > 4 else ""
                diem_cuoi = row[5].strip() if len(row) > 5 else ""

                chieu_dai_str = row[6].strip().replace(",", ".") if len(row) > 6 else "0"
                try:
                    chieu_dai_m = float(chieu_dai_str) * 1000.0
                except:
                    chieu_dai_m = 0.0

                be_rong_m = row[8].strip() if len(row) > 8 else "4.0"
                ket_cau = row[10].strip() if len(row) > 10 else ""

                id_tuyen = f"TD_{ten_duong.replace(' ', '_').replace('.', '_')}"

                # Tọa độ WGS84 phân bổ chuẩn xung quanh xã Tân Phú, tỉnh Tây Ninh
                # Bán kính 11.5950 - 11.6250, 106.1700 - 106.2100
                delta_lat = ((count_updated % 15) - 7) * 0.0025
                delta_lng = ((count_updated // 15) - 8) * 0.0030
                lat_start = round(base_lat + delta_lat, 5)
                lng_start = round(base_lng + delta_lng, 5)

                # Chiều dài ước tính theo WGS84
                lat_end = round(lat_start + (chieu_dai_m / 111000.0) * 0.7, 5)
                lng_end = round(lng_start + (chieu_dai_m / 111000.0) * 0.7, 5)

                start_coord = json.dumps({"lat": lat_start, "lng": lng_start})
                end_coord = json.dumps({"lat": lat_end, "lng": lng_end})

                cursor.execute("""
                INSERT OR REPLACE INTO tuyen_duong (
                    id_tuyen, ten_duong, vi_tri, toado_batdau, toado_kethuc, phan_loai,
                    diem_dau, diem_cuoi, chieu_dai_m, be_rong_m, ket_cau, tong_so_nha,
                    quy_tac_danh_so, nguon_du_lieu
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    id_tuyen, ten_duong, vi_tri, start_coord, end_coord, current_category,
                    diem_dau, diem_cuoi, chieu_dai_m, be_rong_m, ket_cau, 0,
                    "Tả Chẵn - Hữu Lẻ", "Google Sheets (UBND Xã Tân Phú)"
                ))
                count_updated += 1

            cursor.execute("INSERT INTO log_hethong (hanh_dong, doi_tuong, chi_tiet) VALUES (?, ?, ?)",
                           ("ĐỒNG BỘ GOOGLE SHEETS", "TUYEN_DUONG", f"Đã đồng bộ {count_updated} tuyến đường thực tế từ Google Sheets xã Tân Phú"))
            conn.commit()

        self._cache.clear()
        return {
            "success": True,
            "message": f"Đã đồng bộ thành công {count_updated} tuyến đường chính thức từ Google Sheets Xã Tân Phú, tỉnh Tây Ninh!",
            "count": count_updated
        }

    def get_system_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM log_hethong ORDER BY thoi_gian DESC LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]

storage = StorageService()
