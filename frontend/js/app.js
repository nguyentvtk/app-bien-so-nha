/**
 * Core Application Controller (app.js)
 * Địa bàn: XÃ TÂN PHÚ, TỈNH TÂY NINH - Cơ quan: ỦY BAN NHÂN DÂN XÃ TÂN PHÚ.
 * Quản lý trạng thái, đồng bộ Google Sheets tuyến đường, công cụ Điều tra viên thực địa (GPS Ghim 1 chạm)
 */

const API_BASE = ""; // Relative to host

const AppState = {
    currentTab: "map_view",
    tuyenDuongs: [],
    selectedTuyenDuong: "TD_DT785",
    soNhas: [],
    virtualNodes: [],
    hoSos: [],
    thongKeDatDai: null,
    systemStatus: null
};

// Toast Notification
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    const colors = {
        success: "bg-emerald-600 text-white border-emerald-400/40 shadow-emerald-500/20",
        error: "bg-rose-600 text-white border-rose-400/40 shadow-rose-500/20",
        warning: "bg-amber-600 text-white border-amber-400/40 shadow-amber-500/20",
        info: "bg-blue-600 text-white border-blue-400/40 shadow-blue-500/20"
    };

    const icons = {
        success: '<i class="fa-solid fa-circle-check mr-2"></i>',
        error: '<i class="fa-solid fa-triangle-exclamation mr-2"></i>',
        warning: '<i class="fa-solid fa-circle-exclamation mr-2"></i>',
        info: '<i class="fa-solid fa-circle-info mr-2"></i>'
    };

    toast.className = `flex items-center px-4 py-3 rounded-xl shadow-xl backdrop-blur-md border text-xs font-semibold transition-all duration-300 transform translate-y-2 opacity-0 ${colors[type] || colors.info}`;
    toast.innerHTML = `${icons[type] || icons.info}<span>${message}</span>`;

    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.remove("translate-y-2", "opacity-0");
    }, 10);

    setTimeout(() => {
        toast.classList.add("opacity-0", "translate-y-2");
        setTimeout(() => toast.remove(), 300);
    }, 4500);
}

// Khởi chạy ứng dụng
document.addEventListener("DOMContentLoaded", async () => {
    setupNavigation();
    await loadInitialData();
    setupModals();
    setupSurveyorTool();
    setupSyncSheetsModal();
    dangKyServiceWorker();
    moLoiNhoTuHash();
});

// ─── PWA: đăng ký Service Worker để cài app & chạy offline lớp vẽ ───
// Chỉ đăng ký trên HTTPS (Vercel) hoặc localhost — mạng LAN http thuần
// không phải secure context nên trình duyệt sẽ tự chặn, ta chủ động bỏ qua.
function dangKyServiceWorker() {
    if (!("serviceWorker" in navigator)) return;
    const laLocalhost = ["localhost", "127.0.0.1"].includes(location.hostname);
    if (location.protocol !== "https:" && !laLocalhost) return;
    navigator.serviceWorker.register("/sw.js")
        .then(() => console.log("[PWA] Service Worker đã sẵn sàng — có thể 'Thêm vào màn hình chính'."))
        .catch((loi) => console.warn("[PWA] Không đăng ký được Service Worker:", loi));
}

// ─── Mở đúng tính năng khi khởi động từ lối tắt trên màn hình chính ───
// (#dieu-tra → tab Điều tra viên, #tra-cuu → ô tìm kiếm)
function moLoiNhoTuHash() {
    const hash = location.hash;
    if (hash === "#dieu-tra") {
        switchTab("surveyor_view");
    } else if (hash === "#tra-cuu") {
        switchTab("map_view");
        setTimeout(() => document.getElementById("multi-search-input")?.focus(), 300);
    }
}
// Lối tắt PWA mở trang mới (DOMContentLoaded) hoặc đổi hash khi đang mở (hashchange)
window.addEventListener("hashchange", moLoiNhoTuHash);

