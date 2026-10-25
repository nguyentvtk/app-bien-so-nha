/**
 * Route Calibrator Controller (route_calibrator.js)
 * Hiệu chỉnh toạ độ 2 điểm chuẩn (đầu & cuối) của 1 tuyến đường —
 * toàn bộ tuyến còn lại của xã Tân Phú tự biến đổi theo phép đồng dạng.
 *
 * Luồng nghiệp vụ:
 *  1. Cán bộ chọn tuyến chuẩn (bảng Thống kê → nút "Hiệu chỉnh toạ độ").
 *  2. Nhập/kéo ghim/lấy GPS cho 2 điểm mới trên mini-map.
 *  3. "Xem trước ảnh hưởng" → backend tính phép biến đổi (không ghi CSDL),
 *     hiển thị tham số + bảng toạ độ cũ→mới của từng tuyến.
 *  4. "Áp dụng cho toàn xã" → backend sao lưu bản cũ rồi cập nhật tất cả.
 *  5. "Hoàn tác lần gần nhất" → phục hồi từ bản sao lưu.
 */

let calibMap = null;
let calibMarkerDau = null;
let calibMarkerCuoi = null;
let calibLine = null;
let calibDuBaoGanNhat = null; // kết quả xem trước hợp lệ cuối cùng

// =========================================================================
// MỞ / ĐÓNG MODAL
// =========================================================================
function openCalibrateModal(idTuyen = null) {
    if (typeof AppState === "undefined" || !AppState.tuyenDuongs.length) {
        showToast("Chưa tải được danh sách tuyến đường. Vui lòng thử lại.", "warning");
        return;
    }
    const modal = document.getElementById("modal-calibrate");
    const select = document.getElementById("calib-route-select");

    // Danh sách tuyến
    select.innerHTML = AppState.tuyenDuongs.map(td => {
        const selected = (idTuyen && td.id_tuyen === idTuyen) || (!idTuyen && td.id_tuyen === AppState.selectedTuyenDuong) ? " selected" : "";
        return `<option value="${td.id_tuyen}"${selected}>${td.ten_duong} (${td.id_tuyen})</option>`;
    }).join("");

    document.getElementById("calib-result").classList.add("hidden");
    document.getElementById("btn-calibrate-apply").disabled = true;
    calibDuBaoGanNhat = null;

    modal.classList.remove("hidden");
    modal.classList.add("flex");

    napToaDoTuyenChuan();
    setTimeout(() => {
        khoiTaoCalibMap();
        if (calibMap) {
            calibMap.invalidateSize();
            bayToiTuyenChuan();
        }
    }, 180);
}

function closeCalibrateModal() {
    const modal = document.getElementById("modal-calibrate");
    modal.classList.add("hidden");
    modal.classList.remove("flex");
}

// =========================================================================
// MINI-MAP: 2 GHIM KÉO THẢ ĐỒNG BỘ VỚI Ô NHẬP
// =========================================================================
function khoiTaoCalibMap() {
    if (calibMap) return;
    calibMap = L.map("calib-map", { zoomControl: true }).setView([11.6050, 106.1850], 15);
    L.tileLayer("https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", {
        attribution: "&copy; Google Satellite | UBND Xã Tân Phú",
        maxZoom: 20
    }).addTo(calibMap);

    const taoIcon = (mau, ten) => L.divIcon({
        html: `<div class="flex items-center justify-center">
                 <div class="w-8 h-8 rounded-full ${mau} text-white flex items-center justify-center shadow-lg border-2 border-white font-bold text-[10px]">${ten}</div>
               </div>`,
        className: "calib-pin",
        iconSize: [32, 32],
        iconAnchor: [16, 32]
    });

    calibMarkerDau = L.marker([11.6050, 106.1850], { icon: taoIcon("bg-blue-600", "ĐẦU"), draggable: true }).addTo(calibMap);
    calibMarkerCuoi = L.marker([11.6090, 106.1890], { icon: taoIcon("bg-rose-600", "CUỐI"), draggable: true }).addTo(calibMap);
    calibLine = L.polyline([], { color: "#4f46e5", weight: 4, dashArray: "8, 6" }).addTo(calibMap);

    calibMarkerDau.on("drag", e => capNhatInputTuMarker("dau", e.target.getLatLng()));
    calibMarkerCuoi.on("drag", e => capNhatInputTuMarker("cuoi", e.target.getLatLng()));
    calibMarkerDau.on("dragend", veLaiLine);
    calibMarkerCuoi.on("dragend", veLaiLine);

    // 4 ô nhập thay đổi → cập nhật ghim
    ["calib-dau-lat", "calib-dau-lng", "calib-cuoi-lat", "calib-cuoi-lng"].forEach(id => {
        document.getElementById(id).addEventListener("input", capNhatMarkerTuInput);
    });
    capNhatMarkerTuInput();
    window.addEventListener("resize", () => calibMap && calibMap.invalidateSize());
}

