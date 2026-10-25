/**
 * GIS Map Controller (map_gis.js)
 * Địa bàn: XÃ TÂN PHÚ, TỈNH TÂY NINH (WGS84: 11.6050°N, 106.1850°E)
 * Tích hợp Google Maps Vệ Tinh (Satellite Hybrid) & Google Maps Đường bộ.
 * Phân loại màu:
 *   - Xanh dương: Nhà đủ điều kiện đã cấp số
 *   - Đỏ: Nhà xây trên đất chưa chuyển đổi mục đích (Chưa đủ điều kiện cấp số)
 *   - Vàng viền đứt nét: Đất thổ cư chưa xây dựng (Virtual Node dự trữ)
 * Hỗ trợ Điều tra viên: Chạm bản đồ để lấy toạ độ WGS84 tức thì.
 */

let gisMap = null;
let markersLayer = null;
let routeLineLayer = null;
let tempSurveyMarker = null;
let gpsPinMarker = null;      // Ghim "Vị trí hiện tại" từ Geolocation API
let gpsAccuracyCircle = null; // Vòng tròn độ chính xác quanh ghim GPS

function initLeafletMap() {
    const mapElement = document.getElementById("gis-map");
    if (!mapElement) return;

    // Toạ độ trung tâm Xã Tân Phú, Tỉnh Tây Ninh: 11.6050, 106.1850
    gisMap = L.map("gis-map", {
        zoomControl: false
    }).setView([11.6050, 106.1850], 15);

    window.gisMap = gisMap;

    L.control.zoom({ position: "topright" }).addTo(gisMap);

    // 1. Google Maps Vệ Tinh (Satellite Hybrid kèm nhãn đường)
    const googleHybrid = L.tileLayer("https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", {
        attribution: '&copy; Google Maps | UBND Xã Tân Phú, Tây Ninh',
        maxZoom: 20
    });

    // 2. Google Maps Đường Bộ (Roadmap)
    const googleRoadmap = L.tileLayer("https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", {
        attribution: '&copy; Google Maps | UBND Xã Tân Phú, Tây Ninh',
        maxZoom: 20
    });

    // 3. CartoDB Positron
    const cartoDB = L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
        attribution: '&copy; CARTO | UBND Xã Tân Phú',
        maxZoom: 19
    });

    // Mặc định nạp Google Maps Roadmap
    googleRoadmap.addTo(gisMap);

    // Bộ chọn lớp bản đồ nền
    const baseMaps = {
        "Google Vệ Tinh (Hybrid)": googleHybrid,
        "Google Đường Bộ": googleRoadmap,
        "Bản Đồ Nền Sáng": cartoDB
    };
    L.control.layers(baseMaps, null, { position: "topright" }).addTo(gisMap);

    markersLayer = L.layerGroup().addTo(gisMap);
    routeLineLayer = L.layerGroup().addTo(gisMap);

    // Tự co lại đúng kích thước khi xoay màn hình / đổi kích thước (mobile)
    window.addEventListener("resize", () => {
        if (gisMap) setTimeout(() => gisMap.invalidateSize(), 150);
    });

    // Sự kiện Chạm bản đồ để lấy toạ độ cho Điều tra viên
    gisMap.on("click", (e) => {
        const lat = e.latlng.lat.toFixed(5);
        const lng = e.latlng.lng.toFixed(5);

        // Hiển thị marker ghim tạm thời
        if (tempSurveyMarker) gisMap.removeLayer(tempSurveyMarker);

        const tempIcon = L.divIcon({
            html: `
                <div class="flex items-center justify-center">
                    <div class="w-8 h-8 rounded-full bg-rose-600 text-white flex items-center justify-center font-bold shadow-lg border-2 border-white animate-bounce">
                        <i class="fa-solid fa-crosshairs text-sm"></i>
                    </div>
                </div>
            `,
            className: "temp-survey-marker",
            iconSize: [32, 32],
            iconAnchor: [16, 32]
        });

        tempSurveyMarker = L.marker([lat, lng], { icon: tempIcon }).addTo(gisMap);
        tempSurveyMarker.bindPopup(`
            <div class="p-2 text-xs font-sans">
                <span class="font-bold text-rose-600 block mb-1">📍 Toạ độ vừa ghim (WGS84):</span>
                <p class="font-mono text-slate-800 bg-slate-100 p-1.5 rounded mb-2">Lat: ${lat}<br/>Lng: ${lng}</p>
                <div class="flex space-x-1">
                    <button onclick="applyCoordsToSurveyor(${lat}, ${lng})" class="px-2 py-1 bg-rose-600 text-white rounded text-[11px] font-semibold hover:bg-rose-700">
                        Áp vào Khảo sát
                    </button>
                    <button onclick="applyCoordsToModal(${lat}, ${lng})" class="px-2 py-1 bg-blue-600 text-white rounded text-[11px] font-semibold hover:bg-blue-700">
                        Áp vào Cấp số
                    </button>
                </div>
            </div>
        `, { className: "glass-popup" }).openPopup();

        // Tự động điền nếu đang mở form
        const surveyorLat = document.getElementById("surveyor-lat");
        const surveyorLng = document.getElementById("surveyor-lng");
        const surveyorDisplay = document.getElementById("surveyor-gps-display");
        if (surveyorLat && surveyorLng && surveyorDisplay) {
            surveyorLat.value = lat;
            surveyorLng.value = lng;
            surveyorDisplay.innerHTML = `<span class="text-rose-600">📍 Toạ độ ghim bản đồ: ${lat}, ${lng}</span>`;
        }
    });

    renderMapMarkers();
}

