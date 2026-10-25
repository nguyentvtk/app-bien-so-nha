"""
API HỘ DÂN & THỬA ĐẤT — kết nối sonha_database.db
=================================================

Bộ API phục vụ ô TÌM KIẾM DUY NHẤT (tìm kiếm toàn văn không phân biệt dấu
tiếng Việt, < 2ms cho 7.400+ bản ghi) và CRUD hồ sơ hộ dân / thửa đất.

Điểm cuối chính:
    GET  /api/ho-dan/tim-kiem?q=...   ← Ô tìm kiếm duy nhất (tên, địa chỉ,
                                        ấp, tờ/thửa, loại đất, GCN, SĐT...)
    GET  /api/ho-dan                   Danh sách phân trang + bộ lọc
    GET  /api/ho-dan/{id}              Chi tiết 1 bản ghi
    POST /api/ho-dan                   Thêm bản ghi mới
    PUT  /api/ho-dan/{id}              Cập nhật (gửi từng trường cần sửa)
    DELETE /api/ho-dan/{id}            Xoá bản ghi
    GET  /api/ho-dan/thong-ke          Thống kê theo ấp / loại đất / GCN
    GET  /api/ho-dan/danh-sach-ap      Danh sách ấp
    POST /api/ho-dan/fts/dong-bo       Xây lại chỉ mục toàn văn

Mọi phản hồi lỗi và thông báo đều bằng tiếng Việt.
"""

from typing import Optional, Literal

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import HoDanDatDaiCreate, HoDanDatDaiUpdate
from app.modules.hodan_store import ho_dan_store

router = APIRouter(
    prefix="/api/ho-dan",
    tags=["Hộ dân & Thửa đất (sonha_database.db)"],
)


def _kiem_tra_store():
    """Đảm bảo CSDL sonha_database.db sẵn sàng (báo lỗi tiếng Việt nếu chưa import)."""
    if ho_dan_store is None:
        raise HTTPException(
            status_code=503,
            detail="CSDL sonha_database.db chưa sẵn sàng. "
                   "Hãy chạy: python3 backend/scripts/import_excel_to_db.py --reset",
        )


# ===========================================================================
# TÌM KIẾM TOÀN VĂN — ô tìm kiếm duy nhất
# ===========================================================================
@router.get("/tim-kiem", summary="🔍 Tìm kiếm toàn văn (ô tìm kiếm duy nhất)")
def tim_kiem(
    q: str = Query(..., min_length=1, max_length=200,
                   description="Từ khoá: tên chủ hộ, địa chỉ, ấp, số tờ, số thửa, "
                               "loại đất, GCN, SĐT... (không cần gõ dấu)"),
    limit: int = Query(20, ge=1, le=200, description="Số kết quả tối đa (1-200)"),
    offset: int = Query(0, ge=0, description="Bỏ qua n kết quả đầu (phân trang)"),
    loai_ban_ghi: Optional[Literal["HO_DAN", "THUA_DAT"]] = Query(
        None, description="Lọc: HO_DAN (hộ dân) hoặc THUA_DAT (thửa đất rà soát)"),
    ap: Optional[str] = Query(None, max_length=50, description="Lọc theo ấp (không cần dấu)"),
):
    """
    Tìm kiếm toàn văn **không phân biệt dấu tiếng Việt** trên mọi trường:
    họ tên chủ hộ, địa chỉ hiện trạng, ấp, xã, số tờ, số thửa, loại đất,
    tình trạng GCN, số điện thoại, ghi chú...

    * Gõ `nguyen van quan` hoặc `Nguyễn Văn Quân` cho kết quả như nhau.
    * Hỗ trợ tiền tố kiểu autocomplete: `nguyen van q` tìm mọi người bắt đầu bằng "q".
    * Kết quả trùng chính xác cụm từ khoá đứng đầu, tiếp theo xếp hạng theo mức
      liên quan (bm25). Thời gian truy vấn thường dưới 2ms cho ~7.400 bản ghi.
    """
    _kiem_tra_store()
    ket_qua = ho_dan_store.tim_kiem(q, limit=limit, offset=offset,
                                    loai_ban_ghi=loai_ban_ghi, ap=ap)
    return {
        "success": True,
        "thong_bao": ket_qua["thong_bao"],
        "tu_khoa": ket_qua["tu_khoa"],
        "phuong_thuc": ket_qua["phuong_thuc"],
        "chien_luoc": ket_qua["chien_luoc"],
        "tong_so_ket_qua": ket_qua["tong_so_ket_qua"],
        "thoi_gian_tra_cuu_ms": ket_qua["thoi_gian_tra_cuu_ms"],
        "limit": limit,
        "offset": offset,
        "ket_qua": ket_qua["ket_qua"],
    }


# ===========================================================================
# DANH SÁCH / CHI TIẾT / THỐNG KÊ
# ===========================================================================
@router.get("/thong-ke", summary="📊 Thống kê hộ dân & thửa đất")
def thong_ke():
    """Thống kê tổng quan: số hộ, số thửa, GCN đã cấp/chưa có, phân bổ theo ấp và loại đất."""
    _kiem_tra_store()
    return {"success": True, "thong_bao": "Thống kê dữ liệu hộ dân & thửa đất.",
            "du_lieu": ho_dan_store.thong_ke()}


