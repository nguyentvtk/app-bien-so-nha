/**
 * Numbering UI Controller (numbering_ui.js)
 * Điều khiển lựa chọn Phương pháp đánh số nhà: ĐÔ THỊ / NÔNG THÔN
 * và gọi API /api/so-nha/de-xuat-so để đề xuất số tự động.
 *
 * ─ 🏙️ ĐÔ THỊ: tuần tự chẵn/lẻ (TT 08/2024/TT-BXD); nhà chèn giữa → 20A/20B
 * ─ 🌾 NÔNG THÔN: số = khoảng cách từ ĐẦU tuyến ÷ 10 m (chuẩn Úc/Mỹ);
 *                 đất trống không cần chừa số — đo mét là có số
 */

// =========================================================================
// Đọc / đổi trạng thái thẻ chọn chế độ
// =========================================================================
function docCheDoDanhSo(tenNhomRadio) {
    const checked = document.querySelector(`input[name="${tenNhomRadio}"]:checked`);
    return checked ? checked.value : "DO_THI";
}

function khoiTaoTheCheDo(tenNhomRadio) {
    document.querySelectorAll(`input[name="${tenNhomRadio}"]`).forEach(radio => {
        const card = radio.closest(".sn-mode-card");
        const capNhat = () => {
            document.querySelectorAll(`input[name="${tenNhomRadio}"]`).forEach(r => {
                r.closest(".sn-mode-card")?.classList.toggle("sn-mode-selected", r.checked);
            });
            // Hiện/ẩn tuỳ chọn theo chế độ (chỉ áp dụng cho modal cấp số)
            if (tenNhomRadio === "sn-che-do") {
                const nongThon = docCheDoDanhSo(tenNhomRadio) === "NONG_THON";
                document.getElementById("sn-do-thi-options")?.classList.toggle("hidden", nongThon);
                document.getElementById("sn-nong-thon-hint")?.classList.toggle("hidden", !nongThon);
            }
        };
        radio.addEventListener("change", capNhat);
        card?.addEventListener("click", (e) => {
            if (e.target !== radio) { radio.checked = true; radio.dispatchEvent(new Event("change")); }
        });
        capNhat();
    });
}

// =========================================================================
// Gọi API đề xuất số
// =========================================================================
async function goiDeXuatSo(payload) {
    const res = await fetch(`${API_BASE}/api/so-nha/de-xuat-so`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) {
        const msg = typeof data.thong_bao === "string" ? data.thong_bao
            : (Array.isArray(data.chi_tiet) ? data.chi_tiet.join("; ") : "Không đề xuất được số nhà.");
        throw new Error(msg);
    }
    return data;
}

// =========================================================================
// MODAL CẤP SỐ NHÀ (form-create-sn)
// =========================================================================
async function deXuatSoTrongModal() {
    const cheDo = docCheDoDanhSo("sn-che-do");
    const idTuyen = document.getElementById("modal-sn-route").value;
    const lat = parseFloat(document.getElementById("modal-sn-lat").value);
    const lng = parseFloat(document.getElementById("modal-sn-lng").value);
    const ketQua = document.getElementById("sn-suggest-result");

    const payload = { che_do: cheDo, id_tuyen: idTuyen };
    if (cheDo === "NONG_THON") {
        if (!isFinite(lat) || !isFinite(lng)) {
            showToast("Chế độ Nông thôn cần toạ độ GPS của nhà — bấm nút '📍 Lấy vị trí hiện tại của nhà' trước.", "warning");
            return;
        }
        payload.toado_gps = { lat, lng };
    } else {
        const phia = document.getElementById("sn-phia").value;
        const chen = parseInt(document.getElementById("sn-chen-sau-so").value);
        if (phia) payload.phia = phia;
        if (isFinite(chen) && chen > 0) payload.chen_sau_so = chen;
    }

    try {
        showToast(cheDo === "DO_THI" ? "Đang tính số tiếp theo theo quy tắc đô thị..." : "Đang đo khoảng cách trên tim tuyến GIS...", "info");
        const data = await goiDeXuatSo(payload);
        if (!data.so_de_xuat) {
            showToast(data.giai_thich || "Không suy ra được số nhà từ dữ liệu hiện có.", "warning");
            return;
        }
        document.getElementById("modal-sn-new").value = data.so_de_xuat;
        ketQua.classList.remove("hidden");
        ketQua.innerHTML = `
            <b class="block mb-0.5"><i class="fa-solid fa-circle-check text-emerald-600 mr-1"></i>Đề xuất: số ${data.so_de_xuat}</b>
            ${data.giai_thich}
        `;
        showToast(`Đề xuất số ${data.so_de_xuat} theo chế độ ${cheDo === "DO_THI" ? "Đô thị" : "Nông thôn"}.`, "success");
    } catch (err) {
        ketQua.classList.remove("hidden");
        ketQua.innerHTML = `<span class="text-rose-700"><i class="fa-solid fa-triangle-exclamation mr-1"></i>${err.message}</span>`;
        showToast(err.message, "error");
    }
}