// Chuyển Tab
function setupNavigation() {
    const tabs = ["map_view", "surveyor_view", "land_stats_view", "tree_view", "dossier_view", "ai_monitor_view"];
    tabs.forEach(tabId => {
        // Gắn cả nút điều hướng trên Header (desktop) lẫn Bottom Nav (điện thoại)
        [`nav-btn-${tabId}`, `bottom-nav-btn-${tabId}`].forEach(btnId => {
            const btn = document.getElementById(btnId);
            if (!btn) return;
            btn.addEventListener("click", () => {
                switchTab(tabId);
            });
        });
    });

    // Nút "Xem vị trí vừa ghim trên bản đồ" (xuất hiện sau khi GPS lấy toạ độ)
    const btnViewOnMap = document.getElementById("btn-view-gps-on-map");
    if (btnViewOnMap) {
        btnViewOnMap.addEventListener("click", () => {
            switchTab("map_view");
            const lat = parseFloat(document.getElementById("surveyor-lat").value);
            const lng = parseFloat(document.getElementById("surveyor-lng").value);
            if (window.gisMap && lat && lng) {
                window.gisMap.flyTo([lat, lng], 18, { duration: 1.2 });
                if (window.focusGpsPin) window.focusGpsPin();
            }
        });
    }
}

function switchTab(tabId) {
    AppState.currentTab = tabId;
    const views = document.querySelectorAll(".tab-view-content");
    views.forEach(v => v.classList.add("hidden"));

    const activeView = document.getElementById(`view-${tabId}`);
    if (activeView) activeView.classList.remove("hidden");

    // Đổi style button điều hướng trên Header (desktop)
    document.querySelectorAll(".nav-tab-btn").forEach(b => {
        b.classList.remove("bg-blue-600/15", "text-blue-600", "font-semibold", "border-blue-500/30");
        b.classList.add("text-slate-600", "hover:bg-slate-100/50");
    });
    const currentBtn = document.getElementById(`nav-btn-${tabId}`);
    if (currentBtn) {
        currentBtn.classList.add("bg-blue-600/15", "text-blue-600", "font-semibold", "border-blue-500/30");
        currentBtn.classList.remove("text-slate-600");
    }

    // Đổi trạng thái active Bottom Navigation (điện thoại)
    document.querySelectorAll(".bottom-nav-item").forEach(b => {
        b.classList.remove("bottom-nav-active");
    });
    const bottomBtn = document.getElementById(`bottom-nav-btn-${tabId}`);
    if (bottomBtn) bottomBtn.classList.add("bottom-nav-active");

    // Trên điện thoại: cuộn lên đầu nội dung khi đổi tab
    if (window.matchMedia("(max-width: 1023px)").matches) {
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    if (tabId === "map_view") {
        setTimeout(() => {
            if (window.gisMap) window.gisMap.invalidateSize();
            // Nếu GPS vừa ghim khi bản đồ còn ẩn → bay tới vị trí đó ngay bây giờ
            if (window.consumePendingGpsFlyTo) window.consumePendingGpsFlyTo();
        }, 100);
    } else if (tabId === "land_stats_view") {
        renderLandStats();
    } else if (tabId === "tree_view") {
        renderAddressTree();
    } else if (tabId === "dossier_view") {
        renderDossierList();
    } else if (tabId === "ai_monitor_view") {
        renderAIMonitor();
    }
}

// Tải dữ liệu ban đầu
async function loadInitialData() {
    try {
        // 1. Tuyến đường
        const tuyenRes = await fetch(`${API_BASE}/api/tuyen-duong`);
        AppState.tuyenDuongs = await tuyenRes.json();
        populateRouteSelectors();

        // 2. Số nhà
        await refreshSoNhaData();

        // 3. Hồ sơ
        const hsRes = await fetch(`${API_BASE}/api/ho-so`);
        AppState.hoSos = await hsRes.json();

        // 4. Thống kê đất đai
        const tkRes = await fetch(`${API_BASE}/api/thong-ke/dat-dai`);
        AppState.thongKeDatDai = await tkRes.json();
        updateStatsCards();

        // 5. Khởi tạo bản đồ GIS
        initLeafletMap();

    } catch (err) {
        console.error("Lỗi tải dữ liệu ban đầu:", err);
        showToast("Không thể nạp dữ liệu ban đầu từ máy chủ!", "error");
    }
}

async function refreshSoNhaData() {
    const snRes = await fetch(`${API_BASE}/api/so-nha?id_tuyen=${AppState.selectedTuyenDuong}`);
    AppState.soNhas = await snRes.json();

    const vnRes = await fetch(`${API_BASE}/api/so-nha/virtual-nodes/${AppState.selectedTuyenDuong}`);
    const vnData = await vnRes.json();
    AppState.virtualNodes = vnData.virtual_nodes || [];

    renderSoNhaTable();
    if (window.renderMapMarkers) {
        window.renderMapMarkers();
    }
}

function populateRouteSelectors() {
    const selectors = [
        document.getElementById("filter-route-select"),
        document.getElementById("modal-sn-route"),
        document.getElementById("surveyor-route-select"),
        document.getElementById("tree-route-select")
    ];

    selectors.forEach(sel => {
        if (!sel) return;
        sel.innerHTML = "";
        AppState.tuyenDuongs.forEach(td => {
            const opt = document.createElement("option");
            opt.value = td.id_tuyen;
            opt.textContent = `${td.ten_duong} (${td.phan_loai})`;
            if (td.id_tuyen === AppState.selectedTuyenDuong) opt.selected = true;
            sel.appendChild(opt);
        });
    });

    const mainFilter = document.getElementById("filter-route-select");
    if (mainFilter) {
        mainFilter.addEventListener("change", async (e) => {
            AppState.selectedTuyenDuong = e.target.value;
            await refreshSoNhaData();
            if (AppState.currentTab === "tree_view") renderAddressTree();
        });
    }
}

function updateStatsCards() {
    const tk = AppState.thongKeDatDai;
    if (!tk) return;

    const elEligible = document.getElementById("stat-card-eligible");
    const elIneligible = document.getElementById("stat-card-ineligible");
    const elReserve = document.getElementById("stat-card-reserve");

    if (elEligible) elEligible.textContent = `${tk.da_cap_so} căn`;
    if (elIneligible) elIneligible.textContent = `${tk.nha_chua_du_dieu_kien} thửa`;
    if (elReserve) elReserve.textContent = `${tk.dat_tho_cu_chua_xay_du_tru} lô`;
}

function renderLandStats() {
    updateStatsCards();
    const tbody = document.getElementById("table-routes-stat-body");
    if (!tbody) return;

    tbody.innerHTML = AppState.tuyenDuongs.map(td => `
        <tr class="border-b border-slate-100 hover:bg-slate-50 transition">
            <td data-label="Mã tuyến" class="px-4 py-2.5 font-mono font-bold text-blue-700">${td.id_tuyen}</td>
            <td data-label="Tên tuyến" class="px-4 py-2.5 font-bold text-slate-900">${td.ten_duong}</td>
            <td data-label="Phân loại" class="px-4 py-2.5 text-slate-600">${td.phan_loai}</td>
            <td data-label="Chiều dài" class="px-4 py-2.5 font-mono text-slate-700">${td.chieu_dai_m}m</td>
            <td data-label="Tổng số nhà" class="px-4 py-2.5 font-semibold text-emerald-700">${td.tong_so_nha} số</td>
            <td data-label="WGS84" class="px-4 py-2.5 font-mono text-[11px] text-slate-500">${td.toado_batdau.lat}, ${td.toado_batdau.lng}</td>
            <td data-label="Thao tác" class="px-4 py-2.5 text-center whitespace-nowrap">
                <button onclick="openCalibrateModal('${td.id_tuyen}')" class="px-2.5 py-1.5 rounded-lg text-[11px] font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition" title="Hiệu chỉnh toạ độ 2 điểm chuẩn cho tuyến này — toàn xã tự cập nhật theo">
                    <i class="fa-solid fa-crosshairs mr-1"></i>Hiệu chỉnh toạ độ
                </button>
            </td>
        </tr>
    `).join("");
}

// CÔNG CỤ ĐIỀU TRA VIÊN (MOBILE SURVEY TOOL)
function setupSurveyorTool() {
    const btnCaptureGPS = document.getElementById("btn-surveyor-capture-gps");
    const latInput = document.getElementById("surveyor-lat");
    const lngInput = document.getElementById("surveyor-lng");
    const displayGPS = document.getElementById("surveyor-gps-display");
    const landPurpose = document.getElementById("surveyor-land-purpose");
    const warningBox = document.getElementById("surveyor-legal-warning");
    const form = document.getElementById("form-surveyor-quick");

    // Lắng nghe thay đổi mục đích sử dụng đất để cảnh báo
    if (landPurpose && warningBox) {
        landPurpose.addEventListener("change", (e) => {
            if (e.target.value === "DAT_CHUA_CHUYEN_MUC_DICH" || e.target.value === "DAT_NONG_NGHIEP") {
                warningBox.classList.remove("hidden");
            } else {
                warningBox.classList.add("hidden");
            }
        });
    }

    // Nút "📍 Lấy Vị Trí Hiện Tại" — Geolocation API: bắt GPS thiết bị,
    // điền toạ độ WGS84 vào form VÀ tự động ghim lên bản đồ GIS.
    if (btnCaptureGPS) {
        btnCaptureGPS.addEventListener("click", () => {
            showToast("Đang kết nối chip định vị GPS của thiết bị...", "info");

            if ("geolocation" in navigator) {
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        const lat = position.coords.latitude.toFixed(5);
                        const lng = position.coords.longitude.toFixed(5);
                        const accuracy = Math.round(position.coords.accuracy);

                        latInput.value = lat;
                        lngInput.value = lng;
                        displayGPS.innerHTML = `
                            <span class="text-emerald-700 font-bold">
                                <i class="fa-solid fa-circle-check text-emerald-600 mr-1"></i>
                                Toạ độ WGS84: ${lat}, ${lng} (Độ chính xác: ±${accuracy}m)
                            </span>
                        `;

                        // ⭐ TỰ ĐỘNG GHIM LÊN BẢN ĐỒ GIS (vòng chính xác + ghim xanh nhịp)
                        if (window.pinGPSOnMap) {
                            window.pinGPSOnMap(parseFloat(lat), parseFloat(lng), accuracy);
                        }

                        // Hiện nút "Xem vị trí vừa ghim trên bản đồ" cho điện thoại
                        const btnViewMap = document.getElementById("btn-view-gps-on-map");
                        if (btnViewMap) btnViewMap.classList.remove("hidden");

                        showToast(`Đã ghim toạ độ WGS84 lên bản đồ: ${lat}, ${lng}`, "success");
                    },
                    (error) => {
                        console.warn("Lỗi GPS:", error.message);
                        let msg = "Không lấy được vị trí GPS.";
                        if (error.code === 1) msg = "Bạn đã từ chối quyền truy cập vị trí. Vui lòng cho phép trong Cài đặt trình duyệt.";
                        if (error.code === 2) msg = "Không tìm được tín hiệu GPS. Hãy ra ngoài trời hoặc bật định vị trên điện thoại.";
                        if (error.code === 3) msg = "Quá thời gian chờ GPS. Vui lòng bấm lại nút.";
                        displayGPS.innerHTML = `<span class="text-rose-600 font-bold">${msg}</span>`;
                        showToast(msg, "error");
                    },
                    { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
                );
            } else {
                showToast("Thiết bị không hỗ trợ Geolocation", "warning");
            }
        });
    }

    // Submit form khảo sát
    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();

            const surveyorName = document.getElementById("surveyor-name").value.trim();
            const route = document.getElementById("surveyor-route-select").value;
            const owner = document.getElementById("surveyor-owner").value.trim();
            const cccd = document.getElementById("surveyor-cccd").value.trim();
            const phone = document.getElementById("surveyor-phone").value.trim();
            const purpose = document.getElementById("surveyor-land-purpose").value;
            const buildStatus = document.getElementById("surveyor-build-status").value;
            const toThua = document.getElementById("surveyor-to-thua").value.trim();
            const width = parseFloat(document.getElementById("surveyor-width").value) || 5.0;
            const desc = document.getElementById("surveyor-desc").value.trim();
            const lat = parseFloat(latInput.value) || 11.6050;
            const lng = parseFloat(lngInput.value) || 106.1850;

            const payload = {
                id_yeu_cau: `KS_${Date.now().toString().slice(-6)}`,
                ho_ten_nguoi_nop: owner,
                cccd: cccd || "---",
                sdt: phone || "---",
                email: "",
                dia_chi_khao_sat: desc || `Khảo sát tại ${route}`,
                id_tuyen_duong: route,
                muc_dich_su_dung_dat: purpose,
                hien_trang_xay_dung: buildStatus,
                so_to_thua: toThua,
                khoang_cach_mat_tien: width,
                toado_gps: { lat, lng },
                hinh_anh_khao_sat: ["https://images.unsplash.com/photo-1513694203232-719a280e022f?w=600"],
                giay_to_phap_ly: [],
                loai_yeu_cau: "KHAO_SAT_THUC_DIA",
                trang_thai: "CHO_TIEP_NHAN",
                dieu_tra_vien: surveyorName,
                so_nha_de_xuat: (document.getElementById("surveyor-sn-dexuat")?.value || "").trim() || null
            };

            try {
                showToast("Đang lưu khảo sát thực địa & Kiểm tra quy định qua Jev...", "info");
                const res = await fetch(`${API_BASE}/api/dieu-tra-vien/khao-sat-nhanh`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();

                if (data.score < 0.70) {
                    showToast(`Đã lưu khảo sát! CẢNH BÁO: ${data.ai_feedback}`, "warning");
                } else {
                    showToast(`Thành công! ${data.message}`, "success");
                }

                form.reset();
                displayGPS.innerHTML = `Toạ độ: Chưa ghim (Bấm nút "Lấy Vị Trí Hiện Tại" để bắt vị trí)`;
                const btnViewMap = document.getElementById("btn-view-gps-on-map");
                if (btnViewMap) btnViewMap.classList.add("hidden");

                // Nạp lại dữ liệu
                await loadInitialData();
            } catch (err) {
                showToast("Lỗi gửi khảo sát: " + err.message, "error");
            }
        });
    }
}