@router.get("/danh-sach-ap", summary="🏘️ Danh sách ấp")
def danh_sach_ap():
    """Danh sách các ấp hiện có trong CSDL (dùng cho bộ lọc tìm kiếm)."""
    _kiem_tra_store()
    danh_sach = ho_dan_store.danh_sach_ap()
    return {"success": True,
            "thong_bao": f"Có {len(danh_sach)} ấp trong CSDL.",
            "danh_sach": danh_sach}


@router.get("", summary="📋 Danh sách bản ghi (phân trang, có bộ lọc)")
def danh_sach(
    limit: int = Query(50, ge=1, le=500, description="Số bản ghi tối đa (1-500)"),
    offset: int = Query(0, ge=0, description="Bỏ qua n bản ghi đầu"),
    ap: Optional[str] = Query(None, description="Lọc theo tên ấp (chính xác, có dấu)"),
    loai_ban_ghi: Optional[Literal["HO_DAN", "THUA_DAT"]] = Query(None),
    co_gcn: Optional[bool] = Query(None, description="true: đã có GCN; false: chưa có"),
    q: Optional[str] = Query(None, max_length=200,
                             description="Có thể truyền từ khoá — hệ thống chuyển sang tìm toàn văn"),
):
    """Danh sách bản ghi phân trang; lọc theo ấp, loại bản ghi, tình trạng GCN."""
    _kiem_tra_store()
    ket_qua = ho_dan_store.danh_sach(limit=limit, offset=offset, ap=ap,
                                     loai_ban_ghi=loai_ban_ghi, co_gcn=co_gcn, q=q)
    return {"success": True,
            "thong_bao": f"Trả về {len(ket_qua.get('danh_sach', ket_qua.get('ket_qua', [])))} bản ghi.",
            **ket_qua}


@router.get("/{id}", summary="📄 Chi tiết 1 bản ghi")
def chi_tiet(id: int):
    """Xem chi tiết bản ghi hộ dân / thửa đất theo mã số (ID)."""
    _kiem_tra_store()
    ban_ghi = ho_dan_store.chi_tiet(id)
    if not ban_ghi:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy bản ghi số {id} trong CSDL. "
                   f"Vui lòng kiểm tra lại mã số bản ghi.",
        )
    return {"success": True, "thong_bao": f"Đã tìm thấy bản ghi số {id}.",
            "du_lieu": ban_ghi}


# ===========================================================================
# THÊM / SỬA / XOÁ
# ===========================================================================
@router.post("", status_code=201, summary="➕ Thêm bản ghi mới")
def them_ban_ghi(ban_ghi: HoDanDatDaiCreate):
    """Thêm mới hộ dân hoặc thửa đất. Cần ít nhất họ tên chủ hộ hoặc địa chỉ."""
    _kiem_tra_store()
    try:
        moi = ho_dan_store.them(ban_ghi.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "success": True,
        "thong_bao": f"Đã thêm thành công bản ghi số {moi['id']} "
                     f"cho {moi.get('ho_ten_chu_ho') or moi.get('dia_chi_hien_trang')}.",
        "du_lieu": moi,
    }


@router.put("/{id}", summary="✏️ Cập nhật bản ghi")
def cap_nhat_ban_ghi(id: int, du_lieu: HoDanDatDaiUpdate):
    """Cập nhật các trường của bản ghi — chỉ cần gửi trường muốn sửa."""
    _kiem_tra_store()
    thay_doi = du_lieu.model_dump(exclude_unset=True, exclude_none=True)
    if not thay_doi:
        raise HTTPException(
            status_code=400,
            detail="Không có trường hợp lệ nào được gửi để cập nhật. "
                   "Vui lòng gửi ít nhất một trường (ví dụ: {\"so_dien_thoai\": \"0909...\"}).",
        )
    try:
        ban_ghi = ho_dan_store.cap_nhat(id, thay_doi)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if ban_ghi is None:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy bản ghi số {id} để cập nhật.",
        )
    return {
        "success": True,
        "thong_bao": f"Đã cập nhật {len(thay_doi)} trường của bản ghi số {id}.",
        "truong_da_sua": list(thay_doi.keys()),
        "du_lieu": ban_ghi,
    }


@router.delete("/{id}", summary="🗑️ Xoá bản ghi")
def xoa_ban_ghi(id: int):
    """Xoá vĩnh viễn một bản ghi khỏi CSDL (kèm xoá khỏi chỉ mục tìm kiếm)."""
    _kiem_tra_store()
    if not ho_dan_store.xoa(id):
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy bản ghi số {id} để xoá.",
        )
    return {"success": True,
            "thong_bao": f"Đã xoá bản ghi số {id} khỏi CSDL.",
            "id": id}


# ===========================================================================
# BẢO TRÌ CHỈ MỤC TOÀN VĂN
# ===========================================================================
@router.post("/fts/dong-bo", summary="🔄 Xây lại chỉ mục tìm kiếm toàn văn")
def dong_bo_fts():
    """Xây lại toàn bộ chỉ mục FTS sau khi import Excel trực tiếp bằng script.
    Thông thường không cần gọi — hệ thống tự đồng bộ khi phát hiện lệch số dòng."""
    _kiem_tra_store()
    so_dong = ho_dan_store.dong_bo_fts()
    return {
        "success": True,
        "thong_bao": f"Đã xây lại chỉ mục toàn văn cho {so_dong} bản ghi.",
        "so_ban_ghi": so_dong,
        "phuong_thuc": "FTS5" if ho_dan_store.fts_ho_tro else "LIKE (dự phòng)",
    }
