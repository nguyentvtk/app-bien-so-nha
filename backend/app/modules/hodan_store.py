"""
Module dữ liệu HỘ DÂN & THỬA ĐẤT — kết nối sonha_database.db (UBND Xã Tân Phú)
=============================================================================

Lớp HoDanStore quản lý bảng `ho_dan_dat_dai` (tạo bởi scripts/import_excel_to_db.py)
và chỉ mục tìm kiếm toàn văn `ho_dan_fts` phục vụ ô tìm kiếm duy nhất.

Điểm nổi bật — TÌM KIẾM TOÀN VĂN KHÔNG PHÂN BIỆT DẤU TIẾNG VIỆT:
    Toàn bộ văn bản (tên chủ hộ, địa chỉ, ấp, tờ/thửa, loại đất...) được
    chuẩn hoá về dạng KHÔNG DẤU, chữ thường ("Nguyễn Văn Quân" -> "nguyen van quan")
    trước khi đưa vào chỉ mục; từ khoá người gõ cũng được chuẩn hoá như vậy.
    => Gõ "nguyen van quan" hay "Nguyễn Văn Quân" đều ra cùng kết quả,
       hỗ trợ tiền tố kiểu autocomplete ("nguyen van q*").
    Chỉ mục dùng FTS5 của SQLite (truy vấn dưới vài mili-giây cho ~7.400 bản ghi);
    nếu bản SQLite không có FTS5 thì tự tạo bảng thường + tìm LIKE thay thế.

CSDL: backend/data/sonha_database.db (độc lập với sonha.db của phân hệ số nhà).
"""

from __future__ import annotations

import logging
import os
import re
import sqlite3
import time
import unicodedata
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Các cột văn bản được đưa vào chỉ mục toàn văn (đã chuẩn hoá không dấu)
FTS_COLUMNS = ["ho_ten", "dia_chi", "ap", "xa", "so_to", "so_thua", "loai_dat",
               "tinh_trang_gcn", "phan_loai", "ghi_chu", "sdt"]

# Ánh xạ cột chỉ mục <-> cột bảng chính ho_dan_dat_dai
FTS_SOURCE = {
    "ho_ten": "ho_ten_chu_ho",
    "dia_chi": "dia_chi_hien_trang",
    "ap": "ap",
    "xa": "xa",
    "so_to": "so_to",
    "so_thua": "so_thua",
    "loai_dat": "loai_dat",
    "tinh_trang_gcn": "tinh_trang_gcn",
    "phan_loai": "phan_loai_du_lieu",
    "ghi_chu": "ghi_chu",
    "sdt": "so_dien_thoai",
}

# Các trường cho phép cập nhật qua API (không gồm id & thông tin nguồn dữ liệu)
CAP_NHAT_FIELDS = {
    "ho_ten_chu_ho", "so_dien_thoai", "dia_chi_hien_trang", "so_to", "so_thua",
    "dien_tich", "loai_dat", "tinh_trang_gcn", "toa_do_gps", "loai_ban_ghi",
    "xa", "ap", "stt_nha", "stt_ho", "so_nhan_khau", "phan_loai_du_lieu",
    "thong_tin_thieu", "ghi_chu",
}


def bo_dau(text: Any) -> str:
    """Chuẩn hoá văn bản tiếng Việt về dạng không dấu, chữ thường, gọn khoảng trắng.

    "Nguyễn Văn Quân" -> "nguyen van quan"; "Đông" -> "dong"; "Tân Phú" -> "tan phu".
    """
    if text is None:
        return ""
    text = unicodedata.normalize("NFD", str(text))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = unicodedata.normalize("NFC", text).replace("đ", "d").replace("Đ", "d")
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return re.sub(r"\s{2,}", " ", text).strip()


def tach_tu(tu_khoa: str, max_token: int = 8) -> list[str]:
    """Tách từ khoá thành token hợp lệ cho chỉ mục (đã bỏ dấu), giới hạn số token."""
    return [t for t in bo_dau(tu_khoa).split() if t][:max_token]


