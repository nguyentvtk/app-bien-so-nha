"""
Pydantic Schemas & Data Models cho Hệ thống Quản lý & Cấp biển số nhà (AppBienSoNha)
Địa bàn: Xã Tân Phú, tỉnh Tây Ninh - Cơ quan quản lý: UBND xã Tân Phú.
Bổ sung nghiệp vụ quản lý pháp lý đất đai và điều kiện cấp số nhà theo quy định.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from datetime import datetime

class TrangThaiSoNha(str, Enum):
    HIEN_HUU = "HIEN_HUU"                                  # Nhà đã xây dựng hợp pháp, có số chính thức
    DAT_TRONG = "DAT_TRONG"                                # Đất trống thổ cư, số nhà dự trữ (Virtual Node)
    CHO_CAP = "CHO_CAP"                                    # Đang làm thủ tục thẩm định
    NHA_CHUA_DU_DIEU_KIEN = "NHA_CHUA_DU_DIEU_KIEN"        # Có nhà nhưng đất chưa chuyển mục đích -> Không cấp số
    DAT_THO_CU_CHUA_XAY = "DAT_THO_CU_CHUA_XAY"            # Đất thổ cư chưa xây dựng (Quỹ dự trữ)

class MucDichSuDungDat(str, Enum):
    DAT_O_THO_CU = "DAT_O_THO_CU"                          # Đất ở tại nông thôn (ONT) / Thổ cư hợp pháp
    DAT_CHUA_CHUYEN_MUC_DICH = "DAT_CHUA_CHUYEN_MUC_DICH"  # Đất nông nghiệp, CLN, lúa... chưa chuyển mục đích
    DAT_NONG_NGHIEP = "DAT_NONG_NGHIEP"                    # Đất nông nghiệp thuần túy
    DAT_KHAC = "DAT_KHAC"                                  # Đất thương mại dịch vụ, công cộng...

class HienTrangXayDung(str, Enum):
    DA_XAY_NHA = "DA_XAY_NHA"                              # Đã xây dựng công trình / nhà ở
    DAT_TRONG = "DAT_TRONG"                                # Thửa đất trống chưa xây dựng

class TrangThaiHoSo(str, Enum):
    CHO_TIEP_NHAN = "CHO_TIEP_NHAN"
    DANG_THAM_DINH = "DANG_THAM_DINH"
    DA_CAP_SO = "DA_CAP_SO"
    TU_CHOI = "TU_CHOI"

class GPSCoordinate(BaseModel):
    lat: float
    lng: float

# 1. Tuyến Đường (WGS84)
class TuyenDuong(BaseModel):
    id_tuyen: str = Field(..., description="Mã tuyến đường, vd: TD_DT785")
    ten_duong: str = Field(..., description="Tên đường, vd: Đường ĐT.785")
    toado_batdau: GPSCoordinate
    toado_kethuc: GPSCoordinate
    phan_loai: str = Field(default="Đường tỉnh", description="Đường tỉnh, Đường liên xã, Đường ấp, Hẻm nội bộ")
    chieu_dai_m: Optional[float] = Field(default=0.0, description="Chiều dài tuyến (mét)")
    lo_gioi_m: Optional[float] = Field(default=0.0, description="Lộ giới quy hoạch (mét)")
    tong_so_nha: int = 0
    quy_tac_danh_so: str = Field(default="Tả Chẵn - Hữu Lẻ", description="Quy chuẩn đánh số")
    nguon_du_lieu: str = Field(default="Google Sheets", description="Nguồn dữ liệu")

# 2. Số Nhà & Thửa Đất (Core)
class SoNha(BaseModel):
    id_nha: str = Field(..., description="ID định danh, vd: SN_TP_001")
    so_nha_moi: str = Field(..., description="Biển số nhà mới chuẩn hoá, vd: 14 Đường ĐT.785")
    so_nha_cu: Optional[str] = Field(default=None, description="Số nhà cũ trước khi đổi/cấp lại")
    ten_chu_ho: str
    cccd: Optional[str] = None
    sdt: Optional[str] = None
    toado_gps: GPSCoordinate
    trang_thai: TrangThaiSoNha = TrangThaiSoNha.HIEN_HUU
    muc_dich_su_dung_dat: MucDichSuDungDat = MucDichSuDungDat.DAT_O_THO_CU
    hien_trang_xay_dung: HienTrangXayDung = HienTrangXayDung.DA_XAY_NHA
    so_to_thua: Optional[str] = Field(default=None, description="Số tờ / Số thửa bản đồ địa chính")
    id_tuyen_duong: str
    id_hem_ngach: Optional[str] = Field(default=None, description="Cây định danh ngõ ngách")
    loai_nha: str = Field(default="Nhà ở riêng lẻ", description="Nhà cấp 4, Nhà kiên cố, Đất trống...")
    dien_tich_mat_tien: float = Field(default=5.0, description="Chiều rộng mặt tiền (mét)")
    ngay_cap: str = Field(default_factory=lambda: datetime.now().strftime("%d/%m/%Y"))
    so_giay_phep: Optional[str] = None
    ghi_chu: Optional[str] = None
    che_do_danh_so: Optional[str] = Field(
        default=None,
        description="Chế độ đánh số đã dùng: DO_THI (tuần tự chẵn/lẻ) hoặc NONG_THON (theo khoảng cách 10m)"
    )

# 3. Hồ Sơ Cấp Mới / Khảo Sát Thực Địa Của Điều Tra Viên
class HoSoCapMoi(BaseModel):
    id_yeu_cau: str
    ho_ten_nguoi_nop: str
    cccd: str
    sdt: str
    email: Optional[str] = None
    dia_chi_khao_sat: str = Field(..., description="Mô tả thực tế của điều tra viên / người dân")
    id_tuyen_duong: str
    hem_ngach: Optional[str] = None
    muc_dich_su_dung_dat: MucDichSuDungDat = MucDichSuDungDat.DAT_O_THO_CU
    hien_trang_xay_dung: HienTrangXayDung = HienTrangXayDung.DA_XAY_NHA
    so_to_thua: Optional[str] = None
    khoang_cach_mat_tien: float = Field(default=5.0, description="Độ rộng mặt tiền để nội suy")
    toado_gps: GPSCoordinate
    hinh_anh_khao_sat: List[str] = []
    giay_to_phap_ly: List[str] = []
    loai_yeu_cau: str = Field(default="KHAO_SAT_THUC_DIA", description="KHAO_SAT_THUC_DIA, CAP_MOI, DOI_SO")
    trang_thai: TrangThaiHoSo = TrangThaiHoSo.CHO_TIEP_NHAN
    so_nha_de_xuat: Optional[str] = None
    ai_risk_score: Optional[float] = None
    ai_feedback: Optional[str] = None
    ngay_tao: str = Field(default_factory=lambda: datetime.now().strftime("%d/%m/%Y %H:%M"))
    dieu_tra_vien: Optional[str] = Field(default=None, description="Tên điều tra viên khảo sát")
    can_bo_duyet: Optional[str] = None

# 4. Typed Decision Objects của Jev (System 1)
class ChoiceDecision(BaseModel):
    type: Literal["choice"] = "choice"
    selected: str
    confidence: float
    probabilities: Dict[str, float]

class ScoreDecision(BaseModel):
    type: Literal["score"] = "score"
    score: float
    confidence: float
    status: Literal["GREEN_SAFE", "YELLOW_WARN", "RED_DANGER"]
    details: Dict[str, Any] = {}

class NoulDecision(BaseModel):
    type: Literal["noul"] = "noul"
    isCompleted: bool = Field(..., alias="isCompleted")
    confidence: float
    reason: Optional[str] = None

    class Config:
        populate_by_name = True

# 5. MCP JSON-RPC 2.0
class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any] = {}
    id: Optional[str] = None

class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

# ============================================================
# 6. HỘ DÂN & THỬA ĐẤT — sonha_database.db (bảng ho_dan_dat_dai)
# ============================================================
class LoaiBanGhi(str, Enum):
    HO_DAN = "HO_DAN"        # Bản ghi hộ dân (bảng kê điều tra thực địa)
    THUA_DAT = "THUA_DAT"    # Bản ghi thửa đất rà soát theo KH 2959/BCA

class HoDanDatDaiCreate(BaseModel):
    """Tạo mới bản ghi hộ dân / thửa đất qua API."""
    ho_ten_chu_ho: Optional[str] = Field(None, description="Họ tên chủ hộ / chủ sử dụng đất")
    so_dien_thoai: Optional[str] = Field(None, max_length=20, description="Số điện thoại liên hệ")
    dia_chi_hien_trang: Optional[str] = Field(None, description="Địa chỉ hiện trạng")
    so_to: Optional[str] = Field(None, description="Số tờ bản đồ")
    so_thua: Optional[str] = Field(None, description="Số thứ tự thửa đất")
    dien_tich: Optional[float] = Field(None, ge=0, description="Diện tích (m²)")
    loai_dat: Optional[str] = Field(None, description="Mã loại đất (ONT, HNK, CLN, BHK...)")
    tinh_trang_gcn: Optional[str] = Field(None, description="Tình trạng giấy chứng nhận")
    toa_do_gps: Optional[str] = Field(None, description="Tọa độ GPS (VD: 11.6050, 106.1850)")
    loai_ban_ghi: LoaiBanGhi = Field(LoaiBanGhi.HO_DAN, description="Loại bản ghi")
    xa: Optional[str] = Field(None, description="Xã/phường")
    ap: Optional[str] = Field(None, description="Ấp/khu phố")
    stt_nha: Optional[int] = Field(None, ge=0)
    stt_ho: Optional[int] = Field(None, ge=0)
    so_nhan_khau: Optional[int] = Field(None, ge=0, description="Số nhân khẩu của hộ")
    phan_loai_du_lieu: Optional[str] = Field(None, description="Phân loại dữ liệu (Nhóm 1/2/3)")
    thong_tin_thieu: Optional[str] = Field(None, description="Thông tin còn thiếu khi rà soát")
    ghi_chu: Optional[str] = Field(None, description="Ghi chú")

class HoDanDatDaiUpdate(BaseModel):
    """Cập nhật một phần bản ghi — chỉ gửi các trường cần sửa."""
    ho_ten_chu_ho: Optional[str] = None
    so_dien_thoai: Optional[str] = Field(None, max_length=20)
    dia_chi_hien_trang: Optional[str] = None
    so_to: Optional[str] = None
    so_thua: Optional[str] = None
    dien_tich: Optional[float] = Field(None, ge=0)
    loai_dat: Optional[str] = None
    tinh_trang_gcn: Optional[str] = None
    toa_do_gps: Optional[str] = None
    loai_ban_ghi: Optional[LoaiBanGhi] = None
    xa: Optional[str] = None
    ap: Optional[str] = None
    stt_nha: Optional[int] = Field(None, ge=0)
    stt_ho: Optional[int] = Field(None, ge=0)
    so_nhan_khau: Optional[int] = Field(None, ge=0)
    phan_loai_du_lieu: Optional[str] = None
    thong_tin_thieu: Optional[str] = None
    ghi_chu: Optional[str] = None

# ============================================================
# 7. HIỆU CHỈNH TOẠ ĐỘ TUYẾN ĐƯỜNG (2 ĐIỂM CHUẨN)
# ============================================================
class ToaDoChuan(BaseModel):
    """Một điểm chuẩn WGS84 (ví độ/kinh độ hợp lệ)."""
    lat: float = Field(..., ge=-90, le=90, description="Vĩ độ WGS84")
    lng: float = Field(..., ge=-180, le=180, description="Kinh độ WGS84")

class HieuChinhToaDoRequest(BaseModel):
    """Yêu cầu hiệu chỉnh toạ độ 1 tuyến chuẩn (đầu + cuối);
    toàn bộ tuyến còn lại của xã sẽ tự biến đổi theo."""
    toado_batdau_moi: ToaDoChuan = Field(..., description="Toạ độ ĐIỂM ĐẦU mới của tuyến chuẩn")
    toado_kethuc_moi: ToaDoChuan = Field(..., description="Toạ độ ĐIỂM CUỐI mới của tuyến chuẩn")
    ap_dung_so_nha: bool = Field(False, description="True: áp dụng phép biến đổi cả cho toạ độ GPS số nhà hiện hữu")
    ghi_chu: Optional[str] = Field(None, max_length=500, description="Ghi chú lý do hiệu chỉnh")

# ============================================================
# 8. ĐỀ XUẤT SỐ NHÀ THEO 2 CHẾ ĐỘ (ĐÔ THỊ / NÔNG THÔN)
# ============================================================
class DeXuatSoRequest(BaseModel):
    """Yêu cầu đề xuất số nhà tự động theo phương pháp đánh số."""
    che_do: Literal["DO_THI", "NONG_THON"] = Field(
        ..., description="DO_THI: tuần tự chẵn/lẻ (TT 08/2024) | NONG_THON: theo khoảng cách 1 số = 10m")
    id_tuyen: str = Field(..., description="Mã tuyến đường đang cấp số")
    toado_gps: Optional[GPSCoordinate] = Field(
        None, description="Toạ độ WGS84 của nhà (BẮT BUỘC với chế độ Nông thôn để đo khoảng cách)")
    phia: Optional[Literal["trai", "phai"]] = Field(
        None, description="Chế độ Đô thị: ép phía trái (lẻ) / phải (chẵn); bỏ trống để tự chọn")
    chen_sau_so: Optional[int] = Field(
        None, ge=0, description="Chế độ Đô thị: nhà chèn giữa → sinh số phụ (VD 20 → 20A)")
