"""
Module ĐỘNG CƠ ĐÁNH SỐ NHÀ (numbering_engine.py)
=================================================

Vận dụng Thông tư 08/2024/TT-BXD (hiệu lực 15/10/2024) và chuẩn mực quốc tế,
cung cấp 2 chế độ đánh số tách bạch Đô thị / Nông thôn cho xã Tân Phú:

┌─────────────────────────────────────────────────────────────────────┐
│ CHẾ ĐỘ ĐÔ THỊ (DO_THI) — Tuần tự chẵn/lẻ kiểu Châu Âu               │
│ • Dãy bên TRÁI chiều đánh số: số LẺ (1, 3, 5...)                    │
│ • Dãy bên PHẢI: số CHẴN (2, 4, 6...)                                │
│ • Nhà chèn giữa (tách thửa phát sinh): số phụ chữ in hoa            │
│   20A, 20B... hoặc 20-1, 20-2 (TT 08/2024/TT-BXD)                   │
│ • Ưu điểm: quen thuộc, dễ đọc — Nhược: phải "chừa số" cho đất trống  │
├─────────────────────────────────────────────────────────────────────┤
│ CHẾ ĐỘ NÔNG THÔN (NONG_THON) — Đánh số theo khoảng cách (Úc/Mỹ)     │
│ • Số nhà = khoảng cách thực (mét) từ ĐẦU TUYẾN đến cổng nhà ÷ 10    │
│   (quy ước 1 đơn vị = 10 m; nhà cách 1.590 m → số 159)              │
│ • Chẵn/lễ vẫn giữ: trái = lẻ, phải = chẵn (làm tròn sát cạnh)       │
│ • Giải QUYẾT vĩnh viễn bài toán "đất trống" của nông thôn:          │
│   lô đất nào xây sau cũng tự có số bằng cách đo mét, không cần      │
│   chừa số, không bao giờ phải dùng số phụ A/B/C.                    │
└─────────────────────────────────────────────────────────────────────┘

Toạ độ chiếu: tuyến đường hiện lưu dạng đoạn thẳng WGS84 (điểm đầu→cuối).
Việc "đo khoảng cách" được thực hiện bằng phép chiếu vuông góc toạ độ
nhà lên tim tuyến (along-track distance) — phù hợp ứng dụng GIS
theo yêu cầu của UBND xã Tân Phú.
"""

from __future__ import annotations

import math
import re
from typing import Any, Optional

from app.modules.storage import storage, StorageService

# 1 đơn vị số nhà ở chế độ nông thôn = 10 mét (quy ước Úc/New Zealand)
MET_MOI_DON_VI = 10.0
MOT_DO_LAT_MET = 110574.0
MOT_DO_LNG_MET = 111320.0

SO_DAU_TIEN = {"trai": 1, "phai": 2}  # trái=lẻ, phải=chẵn