function applyCoordsToSurveyor(lat, lng) {
    document.getElementById("surveyor-lat").value = lat;
    document.getElementById("surveyor-lng").value = lng;
    document.getElementById("surveyor-gps-display").innerHTML = `<span class="text-rose-600">📍 Toạ độ đã ghim: ${lat}, ${lng}</span>`;
    switchTab("surveyor_view");
    showToast(`Đã lấy toạ độ WGS84: ${lat}, ${lng}`, "success");
}

/**
 * ⭐ TỰ ĐỘNG GHIM VỊ TRÍ GPS LÊN BẢN ĐỒ (Geolocation API → GIS)
 * Được gọi khi Điều tra viên bấm nút "Lấy Vị Trí Hiện Tại":
 *  - Thả ghim xanh nhấp nháy + vòng tròn độ chính xác (±m) tại toạ độ WGS84 thật
 *  - Bản đồ tự bay (flyTo) về vị trí vừa ghim
 *  - Ghim cũ (nếu có) tự xoá, luôn chỉ còn 1 ghim GPS hiện hành
 * Chịu lỗi an toàn: nếu bản đồ đang ẩn (kích thước 0 vì ở tab khác),
 * việc flyTo sẽ được trì hoãn đến khi người dùng mở lại tab Bản đồ.
 */
let pendingGpsFlyTo = null; // [lat, lng] chờ flyTo khi bản đồ hiển thị lại

function pinGPSOnMap(lat, lng, accuracy = null) {
    if (!gisMap) return false;

    // Dọn ghim cũ
    if (gpsPinMarker) { gisMap.removeLayer(gpsPinMarker); gpsPinMarker = null; }
    if (gpsAccuracyCircle) { gisMap.removeLayer(gpsAccuracyCircle); gpsAccuracyCircle = null; }

    const pinIcon = L.divIcon({
        html: `
            <div class="flex items-center justify-center">
                <div class="gps-pin-pulse w-9 h-9 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold shadow-xl border-[3px] border-white">
                    <i class="fa-solid fa-location-crosshairs text-sm"></i>
                </div>
            </div>
        `,
        className: "gps-current-pin",
        iconSize: [36, 36],
        iconAnchor: [18, 18]
    });

    gpsPinMarker = L.marker([lat, lng], { icon: pinIcon, zIndexOffset: 1000 }).addTo(gisMap);

    // Vòng tròn thể hiện độ chính xác thiết bị (bán kính mét)
    if (accuracy && accuracy > 0 && accuracy <= 500) {
        gpsAccuracyCircle = L.circle([lat, lng], {
            radius: accuracy,
            color: "#2563eb",
            fillColor: "#3b82f6",
            fillOpacity: 0.12,
            weight: 1.5,
            dashArray: "4, 4"
        }).addTo(gisMap);
    }

    const accText = accuracy ? ` (±${Math.round(accuracy)}m)` : "";
    gpsPinMarker.bindPopup(`
        <div class="p-2 text-xs font-sans min-w-[190px]">
            <span class="font-bold text-blue-700 block mb-1">📍 Vị trí hiện tại của bạn (WGS84)</span>
            <p class="font-mono text-slate-800 bg-slate-100 p-1.5 rounded mb-2">Lat: ${lat}<br/>Lng: ${lng}${accText}</p>
            <div class="flex flex-wrap gap-1">
                <button onclick="applyCoordsToSurveyor(${lat}, ${lng})" class="px-2 py-1 bg-blue-600 text-white rounded text-[11px] font-semibold hover:bg-blue-700">
                    Áp vào Khảo sát
                </button>
                <button onclick="applyCoordsToModal(${lat}, ${lng})" class="px-2 py-1 bg-indigo-600 text-white rounded text-[11px] font-semibold hover:bg-indigo-700">
                    Áp vào Cấp số
                </button>
                <button onclick="navigator.clipboard && navigator.clipboard.writeText('${lat}, ${lng}'); showToast('Đã sao chép toạ độ ${lat}, ${lng}', 'success');" class="px-2 py-1 bg-slate-600 text-white rounded text-[11px] font-semibold hover:bg-slate-700">
                    📋 Sao chép
                </button>
            </div>
        </div>
    `, { className: "glass-popup" });

    // Fly tới vị trí vừa ghim — chỉ khi bản đồ đang hiển thị (kích thước > 0),
    // nếu đang ẩn thì trì hoãn để tránh lỗi chiếu toạ độ NaN trên bản đồ 0px.
    const kichThuoc = gisMap.getSize();
    if (kichThuoc.x > 0 && kichThuoc.y > 0) {
        gisMap.flyTo([lat, lng], 17, { duration: 1.2 });
        if (AppState.currentTab === "map_view") {
            setTimeout(() => { if (gpsPinMarker) gpsPinMarker.openPopup(); }, 1300);
        }
    } else {
        pendingGpsFlyTo = [lat, lng];
    }
    return true;
}

