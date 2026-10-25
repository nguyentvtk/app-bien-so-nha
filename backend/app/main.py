"""
Main FastAPI Application: Hệ Thống Cơ Sở Dữ Liệu Quản Lý & Cấp Biển Số Nhà
Địa bàn: XÃ TÂN PHÚ, TỈNH TÂY NINH - Cơ quan: ỦY BAN NHÂN DÂN XÃ TÂN PHÚ.
Tích hợp MCP Gateway, Thinking Layer (Qwen3), Jev Decision Layer và Static Frontend.
"""

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import os
import math
import uuid
import httpx
import logging
from typing import Optional, List, Dict, Any

from app.models.schemas import SoNha, HoSoCapMoi, TrangThaiHoSo, TrangThaiSoNha, MucDichSuDungDat, HienTrangXayDung
from app.modules.storage import storage, DEFAULT_GOOGLE_SHEET_URL
from app.modules.address_tree import address_tree_service
from app.modules.virtual_nodes import virtual_node_service
from app.modules.cert_generator import cert_generator, CERT_DIR
from app.ai_agents.thinking_llm import thinking_llm
from app.ai_agents.jev_decision import jev_engine
from app.mcp_gateway.router import gateway_router
from app.mcp_gateway.middleware import mcp_middleware
from app.modules.data_importer import DataImporter
from app.routers.ho_dan import router as ho_dan_router

logger = logging.getLogger("sonha.backend")

app = FastAPI(
    title="Hệ thống Quản lý & Cấp số nhà - Xã Tân Phú, Tỉnh Tây Ninh",
    description="Kiến trúc Vibe Coding 3 tầng: LLM Thinking (Qwen3) -> Jev Decision (System 1) -> MCP Gateway & Execution. Quản lý bản đồ GIS và điều kiện pháp lý đất đai.",
    version="2.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gắn MCP Gateway Router
app.include_router(gateway_router)

# Gắn API Hộ dân & Thửa đất (sonha_database.db — tìm kiếm toàn văn FTS)
app.include_router(ho_dan_router)

# Khởi tạo module nhập liệu từ Excel thực địa
data_importer = DataImporter(storage)

# =======================================================
# BỘ XỬ LÝ LỖI TIẾNG VIỆT TOÀN HỆ THỐNG
# Mọi phản hồi lỗi (422/404/500...) đều có "thong_bao" rõ ràng, dễ hiểu
# =======================================================

THONG_BAO_LOI_HTTP = {
    400: "Yêu cầu không hợp lệ. Vui lòng kiểm tra lại dữ liệu đã gửi.",
    401: "Bạn cần đăng nhập để thực hiện thao tác này.",
    403: "Bạn không có quyền thực hiện thao tác này.",
    404: "Không tìm thấy địa chỉ API hoặc tài nguyên được yêu cầu. "
         "Vui lòng kiểm tra lại đường dẫn (xem danh sách API tại /docs).",
    405: "Phương thức truy cập (GET/POST/PUT/DELETE) không được hỗ trợ cho địa chỉ này.",
    422: "Dữ liệu gửi lên chưa đúng định dạng.",
    429: "Quá nhiều yêu cầu trong thời gian ngắn. Vui lòng chờ chút rồi thử lại.",
    500: "Hệ thống gặp lỗi không mong muốn. Vui lòng thử lại hoặc liên hệ quản trị viên.",
    503: "Hệ thống đang bảo trì hoặc cơ sở dữ liệu chưa sẵn sàng.",
}

# Bản dịch tiếng Việt cho các loại lỗi xác thực dữ liệu (Pydantic v2)
DICH_LOI_XAC_THUC = {
    "missing": "thiếu trường bắt buộc",
    "string_too_short": "quá ngắn (yêu cầu tối thiểu {min_length} ký tự)",
    "string_too_long": "quá dài (tối đa {max_length} ký tự)",
    "string_type": "phải là chuỗi ký tự",
    "int_parsing": "phải là số nguyên",
    "int_type": "phải là số nguyên",
    "float_parsing": "phải là số",
    "bool_parsing": "phải là giá trị đúng/sai (true/false)",
    "bool_type": "phải là giá trị đúng/sai (true/false)",
    "greater_than_equal": "phải lớn hơn hoặc bằng {ge}",
    "less_than_equal": "phải nhỏ hơn hoặc bằng {le}",
    "greater_than": "phải lớn hơn {gt}",
    "less_than": "phải nhỏ hơn {lt}",
    "enum": "giá trị không nằm trong danh sách cho phép",
    "literal_error": "giá trị không nằm trong danh sách cho phép",
    "json_invalid": "dữ liệu JSON không hợp lệ",
    "value_error": "giá trị không hợp lệ",
}

def _dich_loi_xac_thuc(err: dict) -> str:
    """Dịch 1 lỗi xác thực Pydantic sang tiếng Việt, kèm vị trí trường."""
    loc = [str(x) for x in err.get("loc", []) if x != "body"]
    ten = loc[-1] if loc else "dữ liệu gửi lên"
    if loc and loc[0] == "query":
        vi_tri = f"tham số '{ten}'"
    elif loc and loc[0] == "path":
        vi_tri = f"tham số đường dẫn '{ten}'"
    else:
        vi_tri = f"trường '{ten}'"
    loai = err.get("type", "")
    ctx = err.get("ctx", {}) or {}
    mau = DICH_LOI_XAC_THUC.get(loai)
    if mau:
        try:
            return f"{vi_tri} {mau.format(**ctx)}"
        except (KeyError, IndexError, ValueError):
            pass
    return f"{vi_tri}: {err.get('msg', 'không hợp lệ')}"

# Các câu lỗi mặc định tiếng Anh của Starlette — luôn thay bằng thông báo tiếng Việt
LOI_MAC_DINH_TIENG_ANH = {
    "Not Found", "Method Not Allowed", "Internal Server Error",
    "Forbidden", "Unauthorized", "Bad Request", "Service Unavailable",
}

@app.exception_handler(StarletteHTTPException)
async def xu_ly_loi_http(request: Request, exc: StarletteHTTPException):
    """Lỗi HTTP (404, 405...) → thông báo tiếng Việt; giữ nguyên detail nếu đã tiếng Việt."""
    chi_tiet = exc.detail
    if (isinstance(chi_tiet, str) and chi_tiet.strip()
            and chi_tiet not in LOI_MAC_DINH_TIENG_ANH):
        thong_bao = chi_tiet  # Endpoint đã tự viết thông báo tiếng Việt
    else:
        thong_bao = THONG_BAO_LOI_HTTP.get(exc.status_code, f"Lỗi hệ thống (mã {exc.status_code}).")
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "thong_bao": thong_bao, "chi_tiet": chi_tiet,
                 "duong_dan": str(request.url.path)},
        headers=getattr(exc, "headers", None),
    )