// MODAL ĐỒNG BỘ GOOGLE SHEETS
function setupSyncSheetsModal() {
    const btnOpen = document.getElementById("btn-open-sync-sheets");
    const modal = document.getElementById("modal-sync-sheets");
    const btnClose = document.getElementById("btn-close-sync-sheets");
    const btnCancel = document.getElementById("btn-cancel-sync");
    const btnOnlineSync = document.getElementById("btn-trigger-online-sync");
    const btnSubmitCsv = document.getElementById("btn-submit-csv-sync");
    const csvInput = document.getElementById("sync-csv-input");

    if (btnOpen && modal) {
        btnOpen.addEventListener("click", () => {
            modal.classList.remove("hidden");
            modal.classList.add("flex");
        });
    }

    const closeModal = () => {
        if (modal) {
            modal.classList.add("hidden");
            modal.classList.remove("flex");
        }
    };

    const btnClearMock = document.getElementById("btn-clear-mock-data");
    if (btnClearMock) {
        btnClearMock.addEventListener("click", async () => {
            if (!confirm("Bạn có chắc chắn muốn xóa toàn bộ số nhà và hồ sơ mẫu để hệ thống sạch sẽ cho dữ liệu thực địa? (Danh mục tuyến đường thực tế sẽ được bảo lưu)")) {
                return;
            }
            try {
                showToast("Đang dọn sạch dữ liệu mẫu...", "info");
                const res = await fetch(`${API_BASE}/api/system/clear-mock-data`, { method: "POST" });
                const data = await res.json();
                if (data.success) {
                    showToast(data.message, "success");
                    await loadInitialData();
                } else {
                    showToast("Lỗi khi xóa: " + (data.message || "Không xác định"), "error");
                }
            } catch (err) {
                showToast("Lỗi kết nối máy chủ: " + err.message, "error");
            }
        });
    }

    if (btnClose) btnClose.addEventListener("click", closeModal);
    if (btnCancel) btnCancel.addEventListener("click", closeModal);

    // Đồng bộ online
    if (btnOnlineSync) {
        btnOnlineSync.addEventListener("click", async () => {
            try {
                showToast("Đang kết nối Google Sheets xã Tân Phú...", "info");
                const res = await fetch(`${API_BASE}/api/tuyen-duong/sync-google-sheets`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({})
                });
                const data = await res.json();

                if (data.success) {
                    showToast(data.message, "success");
                    closeModal();
                    await loadInitialData();
                } else {
                    showToast(data.message, "warning");
                }
            } catch (err) {
                showToast("Lỗi đồng bộ: " + err.message, "error");
            }
        });
    }

    // Nhập dữ liệu CSV
    if (btnSubmitCsv && csvInput) {
        btnSubmitCsv.addEventListener("click", async () => {
            const csvText = csvInput.value.trim();
            if (!csvText) {
                showToast("Vui lòng dán nội dung CSV từ Google Sheets", "warning");
                return;
            }

            try {
                showToast("Đang phân tích và nhập dữ liệu tuyến đường WGS84...", "info");
                const res = await fetch(`${API_BASE}/api/tuyen-duong/sync-google-sheets`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ csv_data: csvText })
                });
                const data = await res.json();
                if (data.success) {
                    showToast(data.message, "success");
                    csvInput.value = "";
                    closeModal();
                    await loadInitialData();
                } else {
                    showToast(data.message, "error");
                }
            } catch (err) {
                showToast("Lỗi nhập CSV: " + err.message, "error");
            }
        });
    }
}