function capNhatInputTuMarker(loai, ll) {
    document.getElementById(`calib-${loai}-lat`).value = ll.lat.toFixed(6);
    document.getElementById(`calib-${loai}-lng`).value = ll.lng.toFixed(6);
}

function capNhatMarkerTuInput() {
    const dau = docDiem("dau"), cuoi = docDiem("cuoi");
    if (calibMarkerDau && dau) calibMarkerDau.setLatLng(dau);
    if (calibMarkerCuoi && cuoi) calibMarkerCuoi.setLatLng(cuoi);
    veLaiLine();
}

function veLaiLine() {
    if (!calibLine) return;
    const dau = docDiem("dau"), cuoi = docDiem("cuoi");
    calibLine.setLatLngs(dau && cuoi ? [dau, cuoi] : []);
}

function docDiem(loai) {
    const lat = parseFloat(document.getElementById(`calib-${loai}-lat`).value);
    const lng = parseFloat(document.getElementById(`calib-${loai}-lng`).value);
    return (isFinite(lat) && isFinite(lng)) ? { lat, lng } : null;
}

function napToaDoTuyenChuan() {
    const idTuyen = document.getElementById("calib-route-select").value;
    const td = AppState.tuyenDuongs.find(t => t.id_tuyen === idTuyen);
    if (!td) return;
    document.getElementById("calib-dau-lat").value = td.toado_batdau.lat;
    document.getElementById("calib-dau-lng").value = td.toado_batdau.lng;
    document.getElementById("calib-cuoi-lat").value = td.toado_kethuc.lat;
    document.getElementById("calib-cuoi-lng").value = td.toado_kethuc.lng;
    capNhatMarkerTuInput();
    bayToiTuyenChuan();
}

function bayToiTuyenChuan() {
    if (!calibMap) return;
    const dau = docDiem("dau"), cuoi = docDiem("cuoi");
    if (dau && cuoi) {
        calibMap.fitBounds(L.latLngBounds([dau, cuoi]).pad(0.4), { animate: false });
    } else if (dau) {
        calibMap.setView(dau, 16);
    }
}

// =========================================================================
// GPS: LẤY VỊ TRÍ HIỆN TẠI CHO ĐIỂM ĐẦU / ĐIỂM CUỐI
// =========================================================================
function ganGPSVaoDiem(loai) {
    if (!navigator.geolocation) {
        showToast("Thiết bị không hỗ trợ Geolocation.", "error");
        return;
    }
    showToast(`Đang lấy vị trí hiện tại gán cho điểm ${loai === "dau" ? "ĐẦU" : "CUỐI"}...`, "info");
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            const lat = pos.coords.latitude.toFixed(6);
            const lng = pos.coords.longitude.toFixed(6);
            document.getElementById(`calib-${loai}-lat`).value = lat;
            document.getElementById(`calib-${loai}-lng`).value = lng;
            capNhatMarkerTuInput();
            if (loai === "dau" && calibMarkerDau) calibMap.panTo([+lat, +lng]);
            showToast(`Đã gán toạ độ GPS ${lat}, ${lng} cho điểm ${loai === "dau" ? "ĐẦU" : "CUỐI"}.`, "success");
        },
        (err) => {
            const msg = err.code === 1 ? "Bạn đã từ chối quyền truy cập vị trí."
                : err.code === 2 ? "Không tìm được tín hiệu GPS."
                : "Quá thời gian chờ GPS.";
            showToast(`${msg} Có thể nhập tay toạ độ hoặc kéo ghim trên bản đồ.`, "error");
        },
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
}

