"""
Module Thuật toán Virtual Node (Điểm ảo Dự trữ số nhà)
Giải quyết bài toán các khoảng đất trống xen kẽ trong đô thị.
Sử dụng phép nội suy GPS (Linear / Geo-Interpolation) theo tim tuyến đường và khoảng cách mặt tiền
để tự động sinh ra các số nhà dự trữ (Virtual Nodes).
Giữ vững nguyên tắc Chẵn - Lẻ liên tục khi có công trình xây mới phát sinh.
"""

import math
from typing import List, Dict, Any, Tuple, Optional
from app.models.schemas import GPSCoordinate

class VirtualNodeService:
    @staticmethod
    def calculate_distance_meters(coord1: Dict[str, float], coord2: Dict[str, float]) -> float:
        """Tính khoảng cách xấp xỉ giữa 2 toạ độ GPS theo công thức Haversine (mét)"""
        lat1, lon1 = coord1["lat"], coord1["lng"]
        lat2, lon2 = coord2["lat"], coord2["lng"]
        R = 6371000  # Bán kính Trái Đất (mét)

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    @staticmethod
    def interpolate_coordinates(coord_a: Dict[str, float], coord_b: Dict[str, float], fraction: float) -> Dict[str, float]:
        """Nội suy toạ độ giữa 2 điểm A và B theo tỷ lệ fraction (0.0 -> 1.0)"""
        return {
            "lat": round(coord_a["lat"] + (coord_b["lat"] - coord_a["lat"]) * fraction, 6),
            "lng": round(coord_a["lng"] + (coord_b["lng"] - coord_a["lng"]) * fraction, 6)
        }

    @classmethod
    def generate_virtual_nodes_between(
        cls, 
        id_tuyen: str,
        ten_duong: str,
        nha_truoc: Dict[str, Any], 
        nha_sau: Dict[str, Any],
        chieu_rong_lo_chuan: float = 5.0
    ) -> List[Dict[str, Any]]:
        """
        Nội suy các điểm ảo dự trữ nằm giữa 2 số nhà hiện hữu (cùng dãy chẵn hoặc cùng dãy lẻ).
        Ví dụ: Giữa số 4 và số 10 còn khoảng trống 18m -> sinh ra điểm ảo số 6 và số 8.
        """
        virtual_nodes = []
        coord_a = nha_truoc["toado_gps"]
        coord_b = nha_sau["toado_gps"]

        total_distance = cls.calculate_distance_meters(coord_a, coord_b)
        if total_distance <= chieu_rong_lo_chuan * 1.5:
            # Hai nhà nằm sát nhau, không còn đất trống
            return []

        # Trích xuất số nhà nguyên thuỷ
        def extract_num(sn_str: str) -> Optional[int]:
            clean = "".join([c for c in sn_str.split()[0] if c.isdigit()])
            return int(clean) if clean else None

        num_a = extract_num(nha_truoc["so_nha_moi"])
        num_b = extract_num(nha_sau["so_nha_moi"])

        if num_a is None or num_b is None or num_b <= num_a:
            return []

        # Số bước nhảy chẵn hoặc lẻ: step = 2
        missing_count = (num_b - num_a) // 2 - 1
        if missing_count <= 0:
            return []

        for i in range(1, missing_count + 1):
            next_num = num_a + (i * 2)
            fraction = i / (missing_count + 1)
            interpolated_gps = cls.interpolate_coordinates(coord_a, coord_b, fraction)

            virtual_node = {
                "id_nha": f"SN_VN_{id_tuyen}_{next_num}",
                "so_nha_moi": f"{next_num} {ten_duong} (Dự trữ)",
                "so_nha_cu": None,
                "ten_chu_ho": "Lô đất trống (Dự trữ số)",
                "toado_gps": interpolated_gps,
                "trang_thai": "DAT_TRONG",
                "id_tuyen_duong": id_tuyen,
                "id_hem_ngach": nha_truoc.get("id_hem_ngach"),
                "loai_nha": "Đất trống",
                "dien_tich_mat_tien": chieu_rong_lo_chuan,
                "ghi_chu": f"Điểm ảo nội suy tự động giữa số {num_a} và số {num_b}"
            }
            virtual_nodes.append(virtual_node)

        return virtual_nodes

virtual_node_service = VirtualNodeService()
