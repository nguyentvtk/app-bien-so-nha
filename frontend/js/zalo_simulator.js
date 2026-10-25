/**
 * Zalo Mini App "Tân Phú Số" Simulator (zalo_simulator.js)
 * Mô phỏng trải nghiệm người dân trên nền tảng Zalo Mini App theo đặc tả AppCapBienSoNha.md.
 * Cung cấp: Tra cứu bản đồ số nhà, Nộp hồ sơ trực tuyến, Định vị GPS và Theo dõi tiến độ.
 */

document.addEventListener("DOMContentLoaded", () => {
    setupZaloSubtabs();
    setupZaloSearch();
    setupZaloForm();
});

function setupZaloSubtabs() {
    const tabs = ["lookup", "submit", "cert"];
    tabs.forEach(t => {
        const btn = document.getElementById(`zalo-tab-btn-${t}`);
        if (!btn) return;
        btn.addEventListener("click", () => {
            tabs.forEach(other => {
                document.getElementById(`zalo-screen-${other}`)?.classList.add("hidden");
                const b = document.getElementById(`zalo-tab-btn-${other}`);
                if (b) {
                    b.classList.remove("text-blue-600", "font-bold");
                    b.classList.add("text-slate-400");
                }
            });
            document.getElementById(`zalo-screen-${t}`)?.classList.remove("hidden");
            btn.classList.add("text-blue-600", "font-bold");
            btn.classList.remove("text-slate-400");
        });
    });
}

function setupZaloSearch() {
    const input = document.getElementById("zalo-search-input");
    const resultBox = document.getElementById("zalo-search-results");
    if (!input || !resultBox) return;

    let debounce;
    input.addEventListener("input", (e) => {
        clearTimeout(debounce);
        const q = e.target.value.trim();
        if (q.length === 0) {
            resultBox.innerHTML = '<p class="text-center text-slate-400 py-6 text-xs">Nhập số nhà cũ hoặc số nhà mới để tra cứu...</p>';
            return;
        }

        debounce = setTimeout(async () => {
            try {
                const res = await fetch(`${API_BASE}/api/so-nha/search?q=${encodeURIComponent(q)}`);
                const items = await res.json();
                if (items.length === 0) {
                    resultBox.innerHTML = '<p class="text-center text-slate-400 py-6 text-xs">Không tìm thấy địa chỉ phù hợp.</p>';
                    return;
                }

                resultBox.innerHTML = items.map(it => `
                    <div class="p-3 mb-2 rounded-xl bg-white border border-slate-100 shadow-sm text-xs">
                        <div class="flex items-center justify-between mb-1">
                            <span class="font-bold text-blue-600 text-sm">${it.so_nha_moi}</span>
                            <span class="px-1.5 py-0.5 rounded text-[10px] bg-emerald-50 text-emerald-700 font-medium">Chính thức</span>
                        </div>
                        ${it.so_nha_cu ? `<p class="text-slate-500 mb-0.5"><b>Số cũ:</b> <span class="text-amber-700 font-semibold">${it.so_nha_cu}</span></p>` : ''}
                        <p class="text-slate-600 mb-1"><b>Chủ hộ:</b> ${it.ten_chu_ho}</p>
                        <div class="flex items-center justify-between pt-1 border-t text-[11px] text-slate-400">
                            <span><i class="fa-solid fa-location-dot mr-1 text-rose-500"></i>${it.id_tuyen_duong}</span>
                            <button onclick="downloadCertFor('${it.id_nha}')" class="text-blue-600 font-semibold hover:underline">
                                Xem Giấy CN <i class="fa-solid fa-chevron-right ml-0.5"></i>
                            </button>
                        </div>
                    </div>
                `).join("");

            } catch (err) {
                resultBox.innerHTML = '<p class="text-center text-rose-500 py-4 text-xs">Lỗi kết nối tra cứu.</p>';
            }
        }, 250);
    });
}

function setupZaloForm() {
    const form = document.getElementById("zalo-submit-form");
    const gpsBtn = document.getElementById("zalo-btn-get-gps");

    if (gpsBtn) {
        gpsBtn.addEventListener("click", () => {
            if ("geolocation" in navigator) {
                navigator.geolocation.getCurrentPosition(
                    (pos) => {
                        document.getElementById("zalo-gps-lat").value = pos.coords.latitude.toFixed(5);
                        document.getElementById("zalo-gps-lng").value = pos.coords.longitude.toFixed(5);
                        showToast("Đã lấy toạ độ GPS chính xác từ thiết bị!", "success");
                    },
                    (err) => {
                        // Fallback tọa độ Tân Phú
                        document.getElementById("zalo-gps-lat").value = (10.7925 + (Math.random() - 0.5) * 0.005).toFixed(5);
                        document.getElementById("zalo-gps-lng").value = (106.6300 + (Math.random() - 0.5) * 0.005).toFixed(5);
                        showToast("Đã thiết lập toạ độ GPS mô phỏng tại Quận Tân Phú", "info");
                    }
                );
            } else {
                document.getElementById("zalo-gps-lat").value = "10.79250";
                document.getElementById("zalo-gps-lng").value = "106.63000";
            }
        });
    }

    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();

            const name = document.getElementById("zalo-form-name").value.trim();
            const cccd = document.getElementById("zalo-form-cccd").value.trim();
            const phone = document.getElementById("zalo-form-phone").value.trim();
            const route = document.getElementById("zalo-route-select").value;
            const desc = document.getElementById("zalo-form-desc").value.trim();
            const width = parseFloat(document.getElementById("zalo-form-width").value) || 5.0;
            const lat = parseFloat(document.getElementById("zalo-gps-lat").value) || 10.7925;
            const lng = parseFloat(document.getElementById("zalo-gps-lng").value) || 106.6300;

            const payload = {
                id_yeu_cau: `ZALO_${Date.now().toString().slice(-6)}`,
                ho_ten_nguoi_nop: name,
                cccd: cccd,
                sdt: phone,
                email: "",
                dia_chi_khao_sat: desc,
                id_tuyen_duong: route,
                khoang_cach_mat_tien: width,
                toado_gps: { lat, lng },
                hinh_anh_khao_sat: ["https://images.unsplash.com/photo-1513694203232-719a280e022f?w=600"],
                giay_to_phap_ly: ["Don-Xin-Cap-So-Nha-Zalo.pdf"],
                loai_yeu_cau: "CAP_MOI",
                trang_thai: "CHO_TIEP_NHAN"
            };

            try {
                showToast("Đang gửi hồ sơ qua Zalo Mini App & Phân tích bằng Qwen3...", "info");
                const res = await fetch(`${API_BASE}/api/ho-so`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.success) {
                    showToast("Nộp hồ sơ thành công! Mã hồ sơ: " + data.id_yeu_cau, "success");
                    form.reset();
                    // Nạp lại danh sách hồ sơ
                    const hsRes = await fetch(`${API_BASE}/api/ho-so`);
                    AppState.hoSos = await hsRes.json();
                    renderDossierList();
                }
            } catch (err) {
                showToast("Lỗi nộp hồ sơ: " + err.message, "error");
            }
        });
    }
}