// =========================================================================
// XEM TRƯỚC & ÁP DỤNG
// =========================================================================
async function xemTruocHieuChinh() {
    const idTuyen = document.getElementById("calib-route-select").value;
    const dau = docDiem("dau"), cuoi = docDiem("cuoi");
    if (!dau || !cuoi) {
        showToast("Vui lòng nhập đủ toạ độ 2 điểm (đầu & cuối) trước khi xem trước.", "warning");
        return;
    }

    const body = {
        toado_batdau_moi: dau,
        toado_kethuc_moi: cuoi,
        ap_dung_so_nha: document.getElementById("calib-apply-sonha").checked
    };

    try {
        showToast("Đang tính toán ảnh hưởng lên toàn bộ tuyến đường...", "info");
        const res = await fetch(`${API_BASE}/api/tuyen-duong/${encodeURIComponent(idTuyen)}/hieu-chinh-toa-do/kiem-tra`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(typeof data.thong_bao === "string" ? data.thong_bao : "Dữ liệu gửi lên chưa hợp lệ.", "error");
            return;
        }
        calibDuBaoGanNhat = { idTuyen, body };
        hienThiKetQuaXemTruoc(data);
        document.getElementById("btn-calibrate-apply").disabled = false;
    } catch (err) {
        showToast("Lỗi kết nối máy chủ: " + err.message, "error");
    }
}

