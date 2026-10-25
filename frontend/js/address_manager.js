/**
 * Address Manager & Tree Hierarchy Controller (address_manager.js)
 * Địa bàn: XÃ TÂN PHÚ, TỈNH TÂY NINH - Cơ quan: ỦY BAN NHÂN DÂN XÃ TÂN PHÚ.
 * Quản lý danh sách số nhà, số tờ thửa, tình trạng pháp lý đất đai và cây ngõ ngách.
 */

function renderSoNhaTable() {
    const tbody = document.getElementById("so-nha-table-body");
    const countEl = document.getElementById("so-nha-count");
    if (!tbody) return;

    tbody.innerHTML = "";
    if (countEl) countEl.textContent = `${AppState.soNhas.length} vị trí / thửa đất`;

    if (AppState.soNhas.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-4 py-8 text-center text-slate-400 italic">
                    <i class="fa-solid fa-folder-open text-2xl mb-2 block"></i>
                    Không có số nhà nào trên tuyến đường được chọn.
                </td>
            </tr>
        `;
        return;
    }

    AppState.soNhas.forEach(sn => {
        const tr = document.createElement("tr");
        tr.className = "border-b border-slate-100 hover:bg-blue-50/50 transition cursor-pointer text-xs";

        const isIneligible = (sn.trang_thai === "NHA_CHUA_DU_DIEU_KIEN" || sn.muc_dich_su_dung_dat === "DAT_CHUA_CHUYEN_MUC_DICH");
        const isVirtual = (sn.trang_thai === "DAT_THO_CU_CHUA_XAY" || sn.trang_thai === "DAT_TRONG");

        let statusBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700">Đã cấp số</span>';
        if (isIneligible) {
            statusBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-700">Chưa đủ ĐK</span>';
        } else if (isVirtual) {
            statusBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">Thổ cư dự trữ</span>';
        }

        const landPurposeBadge = (sn.muc_dich_su_dung_dat === "DAT_O_THO_CU")
            ? '<span class="text-emerald-700 font-semibold">Đất ở (ONT)</span>'
            : '<span class="text-rose-600 font-semibold">Chưa chuyển MĐ</span>';

        tr.innerHTML = `
            <td data-label="Số nhà / Thửa" class="px-3 py-2.5">
                <div class="font-bold text-slate-900">${sn.so_nha_moi}</div>
                ${sn.so_to_thua ? `<div class="text-[10px] text-blue-600 font-mono">${sn.so_to_thua}</div>` : ''}
                ${sn.dien_tich_thua_dat > 0 ? `<div class="text-[10px] text-slate-500">${sn.dien_tich_thua_dat}m²${sn.dien_tich_dat_o > 0 ? ` (ĐO: ${sn.dien_tich_dat_o}m²)` : ''}</div>` : ''}
            </td>
            <td data-label="Chủ hộ" class="px-3 py-2.5">
                <div class="font-medium text-slate-800">${sn.ten_chu_ho}</div>
                ${sn.cccd ? `<div class="text-[10px] text-slate-500 font-mono">CCCD: ${sn.cccd}</div>` : ''}
                ${sn.sdt ? `<div class="text-[10px] text-blue-600">📞 ${sn.sdt}</div>` : ''}
                ${sn.ap ? `<div class="text-[10px] text-slate-400">Ấp ${sn.ap}</div>` : ''}
            </td>
            <td data-label="Pháp lý đất" class="px-3 py-2.5">
                ${landPurposeBadge}
                ${sn.ma_loai_dat_goc ? `<div class="text-[10px] text-slate-500 font-mono mt-0.5">${sn.ma_loai_dat_goc}</div>` : ''}
                ${sn.so_gcn ? `<div class="text-[10px] text-indigo-600 mt-0.5">GCN: ${sn.so_gcn}</div>` : ''}
            </td>
            <td data-label="Trạng thái" class="px-3 py-2.5">${statusBadge}</td>
            <td data-label="GCN" class="px-3 py-2.5 text-right">
                ${!isIneligible && !isVirtual ? `
                    <button onclick="event.stopPropagation(); downloadCertFor('${sn.id_nha}')" class="p-1.5 text-blue-600 hover:bg-blue-100 rounded-lg transition" title="Tải Giấy chứng nhận PDF">
                        <i class="fa-solid fa-file-pdf"></i>
                    </button>
                ` : `
                    <span class="text-slate-300">--</span>
                `}
            </td>
            <td data-label="Thao tác" class="px-3 py-2.5 text-center whitespace-nowrap">
                <button onclick="event.stopPropagation(); ghimToaDoGPS('${sn.id_nha}')" class="p-1 text-emerald-600 hover:bg-emerald-100 rounded-lg transition" title="📍 Lấy vị trí hiện tại từ thiết bị">
                    <i class="fa-solid fa-location-crosshairs"></i>
                </button>
                <button onclick="event.stopPropagation(); openEditModal('${sn.id_nha}')" class="p-1 text-amber-600 hover:bg-amber-100 rounded-lg transition" title="✏️ Sửa / Làm sạch dữ liệu">
                    <i class="fa-solid fa-pen-to-square"></i>
                </button>
            </td>
        `;

        tr.addEventListener("click", () => {
            if (window.gisMap && sn.toado_gps) {
                switchTab("map_view");
                window.gisMap.flyTo([sn.toado_gps.lat, sn.toado_gps.lng], 18, { duration: 1.2 });
                if (sn._marker) sn._marker.openPopup();
            }
        });

        tbody.appendChild(tr);
    });
}

// ====================== CHỈNH SỬA / LÀM SẠCH DỮ LIỆU ======================

/**
 * Mở modal chỉnh sửa với dữ liệu bản ghi hiện tại
 */
function openEditModal(id_nha) {
    const sn = AppState.soNhas.find(x => x.id_nha === id_nha);
    if (!sn) {
        showToast("Không tìm thấy bản ghi " + id_nha, "error");
        return;
    }

    // Helper: safely set value
    const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.value = (val !== null && val !== undefined) ? val : "";
    };

    // Populate selector tuyến đường
    const routeSel = document.getElementById("edit-sn-route");
    if (routeSel) {
        routeSel.innerHTML = "";
        AppState.tuyenDuongs.forEach(td => {
            const opt = document.createElement("option");
            opt.value = td.id_tuyen;
            opt.textContent = `${td.ten_duong} (${td.phan_loai})`;
            if (td.id_tuyen === sn.id_tuyen_duong) opt.selected = true;
            routeSel.appendChild(opt);
        });
    }

    // Điền dữ liệu cơ bản
    setVal("edit-sn-id", sn.id_nha);
    setVal("edit-sn-new", sn.so_nha_moi);
    setVal("edit-sn-old", sn.so_nha_cu);
    setVal("edit-sn-owner", sn.ten_chu_ho);
    setVal("edit-sn-cccd", sn.cccd);
    setVal("edit-sn-sdt", sn.sdt);
    setVal("edit-sn-to-thua", sn.so_to_thua);
    setVal("edit-sn-width", sn.dien_tich_mat_tien || 5.0);
    setVal("edit-sn-ghi-chu", sn.ghi_chu);

    // Thông tin thửa đất bổ sung
    setVal("edit-sn-dt-thua-dat", sn.dien_tich_thua_dat || 0);
    setVal("edit-sn-dt-dat-o", sn.dien_tich_dat_o || 0);
    setVal("edit-sn-gcn", sn.so_gcn);
    setVal("edit-sn-ma-loai-dat", sn.ma_loai_dat_goc);
    setVal("edit-sn-nhan-khau", sn.so_nhan_khau || 0);
    setVal("edit-sn-dia-chi", sn.dia_chi_day_du);
    setVal("edit-sn-ap", sn.ap);

    // Tọa độ GPS
    if (sn.toado_gps) {
        setVal("edit-sn-lat", sn.toado_gps.lat || 11.6050);
        setVal("edit-sn-lng", sn.toado_gps.lng || 106.1850);
    }

    // Selects
    const setSelect = (id, val) => {
        const el = document.getElementById(id);
        if (el && val) el.value = val;
    };
    setSelect("edit-sn-land-purpose", sn.muc_dich_su_dung_dat);
    setSelect("edit-sn-build-status", sn.hien_trang_xay_dung);
    setSelect("edit-sn-trang-thai", sn.trang_thai);
    setSelect("edit-sn-loai-nha", sn.loai_nha);

    // Hiển thị ID bản ghi + thông tin tóm tắt
    document.getElementById("edit-sn-id-display").textContent = `ID: ${sn.id_nha}`;
    const subtitle = document.getElementById("edit-modal-subtitle");
    let subtitleText = `Bản ghi: ${sn.ten_chu_ho} — ${sn.so_nha_moi}`;
    if (sn.ap) subtitleText += ` | Ấp ${sn.ap}`;
    if (sn.ma_loai_dat_goc) subtitleText += ` | Loại đất: ${sn.ma_loai_dat_goc}`;
    subtitle.textContent = subtitleText;

    // Hiển thị modal
    const modal = document.getElementById("modal-edit-sn");
    modal.classList.remove("hidden");
    modal.style.display = "flex";
}

/**
 * Đóng modal chỉnh sửa
 */
function closeEditModal() {
    const modal = document.getElementById("modal-edit-sn");
    modal.classList.add("hidden");
    modal.style.display = "none";
}

/**
 * Gửi dữ liệu đã chỉnh sửa lên server (PUT /api/so-nha/{id_nha})
 */
async function submitEditSoNha() {
    const id_nha = document.getElementById("edit-sn-id").value;
    if (!id_nha) return;

    // Helper: safely get value from form element
    const getVal = (id) => {
        const el = document.getElementById(id);
        return el ? el.value : null;
    };

    const payload = {
        so_nha_moi: getVal("edit-sn-new"),
        so_nha_cu: getVal("edit-sn-old") || null,
        ten_chu_ho: getVal("edit-sn-owner"),
        cccd: getVal("edit-sn-cccd") || null,
        sdt: getVal("edit-sn-sdt") || null,
        trang_thai: getVal("edit-sn-trang-thai"),
        muc_dich_su_dung_dat: getVal("edit-sn-land-purpose"),
        hien_trang_xay_dung: getVal("edit-sn-build-status"),
        so_to_thua: getVal("edit-sn-to-thua") || null,
        id_tuyen_duong: getVal("edit-sn-route"),
        loai_nha: getVal("edit-sn-loai-nha"),
        dien_tich_mat_tien: parseFloat(getVal("edit-sn-width")) || 5.0,
        ghi_chu: getVal("edit-sn-ghi-chu") || null,
        // Thông tin thửa đất bổ sung
        dien_tich_thua_dat: parseFloat(getVal("edit-sn-dt-thua-dat")) || 0,
        dien_tich_dat_o: parseFloat(getVal("edit-sn-dt-dat-o")) || 0,
        so_gcn: getVal("edit-sn-gcn") || null,
        ma_loai_dat_goc: getVal("edit-sn-ma-loai-dat") || null,
        so_nhan_khau: parseInt(getVal("edit-sn-nhan-khau")) || 0,
        dia_chi_day_du: getVal("edit-sn-dia-chi") || null,
        ap: getVal("edit-sn-ap") || null,
        toado_gps: {
            lat: parseFloat(getVal("edit-sn-lat")),
            lng: parseFloat(getVal("edit-sn-lng"))
        }
    };

    try {
        const res = await fetch(`${API_BASE}/api/so-nha/${id_nha}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await res.json();

        if (res.ok) {
            showToast(`✅ Đã lưu thay đổi cho ${payload.ten_chu_ho}`, "success");
            closeEditModal();
            await refreshSoNhaData();
        } else {
            showToast(`❌ Lỗi: ${result.detail || "Không xác định"}`, "error");
        }
    } catch (err) {
        showToast(`❌ Lỗi kết nối: ${err.message}`, "error");
    }
}