@app.exception_handler(RequestValidationError)
async def xu_ly_loi_xac_thuc(request: Request, exc: RequestValidationError):
    """Lỗi dữ liệu gửi lên (422) → liệt kê từng trường sai kèm lời giải tiếng Việt."""
    cac_loi = [_dich_loi_xac_thuc(err) for err in exc.errors()]
    thong_bao = ("Dữ liệu gửi lên chưa hợp lệ: " + "; ".join(cac_loi[:5])
                 + ("..." if len(cac_loi) > 5 else "."))
    return JSONResponse(
        status_code=422,
        content={"success": False, "thong_bao": thong_bao, "chi_tiet": cac_loi,
                 "duong_dan": str(request.url.path)},
    )

@app.exception_handler(Exception)
async def xu_ly_loi_he_thong(request: Request, exc: Exception):
    """Lỗi chưa được xử lý (500) → che chi tiết kỹ thuật, báo tiếng Việt + ghi log."""
    logger.exception("Lỗi chưa xử lý tại %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"success": False,
                 "thong_bao": "Hệ thống gặp lỗi không mong muốn khi xử lý yêu cầu. "
                              "Vui lòng thử lại hoặc liên hệ quản trị viên.",
                 "duong_dan": str(request.url.path)},
    )

# --- RESTful Endpoints ---