/** Mở popup của ghim GPS hiện hành (dùng khi quay lại tab bản đồ từ form) */
function focusGpsPin() {
    if (gpsPinMarker) {
        gpsPinMarker.openPopup();
    }
}

/**
 * Thực hiện flyTo đang chờ (nếu có) ngay sau khi tab Bản đồ được mở.
 * Được switchTab("map_view") gọi sau invalidateSize.
 */
function consumePendingGpsFlyTo() {
    if (pendingGpsFlyTo && gisMap) {
        const [lat, lng] = pendingGpsFlyTo;
        pendingGpsFlyTo = null;
        gisMap.flyTo([lat, lng], 17, { duration: 1.2 });
        if (gpsPinMarker) {
            setTimeout(() => gpsPinMarker.openPopup(), 1300);
        }
    }
}

function applyCoordsToModal(lat, lng) {
    document.getElementById("modal-sn-lat").value = lat;
    document.getElementById("modal-sn-lng").value = lng;
    document.getElementById("modal-create-sn").classList.remove("hidden");
    document.getElementById("modal-create-sn").classList.add("flex");
    showToast(`Đã chuyển toạ độ WGS84 ${lat}, ${lng} vào form cấp số`, "info");
}

function renderMapMarkers() {
    if (!gisMap || !markersLayer) return;

    markersLayer.clearLayers();
    routeLineLayer.clearLayers();

    // 1. Vẽ Tim Tuyến Đường Hiện Tại tại Tân Phú, Tây Ninh
    const currentRoute = AppState.tuyenDuongs.find(t => t.id_tuyen === AppState.selectedTuyenDuong);
    if (currentRoute) {
        const start = [currentRoute.toado_batdau.lat, currentRoute.toado_batdau.lng];
        const end = [currentRoute.toado_kethuc.lat, currentRoute.toado_kethuc.lng];

        const line = L.polyline([start, end], {
            color: "#2563eb",
            weight: 6,
            opacity: 0.75,
            dashArray: "8, 6"
        }).addTo(routeLineLayer);

        line.bindTooltip(`<b>${currentRoute.ten_duong}</b><br/>${currentRoute.phan_loai}<br/>Dài: ${currentRoute.chieu_dai_m}m | Lộ giới: ${currentRoute.lo_gioi_m}m`, { permanent: false });
    }

    const showUnconverted = document.getElementById("toggle-unconverted-land")?.checked ?? true;
    const showVirtual = document.getElementById("toggle-virtual-nodes")?.checked ?? true;

    // 2. Vẽ các số nhà & thửa đất
    AppState.soNhas.forEach(sn => {
        const lat = sn.toado_gps.lat;
        const lng = sn.toado_gps.lng;

        // Phân loại:
        const isIneligible = (sn.trang_thai === "NHA_CHUA_DU_DIEU_KIEN" || sn.muc_dich_su_dung_dat === "DAT_CHUA_CHUYEN_MUC_DICH");
        const isVirtual = (sn.trang_thai === "DAT_THO_CU_CHUA_XAY" || sn.trang_thai === "DAT_TRONG");

        if (isIneligible && !showUnconverted) return;
        if (isVirtual && !showVirtual) return;

        let iconColor = "#2563eb"; // Blue: Đủ điều kiện
        let iconSymbol = "fa-house";
        let statusBadge = '<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-100 text-emerald-700">Đã cấp số</span>';

        if (isIneligible) {
            iconColor = "#e11d48"; // Rose: Nhà trên đất chưa chuyển mục đích
            iconSymbol = "fa-ban";
            statusBadge = '<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-rose-100 text-rose-700">Chưa đủ ĐK cấp số</span>';
        } else if (isVirtual) {
            iconColor = "#d97706"; // Amber: Đất thổ cư chưa xây (Dự trữ)
            iconSymbol = "fa-draw-polygon";
            statusBadge = '<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-800">Thổ cư dự trữ</span>';
        }

        const markerHtml = `
            <div class="relative group cursor-pointer flex items-center justify-center ${isVirtual ? 'node-pulse-vn' : ''}">
                <div class="w-8 h-8 rounded-full flex items-center justify-center text-white shadow-lg font-bold text-xs border-2 border-white transform transition-transform group-hover:scale-125" style="background: ${iconColor};">
                    <i class="fa-solid ${iconSymbol} text-[11px]"></i>
                </div>
                <div class="absolute -bottom-6 px-1.5 py-0.5 rounded bg-slate-900/80 text-white text-[10px] font-semibold whitespace-nowrap shadow backdrop-blur-sm pointer-events-none">
                    ${sn.so_nha_moi.split(" ")[0]}
                </div>
            </div>
        `;

        const customIcon = L.divIcon({
            html: markerHtml,
            className: "custom-gis-marker",
            iconSize: [32, 32],
            iconAnchor: [16, 16]
        });

        const marker = L.marker([lat, lng], { icon: customIcon }).addTo(markersLayer);

        const popupContent = `
            <div class="p-2.5 max-w-[270px] text-slate-800 text-xs">
                <div class="flex items-center justify-between border-b pb-1.5 mb-2">
                    <span class="font-bold text-blue-700 uppercase tracking-wide text-[11px]">UBND XÃ TÂN PHÚ</span>
                    ${statusBadge}
                </div>
                <h4 class="font-extrabold text-sm text-slate-900 leading-tight mb-1">${sn.so_nha_moi}</h4>
                ${sn.so_to_thua ? `<p class="text-[11px] text-blue-600 font-semibold mb-1"><i class="fa-solid fa-map mr-1"></i>Địa chính: ${sn.so_to_thua}</p>` : ''}
                <p class="text-slate-600 mb-1"><b>Chủ sở hữu:</b> ${sn.ten_chu_ho}</p>
                <p class="text-slate-600 mb-1"><b>Pháp lý đất:</b> ${sn.muc_dich_su_dung_dat === 'DAT_O_THO_CU' ? '<span class="text-emerald-700 font-bold">Đất thổ cư (ONT)</span>' : '<span class="text-rose-600 font-bold">Chưa chuyển mục đích</span>'}</p>
                <p class="text-[10px] text-slate-500 mb-2 font-mono">WGS84: ${lat.toFixed(5)}, ${lng.toFixed(5)}</p>
                ${sn.ghi_chu ? `<p class="text-[11px] text-slate-500 italic mb-2 bg-slate-50 p-1 rounded border">${sn.ghi_chu}</p>` : ''}
                
                <div class="pt-2 border-t flex justify-end">
                    ${!isIneligible && !isVirtual ? `
                        <button onclick="downloadCertFor('${sn.id_nha}')" class="px-2.5 py-1 rounded-lg bg-blue-600 text-white text-[11px] font-semibold hover:bg-blue-700 transition flex items-center shadow-sm">
                            <i class="fa-solid fa-file-pdf mr-1"></i>Xuất Giấy CN
                        </button>
                    ` : `
                        <span class="text-[10px] text-slate-400 font-medium italic">Không phát hành số</span>
                    `}
                </div>
            </div>
        `;

        marker.bindPopup(popupContent, { className: "glass-popup" });
        sn._marker = marker;
    });

    // Auto-fit bounds
    if (AppState.soNhas.length > 0) {
        const group = new L.featureGroup(AppState.soNhas.map(s => s._marker).filter(Boolean));
        gisMap.fitBounds(group.getBounds().pad(0.2));
    }
}

async function downloadCertFor(id_nha) {
    try {
        showToast("📄 Đang sinh Giấy chứng nhận biển số nhà...", "info");
        
        const res = await fetch(`${API_BASE}/api/cert/generate/${id_nha}`);
        const data = await res.json();
        
        if (!res.ok) {
            const errMsg = data.detail || "Không thể sinh GCN";
            showToast(`❌ ${typeof errMsg === 'string' ? errMsg : JSON.stringify(errMsg)}`, "error");
            return;
        }
        
        if (data.certificate_url) {
            window.open(data.certificate_url, "_blank");
            showToast(`✅ Đã mở Giấy chứng nhận: ${data.message}`, "success");
        }
    } catch (e) {
        showToast("❌ Lỗi tải chứng nhận: " + e.message, "error");
    }
}

window.renderMapMarkers = renderMapMarkers;
window.downloadCertFor = downloadCertFor;
window.applyCoordsToSurveyor = applyCoordsToSurveyor;
window.applyCoordsToModal = applyCoordsToModal;
window.pinGPSOnMap = pinGPSOnMap;
window.focusGpsPin = focusGpsPin;
window.consumePendingGpsFlyTo = consumePendingGpsFlyTo;