// ====================== GHIM TOẠ ĐỘ GPS TỪ THIẾT BỊ ======================

/**
 * Ghim toạ độ GPS thực tế từ thiết bị (điện thoại/máy tính bảng) cho một bản ghi.
 * Sử dụng Geolocation API của trình duyệt → lấy vị trí hiện tại → cập nhật lên server.
 * Dành cho Điều tra viên đi thực địa.
 */
async function ghimToaDoGPS(id_nha) {
    const sn = AppState.soNhas.find(x => x.id_nha === id_nha);
    if (!sn) {
        showToast("Không tìm thấy bản ghi " + id_nha, "error");
        return;
    }

    // Kiểm tra trình duyệt hỗ trợ Geolocation
    if (!navigator.geolocation) {
        showToast("❌ Trình duyệt không hỗ trợ Geolocation. Vui lòng dùng Chrome/Safari trên điện thoại.", "error");
        return;
    }

    showToast(`📍 Đang lấy vị trí GPS cho: ${sn.ten_chu_ho}...`, "info");

    try {
        const position = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,   // Yêu cầu độ chính xác cao (GPS thực)
                timeout: 15000,             // Timeout 15 giây
                maximumAge: 0               // Không dùng cache, luôn lấy vị trí mới nhất
            });
        });

        const lat = Math.round(position.coords.latitude * 1000000) / 1000000;
        const lng = Math.round(position.coords.longitude * 1000000) / 1000000;
        const accuracy = Math.round(position.coords.accuracy);

        // Hiển thị xác nhận trước khi lưu
        const oldLat = sn.toado_gps ? sn.toado_gps.lat : "N/A";
        const oldLng = sn.toado_gps ? sn.toado_gps.lng : "N/A";

        const confirmed = confirm(
            `📍 GHIM TOẠ ĐỘ GPS — ${sn.ten_chu_ho}\n` +
            `━━━━━━━━━━━━━━━━━━━━━━━\n` +
            `Số nhà: ${sn.so_nha_moi}\n` +
            `${sn.so_to_thua || ''}\n\n` +
            `🔴 Toạ độ CŨ: ${oldLat}, ${oldLng}\n` +
            `🟢 Toạ độ MỚI: ${lat}, ${lng}\n` +
            `📏 Độ chính xác: ±${accuracy}m\n\n` +
            `Bạn có chắc chắn muốn cập nhật toạ độ?`
        );

        if (!confirmed) {
            showToast("Đã hủy ghim toạ độ.", "info");
            return;
        }

        // Gửi lên server
        const res = await fetch(`${API_BASE}/api/so-nha/${id_nha}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                toado_gps: { lat, lng },
                ghi_chu: (sn.ghi_chu || "") +
                    ` | 📍 GPS ghim ${new Date().toLocaleDateString('vi-VN')} (±${accuracy}m)`
            })
        });

        if (res.ok) {
            showToast(
                `✅ Đã ghim GPS cho ${sn.ten_chu_ho}: ${lat}, ${lng} (±${accuracy}m)`,
                "success"
            );
            await refreshSoNhaData();

            // Tự động ghim vị trí WGS84 vừa đo lên bản đồ GIS
            if (window.pinGPSOnMap) window.pinGPSOnMap(lat, lng, accuracy);
        } else {
            const err = await res.json();
            showToast(`❌ Lỗi lưu GPS: ${err.detail || "Không xác định"}`, "error");
        }

    } catch (geoError) {
        let msg = "Không thể lấy vị trí GPS.";
        if (geoError.code === 1) msg = "Bạn đã từ chối quyền truy cập vị trí. Vui lòng cho phép trong Cài đặt trình duyệt.";
        if (geoError.code === 2) msg = "Không tìm được tín hiệu GPS. Vui lòng ra ngoài trời hoặc bật GPS trên điện thoại.";
        if (geoError.code === 3) msg = "Quá thời gian chờ GPS (15s). Thử lại lần nữa.";
        showToast(`❌ ${msg}`, "error");
    }
}

// Lắng nghe sự kiện submit form chỉnh sửa
document.addEventListener("DOMContentLoaded", () => {
    const editForm = document.getElementById("form-edit-sn");
    if (editForm) {
        editForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            await submitEditSoNha();
        });
    }
});

// Multi-Search Handler
document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("multi-search-input");
    if (!searchInput) return;

    let debounceTimer;
    searchInput.addEventListener("input", (e) => {
        clearTimeout(debounceTimer);
        const query = e.target.value.trim();

        debounceTimer = setTimeout(async () => {
            if (query.length === 0) {
                await refreshSoNhaData();
                return;
            }

            try {
                const res = await fetch(`${API_BASE}/api/so-nha/search?q=${encodeURIComponent(query)}`);
                const results = await res.json();
                AppState.soNhas = results;
                renderSoNhaTable();
                if (window.renderMapMarkers) window.renderMapMarkers();
                showToast(`Tìm thấy ${results.length} kết quả tại Tân Phú, Tây Ninh`, "info");
            } catch (err) {
                console.error("Lỗi tìm kiếm:", err);
            }
        }, 250);
    });

    const toggleVN = document.getElementById("toggle-virtual-nodes");
    if (toggleVN) {
        toggleVN.addEventListener("change", () => {
            if (window.renderMapMarkers) window.renderMapMarkers();
        });
    }

    const toggleUnconverted = document.getElementById("toggle-unconverted-land");
    if (toggleUnconverted) {
        toggleUnconverted.addEventListener("change", () => {
            if (window.renderMapMarkers) window.renderMapMarkers();
        });
    }
});

// Render Address Tree (Cây Hẻm Ngách Xã Tân Phú)
async function renderAddressTree() {
    const container = document.getElementById("address-tree-container");
    if (!container) return;

    container.innerHTML = `
        <div class="flex items-center justify-center p-8 text-slate-400">
            <i class="fa-solid fa-spinner fa-spin mr-2"></i>Đang khởi dựng cấu trúc cây hẻm...
        </div>
    `;

    try {
        const res = await fetch(`${API_BASE}/api/so-nha/tree/${AppState.selectedTuyenDuong}`);
        const treeData = await res.json();

        container.innerHTML = "";
        const routeObj = AppState.tuyenDuongs.find(t => t.id_tuyen === AppState.selectedTuyenDuong);
        const routeName = routeObj ? routeObj.ten_duong : "Tuyến đường";

        const rootCard = document.createElement("div");
        rootCard.className = "p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 mb-4 flex items-center justify-between";
        rootCard.innerHTML = `
            <div class="flex items-center space-x-3">
                <div class="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center font-bold text-lg shadow-md">
                    <i class="fa-solid fa-road"></i>
                </div>
                <div>
                    <h3 class="font-bold text-base text-slate-900">${routeName} (Xã Tân Phú, Tây Ninh)</h3>
                    <p class="text-xs text-slate-500">Cấu trúc cây Path-based routing: Trục chính & Nhánh ngõ hẻm ấp</p>
                </div>
            </div>
            <span class="px-3 py-1 rounded-full text-xs font-semibold bg-blue-600 text-white">Tim đường WGS84</span>
        `;
        container.appendChild(rootCard);

        const children = treeData.children || {};

        // 1. Mặt tiền
        if (children.mat_tien && children.mat_tien.items) {
            const frontCard = document.createElement("div");
            frontCard.className = "mb-4 border border-slate-200/80 rounded-xl p-4 bg-white/60 backdrop-blur-md shadow-sm";
            frontCard.innerHTML = `
                <div class="font-bold text-sm text-slate-800 mb-3 flex items-center">
                    <i class="fa-solid fa-store mr-2 text-blue-600"></i>Nhà Mặt Tiền Tuyến Đường (${children.mat_tien.items.length} vị trí)
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                    ${children.mat_tien.items.map(sn => `
                        <div class="p-2.5 rounded-lg bg-slate-50 hover:bg-blue-50/60 border border-slate-200/60 flex items-center justify-between transition cursor-pointer" onclick="focusOnHouse('${sn.id_nha}')">
                            <div>
                                <span class="font-bold text-xs text-slate-900">${sn.so_nha_moi}</span>
                                <p class="text-[11px] text-slate-500">${sn.ten_chu_ho} ${sn.so_to_thua ? `(${sn.so_to_thua})` : ''}</p>
                            </div>
                            <span class="text-[10px] px-1.5 py-0.5 rounded ${sn.muc_dich_su_dung_dat === 'DAT_O_THO_CU' ? 'bg-blue-100 text-blue-700' : 'bg-rose-100 text-rose-700'} font-medium">
                                ${sn.muc_dich_su_dung_dat === 'DAT_O_THO_CU' ? 'Thổ cư' : 'Chưa chuyển MĐ'}
                            </span>
                        </div>
                    `).join("")}
                </div>
            `;
            container.appendChild(frontCard);
        }

        // 2. Các nhánh hẻm
        Object.keys(children).forEach(key => {
            if (key === "mat_tien") return;
            const alley = children[key];
            const alleyCard = document.createElement("div");
            alleyCard.className = "mb-4 border border-cyan-200/80 rounded-xl p-4 bg-white/70 backdrop-blur-md shadow-sm";

            alleyCard.innerHTML = `
                <div class="font-bold text-sm text-cyan-900 flex items-center justify-between">
                    <span><i class="fa-solid fa-signs-post mr-2 text-cyan-600"></i>${alley.name}</span>
                    <span class="text-xs px-2 py-0.5 rounded-full bg-cyan-100 text-cyan-700 font-medium">${alley.items ? alley.items.length : 0} căn</span>
                </div>
                ${alley.items && alley.items.length > 0 ? `
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 mt-3">
                        ${alley.items.map(sn => `
                            <div class="p-2.5 rounded-lg bg-slate-50 hover:bg-cyan-50/60 border border-slate-200/60 flex items-center justify-between transition cursor-pointer" onclick="focusOnHouse('${sn.id_nha}')">
                                <div>
                                    <span class="font-bold text-xs text-slate-900">${sn.so_nha_moi}</span>
                                    <p class="text-[11px] text-slate-500">${sn.ten_chu_ho}</p>
                                </div>
                                <span class="text-[10px] px-1.5 py-0.5 rounded bg-cyan-100 text-cyan-800 font-medium">Hẻm nội bộ</span>
                            </div>
                        `).join("")}
                    </div>
                ` : ''}
            `;
            container.appendChild(alleyCard);
        });

    } catch (err) {
        console.error("Lỗi dựng cây:", err);
        container.innerHTML = `<p class="p-4 text-rose-500">Lỗi nạp cây phân cấp: ${err.message}</p>`;
    }
}

function focusOnHouse(id_nha) {
    const sn = AppState.soNhas.find(x => x.id_nha === id_nha);
    if (sn && sn.toado_gps) {
        switchTab("map_view");
        if (window.gisMap) {
            window.gisMap.flyTo([sn.toado_gps.lat, sn.toado_gps.lng], 18, { duration: 1.2 });
            if (sn._marker) sn._marker.openPopup();
        }
    }
}

// ====================== GHIM GPS TRONG MODAL CHỈNH SỬA ======================

/**
 * Ghim toạ độ GPS trực tiếp vào form chỉnh sửa (không gửi lên server,
 * chỉ điền vào ô Lat/Lng để user xem rồi bấm Lưu).
 */
async function ghimToaDoInModal() {
    if (!navigator.geolocation) {
        showToast("❌ Trình duyệt không hỗ trợ Geolocation.", "error");
        return;
    }

    showToast("📍 Đang lấy vị trí GPS...", "info");

    try {
        const position = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 0
            });
        });

        const lat = Math.round(position.coords.latitude * 1000000) / 1000000;
        const lng = Math.round(position.coords.longitude * 1000000) / 1000000;
        const accuracy = Math.round(position.coords.accuracy);

        document.getElementById("edit-sn-lat").value = lat;
        document.getElementById("edit-sn-lng").value = lng;

        // Đồng thời thả ghim xanh lên bản đồ để cán bộ đối chiếu vị trí thực
        if (window.pinGPSOnMap) window.pinGPSOnMap(lat, lng, accuracy);

        showToast(`✅ Đã bắt GPS: ${lat}, ${lng} (±${accuracy}m). Nhấn "Lưu Thay Đổi" để cập nhật.`, "success");
    } catch (geoError) {
        let msg = "Không thể lấy vị trí GPS.";
        if (geoError.code === 1) msg = "Bạn đã từ chối quyền truy cập vị trí.";
        if (geoError.code === 2) msg = "Không tìm được tín hiệu GPS.";
        if (geoError.code === 3) msg = "Quá thời gian chờ GPS (15s).";
        showToast(`❌ ${msg}`, "error");
    }
}

// ====================== WINDOW EXPORTS ======================

window.renderSoNhaTable = renderSoNhaTable;
window.renderAddressTree = renderAddressTree;
window.focusOnHouse = focusOnHouse;
window.openEditModal = openEditModal;
window.closeEditModal = closeEditModal;
window.submitEditSoNha = submitEditSoNha;
window.ghimToaDoGPS = ghimToaDoGPS;
window.ghimToaDoInModal = ghimToaDoInModal;