function hienThiKetQuaXemTruoc(data) {
    const box = document.getElementById("calib-result");
    const pb = data.phep_bien_doi;
    const mau = data.du_kien.slice(0, 10);

    box.className = "mt-3 p-3.5 rounded-2xl bg-indigo-50/80 border border-indigo-200 space-y-3";
    box.innerHTML = `
        <div class="text-xs text-indigo-900 leading-relaxed">
            <div class="font-bold mb-1"><i class="fa-solid fa-calculator mr-1"></i>Phép biến đổi suy ra từ tuyến chuẩn <b>${data.tuyen_chuan.ten_duong}</b>:</div>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-1.5">
                <div class="bg-white/70 rounded-xl p-2 text-center"><div class="font-extrabold text-sm">${data.phep_bien_doi.dich_chuyen_m} m</div><div class="text-[10px] text-slate-500">Dịch điểm đầu</div></div>
                <div class="bg-white/70 rounded-xl p-2 text-center"><div class="font-extrabold text-sm">${pb.xoay_do}°</div><div class="text-[10px] text-slate-500">Xoay</div></div>
                <div class="bg-white/70 rounded-xl p-2 text-center"><div class="font-extrabold text-sm">${pb.ty_le}</div><div class="text-[10px] text-slate-500">Tỉ lệ</div></div>
                <div class="bg-white/70 rounded-xl p-2 text-center"><div class="font-extrabold text-sm">${data.so_tuyen_se_cap_nhat}</div><div class="text-[10px] text-slate-500">Tuyến cập nhật</div></div>
            </div>
            <p class="mt-2 text-slate-600">${pb.mo_ta}. Dịch chuyển trung bình mỗi tuyến: <b>${data.dich_chuyen_trung_binh_m} m</b>${data.so_nha_se_cap_nhat ? ` — kèm theo <b>${data.so_nha_se_cap_nhat}</b> bản ghi số nhà.` : ""}</p>
        </div>
        <div class="overflow-x-auto max-h-56 overflow-y-auto rounded-xl border border-indigo-100">
            <table class="w-full text-left text-[11px] table-mobile-cards">
                <thead class="bg-indigo-100/70 font-bold text-indigo-800 uppercase sticky top-0">
                    <tr>
                        <th class="px-2.5 py-1.5">Tuyến</th>
                        <th class="px-2.5 py-1.5">Điểm đầu cũ → mới</th>
                        <th class="px-2.5 py-1.5">Điểm cuối cũ → mới</th>
                        <th class="px-2.5 py-1.5">Dịch</th>
                    </tr>
                </thead>
                <tbody>
                    ${mau.map(t => `
                        <tr class="border-b border-indigo-50">
                            <td data-label="Tuyến" class="px-2.5 py-1.5 font-bold">${t.ten_duong}</td>
                            <td data-label="Đầu cũ→mới" class="px-2.5 py-1.5 font-mono">${t.cu_batdau.lat.toFixed(5)}, ${t.cu_batdau.lng.toFixed(5)} → <b class="text-indigo-700">${t.moi_batdau.lat.toFixed(5)}, ${t.moi_batdau.lng.toFixed(5)}</b></td>
                            <td data-label="Cuối cũ→mới" class="px-2.5 py-1.5 font-mono">${t.cu_kethuc.lat.toFixed(5)}, ${t.cu_kethuc.lng.toFixed(5)} → <b class="text-indigo-700">${t.moi_kethuc.lat.toFixed(5)}, ${t.moi_kethuc.lng.toFixed(5)}</b></td>
                            <td data-label="Dịch" class="px-2.5 py-1.5 font-semibold text-amber-700">${t.dich_chuyen_m} m</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        </div>
        <p class="text-[10px] text-slate-500 italic">Hiển thị 10/${data.so_tuyen_se_cap_nhat} tuyến đầu tiên. Bấm "Áp dụng cho toàn xã" để ghi nhận (tự động sao lưu để hoàn tác).</p>
    `;
    box.classList.remove("hidden");
    box.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function apDungHieuChinh() {
    if (!calibDuBaoGanNhat) {
        showToast("Hãy bấm 'Xem trước ảnh hưởng' trước khi áp dụng.", "warning");
        return;
    }
    const { idTuyen, body } = calibDuBaoGanNhat;
    if (!confirm(`XÁC NHẬN ÁP DỤNG TOÀN XÃ:\nPhép biến đổi sẽ cập nhật toạ độ cho mọi tuyến đường${body.ap_dung_so_nha ? " và các số nhà hiện hữu" : ""}.\nHệ thống tự sao lưu bản cũ để hoàn tác.\n\nBạn có chắc chắn?`)) return;

    try {
        showToast("Đang cập nhật toạ độ toàn xã & sao lưu bản cũ...", "info");
        const res = await fetch(`${API_BASE}/api/tuyen-duong/${encodeURIComponent(idTuyen)}/hieu-chinh-toa-do`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.thong_bao || "Áp dụng thất bại.", "error");
            return;
        }
        showToast(`✅ ${data.thong_bao}`, "success");
        closeCalibrateModal();
        await loadInitialData(); // nạp lại tuyến đường + số nhà + vẽ lại bản đồ
        if (window.gisMap) setTimeout(() => window.gisMap.invalidateSize(), 200);
    } catch (err) {
        showToast("Lỗi kết nối: " + err.message, "error");
    }
}

async function hoanTacHieuChinh() {
    if (!confirm("Hoàn tác lần hiệu chỉnh toạ độ gần nhất (phục hồi toàn bộ toạ độ cũ)?")) return;
    try {
        const res = await fetch(`${API_BASE}/api/tuyen-duong/phuc-hoi-toa-do`, { method: "POST" });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.thong_bao || "Không thể hoàn tác.", "warning");
            return;
        }
        showToast(`↩️ ${data.thong_bao}`, "success");
        closeCalibrateModal();
        await loadInitialData();
    } catch (err) {
        showToast("Lỗi kết nối: " + err.message, "error");
    }
}

// =========================================================================
// GẮN SỰ KIỆN
// =========================================================================
document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("modal-calibrate");
    if (!modal) return;

    document.getElementById("btn-close-calibrate")?.addEventListener("click", closeCalibrateModal);
    modal.addEventListener("click", (e) => { if (e.target === modal) closeCalibrateModal(); });
    document.getElementById("calib-route-select")?.addEventListener("change", napToaDoTuyenChuan);
    document.getElementById("calib-dau-gps")?.addEventListener("click", () => ganGPSvaoDiem("dau"));
    document.getElementById("calib-cuoi-gps")?.addEventListener("click", () => ganGPSvaoDiem("cuoi"));
    document.getElementById("btn-calibrate-preview")?.addEventListener("click", xemTruocHieuChinh);
    document.getElementById("btn-calibrate-apply")?.addEventListener("click", apDungHieuChinh);
    document.getElementById("btn-calibrate-undo")?.addEventListener("click", hoanTacHieuChinh);
});

// =========================================================================
// WINDOW EXPORTS
// =========================================================================
window.openCalibrateModal = openCalibrateModal;
window.closeCalibrateModal = closeCalibrateModal;