@app.get("/api/system/status")
async def get_system_status(request: Request, format: Optional[str] = None):
    """
    Kiểm tra tình trạng hoạt động của 3 tầng AI, MCP Gateway và Thống kê Đất đai UBND Xã Tân Phú.
    - Truy cập qua trình duyệt Web -> Trả về giao diện Dashboard Glassmorphism trực quan.
    - Truy cập qua API hoặc có param format=json -> Trả về JSON chuẩn.
    """
    thong_ke = storage.get_thong_ke_dat_dai()
    status_data = {
        "status": "ONLINE",
        "dia_phuong": "Xã Tân Phú, tỉnh Tây Ninh",
        "co_quan_chu_quan": "ỦY BAN NHÂN DÂN XÃ TÂN PHÚ",
        "layer_1_thinking": {
            "model": thinking_llm.model,
            "engine": "Ollama / Local LLM",
            "state": "READY"
        },
        "layer_2_decision": {
            "engine": "Jev Reflex Engine (System 1)",
            "risk_rules": ["TRUNG_SO_NHA", "DAT_CHUA_CHUYEN_MUC_DICH", "VIRTUAL_NODE"],
            "state": "ACTIVE"
        },
        "layer_3_gateway": {
            "endpoint": "/mcp-gateway/rpc",
            "protocol": "JSON-RPC 2.0"
        },
        "thong_ke_dat_dai": thong_ke
    }

    # Nếu client yêu cầu JSON rõ ràng
    accept = request.headers.get("accept", "")
    if format == "json" or ("application/json" in accept and "text/html" not in accept):
        return JSONResponse(status_data)

    # Trả về Giao diện Web Glassmorphism cực đẹp cho trình duyệt
    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trạng Thái Hệ Thống - UBND Xã Tân Phú</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
        body {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
            min-height: 100vh;
        }}
        .glass-card {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .glass-card:hover {{
            border-color: rgba(255, 255, 255, 0.2);
            transform: translateY(-2px);
            transition: all 0.3s ease;
        }}
    </style>
</head>
<body class="text-slate-100 flex flex-col justify-between p-4 md:p-8">
    <div class="max-w-5xl w-full mx-auto space-y-6">
        <!-- Header -->
        <div class="glass-card rounded-3xl p-6 md:p-8 flex flex-col md:flex-row items-center justify-between gap-6 shadow-2xl">
            <div class="flex items-center space-x-4">
                <div class="w-16 h-16 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-indigo-500/30 text-white text-2xl font-bold">
                    <i class="fa-solid fa-landmark-flag"></i>
                </div>
                <div>
                    <div class="flex items-center space-x-2">
                        <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                            <i class="fa-solid fa-circle text-[8px] mr-1 animate-pulse"></i>HỆ THỐNG ONLINE
                        </span>
                        <span class="text-xs text-slate-400">Phiên bản 2.1.0</span>
                    </div>
                    <h1 class="text-xl md:text-2xl font-extrabold text-white mt-1">ỦY BAN NHÂN DÂN XÃ TÂN PHÚ</h1>
                    <p class="text-xs md:text-sm text-indigo-300 font-medium">Hệ thống Cơ sở dữ liệu Quản lý & Cấp biển số nhà — Tỉnh Tây Ninh</p>
                </div>
            </div>

            <!-- Nút hành động chính -->
            <div class="flex flex-wrap items-center gap-3">
                <a href="/" class="px-5 py-3 rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-sm font-bold shadow-lg shadow-indigo-600/30 flex items-center transition transform active:scale-95">
                    <i class="fa-solid fa-house-chimney mr-2"></i>Vào Ứng Dụng Chính
                </a>
                <a href="/docs" class="px-4 py-3 rounded-2xl glass-card hover:bg-white/10 text-slate-200 text-sm font-semibold flex items-center transition">
                    <i class="fa-solid fa-book-open mr-2 text-indigo-400"></i>Tài Liệu API
                </a>
            </div>
        </div>

        <!-- 3 Tầng Kiến Trúc Vibe Coding -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <!-- Tầng 1 -->
            <div class="glass-card rounded-2xl p-5 space-y-3">
                <div class="flex items-center justify-between">
                    <span class="text-xs font-bold uppercase tracking-wider text-indigo-400">Tầng 1: LLM Thinking</span>
                    <span class="px-2 py-0.5 rounded-md bg-emerald-500/20 text-emerald-300 text-[10px] font-bold">READY</span>
                </div>
                <div class="flex items-center space-x-3">
                    <div class="w-10 h-10 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center text-lg">
                        <i class="fa-solid fa-brain"></i>
                    </div>
                    <div>
                        <div class="text-sm font-bold text-white">{thinking_llm.model}</div>
                        <div class="text-xs text-slate-400">Ollama / Local LLM Agent</div>
                    </div>
                </div>
                <p class="text-xs text-slate-400">Bóc tách địa chỉ không cấu trúc, suy luận ngữ nghĩa tên đường và phát hiện bất thường.</p>
            </div>

            <!-- Tầng 2 -->
            <div class="glass-card rounded-2xl p-5 space-y-3">
                <div class="flex items-center justify-between">
                    <span class="text-xs font-bold uppercase tracking-wider text-blue-400">Tầng 2: Jev Decision</span>
                    <span class="px-2 py-0.5 rounded-md bg-emerald-500/20 text-emerald-300 text-[10px] font-bold">ACTIVE</span>
                </div>
                <div class="flex items-center space-x-3">
                    <div class="w-10 h-10 rounded-xl bg-blue-500/20 text-blue-400 flex items-center justify-center text-lg">
                        <i class="fa-solid fa-shield-halved"></i>
                    </div>
                    <div>
                        <div class="text-sm font-bold text-white">Jev Reflex Engine</div>
                        <div class="text-xs text-slate-400">System 1 Fast Decision</div>
                    </div>
                </div>
                <p class="text-xs text-slate-400">Kiểm tra quy tắc chẵn/lẻ, chặn đất chưa chuyển mục đích, phát hành Virtual Node.</p>
            </div>

            <!-- Tầng 3 -->
            <div class="glass-card rounded-2xl p-5 space-y-3">
                <div class="flex items-center justify-between">
                    <span class="text-xs font-bold uppercase tracking-wider text-emerald-400">Tầng 3: MCP Gateway</span>
                    <span class="px-2 py-0.5 rounded-md bg-emerald-500/20 text-emerald-300 text-[10px] font-bold">2.0 RPC</span>
                </div>
                <div class="flex items-center space-x-3">
                    <div class="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-lg">
                        <i class="fa-solid fa-network-wired"></i>
                    </div>
                    <div>
                        <div class="text-sm font-bold text-white">/mcp-gateway/rpc</div>
                        <div class="text-xs text-slate-400">Standard Tool Execution</div>
                    </div>
                </div>
                <p class="text-xs text-slate-400">Cầu nối thực thi chuẩn hóa Model Context Protocol, cấp phát chứng nhận PDF mộc đỏ.</p>
            </div>
        </div>

        <!-- Thống Kê Đất Đai & Tuyến Đường Thực Tế -->
        <div class="glass-card rounded-3xl p-6 space-y-4">
            <div class="flex items-center justify-between border-b border-white/10 pb-4">
                <h2 class="text-base font-bold text-white flex items-center">
                    <i class="fa-solid fa-chart-column mr-2 text-indigo-400"></i>Dữ Liệu Thực Tế Địa Bàn Xã Tân Phú
                </h2>
                <span class="text-xs text-slate-400"><i class="fa-solid fa-map-pin mr-1 text-rose-400"></i>Tọa độ WGS84: 11.6050°N, 106.1850°E</span>
            </div>

            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div class="bg-white/5 rounded-2xl p-4 border border-white/5">
                    <span class="text-xs text-slate-400 block font-medium">Tuyến đường thực tế</span>
                    <div class="text-2xl md:text-3xl font-black text-indigo-400 mt-1">{thong_ke.get('tong_tuyen_duong', 0)}</div>
                    <span class="text-[11px] text-emerald-400 mt-1 block"><i class="fa-solid fa-check mr-1"></i>Từ Google Sheets</span>
                </div>

                <div class="bg-white/5 rounded-2xl p-4 border border-white/5">
                    <span class="text-xs text-slate-400 block font-medium">Số nhà đã cấp</span>
                    <div class="text-2xl md:text-3xl font-black text-white mt-1">{thong_ke.get('da_cap_so', 0)}</div>
                    <span class="text-[11px] text-slate-400 mt-1 block">Dữ liệu thực địa</span>
                </div>

                <div class="bg-white/5 rounded-2xl p-4 border border-white/5">
                    <span class="text-xs text-slate-400 block font-medium">Đất chưa chuyển MĐ</span>
                    <div class="text-2xl md:text-3xl font-black text-rose-400 mt-1">{thong_ke.get('nha_chua_du_dieu_kien', 0)}</div>
                    <span class="text-[11px] text-rose-300 mt-1 block"><i class="fa-solid fa-ban mr-1"></i>Chặn cấp số</span>
                </div>

                <div class="bg-white/5 rounded-2xl p-4 border border-white/5">
                    <span class="text-xs text-slate-400 block font-medium">Đất trống (Điểm ảo)</span>
                    <div class="text-2xl md:text-3xl font-black text-amber-400 mt-1">{thong_ke.get('dat_tho_cu_chua_xay_du_tru', 0)}</div>
                    <span class="text-[11px] text-amber-300 mt-1 block"><i class="fa-solid fa-draw-polygon mr-1"></i>Quỹ số dự trữ</span>
                </div>
            </div>
        </div>

        <!-- Điều Hướng & JSON Link -->
        <div class="flex flex-col sm:flex-row items-center justify-between text-xs text-slate-400 gap-3 pt-2">
            <div>
                <span>Cơ quan chủ quản: <strong>Ủy ban nhân dân Xã Tân Phú, tỉnh Tây Ninh</strong></span>
            </div>
            <div class="flex items-center space-x-4">
                <a href="/api/system/status?format=json" class="text-indigo-400 hover:text-indigo-300 underline flex items-center">
                    <i class="fa-solid fa-code mr-1"></i>Xem dữ liệu thô (JSON format)
                </a>
                <span>•</span>
                <a href="/" class="text-slate-300 hover:text-white font-semibold flex items-center">
                    <i class="fa-solid fa-arrow-right mr-1"></i>Đến Bản Đồ GIS
                </a>
            </div>
        </div>
    </div>
</body>
</html>
"""
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/api/thong-ke/dat-dai")
def get_thong_ke_dat_dai():
    """Thống kê đất đai và điều kiện cấp số nhà phục vụ báo cáo UBND xã Tân Phú"""
    return storage.get_thong_ke_dat_dai()

@app.get("/api/tuyen-duong")
def list_tuyen_duong():
    return storage.get_all_tuyen_duong()

# =======================================================
# HIỆU CHỈNH TOẠ ĐỘ TUYẾN ĐƯỜNG TOÀN XÃ (2 ĐIỂM CHUẨN)
# =======================================================
from app.modules.route_calibrator import route_calibrator
from app.models.schemas import HieuChinhToaDoRequest

def _kiem_tra_2_diem_moi(yc: HieuChinhToaDoRequest):
    """Chặn trước khi tính: 2 điểm mới không được trùng nhau (sẽ sụp toàn bộ lưới)."""
    d1, d2 = yc.toado_batdau_moi, yc.toado_kethuc_moi
    duong = ((d2.lng - d1.lng) * 111320 * math.cos(math.radians(d1.lat))) ** 2 \
            + ((d2.lat - d1.lat) * 110574) ** 2
    if duong ** 0.5 < 1.0:
        raise HTTPException(
            status_code=400,
            detail="Hai điểm mới (điểm đầu & điểm cuối) cách nhau dưới 1 mét — "
                   "vui lòng kiểm tra lại, không thể suy ra phép biến đổi từ 2 điểm trùng nhau.",
        )

@app.post("/api/tuyen-duong/{id_tuyen}/hieu-chinh-toa-do/kiem-tra",
          summary="🧮 Xem trước ảnh hưởng hiệu chỉnh toạ độ (KHÔNG ghi CSDL)")
def xem_truoc_hieu_chinh_toa_do(id_tuyen: str, yc: HieuChinhToaDoRequest):
    """
    Nhập toạ độ mới ĐIỂM ĐẦU & ĐIỂM CUỐI của tuyến chuẩn → hệ thống tính
    phép biến đổi đồng dạng (dịch chuyển + xoay + tỉ lệ) và trả về dự kiến
    toạ độ mới của TOÀN BỘ tuyến đường còn lại để cán bộ duyệt trước.
    """
    _kiem_tra_2_diem_moi(yc)
    try:
        return {"success": True, **route_calibrator.du_bao(
            id_tuyen, yc.toado_batdau_moi.dict(), yc.toado_kethuc_moi.dict(),
            ap_dung_so_nha=yc.ap_dung_so_nha)}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@app.post("/api/tuyen-duong/{id_tuyen}/hieu-chinh-toa-do",
          summary="📍 Áp dụng hiệu chỉnh toạ độ cho toàn xã")
def ap_dung_hieu_chinh_toa_do(id_tuyen: str, yc: HieuChinhToaDoRequest):
    """
    Cập nhật toạ độ 2 điểm của tuyến chuẩn theo giá trị nhập, tự động biến đổi
    toạ độ toàn bộ tuyến đường còn lại (và số nhà nếu chọn). Có sao lưu &
    hoàn tác được. Dùng nút 'Xem trước ảnh hưởng' trước khi áp dụng.
    """
    _kiem_tra_2_diem_moi(yc)
    try:
        ket_qua = route_calibrator.ap_dung(
            id_tuyen, yc.toado_batdau_moi.dict(), yc.toado_kethuc_moi.dict(),
            ap_dung_so_nha=yc.ap_dung_so_nha, ghi_chu=yc.ghi_chu)
        return {"success": True, **ket_qua}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@app.post("/api/tuyen-duong/phuc-hoi-toa-do", summary="↩️ Hoàn tác lần hiệu chỉnh gần nhất")
def phuc_hoi_toa_do_tuyen_duong():
    """Phục hồi toàn bộ toạ độ (tuyến đường & số nhà) về trước lần hiệu chỉnh gần nhất."""
    ket_qua = route_calibrator.phuc_hoi()
    if not ket_qua.get("thanh_cong", False):
        raise HTTPException(status_code=404, detail=ket_qua.get(
            "thong_bao", "Không có bản sao lưu để hoàn tác."))
    return {"success": True, **ket_qua}

@app.post("/api/tuyen-duong/sync-google-sheets")
async def sync_routes_google_sheets(payload: Optional[Dict[str, Any]] = None):
    """
    Đồng bộ danh sách tuyến đường từ Google Sheets chính thức của UBND xã Tân Phú:
    https://docs.google.com/spreadsheets/d/1LYgA4jQQ9VgCZFpfKT4KyMQzlzg2jaB2jXlP1E870NM/edit?gid=1984523791
    """
    csv_data = payload.get("csv_data") if payload else None

    # Nếu người dùng truyền nội dung CSV dán trực tiếp
    if csv_data:
        return storage.sync_tuyen_duong_from_csv(csv_data)

    # Tải xuất CSV trực tiếp từ Google Sheets qua httpx với follow redirects
    url = DEFAULT_GOOGLE_SHEET_URL
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0, headers=headers) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {
                    "success": False,
                    "need_auth": True,
                    "message": f"Không thể tải từ Google Sheets (Mã HTTP {resp.status_code}). Vui lòng kiểm tra quyền chia sẻ."
                }
            content = resp.text
            if "Cho phép Google Trang tính truy cập" in content or ("<html" in content.lower() and "STT,Tên đường" not in content):
                return {
                    "success": False,
                    "need_auth": True,
                    "message": "Trang tính Google Sheets đang ở chế độ Riêng tư (cần đăng nhập) hoặc trả về HTML. "
                               "Vui lòng vào Google Sheet chọn Chia sẻ -> 'Bất kỳ ai có đường liên kết đều có thể xem' "
                               "hoặc dán nội dung CSV trực tiếp."
                }
            return storage.sync_tuyen_duong_from_csv(content)
    except Exception as e:
        return {
            "success": False,
            "need_auth": True,
            "message": f"Lỗi kết nối tải Google Sheets: {str(e)}. Bạn có thể copy dữ liệu CSV dán vào ô nhập liệu để đồng bộ."
        }

@app.post("/api/system/clear-mock-data")
def clear_mock_data():
    """Xóa bỏ hoàn toàn số nhà và hồ sơ mẫu, giữ nguyên danh mục 261 tuyến đường thực địa từ Google Sheets"""
    storage.clear_mock_data()
    return {
        "success": True,
        "message": "Đã xóa toàn bộ số nhà và hồ sơ mẫu. Danh mục tuyến đường thực địa Xã Tân Phú được giữ nguyên vẹn!"
    }

@app.get("/api/so-nha")
def list_so_nha(id_tuyen: Optional[str] = None, trang_thai: Optional[str] = None):
    return storage.get_all_so_nha(id_tuyen, trang_thai)

# =======================================================
# ĐỀ XUẤT SỐ NHÀ THEO 2 CHẾ ĐỘ: ĐÔ THỊ / NÔNG THÔN
# (Đô thị: tuần tự chẵn/lẻ + số phụ A/B — TT 08/2024/TT-BXD
#  Nông thôn: theo khoảng cách 1 số = 10 m — chuẩn Úc/Mỹ,
#  giải quyết vĩnh viễn bài toán "chừa số đất trống")
# =======================================================
from app.modules.numbering_engine import numbering_engine
from app.models.schemas import DeXuatSoRequest

@app.post("/api/so-nha/de-xuat-so", summary="🔢 Đề xuất số nhà tự động (Đô thị / Nông thôn)")
def de_xuat_so_nha(yc: DeXuatSoRequest):
    """
    **Chế độ Đô thị (DO_THI)** — tuần tự chẵn/lẻ theo TT 08/2024/TT-BXD:
    dãy trái số lẻ, dãy phải số chẵn; nhà chèn giữa (tách thửa) nhận số phụ
    20A, 20B... khi truyền `chen_sau_so`.

    **Chế độ Nông thôn (NONG_THON)** — đánh số theo khoảng cách (chuẩn Úc/Mỹ):
    số nhà = khoảng cách cổng nhà tính từ ĐẦU tuyến ÷ 10 (1.590 m → số 159),
    chẵn/lẻ theo bên trái/phải. Đất trống xây sau tự có số, không cần chừa.
    Yêu cầu bắt buộc `toado_gps` của nhà.
    """
    try:
        ket_qua = numbering_engine.de_xuat(
            che_do=yc.che_do,
            id_tuyen=yc.id_tuyen,
            toado_gps=yc.toado_gps.dict() if yc.toado_gps else None,
            phia=yc.phia,
            chen_sau_so=yc.chen_sau_so,
        )
        return {"success": True, **ket_qua}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/api/so-nha/search")
def search_so_nha(q: str = Query(..., min_length=1)):
    """Multi-search: Tra cứu chéo đồng thời cả Số nhà cũ, Số mới, Chủ hộ và Số tờ/Số thửa"""
    return storage.search_so_nha(q)

@app.get("/api/so-nha/tree/{id_tuyen}")
def get_address_tree(id_tuyen: str):
    so_nhas = storage.get_all_so_nha(id_tuyen)
    return address_tree_service.build_tree_structure(so_nhas)

@app.get("/api/so-nha/virtual-nodes/{id_tuyen}")
def get_virtual_nodes(id_tuyen: str):
    tuyen_list = [t for t in storage.get_all_tuyen_duong() if t["id_tuyen"] == id_tuyen]
    ten_duong = tuyen_list[0]["ten_duong"] if tuyen_list else "Tuyến đường"
    so_nhas = storage.get_all_so_nha(id_tuyen)

    chan = []
    le = []
    for sn in so_nhas:
        raw_num = sn["so_nha_moi"].split()[0]
        if "/" in raw_num:
            raw_num = raw_num.split("/")[0]
        digits = "".join([c for c in raw_num if c.isdigit()])
        if digits:
            if int(digits) % 2 == 0:
                chan.append(sn)
            else:
                le.append(sn)

    virtual_nodes = []
    for i in range(len(chan) - 1):
        vn = virtual_node_service.generate_virtual_nodes_between(id_tuyen, ten_duong, chan[i], chan[i+1])
        virtual_nodes.extend(vn)

    for i in range(len(le) - 1):
        vn = virtual_node_service.generate_virtual_nodes_between(id_tuyen, ten_duong, le[i], le[i+1])
        virtual_nodes.extend(vn)

    return {
        "id_tuyen": id_tuyen,
        "ten_duong": ten_duong,
        "total_virtual_nodes": len(virtual_nodes),
        "virtual_nodes": virtual_nodes
    }

@app.post("/api/so-nha/cap-so")
async def cap_so_nha(so_nha: SoNha):
    """
    Quy trình cấp biển số nhà chính thức:
    Đánh chặn chặt chẽ qua Jev Score:
    - Nếu đất chưa chuyển mục đích sử dụng sang đất ở -> BỊ CHẶN LẬP TỨC.
    - Nếu trùng số nhà -> BỊ CHẶN.
    """
    existing = storage.get_all_so_nha(so_nha.id_tuyen_duong)
    is_virtual = (so_nha.trang_thai == TrangThaiSoNha.DAT_TRONG or so_nha.trang_thai == TrangThaiSoNha.DAT_THO_CU_CHUA_XAY)

    score_decision = jev_engine.score_house_number_assignment(
        so_nha_moi=so_nha.so_nha_moi,
        tuyen_duong_id=so_nha.id_tuyen_duong,
        existing_so_nhas=existing,
        muc_dich_dat=so_nha.muc_dich_su_dung_dat.value,
        hien_trang=so_nha.hien_trang_xay_dung.value,
        is_virtual_node=is_virtual
    )

    allowed, message = mcp_middleware.evaluate_and_intercept("cap_so_nha", score_decision)
    if not allowed:
        raise HTTPException(status_code=400, detail={
            "error": "BỊ CHẶN BỞI QUY ĐỊNH PHÁP LÝ",
            "score": score_decision.score,
            "message": message,
            "details": score_decision.details
        })

    storage.insert_so_nha(so_nha)

    pdf_path = cert_generator.generate_pdf(so_nha.dict())
    filename = os.path.basename(pdf_path)

    return {
        "success": True,
        "message": message,
        "jev_score": score_decision.dict(),
        "so_nha": so_nha,
        "certificate_url": f"/api/cert/download/{filename}"
    }

@app.post("/api/dieu-tra-vien/khao-sat-nhanh")
async def survey_quick_submit(ho_so: HoSoCapMoi):
    """
    Endpoint tối ưu cho Điều tra viên thực địa cầm thiết bị di động thông minh:
    - Bấm nút ghim GPS lấy toạ độ WGS84 tức thì.
    - Chọn tình trạng pháp lý đất đai (Đất thổ cư / Đất chưa chuyển mục đích).
    - Tự động thẩm định qua Qwen3 & Jev Score.
    """
    # Đánh giá sơ bộ từ Jev
    existing = storage.get_all_so_nha(ho_so.id_tuyen_duong)
    score_eval = jev_engine.score_house_number_assignment(
        so_nha_moi=ho_so.so_nha_de_xuat or "10 Đường ĐT.785",
        tuyen_duong_id=ho_so.id_tuyen_duong,
        existing_so_nhas=existing,
        muc_dich_dat=ho_so.muc_dich_su_dung_dat.value,
        hien_trang=ho_so.hien_trang_xay_dung.value
    )

    ho_so.ai_risk_score = score_eval.score
    ho_so.ai_feedback = score_eval.details.get("message", "Đã ghi nhận khảo sát toạ độ GPS thực địa.")

    storage.insert_ho_so(ho_so)
    return {
        "success": True,
        "id_yeu_cau": ho_so.id_yeu_cau,
        "score": score_eval.score,
        "message": "Đã lưu kết quả khảo sát thực địa của điều tra viên.",
        "ai_feedback": ho_so.ai_feedback
    }

@app.get("/api/ho-so")
def list_ho_so():
    return storage.get_all_ho_so()

@app.post("/api/ho-so")
async def submit_ho_so(ho_so: HoSoCapMoi):
    ai_analysis = await thinking_llm.analyze_unstructured_address(ho_so.dia_chi_khao_sat)
    ho_so.ai_feedback = ai_analysis["ai_interpretation"]
    storage.insert_ho_so(ho_so)
    return {
        "success": True,
        "message": "Nộp hồ sơ thành công! Đã gửi tới UBND xã Tân Phú thẩm định.",
        "id_yeu_cau": ho_so.id_yeu_cau,
        "ai_feedback": ho_so.ai_feedback
    }

@app.post("/api/ho-so/{id_yeu_cau}/approve")
def approve_dossier(id_yeu_cau: str, so_nha_cap: str, can_bo: str = "UBND Xã Tân Phú"):
    hs = storage.get_ho_so_by_id(id_yeu_cau)
    if not hs:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ")

    # Kiểm tra điều kiện đất đai
    if hs.get("muc_dich_su_dung_dat") in ["DAT_CHUA_CHUYEN_MUC_DICH", "DAT_NONG_NGHIEP"]:
        raise HTTPException(status_code=400, detail="Không thể cấp biển số: Thửa đất chưa chuyển đổi mục đích sang đất ở!")

    sn_id = f"SN_{uuid.uuid4().hex[:6].upper()}"
    new_sn = SoNha(
        id_nha=sn_id,
        so_nha_moi=so_nha_cap,
        so_nha_cu=None,
        ten_chu_ho=hs["ho_ten_nguoi_nop"],
        cccd=hs["cccd"],
        sdt=hs["sdt"],
        toado_gps=hs["toado_gps"],
        trang_thai=TrangThaiSoNha.HIEN_HUU,
        muc_dich_su_dung_dat=MucDichSuDungDat.DAT_O_THO_CU,
        hien_trang_xay_dung=HienTrangXayDung.DA_XAY_NHA,
        so_to_thua=hs.get("so_to_thua"),
        id_tuyen_duong=hs["id_tuyen_duong"],
        id_hem_ngach=hs.get("hem_ngach"),
        dien_tich_mat_tien=hs.get("khoang_cach_mat_tien", 5.0),
        ghi_chu=f"UBND Xã Tân Phú cấp theo hồ sơ {id_yeu_cau}"
    )

    storage.insert_so_nha(new_sn)
    storage.update_ho_so_status(id_yeu_cau, "DA_CAP_SO", can_bo, so_nha_cap)

    pdf_path = cert_generator.generate_pdf(new_sn.dict())
    filename = os.path.basename(pdf_path)

    return {
        "success": True,
        "message": f"UBND Xã Tân Phú đã duyệt và cấp biển số '{so_nha_cap}' cho công dân {hs['ho_ten_nguoi_nop']}.",
        "so_nha_moi": new_sn.dict(),
        "certificate_url": f"/api/cert/download/{filename}"
    }

@app.get("/api/cert/generate/{id_nha}")
def generate_certificate_for_existing(id_nha: str):
    """
    Sinh Giấy chứng nhận PDF cho bản ghi số nhà ĐÃ TỒN TẠI trong CSDL.
    Dành cho Điều tra viên / Cán bộ nội nghiệp tải GCN cho bản ghi hiện hữu.
    """
    sn = storage.get_so_nha_by_id(id_nha)
    if not sn:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy bản ghi {id_nha}")
    
    # Kiểm tra điều kiện: chỉ cấp GCN cho HIEN_HUU (đất thổ cư hợp pháp)
    if sn.get("trang_thai") == "NHA_CHUA_DU_DIEU_KIEN":
        raise HTTPException(status_code=400, detail="Không thể cấp GCN: Nhà chưa đủ điều kiện (đất chưa chuyển mục đích sử dụng)")
    if sn.get("trang_thai") == "DAT_THO_CU_CHUA_XAY":
        raise HTTPException(status_code=400, detail="Không thể cấp GCN: Thửa đất thổ cư chưa xây dựng nhà")
    
    try:
        pdf_path = cert_generator.generate_pdf(sn)
        filename = os.path.basename(pdf_path)
        
        # Ghi log
        with storage.get_connection() as conn:
            conn.execute(
                "INSERT INTO log_hethong (hanh_dong, doi_tuong, chi_tiet) VALUES (?, ?, ?)",
                ("XUẤT GIẤY CHỨNG NHẬN", id_nha,
                 f"Xuất PDF GCN biển số nhà {sn.get('so_nha_moi')} cho {sn.get('ten_chu_ho')}")
            )
            conn.commit()
        
        return {
            "success": True,
            "message": f"Đã sinh Giấy chứng nhận cho {sn.get('ten_chu_ho')} — Biển số: {sn.get('so_nha_moi')}",
            "certificate_url": f"/api/cert/download/{filename}",
            "filename": filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi sinh PDF: {str(e)}")

@app.get("/api/cert/download/{filename}")
def download_certificate(filename: str):
    filepath = os.path.join(CERT_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Tệp chứng nhận không tồn tại")
    return FileResponse(filepath, media_type="application/pdf", filename=filename)

@app.get("/api/system/logs")
def get_logs():
    return storage.get_system_logs()

# =======================================================
# NHẬP LIỆU TỪ FILE EXCEL THỰC ĐỊA (04 file .xlsx)
# =======================================================

@app.post("/api/data-import/thua-dat")
def import_thua_dat(folder: Optional[str] = None):
    """
    Nhập 6.491 thửa đất địa chính từ Trang_1.xlsx, Trang_2.xlsx, Trang_3.xlsx
    (Kế hoạch 2959/KH-BNNMT-BCA kết nối CSDL Quốc gia về dân cư)
    """
    kwargs = {"folder": folder} if folder else {}
    return data_importer.import_thua_dat(**kwargs)

@app.post("/api/data-import/ho-dan")
def import_ho_dan(folder: Optional[str] = None):
    """
    Nhập 7.400 hộ dân thực tế từ DS_Nha_thuc_te.xlsx (11 ấp xã Tân Phú)
    (Bảng kê hộ điều tra thu nhập bình quân năm 2026)
    """
    kwargs = {"folder": folder} if folder else {}
    return data_importer.import_ho_dan(**kwargs)

@app.post("/api/data-import/doi-soat-cheo")
def doi_soat_cheo():
    """
    Chạy thuật toán đối soát chéo: khớp 7.400 hộ dân <-> 6.491 thửa đất theo tên chủ hộ.
    Tự động phân loại pháp lý: Đủ điều kiện cấp số / Chưa đủ / Chưa đối soát.
    """
    return data_importer.doi_soat_cheo()

@app.post("/api/data-import/nap-toan-bo")
async def import_all_data():
    """
    Quy trình 1-Click: Nạp toàn bộ 04 file Excel + Đối soát chéo tự động.
    Bước 1: Nạp 6.491 thửa đất -> Bước 2: Nạp 7.400 hộ dân -> Bước 3: Đối soát chéo.
    """
    result_thua_dat = data_importer.import_thua_dat()
    if not result_thua_dat["success"]:
        return result_thua_dat

    result_ho_dan = data_importer.import_ho_dan()
    if not result_ho_dan["success"]:
        return result_ho_dan

    result_doi_soat = data_importer.doi_soat_cheo()

    return {
        "success": True,
        "message": "Hoàn tất quy trình nạp toàn bộ dữ liệu 04 file Excel và đối soát chéo!",
        "thua_dat": result_thua_dat,
        "ho_dan": result_ho_dan,
        "doi_soat": result_doi_soat
    }

@app.get("/api/data-import/thong-ke-thua-dat")
def thong_ke_thua_dat():
    """Thống kê phân bổ loại đất trong 6.491 thửa đất địa chính."""
    return data_importer.thong_ke_thua_dat()

@app.get("/api/data-import/thong-ke-ho-dan")
def thong_ke_ho_dan():
    """Thống kê hộ dân theo 11 ấp và phân loại pháp lý."""
    return data_importer.thong_ke_ho_dan()

@app.get("/api/data-import/danh-sach-ap")
def danh_sach_ap():
    """Danh sách 11 ấp kèm số hộ, nhân khẩu và tình trạng đối soát."""
    return data_importer.get_danh_sach_ap()

@app.get("/api/data-import/search-ho-dan")
def search_ho_dan(q: str = Query(..., min_length=1), limit: int = 50):
    """Tìm kiếm hộ dân theo tên chủ hộ, địa chỉ, ấp hoặc thông tin thửa đất liên kết."""
    return data_importer.search_ho_dan(q, limit)

@app.get("/api/data-import/search-thua-dat")
def search_thua_dat(q: str = Query(..., min_length=1), limit: int = 50):
    """Tìm kiếm thửa đất theo số tờ, số thửa, tên chủ hoặc mã loại đất."""
    return data_importer.search_thua_dat(q, limit)

@app.get("/api/data-import/ho-dan-theo-ap/{ap}")
def ho_dan_theo_ap(ap: str):
    """Lấy toàn bộ hộ dân của một ấp cụ thể."""
    return data_importer.get_ho_dan_by_ap(ap)

@app.post("/api/data-import/nap-vao-so-nha")
def nap_vao_so_nha():
    """
    Nạp dữ liệu đã đối soát (DU_DIEU_KIEN + CHUA_DU_DIEU_KIEN) từ bảng ho_dan
    vào bảng so_nha chính thức. Tự động:
    - Map tên đường trong địa chỉ → id_tuyen_duong
    - Tạo tuyến đường cấp ấp/tỉnh/huyện nếu chưa có
    - Parse tờ thửa, generate GPS, phân loại pháp lý
    """
    try:
        return data_importer.nap_vao_so_nha()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/so-nha/{id_nha}")
async def update_so_nha(id_nha: str, request: Request):
    """
    Cập nhật thông tin số nhà — Dành cho Điều tra viên và Cán bộ nội nghiệp
    thực hiện công tác làm sạch dữ liệu (data cleaning).
    Chỉ cập nhật các trường được gửi trong body JSON.
    """
    body = await request.json()
    if not body:
        raise HTTPException(status_code=400, detail="Không có dữ liệu cần cập nhật")

    # Kiểm tra bản ghi tồn tại
    existing = storage.get_so_nha_by_id(id_nha)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy bản ghi {id_nha}")

    # Các trường cho phép cập nhật
    allowed_fields = {
        "so_nha_moi", "so_nha_cu", "ten_chu_ho", "cccd", "sdt",
        "trang_thai", "muc_dich_su_dung_dat", "hien_trang_xay_dung",
        "so_to_thua", "id_tuyen_duong", "id_hem_ngach", "loai_nha",
        "dien_tich_mat_tien", "ngay_cap", "so_giay_phep", "ghi_chu",
        # Các trường bổ sung từ đối soát thửa đất & hộ dân
        "dien_tich_thua_dat", "dien_tich_dat_o", "so_gcn",
        "ma_loai_dat_goc", "so_nhan_khau", "dia_chi_day_du",
        "dieu_tra_vien", "ap"
    }

    import json as json_mod
    set_clauses = []
    params = []

    for key, val in body.items():
        if key == "toado_gps" and isinstance(val, dict):
            set_clauses.append("toado_gps = ?")
            params.append(json_mod.dumps(val))
        elif key in allowed_fields:
            set_clauses.append(f"{key} = ?")
            params.append(val)

    if not set_clauses:
        raise HTTPException(status_code=400, detail="Không có trường hợp lệ để cập nhật")

    params.append(id_nha)
    sql = f"UPDATE so_nha SET {', '.join(set_clauses)} WHERE id_nha = ?"

    conn = storage.get_connection()
    cursor = conn.cursor()
    cursor.execute(sql, params)

    # Ghi log thao tác làm sạch dữ liệu
    ten_chu = body.get("ten_chu_ho", existing.get("ten_chu_ho", ""))
    cursor.execute(
        "INSERT INTO log_hethong (hanh_dong, doi_tuong, chi_tiet) VALUES (?, ?, ?)",
        ("LÀM SẠCH DỮ LIỆU", id_nha,
         f"Cán bộ nội nghiệp cập nhật {len(set_clauses)} trường cho {ten_chu} ({id_nha})")
    )
    conn.commit()
    conn.close()
    storage._cache.clear()

    return {
        "success": True,
        "message": f"Đã cập nhật {len(set_clauses)} trường cho bản ghi {id_nha}",
        "id_nha": id_nha,
        "fields_updated": [c.split(" = ")[0] for c in set_clauses]
    }

@app.post("/api/data-import/nap-dat-tho-cu")
def nap_dat_tho_cu():
    """
    Nạp 1.308 thửa đất thổ cư (ONT) chưa có nhà vào bảng so_nha
    với trạng thái DAT_THO_CU_CHUA_XAY để theo dõi quỹ đất dự trữ.
    """
    try:
        return data_importer.nap_dat_tho_cu_chua_xay()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Static Frontend UI
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="frontend_static")

    @app.get("/")
    def serve_frontend_root():
        index_file = os.path.join(FRONTEND_DIR, "index.html")
        return FileResponse(index_file)