function layViTriNhaChoModal() {
    if (!navigator.geolocation) {
        showToast("Thiết bị không hỗ trợ Geolocation.", "error");
        return;
    }
    showToast("Đang lấy vị trí hiện tại của nhà qua GPS...", "info");
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            const lat = pos.coords.latitude.toFixed(6);
            const lng = pos.coords.longitude.toFixed(6);
            document.getElementById("modal-sn-lat").value = lat;
            document.getElementById("modal-sn-lng").value = lng;
            if (window.pinGPSOnMap) window.pinGPSOnMap(+lat, +lng, pos.coords.accuracy);
            showToast(`Đã lấy toạ độ nhà: ${lat}, ${lng} (±${Math.round(pos.coords.accuracy)}m).`, "success");
        },
        (err) => {
            const msg = err.code === 1 ? "Bạn đã từ chối quyền truy cập vị trí."
                : err.code === 2 ? "Không tìm được tín hiệu GPS." : "Quá thời gian chờ GPS.";
            showToast(msg + " Có thể nhập tay toạ độ.", "error");
        },
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
}

// =========================================================================
// CÔNG CỤ ĐIỀU TRA VIÊN — đề xuất theo GPS vừa ghim
// =========================================================================
async function deXuatSoDieuTraVien() {
    const cheDo = docCheDoDanhSo("surveyor-che-do");
    const idTuyen = document.getElementById("surveyor-route-select").value;
    const lat = parseFloat(document.getElementById("surveyor-lat").value);
    const lng = parseFloat(document.getElementById("surveyor-lng").value);
    const ketQua = document.getElementById("surveyor-suggest-result");

    const payload = { che_do: cheDo, id_tuyen: idTuyen };
    if (cheDo === "NONG_THON") {
        if (!isFinite(lat) || !isFinite(lng)) {
            showToast("Chưa ghim GPS — bấm nút '📍 Lấy Vị Trí Hiện Tại' trước khi đề xuất số.", "warning");
            return;
        }
        payload.toado_gps = { lat, lng };
    }

    try {
        const data = await goiDeXuatSo(payload);
        if (!data.so_de_xuat) {
            showToast(data.giai_thich || "Không suy ra được số nhà.", "warning");
            return;
        }
        document.getElementById("surveyor-sn-dexuat").value = data.so_de_xuat;
        ketQua.classList.remove("hidden");
        ketQua.innerHTML = `<b>Đề xuất số ${data.so_de_xuat}:</b> ${data.giai_thich}`;
        showToast(`Đề xuất số ${data.so_de_xuat} cho tuyến đang khảo sát.`, "success");
    } catch (err) {
        ketQua.classList.remove("hidden");
        ketQua.innerHTML = `<span class="text-rose-700">${err.message}</span>`;
        showToast(err.message, "error");
    }
}

// =========================================================================
// GẮN SỰ KIỆN
// =========================================================================
document.addEventListener("DOMContentLoaded", () => {
    khoiTaoTheCheDo("sn-che-do");
    khoiTaoTheCheDo("surveyor-che-do");
    document.getElementById("btn-sn-suggest")?.addEventListener("click", deXuatSoTrongModal);
    document.getElementById("btn-sn-house-gps")?.addEventListener("click", layViTriNhaChoModal);
    document.getElementById("btn-surveyor-suggest")?.addEventListener("click", deXuatSoDieuTraVien);
});

// =========================================================================
// WINDOW EXPORTS
// =========================================================================
window.docCheDoDanhSo = docCheDoDanhSo;
