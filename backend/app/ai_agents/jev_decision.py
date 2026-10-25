"""
Tầng 2: Jev Decision Layer (System 1 - Typed Decisions)
Phản xạ nhanh (70–150ms), phi sinh ngữ (non-generative), tỷ lệ ảo giác = 0%.
Bổ sung kiểm tra tính pháp lý đất đai theo quy định:
- Đất chưa chuyển đổi mục đích sử dụng sang đất ở (chưa có thổ cư) -> Chặn cấp biển số (Score < 0.70 - RED_DANGER).
- Đất thổ cư nhưng chưa xây dựng -> Ghi nhận Điểm ảo dự trữ (Virtual Node) chờ xây dựng (Score 0.98 - GREEN_SAFE).
"""

import re
from typing import List, Dict, Any, Optional
from app.models.schemas import ChoiceDecision, ScoreDecision, NoulDecision, MucDichSuDungDat, HienTrangXayDung

class JevDecisionEngine:
    @staticmethod
    def choice(action_type: str, context: Dict[str, Any]) -> ChoiceDecision:
        options = {
            "LOOKUP": 0.95,
            "ASSIGN_HOUSE_NUMBER": 0.92,
            "SURVEY_FIELD_GPS": 0.97,
            "INTERPOLATE_VIRTUAL_NODE": 0.88,
            "GENERATE_CERTIFICATE": 0.96,
            "ESCALATE_LLM": 0.10
        }
        selected = action_type if action_type in options else "LOOKUP"
        return ChoiceDecision(
            type="choice",
            selected=selected,
            confidence=options.get(selected, 0.90),
            probabilities=options
        )

    @staticmethod
    def score_house_number_assignment(
        so_nha_moi: str,
        tuyen_duong_id: str,
        existing_so_nhas: List[Dict[str, Any]],
        muc_dich_dat: str = "DAT_O_THO_CU",
        hien_trang: str = "DA_XAY_NHA",
        is_virtual_node: bool = False
    ) -> ScoreDecision:
        """
        Chấm điểm rủi ro & tính hợp lệ của việc cấp số nhà theo quy chuẩn UBND xã Tân Phú, tỉnh Tây Ninh:
        1. PHÁP LÝ ĐẤT ĐAI: Có nhà nhưng đất chưa chuyển mục đích sử dụng sang đất ở -> Score 0.20 (RED_DANGER - BLOCK)
        2. ĐẤT THỔ CƯ CHƯA XÂY: Thửa đất trống đã có thổ cư -> Score 0.98 (GREEN_SAFE - Quy hoạch Điểm ảo Virtual Node)
        3. TRÙNG SỐ NHÀ: Score 0.15 (RED_DANGER - BLOCK)
        4. SAI ĐỊNH DẠNG: Score 0.50 (RED_DANGER - BLOCK)
        5. BƯỚC NHẢY LỚN: Score 0.76 (YELLOW_WARN)
        6. HỢP LỆ HOÀN TOÀN: Score 0.96 (GREEN_SAFE)
        """
        # 1. Kiểm tra pháp lý chuyển mục đích sử dụng đất
        if muc_dich_dat in ["DAT_CHUA_CHUYEN_MUC_DICH", "DAT_NONG_NGHIEP"]:
            return ScoreDecision(
                type="score",
                score=0.20,
                confidence=0.99,
                status="RED_DANGER",
                details={
                    "rule_violated": "DAT_CHUA_CHUYEN_MUC_DICH",
                    "message": "BỊ CHẶN: Thửa đất chưa được chuyển đổi mục đích sử dụng sang đất ở (chưa lên thổ cư). "
                               "Theo quy định, công trình xây dựng trên đất chưa chuyển mục đích KHÔNG ĐƯỢC CẤP SỐ NHÀ, "
                               "chỉ ghi nhận hiện trạng để quản lý trật tự xây dựng.",
                    "action_required": "BLOCK",
                    "phan_loai": "NHA_CHUA_DU_DIEU_KIEN"
                }
            )

        # 2. Đất thổ cư nhưng chưa xây dựng nhà
        if hien_trang == "DAT_TRONG" and muc_dich_dat == "DAT_O_THO_CU":
            return ScoreDecision(
                type="score",
                score=0.98,
                confidence=0.98,
                status="GREEN_SAFE",
                details={
                    "rule_passed": "DAT_THO_CU_QUY_HOACH_DU_TRU",
                    "message": "Thửa đất đã có thổ cư hợp pháp nhưng chưa xây dựng. "
                               "Hệ thống quy hoạch thành Điểm ảo dự trữ (Virtual Node) để giữ quỹ số nhà liên tục.",
                    "action_required": "RESERVE_VIRTUAL_NODE",
                    "phan_loai": "DAT_THO_CU_CHUA_XAY"
                }
            )

        so_nha_moi_clean = so_nha_moi.strip().lower()

        # 3. Kiểm tra trùng lặp
        for sn in existing_so_nhas:
            existing_clean = sn.get("so_nha_moi", "").strip().lower()
            existing_clean = existing_clean.replace("(dự trữ)", "").strip()
            target_clean = so_nha_moi_clean.replace("(dự trữ)", "").strip()

            if existing_clean == target_clean and sn.get("trang_thai") == "HIEN_HUU":
                return ScoreDecision(
                    type="score",
                    score=0.15,
                    confidence=0.99,
                    status="RED_DANGER",
                    details={
                        "rule_violated": "TRUNG_SO_NHA",
                        "message": f"Số nhà '{so_nha_moi}' đã tồn tại trên tuyến đường và đang thuộc sở hữu của {sn.get('ten_chu_ho')}!",
                        "action_required": "BLOCK"
                    }
                )

        # 4. Kiểm tra định dạng số đầu tiên
        match = re.match(r"^(\d+)", so_nha_moi.strip())
        if not match:
            return ScoreDecision(
                type="score",
                score=0.50,
                confidence=0.95,
                status="RED_DANGER",
                details={
                    "rule_violated": "SAI_DINH_DANG",
                    "message": "Số nhà bắt buộc phải bắt đầu bằng chữ số (Ví dụ: 14, 14/2, 28)!",
                    "action_required": "BLOCK"
                }
            )

        number_val = int(match.group(1))

        # 5. Điểm ảo dự trữ
        if is_virtual_node:
            return ScoreDecision(
                type="score",
                score=0.98,
                confidence=0.97,
                status="GREEN_SAFE",
                details={
                    "rule_passed": "VIRTUAL_NODE_MATCHED",
                    "message": "Vị trí đất thổ cư trống hoàn toàn trùng khớp với Điểm ảo dự trữ trong quy hoạch.",
                    "action_required": "ALLOW_EXECUTION"
                }
            )

        # 6. Kiểm tra bước nhảy số quá lớn
        same_route_numbers = []
        for sn in existing_so_nhas:
            m = re.match(r"^(\d+)", sn.get("so_nha_moi", ""))
            if m:
                same_route_numbers.append(int(m.group(1)))

        if same_route_numbers:
            max_num = max(same_route_numbers)
            if number_val > max_num + 30:
                return ScoreDecision(
                    type="score",
                    score=0.76,
                    confidence=0.88,
                    status="YELLOW_WARN",
                    details={
                        "rule_violated": "BUOC_NHAY_LON",
                        "message": f"Số đề xuất ({number_val}) cách xa số lớn nhất hiện tại ({max_num}) hơn 30 đơn vị. Cần cán bộ đối chiếu lại quy hoạch.",
                        "action_required": "REQUIRE_CONFIRMATION"
                    }
                )

        # 7. Mặc định an toàn
        return ScoreDecision(
            type="score",
            score=0.96,
            confidence=0.95,
            status="GREEN_SAFE",
            details={
                "rule_passed": "QUY_CHUAN_HOP_LE",
                "message": "Đất thổ cư hợp pháp, công trình xây dựng thực tế và số nhà đề xuất tuân thủ đúng quy chuẩn.",
                "action_required": "ALLOW_EXECUTION"
            }
        )

    @staticmethod
    def noul_check_goal(state: Dict[str, Any]) -> NoulDecision:
        has_certificate = state.get("certificate_generated", False)
        status_updated = state.get("status_updated", False)
        is_done = has_certificate and status_updated
        return NoulDecision(
            type="noul",
            isCompleted=is_done,
            confidence=0.99 if is_done else 0.85,
            reason="Quy trình hoàn tất: Giấy chứng nhận đã được xuất và dữ liệu đã lưu trữ." if is_done else "Chưa hoàn tất quy trình."
        )

jev_engine = JevDecisionEngine()