// MODAL CẤP SỐ NHÀ MỚI
function setupModals() {
    const btnOpen = document.getElementById("btn-open-create-sn");
    const modal = document.getElementById("modal-create-sn");
    const btnClose = document.getElementById("btn-close-create-sn");
    const form = document.getElementById("form-create-sn");

    if (btnOpen && modal) {
        btnOpen.addEventListener("click", () => {
            modal.classList.remove("hidden");
            modal.classList.add("flex");
        });
    }

    if (btnClose && modal) {
        btnClose.addEventListener("click", () => {
            modal.classList.add("hidden");
            modal.classList.remove("flex");
        });
    }

    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            await submitCreateSoNha();
        });
    }
}

async function submitCreateSoNha() {
    const soNhaMoi = document.getElementById("modal-sn-new").value.trim();
    const soNhaCu = document.getElementById("modal-sn-old").value.trim() || null;
    const tenChuHo = document.getElementById("modal-sn-owner").value.trim();
    const cccd = document.getElementById("modal-sn-cccd").value.trim();
    const purpose = document.getElementById("modal-sn-land-purpose").value;
    const buildStatus = document.getElementById("modal-sn-build-status").value;
    const idTuyen = document.getElementById("modal-sn-route").value;
    const toThua = document.getElementById("modal-sn-to-thua").value.trim();
    const matTien = parseFloat(document.getElementById("modal-sn-width").value) || 5.0;
    const lat = parseFloat(document.getElementById("modal-sn-lat").value) || 11.6050;
    const lng = parseFloat(document.getElementById("modal-sn-lng").value) || 106.1850;

    const payload = {
        id_nha: `SN_TP_${Date.now().toString().slice(-5)}`,
        so_nha_moi: soNhaMoi,
        so_nha_cu: soNhaCu,
        ten_chu_ho: tenChuHo,
        cccd: cccd,
        sdt: "",
        toado_gps: { lat, lng },
        trang_thai: (buildStatus === "DAT_TRONG") ? "DAT_THO_CU_CHUA_XAY" : "HIEN_HUU",
        muc_dich_su_dung_dat: purpose,
        hien_trang_xay_dung: buildStatus,
        so_to_thua: toThua,
        id_tuyen_duong: idTuyen,
        id_hem_ngach: null,
        loai_nha: "Nhà ở riêng lẻ",
        dien_tich_mat_tien: matTien,
        ghi_chu: "UBND Xã Tân Phú cấp",
        che_do_danh_so: (typeof docCheDoDanhSo === "function") ? docCheDoDanhSo("sn-che-do") : null
    };

    try {
        showToast("Đang kiểm tra pháp lý đất đai và Jev Score...", "info");
        const res = await fetch(`${API_BASE}/api/so-nha/cap-so`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) {
            const detail = data.detail || {};
            showToast(`Lỗi thẩm định: ${detail.message || "Bị chặn bởi quy định pháp lý"}`, "error");
            return;
        }

        showToast(`Thành công! ${data.message}`, "success");
        document.getElementById("modal-create-sn").classList.add("hidden");
        document.getElementById("modal-create-sn").classList.remove("flex");
        document.getElementById("form-create-sn").reset();

        await loadInitialData();

        if (data.certificate_url) {
            window.open(data.certificate_url, "_blank");
        }
    } catch (err) {
        showToast(`Lỗi hệ thống: ${err.message}`, "error");
    }
}
