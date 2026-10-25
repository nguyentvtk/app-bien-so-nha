"""
Tầng 3: MCP Gateway Middleware Security & Interception Rules
Đánh chặn toàn bộ thao tác ghi/sửa dữ liệu theo thang điểm Jev Score:
- Score >= 0.95 (GREEN_SAFE): Cho phép thực thi tự động.
- 0.70 <= Score < 0.95 (YELLOW_WARN): Gắn cảnh báo / Yêu cầu xác nhận từ cán bộ.
- Score < 0.70 (RED_DANGER): Ngăn chặn (Block) lập tức, ghi log vết bảo mật.
"""

import logging
from typing import Dict, Any, Tuple
from app.models.schemas import ScoreDecision

logger = logging.getLogger(__name__)

class RiskInterceptionMiddleware:
    RISK_SAFE_THRESHOLD = 0.95
    RISK_WARN_THRESHOLD = 0.70

    @classmethod
    def evaluate_and_intercept(cls, action_name: str, decision: ScoreDecision) -> Tuple[bool, str]:
        """
        Đánh chặn thao tác dựa trên ScoreDecision của Jev.
        Trả về: (được phép thực thi hay không, thông điệp phản hồi)
        """
        score = decision.score

        if score >= cls.RISK_SAFE_THRESHOLD:
            logger.info(f"[MCP GATEWAY - SAFE] Thao tác '{action_name}' đạt điểm {score:.2f} >= {cls.RISK_SAFE_THRESHOLD}. Tự động thực thi.")
            return True, "Thao tác an toàn, đã được duyệt tự động."

        elif score >= cls.RISK_WARN_THRESHOLD:
            msg = decision.details.get("message", "Cần xác nhận từ cán bộ quản lý do có cảnh báo quy chuẩn.")
            logger.warning(f"[MCP GATEWAY - WARN] Thao tác '{action_name}' đạt điểm {score:.2f}. Cảnh báo: {msg}")
            return True, f"CẢNH BÁO: {msg}"

        else:
            msg = decision.details.get("message", "Thao tác vi phạm an toàn quy chuẩn cấp số nhà.")
            logger.error(f"[MCP GATEWAY - BLOCK] Thao tác '{action_name}' bị chặn! Điểm {score:.2f} < {cls.RISK_WARN_THRESHOLD}. Lý do: {msg}")
            return False, f"BỊ NGĂN CHẶN: {msg}"

mcp_middleware = RiskInterceptionMiddleware()
