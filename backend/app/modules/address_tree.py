"""
Module Cây Hẻm Ngách (Path-based Routing)
Giải quyết bài toán ngõ ngách chằng chịt, tự động nối chuỗi tạo số nhà chuẩn:
Hem_12 -> Ngach_34 -> SoNha_56  ==>  12/34/56 Đường X
Hỗ trợ trực quan hoá cây phân cấp hẻm ngách cho giao diện người dùng.
"""

from typing import List, Dict, Any, Optional

class AddressTreeService:
    @staticmethod
    def parse_path_to_address(tuyen_duong: str, hem_ngach_path: Optional[str], so_thu_tu: str) -> str:
        """
        Nối chuỗi phân cấp:
        Ví dụ:
          tuyen_duong: "Đường Cách Mạng"
          hem_ngach_path: "Hem_12/Ngach_6"
          so_thu_tu: "4"
          -> "12/6/4 Đường Cách Mạng"
        """
        if not hem_ngach_path:
            return f"{so_thu_tu} {tuyen_duong}"

        parts = hem_ngach_path.split("/")
        segments = []
        for p in parts:
            p_clean = p.replace("Hem_", "").replace("Ngach_", "").replace("Hem", "").replace("Ngach", "")
            if p_clean:
                segments.append(p_clean)

        segments.append(str(so_thu_tu))
        prefix = "/".join(segments)
        return f"{prefix} {tuyen_duong}"

    @staticmethod
    def build_tree_structure(so_nhas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Gom nhóm toàn bộ số nhà theo cây phân cấp:
        Mặt tiền -> Hẻm cấp 1 -> Ngách cấp 2 -> Số nhà chi tiết
        """
        tree: Dict[str, Any] = {
            "name": "Mặt tiền đường",
            "type": "root",
            "children": {}
        }

        for sn in so_nhas:
            hem_ngach = sn.get("id_hem_ngach")
            if not hem_ngach:
                # Nhà mặt tiền
                if "mat_tien" not in tree["children"]:
                    tree["children"]["mat_tien"] = {
                        "name": "Nhà Mặt Tiền Chính",
                        "type": "street_front",
                        "items": []
                    }
                tree["children"]["mat_tien"]["items"].append(sn)
            else:
                # Nhà trong hẻm/ngách
                parts = hem_ngach.split("/")
                current_node = tree["children"]
                for i, part in enumerate(parts):
                    if part not in current_node:
                        is_last = (i == len(parts) - 1)
                        part_name = part.replace("Hem_", "Hẻm ").replace("Ngach_", "Ngách ")
                        current_node[part] = {
                            "name": part_name,
                            "type": "alley" if "Hem" in part else "branch",
                            "children": {},
                            "items": []
                        }
                    if i == len(parts) - 1:
                        current_node[part]["items"].append(sn)
                    current_node = current_node[part]["children"]

        return tree

address_tree_service = AddressTreeService()
