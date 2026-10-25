"""
Module Sinh Giấy Chứng Nhận Biển Số Nhà Điện Tử (PDF & Ký Số QR)
Cơ quan phát hành: ỦY BAN NHÂN DÂN XÃ TÂN PHÚ, TỈNH TÂY NINH
Tuân thủ chuẩn thể thức văn bản hành chính theo Nghị định 30/2020/NĐ-CP.
Sử dụng font Times New Roman Unicode cho tiếng Việt.
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode import qr
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Thư mục xuất PDF: mặc định backend/data/certificates; trên serverless (Vercel)
# chuyển theo SONHA_DATA_DIR (/tmp) vì filesystem chỉ ghi được trong /tmp
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DATA_DIR = os.environ.get("SONHA_DATA_DIR") or os.path.join(_BACKEND_DIR, "data")
CERT_DIR = os.path.join(_DATA_DIR, "certificates")
os.makedirs(CERT_DIR, exist_ok=True)

# ============================================================
# Đăng ký font Times New Roman (hỗ trợ tiếng Việt Unicode)
# ============================================================
_FONT_DIRS = [
    "/System/Library/Fonts/Supplemental",
    "/Library/Fonts",
    os.path.expanduser("~/Library/Fonts"),
    "/usr/share/fonts/truetype/msttcorefonts",
    "/usr/share/fonts/truetype/dejavu",
]

def _find_font(name_patterns, dirs=_FONT_DIRS):
    """Tìm file font .ttf theo pattern trong các thư mục hệ thống."""
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            fl = f.lower()
            if fl.endswith('.ttf'):
                for pat in name_patterns:
                    if pat.lower() in fl:
                        return os.path.join(d, f)
    return None

# Đăng ký font tiếng Việt
_font_registered = False

def _ensure_fonts():
    global _font_registered
    if _font_registered:
        return
    
    # Times New Roman (ưu tiên cho văn bản hành chính)
    tnr = _find_font(["Times New Roman.ttf", "times new roman.ttf", "timesnewroman"])
    tnr_bold = _find_font(["Times New Roman Bold.ttf", "times new roman bold"])
    tnr_italic = _find_font(["Times New Roman Italic.ttf", "times new roman italic"])
    tnr_bi = _find_font(["Times New Roman Bold Italic.ttf", "times new roman bold italic"])
    
    if tnr:
        pdfmetrics.registerFont(TTFont("TimesVN", tnr))
        if tnr_bold:
            pdfmetrics.registerFont(TTFont("TimesVN-Bold", tnr_bold))
        if tnr_italic:
            pdfmetrics.registerFont(TTFont("TimesVN-Italic", tnr_italic))
        if tnr_bi:
            pdfmetrics.registerFont(TTFont("TimesVN-BoldItalic", tnr_bi))
        
        # Đăng ký font family
        from reportlab.pdfbase.pdfmetrics import registerFontFamily
        registerFontFamily(
            "TimesVN",
            normal="TimesVN",
            bold="TimesVN-Bold" if tnr_bold else "TimesVN",
            italic="TimesVN-Italic" if tnr_italic else "TimesVN",
            boldItalic="TimesVN-BoldItalic" if tnr_bi else "TimesVN"
        )
        _font_registered = True
    else:
        # Fallback: Arial Unicode
        arial_uni = _find_font(["Arial Unicode.ttf", "arialunicode"])
        if arial_uni:
            pdfmetrics.registerFont(TTFont("TimesVN", arial_uni))
            pdfmetrics.registerFont(TTFont("TimesVN-Bold", arial_uni))
            pdfmetrics.registerFont(TTFont("TimesVN-Italic", arial_uni))
            pdfmetrics.registerFont(TTFont("TimesVN-BoldItalic", arial_uni))
            from reportlab.pdfbase.pdfmetrics import registerFontFamily
            registerFontFamily("TimesVN", normal="TimesVN", bold="TimesVN-Bold",
                             italic="TimesVN-Italic", boldItalic="TimesVN-BoldItalic")
            _font_registered = True


class CertificateGenerator:
    @staticmethod
    def generate_pdf(so_nha: dict, output_filename: str = None) -> str:
        """Sinh file PDF Giấy chứng nhận Biển số nhà cho UBND Xã Tân Phú, Tây Ninh."""
        _ensure_fonts()
        
        if not output_filename:
            id_nha_clean = so_nha.get("id_nha", "SN").replace("/", "_").replace(" ", "_")
            output_filename = f"GCN_{id_nha_clean}_{datetime.now().strftime('%Y%m%d%H%M')}.pdf"

        filepath = os.path.join(CERT_DIR, output_filename)
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=25*mm,
            leftMargin=25*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )

        # ============================================================
        # Định nghĩa styles (dùng font TimesVN Unicode)
        # ============================================================
        font_main = "TimesVN" if _font_registered else "Helvetica"
        font_bold = "TimesVN-Bold" if _font_registered else "Helvetica-Bold"
        font_italic = "TimesVN-Italic" if _font_registered else "Helvetica-Oblique"
        font_bi = "TimesVN-BoldItalic" if _font_registered else "Helvetica-BoldOblique"
        
        styles = getSampleStyleSheet()
        normal = styles["Normal"]

        st_header_left = ParagraphStyle("HeaderLeft", parent=normal,
            fontName=font_bold, fontSize=11, alignment=1, leading=15,
            textColor=colors.HexColor("#1e293b"))

        st_header_right = ParagraphStyle("HeaderRight", parent=normal,
            fontName=font_bold, fontSize=11, alignment=1, leading=15,
            textColor=colors.HexColor("#1e293b"))

        st_sub = ParagraphStyle("Sub", parent=normal,
            fontName=font_main, fontSize=10, alignment=1, leading=13,
            textColor=colors.HexColor("#475569"))

        st_main_title = ParagraphStyle("MainTitle", parent=normal,
            fontName=font_bold, fontSize=16, alignment=1, leading=22,
            textColor=colors.HexColor("#be123c"), spaceAfter=3*mm)

        st_badge = ParagraphStyle("Badge", parent=normal,
            fontName=font_bold, fontSize=28, alignment=1, leading=36,
            textColor=colors.HexColor("#1d4ed8"))

        st_label = ParagraphStyle("Label", parent=normal,
            fontName=font_bold, fontSize=10, leading=14,
            textColor=colors.HexColor("#334155"))

        st_value = ParagraphStyle("Value", parent=normal,
            fontName=font_main, fontSize=10, leading=14,
            textColor=colors.HexColor("#0f172a"))

        st_footer = ParagraphStyle("Footer", parent=normal,
            fontName=font_main, fontSize=9, alignment=1, leading=13,
            textColor=colors.HexColor("#64748b"))

        st_sign = ParagraphStyle("Sign", parent=normal,
            fontName=font_bold, fontSize=10, alignment=1, leading=14,
            textColor=colors.HexColor("#1e293b"))

        elements = []

        # ============================================================
        # 1. HEADER: Quốc hiệu & Cơ quan
        # ============================================================
        ngay_str = datetime.now().strftime("%d tháng %m năm %Y")
        
        header_left = Paragraph(
            f"<b>ỦY BAN NHÂN DÂN</b><br/>"
            f"<b>XÃ TÂN PHÚ</b><br/>"
            f"<font size=9>Số: .../GCN-UBND</font>",
            st_header_left
        )
        header_right = Paragraph(
            f"<b>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</b><br/>"
            f"<b><u>Độc lập - Tự do - Hạnh phúc</u></b><br/>"
            f"<font size=9><i>Tân Phú, ngày {ngay_str}</i></font>",
            st_header_right
        )
        
        header_table = Table([[header_left, header_right]], colWidths=[55*mm, 105*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('LINEBELOW', (0,0), (0,0), 0.8, colors.HexColor("#1e293b")),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 8*mm))

        # ============================================================
        # 2. TIÊU ĐỀ CHÍNH
        # ============================================================
        elements.append(Paragraph("GIẤY CHỨNG NHẬN", st_main_title))
        elements.append(Paragraph("CẤP BIỂN SỐ NHÀ", ParagraphStyle("Title2", parent=normal,
            fontName=font_bold, fontSize=14, alignment=1, leading=20,
            textColor=colors.HexColor("#be123c"))))
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph(
            "Hệ Thống Cơ Sở Dữ Liệu Quản Lý Số Nhà – Xã Tân Phú, Tỉnh Tây Ninh",
            st_sub))
        elements.append(Spacer(1, 5*mm))

        # ============================================================
        # 3. KHUNG BIỂN SỐ NHÀ
        # ============================================================
        so_nha_moi = so_nha.get("so_nha_moi", "---")
        
        badge_inner = Paragraph(
            f"BIỂN SỐ NHÀ<br/><font size=28 color='#1d4ed8'><b>{so_nha_moi}</b></font>",
            ParagraphStyle("BadgeInner", parent=normal,
                fontName=font_bold, fontSize=11, alignment=1, leading=16,
                textColor=colors.HexColor("#475569"))
        )
        badge_table = Table([[badge_inner]], colWidths=[160*mm])
        badge_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#eff6ff")),
            ('BOX', (0,0), (-1,-1), 2, colors.HexColor("#2563eb")),
            ('ROUNDEDCORNERS', [4, 4, 4, 4]),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        elements.append(badge_table)
        elements.append(Spacer(1, 5*mm))

        # ============================================================
        # 4. BẢNG THÔNG TIN CHI TIẾT
        # ============================================================
        toado = so_nha.get("toado_gps", {})
        if isinstance(toado, str):
            import json
            try:
                toado = json.loads(toado)
            except:
                toado = {}
        
        lat = toado.get("lat", 0.0)
        lng = toado.get("lng", 0.0)
        gps_str = f"{lat:.6f}°N, {lng:.6f}°E (WGS84)" if lat else "Chưa cập nhật"
        
        # Lấy thông tin bổ sung
        ten_chu = str(so_nha.get("ten_chu_ho") or "---")
        cccd = str(so_nha.get("cccd") or "Chưa cập nhật")
        sdt = str(so_nha.get("sdt") or "Chưa cập nhật")
        tuyen_duong = str(so_nha.get("id_tuyen_duong") or "---")
        so_to_thua = str(so_nha.get("so_to_thua") or "Chưa cập nhật")
        so_nha_cu = str(so_nha.get("so_nha_cu") or "Không có (Cấp mới)")
        
        # Thông tin thửa đất enriched
        dt_thua = so_nha.get("dien_tich_thua_dat", 0) or 0
        dt_dat_o = so_nha.get("dien_tich_dat_o", 0) or 0
        so_gcn = str(so_nha.get("so_gcn") or "Chưa cập nhật")
        ma_loai = str(so_nha.get("ma_loai_dat_goc") or "---")
        nhan_khau = so_nha.get("so_nhan_khau", 0) or 0
        ap_name = str(so_nha.get("ap") or "---")
        dia_chi = str(so_nha.get("dia_chi_day_du") or "Xã Tân Phú, Tỉnh Tây Ninh")
        
        muc_dich_text = "Đất ở tại nông thôn (ONT)" if so_nha.get("muc_dich_su_dung_dat") == "DAT_O_THO_CU" \
            else "Đất chưa chuyển mục đích" if so_nha.get("muc_dich_su_dung_dat") == "DAT_CHUA_CHUYEN_MUC_DICH" \
            else str(so_nha.get("muc_dich_su_dung_dat", "---"))
        
        dt_str = f"{dt_thua} m²" if dt_thua > 0 else "Chưa cập nhật"
        dt_o_str = f"{dt_dat_o} m²" if dt_dat_o > 0 else "Chưa cập nhật"

        info_rows = [
            [Paragraph("<b>1. Chủ sở hữu / Người đại diện:</b>", st_label),
             Paragraph(f"<b>{ten_chu}</b>", st_value)],
            [Paragraph("<b>2. Số CCCD:</b>", st_label),
             Paragraph(cccd, st_value)],
            [Paragraph("<b>3. Số điện thoại:</b>", st_label),
             Paragraph(sdt, st_value)],
            [Paragraph("<b>4. Địa chỉ:</b>", st_label),
             Paragraph(f"Ấp {ap_name}, {dia_chi}", st_value)],
            [Paragraph("<b>5. Tuyến đường:</b>", st_label),
             Paragraph(tuyen_duong, st_value)],
            [Paragraph("<b>6. Số tờ / Số thửa:</b>", st_label),
             Paragraph(so_to_thua, st_value)],
            [Paragraph("<b>7. Mục đích sử dụng đất:</b>", st_label),
             Paragraph(f"{muc_dich_text} ({ma_loai})", st_value)],
            [Paragraph("<b>8. Diện tích thửa đất:</b>", st_label),
             Paragraph(f"{dt_str} | Đất ở: {dt_o_str}", st_value)],
            [Paragraph("<b>9. Số GCN QSDĐ:</b>", st_label),
             Paragraph(so_gcn, st_value)],
            [Paragraph("<b>10. Số nhân khẩu:</b>", st_label),
             Paragraph(str(nhan_khau) if nhan_khau > 0 else "Chưa cập nhật", st_value)],
            [Paragraph("<b>11. Số nhà cũ:</b>", st_label),
             Paragraph(so_nha_cu, st_value)],
            [Paragraph("<b>12. Tọa độ GIS (WGS84):</b>", st_label),
             Paragraph(f"<font face='{font_main}' size=9>{gps_str}</font>", st_value)],
        ]

        info_table = Table(info_rows, colWidths=[55*mm, 105*mm])
        info_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor("#f1f5f9")),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 6*mm))

        # ============================================================
        # 5. QR CODE + KÝ SỐ
        # ============================================================
        qr_content = f"UBND XA TAN PHU | SN:{so_nha.get('id_nha')} | BSN:{so_nha_moi} | CHU:{ten_chu} | GPS:{lat},{lng}"
        qr_code = qr.QrCodeWidget(qr_content)
        qr_code.barWidth = 22*mm
        qr_code.barHeight = 22*mm
        qr_drawing = Drawing(22*mm, 22*mm)
        qr_drawing.add(qr_code)

        qr_info = Paragraph(
            f"<b>XÁC THỰC SỐ HÓA ĐỊA CHÍNH</b><br/>"
            f"<font size=8>Quét mã QR để tra cứu trên<br/>Bản đồ số GIS Xã Tân Phú.</font><br/>"
            f"<font size=7><i>Mã: {so_nha.get('id_nha')}</i></font><br/>"
            f"<font size=7><i>Thời gian: {datetime.now().strftime('%H:%M %d/%m/%Y')}</i></font>",
            st_footer
        )

        sign_block = Paragraph(
            f"<b>TM. ỦY BAN NHÂN DÂN</b><br/>"
            f"<b>CHỦ TỊCH</b><br/><br/>"
            f"<i>(Ký số điện tử)</i><br/><br/>"
            f"<font color='#dc2626'><b>[ĐÃ KÝ SỐ]</b></font><br/>"
            f"<b>UBND XÃ TÂN PHÚ</b>",
            st_sign
        )

        footer_table = Table([[qr_drawing, qr_info, sign_block]], colWidths=[28*mm, 75*mm, 57*mm])
        footer_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (0,0), (0,0), 'CENTER'),
            ('ALIGN', (1,0), (1,0), 'LEFT'),
            ('ALIGN', (2,0), (2,0), 'CENTER'),
            ('LINEABOVE', (0,0), (-1,0), 0.5, colors.HexColor("#cbd5e1")),
            ('TOPPADDING', (0,0), (-1,-1), 8),
        ]))
        elements.append(footer_table)

        # ============================================================
        # 6. GHI CHÚ CUỐI
        # ============================================================
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph(
            f"<i>Giấy chứng nhận này được cấp bởi Hệ Thống CSDL Quản Lý Số Nhà – UBND Xã Tân Phú, Tỉnh Tây Ninh. "
            f"Có giá trị pháp lý khi được xác thực qua mã QR.</i>",
            ParagraphStyle("Note", parent=normal, fontName=font_italic, fontSize=8,
                         alignment=1, leading=11, textColor=colors.HexColor("#94a3b8"))
        ))

        doc.build(elements)
        return filepath

cert_generator = CertificateGenerator()