class NumberingEngine:
    """Đề xuất số nhà theo 2 chế độ: Đô thị (tuần tự) / Nông thôn (khoảng cách)."""

    def __init__(self, storage: StorageService):
        self.storage = storage

    # ------------------------------------------------------------------
    # A. CHẾ ĐỘ ĐÔ THỊ — tuần tự chẵn/lẻ + số phụ cho nhà chèn giữa
    # ------------------------------------------------------------------
    @staticmethod
    def _tach_so(so_nha_moi: str) -> Optional[int]:
        """Lấy số nguyên ĐẦU TIÊN gặp trong chuỗi số nhà (VD '20A Đường X' → 20,
        'DT-100/125' → 100, '159' → 159). Chấp nhận nhiều định dạng dữ liệu thật."""
        m = re.search(r"\d+", str(so_nha_moi or ""))
        return int(m.group(0)) if m else None

    def de_xuat_do_thi(
        self,
        id_tuyen: str,
        phia: Optional[str] = None,
        chen_sau_so: Optional[int] = None,
    ) -> dict[str, Any]:
        """Đề xuất số theo tuần tự chẵn/lẻ (đô thị).

        phia: 'trai' (lẻ) | 'phai' (chẵn) | None (tự chọn phía số kế tiếp)
        chen_sau_so: nếu có → nhà MỚI XÂY CHÈN giữa, sinh số phụ 20A/20B...
        """
        ds = self.storage.get_all_so_nha(id_tuyen)
        if not any(t["id_tuyen"] == id_tuyen for t in self.storage.get_all_tuyen_duong()):
            raise LookupError(f"Không tìm thấy tuyến đường '{id_tuyen}'.")
        cac_so = {}
        cac_so_phu = set()
        for sn in ds:
            n = self._tach_so(sn.get("so_nha_moi", ""))
            if n is None:
                continue
            cac_so.setdefault(n, []).append(sn.get("so_nha_moi", ""))
            # Ghi nhận các số phụ dạng "20A", "20-1" để không cấp trùng
            m = re.match(rf"^\s*{n}\s*([A-Z]|\-\d+)", str(sn.get("so_nha_moi", "")))
            if m:
                cac_so_phu.add(f"{n}{m.group(1)}")

        # --- Trường hợp NHÀ CHÈN GIỮA: sinh số phụ theo TT 08/2024 ---
        if chen_sau_so is not None:
            for kitu in ["A", "B", "C", "D", "E", "F", "G", "H"]:
                ung_vien = f"{chen_sau_so}{kitu}"
                if ung_vien not in cac_so_phu and not any(
                    str(sn.get("so_nha_moi", "")).strip().upper().startswith(ung_vien) for sn in ds
                ):
                    return {
                        "che_do": "DO_THI",
                        "so_de_xuat": ung_vien,
                        "phia": None,
                        "giai_thich": (
                            f"Nhà phát sinh chèn sau số {chen_sau_so} (tách thửa giữa dòng phố) "
                            f"→ cấp số phụ '{ung_vien}' theo Thông tư 08/2024/TT-BXD "
                            f"(chữ in hoa nối sau số nhà gốc)."
                        ),
                        "so_luong_da_cap_tren_tuyen": len(ds),
                    }
            return {
                "che_do": "DO_THI", "so_de_xuat": f"{chen_sau_so}-1",
                "phia": None,
                "giai_thich": f"Đã dùng hết số phụ A–H sau số {chen_sau_so}, đề xuất dạng gạch ngang {chen_sau_so}-1.",
                "so_luong_da_cap_tren_tuyen": len(ds),
            }

        # --- Cấp SỐ MỚI TUẦN TỰ: tiếp dãy chẵn/lẻ theo phía ---
        def max_so(theo_le: bool) -> int:
            vals = [n for n in cac_so if (n % 2 == 1) == theo_le]
            return max(vals) if vals else 0

        if phia not in ("trai", "phai"):
            # Tự chọn: phía nào còn dãy nhỏ hơn thì tiếp phía đó (ưu tiên lẻ trái)
            phia = "trai" if max_so(True) <= max_so(False) else "phai"
        la_le = (phia == "trai")
        lon_nhat = max_so(la_le)
        so_moi = (lon_nhat + 2) if lon_nhat else SO_DAU_TIEN[phia]

        # Phòng trùng ngoại lệ (số trùng do dữ liệu lạ) → tăng dần 2 đơn vị
        while any(self._tach_so(sn.get("so_nha_moi", "")) == so_moi for sn in ds):
            so_moi += 2

        return {
            "che_do": "DO_THI",
            "so_de_xuat": str(so_moi),
            "phia": phia,
            "giai_thich": (
                f"Chế độ Đô thị — tuần tự chẵn/lẻ: dãy bên {'trái (số lẻ)' if la_le else 'phải (số chẵn)'} "
                f"hiện lớn nhất là {lon_nhat or 'chưa có'} → đề xuất tiếp {so_moi}. "
                f"Lưu ý: cần chừa số dự trữ cho đất trống theo quy hoạch."
            ),
            "so_luong_da_cap_tren_tuyen": len(ds),
        }

    # ------------------------------------------------------------------
    # B. CHẾ ĐỘ NÔNG THÔN — đánh số theo KHOẢNG CÁCH (1 số = 10 m)
    # ------------------------------------------------------------------
    def de_xuat_nong_thon(
        self,
        id_tuyen: str,
        toado_gps: dict,
    ) -> dict[str, Any]:
        """Chiếu toạ độ nhà lên tim tuyến → khoảng cách từ đầu tuyến → số nhà.

        Quy tắc: số = round(khoảng_cách_m / 10); bên TRÁI = lẻ, bên PHẢI = chẵn
        (làm tròn đến số chẵn/lẻ sát nhất). Không cần chừa số đất trống.
        """
        tuyen = next((t for t in self.storage.get_all_tuyen_duong()
                      if t["id_tuyen"] == id_tuyen), None)
        if not tuyen:
            raise LookupError(f"Không tìm thấy tuyến đường '{id_tuyen}'.")

        a, b = tuyen["toado_batdau"], tuyen["toado_kethuc"]
        e_lng = MOT_DO_LNG_MET * math.cos(math.radians((a["lat"] + b["lat"]) / 2))
        ax = (b["lng"] - a["lng"]) * e_lng           # vectơ tim tuyến (mét, Đông)
        ay = (b["lat"] - a["lat"]) * MOT_DO_LAT_MET  # (mét, Bắc)
        px = (toado_gps["lng"] - a["lng"]) * e_lng   # vectơ đầu tuyến → nhà
        py = (toado_gps["lat"] - a["lat"]) * MOT_DO_LAT_MET

        dai_tuyen = math.hypot(ax, ay)  # chiều dài tim tuyến (m)
        if dai_tuyen < 1:
            return {"che_do": "NONG_THON", "so_de_xuat": None,
                    "giai_thich": "Tuyến đường quá ngắn (<1 m), không thể suy số theo khoảng cách. Hãy hiệu chỉnh toạ độ tuyến trước."}

        # Along-track: khoảng cách chiếu từ ĐẦU TUYẾN đến chân chiếu của nhà
        khoang_cach = (px * ax + py * ay) / dai_tuyen
        # Cross-track: dấu tích có hướng quyết định nhà bên trái hay phải
        cross = (ax * py - ay * px) / dai_tuyen
        phia = "trai" if cross >= 0 else "phai"  # nhìn theo chiều đầu→cuối tuyến

        khoang_cach = max(0.0, khoang_cach)
        so_goc = int(round(khoang_cach / MET_MOI_DON_VI))
        la_le = (phia == "trai")
        # Làm tròn cho đúng quy luật chẵn/lẻ: trái=lẻ, phải=chẵn
        if la_le and so_goc % 2 == 0:
            so_goc += 1
        elif (not la_le) and so_goc % 2 == 1:
            so_goc += 1
        if so_goc == 0:
            so_goc = 1 if la_le else 2

        # Phòng hiếm: cùng số cùng tuyến (hai cổng trùng khoảng cách) → nhích +2
        ds = self.storage.get_all_so_nha(id_tuyen)
        da_trung = {self._tach_so(sn.get("so_nha_moi", "")) for sn in ds}
        while so_goc in da_trung:
            so_goc += 2

        return {
            "che_do": "NONG_THON",
            "so_de_xuat": str(so_goc),
            "phia": phia,
            "khoang_cach_tu_dau_tuyen_m": round(khoang_cach, 1),
            "dai_tuyen_m": round(dai_tuyen, 1),
            "so_luong_da_cap_tuyen": len(ds),
            "giai_thich": (
                f"Chế độ Nông thôn — đánh số theo khoảng cách (chuẩn Úc/Mỹ): "
                f"cổng nhà cách ĐẦU tuyến {khoang_cach:,.0f} m, nằm bên {'TRÁI' if la_le else 'PHẢI'} "
                f"chiều đánh số → số nhà = {khoang_cach:,.0f} ÷ 10 ≈ <b>{so_goc}</b> "
                f"({'số lẻ - bên trái' if la_le else 'số chẵn - bên phải'}). "
                f"Đất trống tương lai không cần chừa số: xây tới đâu đo mét tới đó."
            ),
        }

    # ------------------------------------------------------------------
    # Điều phối theo chế độ
    # ------------------------------------------------------------------
    def de_xuat(
        self,
        che_do: str,
        id_tuyen: str,
        toado_gps: Optional[dict] = None,
        phia: Optional[str] = None,
        chen_sau_so: Optional[int] = None,
    ) -> dict[str, Any]:
        if che_do == "DO_THI":
            return self.de_xuat_do_thi(id_tuyen, phia=phia, chen_sau_so=chen_sau_so)
        if che_do == "NONG_THON":
            if not toado_gps:
                raise ValueError(
                    "Chế độ Nông thôn cần toạ độ GPS của nhà (bấm nút 'Lấy vị trí hiện tại' "
                    "hoặc ghim trên bản đồ) để đo khoảng cách từ đầu tuyến."
                )
            return self.de_xuat_nong_thon(id_tuyen, toado_gps)
        raise ValueError("Chế độ đánh số không hợp lệ — chỉ nhận 'DO_THI' hoặc 'NONG_THON'.")


# Instance dùng chung toàn ứng dụng
numbering_engine = NumberingEngine(storage)