# Từ "chỉ dẫn" người dùng hay gõ kèm (tờ, thửa, số, ấp...) — nếu tìm chặt không ra
# kết quả nào, hệ thống sẽ bỏ qua các từ này và thử lại.
TU_CHI_DAN = {"to", "thua", "so", "ap", "xa", "thon", "to", "ho", "nha", "dat"}


class HoDanStore:
    """Lớp truy cập dữ liệu ho_dan_dat_dai + chỉ mục toàn văn ho_dan_fts."""

    def __init__(self, db_path: Optional[str] = None):
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # Serverless (Vercel): chuyển CSDL sang /tmp qua SONHA_DATA_DIR
        data_dir = os.environ.get("SONHA_DATA_DIR") or os.path.join(backend_dir, "data")
        self.db_path = db_path or os.path.join(data_dir, "sonha_database.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.fts_ho_tro = False  # True nếu ho_dan_fts là bảng ảo FTS5
        self.khoi_tao()

    # ------------------------------------------------------------------
    # Kết nối & khởi tạo
    # ------------------------------------------------------------------
    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def khoi_tao(self) -> None:
        """Đảm bảo bảng & chỉ mục tồn tại; tự đồng bộ FTS nếu lệch số dòng."""
        with self.get_connection() as conn:
            if not conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='ho_dan_dat_dai'"
            ).fetchone():
                raise RuntimeError(
                    "Chưa tìm thấy bảng 'ho_dan_dat_dai' trong sonha_database.db. "
                    "Hãy chạy: python3 backend/scripts/import_excel_to_db.py --reset"
                )
            self._tao_chi_muc(conn)
            n_chinh = conn.execute("SELECT COUNT(*) FROM ho_dan_dat_dai").fetchone()[0]
            n_fts = conn.execute("SELECT COUNT(*) FROM ho_dan_fts").fetchone()[0]
            if n_chinh != n_fts:
                logger.info("Đồng bộ chỉ mục toàn văn: %s bản ghi (hiện có %s).", n_chinh, n_fts)
                self.dong_bo_fts(conn)

    def _tao_chi_muc(self, conn: sqlite3.Connection) -> None:
        """Tạo chỉ mục ho_dan_fts: FTS5 nếu khả dụng, ngược lại bảng thường.
        Nếu chỉ mục cũ thiếu cột (cấu trúc mới hơn) thì xoá xây lại."""
        da_co = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name='ho_dan_fts'"
        ).fetchone()
        if da_co:
            self.fts_ho_tro = "USING fts5" in (da_co["sql"] or "")
            cot_hien_co = {r["name"] for r in conn.execute(
                "PRAGMA table_info(ho_dan_fts)"
            ).fetchall()}
            if not set(FTS_COLUMNS).issubset(cot_hien_co):
                logger.info("Chỉ mục ho_dan_fts cũ thiếu cột — xoá và xây lại.")
                conn.execute("DROP TABLE ho_dan_fts")
                conn.commit()
            else:
                return
        cols = ", ".join(FTS_COLUMNS)
        try:
            conn.execute(
                f"CREATE VIRTUAL TABLE ho_dan_fts USING fts5({cols}, tokenize='unicode61')"
            )
            self.fts_ho_tro = True
        except sqlite3.OperationalError as exc:
            logger.warning("SQLite không hỗ trợ FTS5 (%s) — dùng bảng thường + LIKE.", exc)
            conn.execute(
                f"CREATE TABLE ho_dan_fts (rowid INTEGER PRIMARY KEY, {cols.replace(' ', ' TEXT, ')} TEXT)"
            )
            self.fts_ho_tro = False
        conn.commit()

    # ------------------------------------------------------------------
    # Đồng bộ / bảo trì chỉ mục
    # ------------------------------------------------------------------
    def _chen_fts(self, conn: sqlite3.Connection, row: sqlite3.Row) -> None:
        cols = ", ".join(FTS_COLUMNS)
        marks = ", ".join("?" for _ in FTS_COLUMNS)
        conn.execute(
            f"INSERT INTO ho_dan_fts(rowid, {cols}) VALUES (?, {marks})",
            [row["id"], *[bo_dau(row[FTS_SOURCE[c]]) for c in FTS_COLUMNS]],
        )

    def dong_bo_fts(self, conn: Optional[sqlite3.Connection] = None) -> int:
        """Xây lại toàn bộ chỉ mục từ bảng chính. Trả về số dòng đã đánh chỉ mục."""
        tu_noi = conn is None
        conn = conn or self.get_connection()
        try:
            ban_ghi = conn.execute("SELECT * FROM ho_dan_dat_dai ORDER BY id").fetchall()
            conn.execute("DELETE FROM ho_dan_fts")
            cols = ", ".join(FTS_COLUMNS)
            marks = ", ".join("?" for _ in FTS_COLUMNS)
            conn.executemany(
                f"INSERT INTO ho_dan_fts(rowid, {cols}) VALUES (?, {marks})",
                [(r["id"], *[bo_dau(r[FTS_SOURCE[c]]) for c in FTS_COLUMNS]) for r in ban_ghi],
            )
            if tu_noi:
                conn.commit()
            return len(ban_ghi)
        finally:
            if tu_noi:
                conn.close()

    # ------------------------------------------------------------------
    # TÌM KIẾM TOÀN VĂN (ô tìm kiếm duy nhất)
    # ------------------------------------------------------------------
    def tim_kiem(
        self,
        tu_khoa: str,
        limit: int = 20,
        offset: int = 0,
        loai_ban_ghi: Optional[str] = None,
        ap: Optional[str] = None,
    ) -> dict[str, Any]:
        """Tìm kiếm không phân biệt dấu trên mọi trường: tên chủ hộ, địa chỉ, ấp,
        xã, số tờ, số thửa, loại đất, tình trạng GCN, ghi chú..."""
        bat_dau = time.perf_counter()
        tokens = tach_tu(tu_khoa)

        if not tokens:
            return {
                "tu_khoa": tu_khoa or "",
                "tokens": [],
                "phuong_thuc": None,
                "chien_luoc": None,
                "tong_so_ket_qua": 0,
                "thoi_gian_tra_cuu_ms": 0.0,
                "ket_qua": [],
                "thong_bao": "Vui lòng nhập từ khoá tìm kiếm "
                             "(tên chủ hộ, địa chỉ, ấp, số tờ, số thửa...).",
            }

        # Chiến lược tìm kiếm descending: chặt nhất trước, nới dần nếu 0 kết quả
        #  1. AND    — mọi token đều phải xuất hiện
        #  2. BO_TU_CHI_DAN — bỏ các từ chỉ dẫn (tờ, thửa, số...) rồi AND lại
        #  3. OR     — chỉ cần 1 token xuất hiện (dành từ khoá gõ dở/sai chính tả)
        chien_luoc = "AND"
        if self.fts_ho_tro:
            thu_tu = [("AND", tokens)]
            tokens_sach = [t for t in tokens if t not in TU_CHI_DAN]
            if tokens_sach and tokens_sach != tokens:
                thu_tu.append(("BO_TU_CHI_DAN", tokens_sach))
            if len(tokens) > 1:
                thu_tu.append(("OR", tokens))
            for ten_chien_luoc, toks in thu_tu:
                ket_qua, dem, cach = self._tim_kiem_fts(
                    toks, limit, offset, loai_ban_ghi, ap, or_mode=(ten_chien_luoc == "OR")
                )
                chien_luoc = ten_chien_luoc
                if dem:
                    break
        else:
            ket_qua, dem, cach = self._tim_kiem_like(tokens, limit, offset, loai_ban_ghi, ap)
            chien_luoc = "AND (LIKE)"

        hoan_thanh = round((time.perf_counter() - bat_dau) * 1000, 2)
        thong_bao = (
            f"Đã tìm thấy {dem} kết quả cho từ khoá \"{tu_khoa}\"."
            if dem else
            f"Không tìm thấy kết quả nào cho từ khoá \"{tu_khoa}\". "
            "Gợi ý: thử từ ngắn hơn, cắt bớt từ cuối hoặc kiểm tra lại cách viết."
        )
        return {
            "tu_khoa": tu_khoa,
            "tokens": tokens,
            "phuong_thuc": cach,
            "chien_luoc": chien_luoc,
            "tong_so_ket_qua": dem,
            "thoi_gian_tra_cuu_ms": hoan_thanh,
            "ket_qua": ket_qua,
            "thong_bao": thong_bao,
        }

    def _dieu_kien_bo_loc(self, loai_ban_ghi: Optional[str], ap: Optional[str]):
        """Bộ lọc phụ (loại bản ghi, ấp — ấp so khớp không dấu) dùng chung 2 chế độ."""
        dieu_kien, tham_so = [], []
        if loai_ban_ghi:
            dieu_kien.append("h.loai_ban_ghi = ?")
            tham_so.append(loai_ban_ghi)
        if ap:
            dieu_kien.append("ho_dan_fts.ap = ?")
            tham_so.append(bo_dau(ap))
        return dieu_kien, tham_so

    def _tim_kiem_fts(
        self,
        tokens: list[str],
        limit: int,
        offset: int,
        loai_ban_ghi: Optional[str],
        ap: Optional[str],
        or_mode: bool = False,
    ) -> tuple[list[dict], int, str]:
        """Chế độ FTS5: mỗi token thành 1 tiền tố, AND-ed (hoặc OR nếu or_mode);
        xếp hạng bm25.

        Lưu ý: SQLite build này không nhận alias cho bảng FTS5 nên phải dùng
        tên đầy đủ `ho_dan_fts MATCH` / `bm25(ho_dan_fts)`.
        """
        joiner = " OR " if or_mode else " AND "
        fts_query = joiner.join(f'"{tok}"*' for tok in tokens)
        dieu_kien, tham_so = self._dieu_kien_bo_loc(loai_ban_ghi, ap)
        where = "ho_dan_fts MATCH ?" + "".join(f" AND {d}" for d in dieu_kien)
        params = [fts_query, *tham_so]
        base = (
            "FROM ho_dan_fts JOIN ho_dan_dat_dai h ON h.id = ho_dan_fts.rowid "
            f"WHERE {where}"
        )
        # Ưu tiên bản ghi trùng KHỚP CHÍNH XÁC toàn bộ cụm từ khoá trước,
        # sau đó mới đến mức liên quan bm25 (điểm bm25 càng âm càng liên quan).
        dung_chinh_xac = " ".join(tokens)
        order = (
            "ORDER BY (ho_dan_fts.ho_ten = ?) DESC, "
            "(ho_dan_fts.dia_chi = ?) DESC, diem_lien_quan, h.id"
        )
        order_params = [dung_chinh_xac, dung_chinh_xac]
        with self.get_connection() as conn:
            dem = conn.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]
            rows = conn.execute(
                f"SELECT h.*, bm25(ho_dan_fts) AS diem_lien_quan {base} "
                f"{order} LIMIT ? OFFSET ?",
                [*params, *order_params, limit, offset],
            ).fetchall()
        return [dict(r) for r in rows], dem, "FTS5"

    def _tim_kiem_like(
        self,
        tokens: list[str],
        limit: int,
        offset: int,
        loai_ban_ghi: Optional[str],
        ap: Optional[str],
    ) -> tuple[list[dict], int, str]:
        """Chế độ dự phòng (không có FTS5): LIKE trên các cột đã bỏ dấu."""
        nhom_dk = []
        params: list[Any] = []
        for tok in tokens:
            dieu_or = " OR ".join(f"ho_dan_fts.{c} LIKE ?" for c in FTS_COLUMNS)
            nhom_dk.append(f"({dieu_or})")
            params.extend(f"%{tok}%" for _ in FTS_COLUMNS)
        dieu_kien, tham_so = self._dieu_kien_bo_loc(loai_ban_ghi, ap)
        where = " AND ".join(nhom_dk) + "".join(f" AND {d}" for d in dieu_kien)
        params.extend(tham_so)
        base = (
            "FROM ho_dan_fts JOIN ho_dan_dat_dai h ON h.id = ho_dan_fts.rowid "
            f"WHERE {where}"
        )
        with self.get_connection() as conn:
            dem = conn.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]
            rows = conn.execute(
                f"SELECT h.* {base} ORDER BY h.id LIMIT ? OFFSET ?",
                [*params, limit, offset],
            ).fetchall()
        return [dict(r) for r in rows], dem, "LIKE"

    # ------------------------------------------------------------------
    # DANH SÁCH / CHI TIẾT
    # ------------------------------------------------------------------
    def danh_sach(
        self,
        limit: int = 50,
        offset: int = 0,
        ap: Optional[str] = None,
        loai_ban_ghi: Optional[str] = None,
        co_gcn: Optional[bool] = None,
        q: Optional[str] = None,
    ) -> dict[str, Any]:
        """Danh sách phân trang + bộ lọc; nếu có `q` thì chuyển sang tìm toàn văn."""
        if q and q.strip():
            return self.tim_kiem(q, limit=limit, offset=offset,
                                 loai_ban_ghi=loai_ban_ghi, ap=ap)

        dieu_kien, tham_so = [], []
        if ap:
            dieu_kien.append("ap = ?")
            tham_so.append(ap)
        if loai_ban_ghi:
            dieu_kien.append("loai_ban_ghi = ?")
            tham_so.append(loai_ban_ghi)
        if co_gcn is True:
            dieu_kien.append("tinh_trang_gcn LIKE 'Đã cấp%'")
        elif co_gcn is False:
            dieu_kien.append("(tinh_trang_gcn IS NULL OR tinh_trang_gcn NOT LIKE 'Đã cấp%')")
        where = ("WHERE " + " AND ".join(dieu_kien)) if dieu_kien else ""

        with self.get_connection() as conn:
            tong = conn.execute(
                f"SELECT COUNT(*) FROM ho_dan_dat_dai {where}", tham_so
            ).fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM ho_dan_dat_dai {where} ORDER BY id LIMIT ? OFFSET ?",
                [*tham_so, limit, offset],
            ).fetchall()
        return {
            "tong_so_ban_ghi": tong,
            "limit": limit,
            "offset": offset,
            "danh_sach": [dict(r) for r in rows],
        }

    def chi_tiet(self, id: int) -> Optional[dict]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM ho_dan_dat_dai WHERE id = ?", (id,)
            ).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # THÊM / SỬA / XOÁ (tự đồng bộ chỉ mục trong cùng giao dịch)
    # ------------------------------------------------------------------
    def them(self, du_lieu: dict[str, Any]) -> dict[str, Any]:
        fields = [k for k in CAP_NHAT_FIELDS if k in du_lieu and du_lieu[k] is not None]
        if not any(f in fields for f in ("ho_ten_chu_ho", "dia_chi_hien_trang")):
            raise ValueError(
                "Bản ghi mới phải có ít nhất họ tên chủ hộ hoặc địa chỉ hiện trạng."
            )
        # Giá trị mặc định cho các cột NOT NULL của bảng
        mac_dinh = {
            "loai_ban_ghi": du_lieu.get("loai_ban_ghi") or "HO_DAN",
            "nguon_file": du_lieu.get("nguon_file") or "Nhập qua API",
            "dong_nguon": du_lieu.get("dong_nguon") or 0,
        }
        for k, v in mac_dinh.items():
            if k not in fields:
                fields.append(k)
                du_lieu[k] = v
        cols = ", ".join(fields)
        marks = ", ".join("?" for _ in fields)
        with self.get_connection() as conn:
            cur = conn.execute(
                f"INSERT INTO ho_dan_dat_dai ({cols}) VALUES ({marks})",
                [du_lieu[f] for f in fields],
            )
            row = conn.execute(
                "SELECT * FROM ho_dan_dat_dai WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
            self._chen_fts(conn, row)
            conn.commit()
        return dict(row)

    def cap_nhat(self, id: int, du_lieu: dict[str, Any]) -> Optional[dict]:
        fields = [k for k in CAP_NHAT_FIELDS if k in du_lieu]
        if not fields:
            raise ValueError("Không có trường hợp lệ nào được gửi để cập nhật.")
        set_sql = ", ".join(f"{k} = ?" for k in fields)
        with self.get_connection() as conn:
            cur = conn.execute(
                f"UPDATE ho_dan_dat_dai SET {set_sql} WHERE id = ?",
                [du_lieu[f] for f in fields] + [id],
            )
            if cur.rowcount == 0:
                return None
            conn.execute("DELETE FROM ho_dan_fts WHERE rowid = ?", (id,))
            row = conn.execute("SELECT * FROM ho_dan_dat_dai WHERE id = ?", (id,)).fetchone()
            self._chen_fts(conn, row)
            conn.commit()
        return dict(row)

    def xoa(self, id: int) -> bool:
        with self.get_connection() as conn:
            cur = conn.execute("DELETE FROM ho_dan_dat_dai WHERE id = ?", (id,))
            if cur.rowcount == 0:
                return False
            conn.execute("DELETE FROM ho_dan_fts WHERE rowid = ?", (id,))
            conn.commit()
        return True

    # ------------------------------------------------------------------
    # THỐNG KÊ
    # ------------------------------------------------------------------
    def thong_ke(self) -> dict[str, Any]:
        with self.get_connection() as conn:
            tong, n_ho, n_thua = conn.execute(
                "SELECT COUNT(*), SUM(loai_ban_ghi='HO_DAN'), SUM(loai_ban_ghi='THUA_DAT') "
                "FROM ho_dan_dat_dai"
            ).fetchone()
            gcn_da_cap = conn.execute(
                "SELECT COUNT(*) FROM ho_dan_dat_dai WHERE tinh_trang_gcn LIKE 'Đã cấp%'"
            ).fetchone()[0]
            gcn_chua = conn.execute(
                "SELECT COUNT(*) FROM ho_dan_dat_dai WHERE tinh_trang_gcn LIKE 'Chưa có%'"
            ).fetchone()[0]
            theo_ap = conn.execute(
                "SELECT ap, COUNT(*) AS so_ho, SUM(COALESCE(so_nhan_khau,0)) AS nhan_khau "
                "FROM ho_dan_dat_dai WHERE loai_ban_ghi='HO_DAN' AND ap IS NOT NULL "
                "GROUP BY ap ORDER BY so_ho DESC"
            ).fetchall()
            theo_loai_dat = conn.execute(
                "SELECT loai_dat, COUNT(*) AS so_luong FROM ho_dan_dat_dai "
                "WHERE loai_dat IS NOT NULL GROUP BY loai_dat ORDER BY so_luong DESC"
            ).fetchall()
            co_gps = conn.execute(
                "SELECT COUNT(*) FROM ho_dan_dat_dai "
                "WHERE toa_do_gps IS NOT NULL AND toa_do_gps != ''"
            ).fetchone()[0]
            co_sdt = conn.execute(
                "SELECT COUNT(*) FROM ho_dan_dat_dai "
                "WHERE so_dien_thoai IS NOT NULL AND so_dien_thoai != ''"
            ).fetchone()[0]
        return {
            "tong_so_ban_ghi": tong or 0,
            "so_ho_dan": n_ho or 0,
            "so_thua_dat": n_thua or 0,
            "gcn_da_cap": gcn_da_cap,
            "gcn_chua_co": gcn_chua,
            "co_toa_do_gps": co_gps,
            "co_so_dien_thoai": co_sdt,
            "theo_ap": [dict(r) for r in theo_ap],
            "theo_loai_dat": [dict(r) for r in theo_loai_dat],
        }

    def danh_sach_ap(self) -> list[str]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT ap FROM ho_dan_dat_dai "
                "WHERE ap IS NOT NULL AND ap != '' ORDER BY ap"
            ).fetchall()
        return [r["ap"] for r in rows]


# Instance dùng chung toàn ứng dụng
try:
    ho_dan_store = HoDanStore()
except RuntimeError as exc:
    logger.error("Khởi tạo HoDanStore thất bại: %s", exc)
    ho_dan_store = None  # type: ignore[assignment]
