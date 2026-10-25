"""
Cổng điều phối tập trung MCP Gateway (Single Entry Point Router)
Hỗ trợ cả chuẩn JSON-RPC 2.0 và RESTful endpoints cho Frontend & Zalo Mini App.
Tích hợp điều phối 3 tầng: LLM Thinking -> Jev Decision -> Modules Execution.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
import uuid
import json

from app.models.schemas import JSONRPCRequest, JSONRPCResponse, SoNha, HoSoCapMoi
from app.modules.storage import storage
from app.modules.address_tree import address_tree_service
from app.modules.virtual_nodes import virtual_node_service
from app.modules.cert_generator import cert_generator
from app.ai_agents.thinking_llm import thinking_llm
from app.ai_agents.jev_decision import jev_engine
from app.mcp_gateway.middleware import mcp_middleware

gateway_router = APIRouter(prefix="/mcp-gateway", tags=["MCP Gateway"])

@gateway_router.post("/rpc", response_model=JSONRPCResponse)
async def handle_json_rpc(req: JSONRPCRequest):
    """
    Điểm vào duy nhất chuẩn JSON-RPC 2.0 (Single Entry Point Gateway)
    Method formats:
      - 'sonha.list': Danh sách số nhà
      - 'sonha.search': Tra cứu chéo cũ - mới
      - 'sonha.tree': Cây phân cấp hẻm ngách
      - 'sonha.assign': Cấp biển số nhà (Bị đánh chặn bởi Jev Score)
      - 'hoso.submit': Nộp hồ sơ dịch vụ công
      - 'ai.analyze_address': Phân tích địa chỉ bằng LLM Qwen3
    """
    method = req.method
    params = req.params or {}

    try:
        # 1. READ Operations (Pass-through)
        if method == "sonha.list":
            id_tuyen = params.get("id_tuyen")
            trang_thai = params.get("trang_thai")
            res = storage.get_all_so_nha(id_tuyen, trang_thai)
            return JSONRPCResponse(id=req.id, result=res)

        elif method == "sonha.search":
            q = params.get("query", "")
            res = storage.search_so_nha(q)
            return JSONRPCResponse(id=req.id, result=res)

        elif method == "sonha.tree":
            id_tuyen = params.get("id_tuyen", "TD_01")
            so_nhas = storage.get_all_so_nha(id_tuyen)
            tree = address_tree_service.build_tree_structure(so_nhas)
            return JSONRPCResponse(id=req.id, result=tree)

        elif method == "tuyen_duong.list":
            res = storage.get_all_tuyen_duong()
            return JSONRPCResponse(id=req.id, result=res)

        elif method == "hoso.list":
            res = storage.get_all_ho_so()
            return JSONRPCResponse(id=req.id, result=res)

        elif method == "ai.analyze_address":
            raw_text = params.get("text", "")
            ai_res = await thinking_llm.analyze_unstructured_address(raw_text)
            return JSONRPCResponse(id=req.id, result=ai_res)

        # 2. WRITE Operations (Intercepted by Jev Decision Layer)
        elif method == "sonha.assign":
            so_nha_moi = params.get("so_nha_moi", "")
            id_tuyen = params.get("id_tuyen_duong", "TD_01")
            existing = storage.get_all_so_nha(id_tuyen)
            is_virtual = params.get("is_virtual_node", False)

            # Bước Jev Score
            score_decision = jev_engine.score_house_number_assignment(
                so_nha_moi=so_nha_moi,
                tuyen_duong_id=id_tuyen,
                existing_so_nhas=existing,
                is_virtual_node=is_virtual
            )

            # Đánh chặn qua Middleware
            allowed, message = mcp_middleware.evaluate_and_intercept("sonha.assign", score_decision)
            if not allowed:
                return JSONRPCResponse(
                    id=req.id,
                    error={"code": -32001, "message": message, "data": score_decision.dict()}
                )

            # Thực thi gán số nhà
            so_nha_obj = SoNha(**params)
            storage.insert_so_nha(so_nha_obj)

            return JSONRPCResponse(
                id=req.id,
                result={
                    "success": True,
                    "message": message,
                    "jev_score": score_decision.dict(),
                    "so_nha": so_nha_obj.dict()
                }
            )

        elif method == "hoso.submit":
            ho_so_obj = HoSoCapMoi(**params)
            # Tự động cho Qwen3 phân tích địa chỉ nếu chưa có ai_feedback
            if not ho_so_obj.ai_feedback:
                ai_eval = await thinking_llm.analyze_unstructured_address(ho_so_obj.dia_chi_khao_sat)
                ho_so_obj.ai_feedback = ai_eval["ai_interpretation"]

            storage.insert_ho_so(ho_so_obj)
            return JSONRPCResponse(id=req.id, result={"success": True, "id_yeu_cau": ho_so_obj.id_yeu_cau})

        else:
            return JSONRPCResponse(id=req.id, error={"code": -32601, "message": f"Method '{method}' không tồn tại"})

    except Exception as e:
        return JSONRPCResponse(id=req.id, error={"code": -32603, "message": str(e)})
