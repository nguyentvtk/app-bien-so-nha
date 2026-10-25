"""
Module HIỆU CHỈNH TOẠ ĐỘ TUYẾN ĐƯỜNG TOÀN XÃ (route_calibrator.py)
====================================================================

Bài toán: toạ độ WGS84 của các tuyến đường trong CSDL bị lệch hệ thống
(sinh tự tạo theo lưới, không khớp thực địa xã Tân Phú). Người dùng chỉ cần
SỬA 2 ĐIỂM CHUẨN (điểm đầu & điểm cuối) của 1 tuyến — module tự suy ra
phép biến đổi đồng dạng (similarity / Helmert 2 điểm) và ÁP DỤNG cho toàn bộ
các tuyến đường còn lại, đồng thời (tùy chọn) cả toạ độ GPS của số nhà.

Toán học: 2 cặp điểm tương ứng (A1→B1, A2→B2) xác định duy nhất phép biến đổi:
    Q = s · R(θ) · (P − A1) + B1        (R(θ): xoay, s: tỉ lệ, + B1: dịch)
- Chuyển sang mặt phẳng mét địa phương (chiếu gần đúng theo vĩ độ) để
  xoay/tỉ lệ có nghĩa vật lý (độ, %).
- Trường hợp đặc biệt A1≈A2 (tuyến chuẩn 2 điểm trùng nhau): suy ra
  phép DỊCH CHUYỂN THUẦN TUÝ (s=1, θ=0) — phổ biến khi dữ liệu chỉ lệch offset.
- Tuyến chuẩn được ghi ĐÚNG toạ độ người dùng nhập (không chịu sai số làm tròn).

An toàn dữ liệu:
- Mỗi lần áp dụng, toàn bộ toạ độ cũ được sao lưu vào bảng `sao_luu_toa_do`
  (theo phiên bản) → có thể HOÀN TÁC bằng 1 lệnh.
- Mọi thao tác ghi nhật ký vào `log_hethong` phục vụ kiểm toán UBND xã.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any, Optional

from app.modules.storage import storage, StorageService

# Hệ số quy đổi độ ↔ mét (xấp xỉ đủ chính xác ở tầm vài km)
MOT_DO_LAT_MET = 110574.0   # chiều dài 1° vĩ độ ≈ 110.574 km
MOT_DO_LNG_MET = 111320.0   # chiều dài 1° kinh độ tại xích đạo


def _met_moi_do_lng(lat: float) -> float:
    return MOT_DO_LNG_MET * math.cos(math.radians(lat))


class RouteCalibrator:
    """Hiệu chỉnh toạ độ tuyến đường theo 2 điểm chuẩn, lan toả toàn xã."""

    def __init__(self, storage: StorageService):
        self.storage = storage

    # ------------------------------------------------------------------
    # Toán học phép biến đổi đồng dạng
    # ------------------------------------------------------------------
    @staticmethod
    def _tinh_phep_doi(a1: dict, a2: dict, b1: dict, b2: dict) -> dict[str, Any]:
        """Tính tham số Q = s·R(θ)·(P−A1)+B1 từ 2 cặp điểm (A→B).

        Trả về dict gồm: b1 (điểm neo mới), e_lat/e_lng (hệ số quy đổi tại B1),
        s (tỉ lệ), cos_t/sin_t (góc xoay), va(x,y) & vb(x,y) vectơ hướng cũ/mới.
        """
        e_lng_a = _met_moi_do_lng(a1["lat"])
        e_lng_b = _met_moi_do_lng(b1["lat"])
        va = ((a2["lng"] - a1["lng"]) * e_lng_a, (a2["lat"] - a1["lat"]) * MOT_DO_LAT_MET)
        vb = ((b2["lng"] - b1["lng"]) * e_lng_b, (b2["lat"] - b1["lat"]) * MOT_DO_LAT_MET)
        la = math.hypot(*va)
        lb = math.hypot(*vb)
        if la < 1.0:  # 2 điểm chuẩn cũ gần trùng → phép dịch thuần tuý
            s, cos_t, sin_t = 1.0, 1.0, 0.0
        else:
            s = lb / la
            cos_t = (va[0] * vb[0] + va[1] * vb[1]) / (la * lb)
            sin_t = (va[0] * vb[1] - va[1] * vb[0]) / (la * lb)
        return {"b1": b1, "e_lat": MOT_DO_LAT_MET, "e_lng": e_lng_b,
                "s": s, "cos_t": cos_t, "sin_t": sin_t,
                "dai_cu_m": la, "dai_moi_m": lb}

    @staticmethod
    def _ap_dung_diem_an_toan(T: dict[str, Any], a1: dict, p: dict) -> dict:
        """Q = s·R(θ)·(P−A1)+B1. Cần A1 (điểm neo cũ) vì hiệu toạ độ lấy theo A1."""
        e_lng_a = _met_moi_do_lng(a1["lat"])
        ex = (p["lng"] - a1["lng"]) * e_lng_a
        ey = (p["lat"] - a1["lat"]) * MOT_DO_LAT_MET
        x2 = T["s"] * (T["cos_t"] * ex - T["sin_t"] * ey)
        y2 = T["s"] * (T["sin_t"] * ex + T["cos_t"] * ey)
        return {"lat": round(T["b1"]["lat"] + y2 / T["e_lat"], 6),
                "lng": round(T["b1"]["lng"] + x2 / T["e_lng"], 6)}

    @staticmethod
    def _khoang_cach_m(p: dict, q: dict) -> float:
        e_lng = _met_moi_do_lng((p["lat"] + q["lat"]) / 2)
        return math.hypot((q["lng"] - p["lng"]) * e_lng,
                          (q["lat"] - p["lat"]) * MOT_DO_LAT_MET)

    # ------------------------------------------------------------------
    # XEM TRƯỚC & ÁP DỤNG
    # ------------------------------------------------------------------
    def du_bao(
        self,
        id_tuyen_chuan: str,
        batdau_moi: dict,
        kethuc_moi: dict,
        ap_dung_so_nha: bool = False,
    ) -> dict[str, Any]:
        """Tính toán trước (KHÔNG ghi CSDL): tham số phép đổi + danh sách
        toạ độ mới của mọi tuyến, phục vụ nút 'Xem trước ảnh hưởng'."""
        tuyen_list = self.storage.get_all_tuyen_duong()
        chuan = next((t for t in tuyen_list if t["id_tuyen"] == id_tuyen_chuan), None)
        if not chuan:
            raise LookupError(f"Không tìm thấy tuyến đường chuẩn '{id_tuyen_chuan}'.")

        a1, a2 = chuan["toado_batdau"], chuan["toado_kethuc"]
        b1, b2 = batdau_moi, kethuc_moi
        T = self._tinh_phep_doi(a1, a2, b1, b2)

        dich_chuyen_m = self._khoang_cach_m(a1, b1)
        xoay_do = math.degrees(math.atan2(T["sin_t"], T["cos_t"]))
        tong_dich = 0.0
        ket_qua = []
        for t in tuyen_list:
            cu_dau, cu_cuoi = t["toado_batdau"], t["toado_kethuc"]
            if t["id_tuyen"] == id_tuyen_chuan:
                # Tuyến chuẩn nhận đúng toạ độ người dùng nhập
                moi_dau, moi_cuoi = b1, b2
            else:
                moi_dau = self._ap_dung_diem_an_toan(T, a1, cu_dau)
                moi_cuoi = self._ap_dung_diem_an_toan(T, a1, cu_cuoi)
            dich = self._khoang_cach_m(cu_dau, moi_dau)
            tong_dich += dich
            ket_qua.append({
                "id_tuyen": t["id_tuyen"],
                "ten_duong": t["ten_duong"],
                "cu_batdau": {"lat": cu_dau["lat"], "lng": cu_dau["lng"]},
                "cu_kethuc": {"lat": cu_cuoi["lat"], "lng": cu_cuoi["lng"]},
                "moi_batdau": moi_dau,
                "moi_kethuc": moi_cuoi,
                "dich_chuyen_m": round(dich, 1),
            })

        # Ước lượng số nhà sẽ chịu ảnh hưởng (nếu bật tùy chọn)
        so_nha_affected = 0
        if ap_dung_so_nha:
            so_nha_affected = len(self.storage.get_all_so_nha())

        return {
            "tuyen_chuan": {
                "id_tuyen": chuan["id_tuyen"],
                "ten_duong": chuan["ten_duong"],
                "cu_batdau": a1, "cu_kethuc": a2,
                "moi_batdau": b1, "moi_kethuc": b2,
            },
            "phep_bien_doi": {
                "dich_chuyen_m": round(dich_chuyen_m, 1),
                "xoay_do": round(xoay_do, 2),
                "ty_le": round(T["s"], 6),
                "do_dai_cu_m": round(T["dai_cu_m"], 1),
                "do_dai_moi_m": round(T["dai_moi_m"], 1),
                "mo_ta": (
                    "Dịch chuyển thuần tuý (không xoay, không đổi tỉ lệ)"
                    if abs(xoay_do) < 0.01 and abs(T["s"] - 1) < 1e-4
                    else f"Dịch {dich_chuan_text(dich_chuyen_m)}, xoay {xoay_do:.2f}°, tỉ lệ {T['s']:.4f}"
                ),
            },
            "so_tuyen_se_cap_nhat": len(ket_qua),
            "dich_chuyen_trung_binh_m": round(tong_dich / max(len(ket_qua), 1), 1),
            "so_nha_se_cap_nhat": so_nha_affected,
            "du_kien": ket_qua,
        }

    def ap_dung(
        self,
        id_tuyen_chuan: str,
        batdau_moi: dict,
        kethuc_moi: dict,
        ap_dung_so_nha: bool = False,
        ghi_chu: Optional[str] = None,
    ) -> dict[str, Any]:
        """Áp dụng thật: sao lưu toạ độ cũ → cập nhật toàn bộ → ghi nhật ký."""
        du_bao = self.du_bao(id_tuyen_chuan, batdau_moi, kethuc_moi, ap_dung_so_nha)

        with self.storage.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sao_luu_toa_do (
                    phien_ban INTEGER NOT NULL,
                    loai        TEXT NOT NULL,
                    ma          TEXT NOT NULL,
                    du_lieu_cu   TEXT NOT NULL,
                    thoi_gian    TEXT NOT NULL
                )
            """)
            row = conn.execute("SELECT COALESCE(MAX(phien_ban), 0) FROM sao_luu_toa_do").fetchone()
            phien_ban = (row[0] if row else 0) + 1
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 1) Sao lưu toạ độ cũ của mọi tuyến
            for t in du_bao["du_kien"]:
                conn.execute(
                    "INSERT INTO sao_luu_toa_do VALUES (?, 'TUYEN_DUONG', ?, ?, ?)",
                    (phien_ban, t["id_tuyen"],
                     json.dumps({"toado_batdau": t["cu_batdau"], "toado_kethuc": t["cu_kethuc"]},
                                ensure_ascii=False), now)
                )

            # 2) Cập nhật toạ độ tuyến
            conn.executemany(
                "UPDATE tuyen_duong SET toado_batdau = ?, toado_kethuc = ? WHERE id_tuyen = ?",
                [(json.dumps(t["moi_batdau"], ensure_ascii=False),
                  json.dumps(t["moi_kethuc"], ensure_ascii=False),
                  t["id_tuyen"]) for t in du_bao["du_kien"]]
            )

            # 3) (Tùy chọn) Lan toả sang toạ độ GPS của số nhà hiện hữu
            so_nha_da_cap_nhat = 0
            if ap_dung_so_nha:
                chuan = du_bao["tuyen_chuan"]
                a1 = chuan["cu_batdau"]
                T = self._tinh_phep_doi(a1, chuan["cu_kethuc"],
                                        chuan["moi_batdau"], chuan["moi_kethuc"])
                rows = conn.execute(
                    "SELECT id_nha, toado_gps FROM so_nha"
                ).fetchall()
                backups, updates = [], []
                for r in rows:
                    try:
                        gps = json.loads(r["toado_gps"])
                        if not isinstance(gps, dict) or "lat" not in gps or "lng" not in gps:
                            continue
                        moi = self._ap_dung_diem_an_toan(T, a1, gps)
                        backups.append((phien_ban, "SO_NHA", r["id_nha"],
                                        json.dumps(gps, ensure_ascii=False), now))
                        updates.append((json.dumps(moi, ensure_ascii=False), r["id_nha"]))
                    except (ValueError, TypeError, KeyError):
                        continue  # bỏ qua bản ghi toạ độ hỏng
                conn.executemany("INSERT INTO sao_luu_toa_do VALUES (?, ?, ?, ?, ?)", backups)
                conn.executemany("UPDATE so_nha SET toado_gps = ? WHERE id_nha = ?", updates)
                so_nha_da_cap_nhat = len(updates)

            # 4) Ghi nhật ký kiểm toán
            pb = du_bao["phep_bien_doi"]
            conn.execute(
                "INSERT INTO log_hethong (hanh_dong, doi_tuong, nguoi_thuc_hien, chi_tiet) "
                "VALUES (?, ?, ?, ?)",
                ("HIỆU CHỈNH TOẠ ĐỘ TUYẾN ĐƯỜNG",
                 id_tuyen_chuan,
                 "Cán bộ địa chính",
                 f"Chỉnh 2 điểm chuẩn tuyến {du_bao['tuyen_chuan']['ten_duong']} "
                 f"({pb['mo_ta']}); cập nhật {len(du_bao['du_kien'])} tuyến đường"
                 + (f" và {so_nha_da_cap_nhat} số nhà" if so_nha_da_cap_nhat else "")
                 + f"; bản sao lưu phiên #{phien_ban}"
                 + (f"; ghi chú: {ghi_chu}" if ghi_chu else ""))
            )
            conn.commit()

        # Xoá cache để frontend lấy toạ độ mới
        self.storage._cache.clear()

        return {
            "so_tuyen_da_cap_nhat": du_bao["so_tuyen_se_cap_nhat"],
            "so_nha_da_cap_nhat": so_nha_da_cap_nhat,
            "phien_ban_sao_luu": phien_ban,
            "phep_bien_doi": pb,
            "thong_bao": (
                f"Đã cập nhật toạ độ cho {du_bao['so_tuyen_se_cap_nhat']} tuyến đường"
                + (f" và {so_nha_da_cap_nhat} bản ghi số nhà" if so_nha_da_cap_nhat else "")
                + f". Bản sao lưu phiên #{phien_ban} — có thể hoàn tác."
            ),
        }

    def phuc_hoi(self) -> dict[str, Any]:
        """Hoàn tác lần hiệu chỉnh gần nhất (pop phiên sao lưu mới nhất)."""
        with self.storage.get_connection() as conn:
            row = conn.execute("SELECT MAX(phien_ban) FROM sao_luu_toa_do").fetchone()
            phien_ban = row[0] if row else None
            if not phien_ban:
                return {"thanh_cong": False,
                        "thong_bao": "Không có bản sao lưu toạ độ nào để hoàn tác."}

            rows = conn.execute(
                "SELECT loai, ma, du_lieu_cu FROM sao_luu_toa_do WHERE phien_ban = ?",
                (phien_ban,)
            ).fetchall()
            so_tuyen = so_nha = 0
            for r in rows:
                if r["loai"] == "TUYEN_DUONG":
                    d = json.loads(r["du_lieu_cu"])
                    conn.execute(
                        "UPDATE tuyen_duong SET toado_batdau = ?, toado_kethuc = ? WHERE id_tuyen = ?",
                        (json.dumps(d["toado_batdau"], ensure_ascii=False),
                         json.dumps(d["toado_kethuc"], ensure_ascii=False), r["ma"])
                    )
                    so_tuyen += 1
                elif r["loai"] == "SO_NHA":
                    conn.execute("UPDATE so_nha SET toado_gps = ? WHERE id_nha = ?",
                                 (r["du_lieu_cu"], r["ma"]))
                    so_nha += 1

            conn.execute("DELETE FROM sao_luu_toa_do WHERE phien_ban = ?", (phien_ban,))
            conn.execute(
                "INSERT INTO log_hethong (hanh_dong, doi_tuong, nguoi_thuc_hien, chi_tiet) "
                "VALUES (?, ?, ?, ?)",
                ("HOÀN TÁC HIỆU CHỈNH TOẠ ĐỘ", f"Phiên #{phien_ban}", "Cán bộ địa chính",
                 f"Phục hồi toạ độ cũ cho {so_tuyen} tuyến đường và {so_nha} số nhà.")
            )
            conn.commit()

        self.storage._cache.clear()
        return {"thanh_cong": True, "so_tuyen_phuc_hoi": so_tuyen, "so_nha_phuc_hoi": so_nha,
                "thong_bao": f"Đã hoàn tác: phục hồi toạ độ cũ cho {so_tuyen} tuyến đường"
                             + (f" và {so_nha} số nhà" if so_nha else "") + "."}


def dich_chuan_text(m: float) -> str:
    if m >= 1000:
        return f"{m/1000:.2f} km"
    return f"{m:.1f} m"


# Instance dùng chung
route_calibrator = RouteCalibrator(storage)
