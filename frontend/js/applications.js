/**
 * Dossier & Public Services Controller (applications.js)
 * Tiếp nhận, quản lý hồ sơ cấp mới/đổi số nhà từ người dân & Zalo Mini App.
 * Tích hợp AI Qwen3 thẩm định hồ sơ và phê duyệt xuất Giấy chứng nhận điện tử.
 */

function renderDossierList() {
    const container = document.getElementById("dossier-list-container");
    const statPending = document.getElementById("stat-pending-count");
    const statReviewing = document.getElementById("stat-reviewing-count");
    const statDone = document.getElementById("stat-done-count");

    if (!container) return;
    container.innerHTML = "";

    let pending = 0, reviewing = 0, done = 0;

    AppState.hoSos.forEach(hs => {
        if (hs.trang_thai === "CHO_TIEP_NHAN") pending++;
        else if (hs.trang_thai === "DANG_THAM_DINH") reviewing++;
        else if (hs.trang_thai === "DA_CAP_SO") done++;

        const card = document.createElement("div");
        card.className = "glass-card rounded-2xl p-5 border border-white/40 shadow-sm transition hover:shadow-md";

        const statusBadges = {
            CHO_TIEP_NHAN: '<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-700 border border-amber-500/20">Chờ tiếp nhận</span>',
            DANG_THAM_DINH: '<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/15 text-blue-700 border border-blue-500/20">Đang thẩm định</span>',
            DA_CAP_SO: '<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-700 border border-emerald-500/20">Đã cấp biển số</span>',
            TU_CHOI: '<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-700 border border-rose-500/20">Từ chối</span>'
        };

        card.innerHTML = `
            <div class="flex items-start justify-between mb-3">
                <div>
                    <span class="text-xs font-mono font-bold text-slate-400 mr-2">${hs.id_yeu_cau}</span>
                    <span class="text-xs font-semibold text-slate-500"><i class="fa-regular fa-clock mr-1"></i>${hs.ngay_tao}</span>
                </div>
                ${statusBadges[hs.trang_thai] || statusBadges.CHO_TIEP_NHAN}
            </div>

            <h4 class="font-bold text-base text-slate-900 mb-1">${hs.ho_ten_nguoi_nop}</h4>
            <p class="text-xs text-slate-600 mb-2"><b>CCCD:</b> ${hs.cccd} | <b>SĐT:</b> ${hs.sdt}</p>

            <div class="p-3 rounded-xl bg-slate-50/80 border border-slate-100 mb-3 text-xs">
                <p class="text-slate-700 mb-1"><b>Mô tả thực địa:</b> ${hs.dia_chi_khao_sat}</p>
                <p class="text-slate-500"><b>Mặt tiền:</b> ${hs.khoang_cach_mat_tien}m | <b>Tuyến:</b> ${hs.id_tuyen_duong} ${hs.hem_ngach ? `(${hs.hem_ngach})` : ''}</p>
            </div>

            ${hs.ai_feedback ? `
                <div class="p-3 rounded-xl bg-blue-50/60 border border-blue-100 text-xs mb-3 text-blue-900">
                    <div class="font-semibold flex items-center mb-1 text-blue-700">
                        <i class="fa-solid fa-robot mr-1.5"></i>Tư vấn từ AI Qwen3 (Thinking Layer):
                    </div>
                    <p class="leading-relaxed">${hs.ai_feedback}</p>
                    ${hs.so_nha_de_xuat ? `<p class="mt-1.5 font-bold text-blue-800">Số đề xuất: ${hs.so_nha_de_xuat}</p>` : ''}
                </div>
            ` : ''}

            <div class="pt-3 border-t border-slate-100 flex items-center justify-between">
                <button onclick="triggerAIReview('${hs.id_yeu_cau}')" class="px-3 py-1.5 rounded-lg text-xs font-semibold text-blue-600 hover:bg-blue-50 transition border border-blue-200 flex items-center">
                    <i class="fa-solid fa-wand-magic-sparkles mr-1.5"></i>Thẩm định AI
                </button>

                ${hs.trang_thai !== "DA_CAP_SO" ? `
                    <button onclick="promptApprove('${hs.id_yeu_cau}', '${hs.so_nha_de_xuat || ''}')" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 transition flex items-center shadow-sm">
                        <i class="fa-solid fa-stamp mr-1.5"></i>Duyệt & Cấp biển
                    </button>
                ` : `
                    <span class="text-xs font-bold text-emerald-600 flex items-center">
                        <i class="fa-solid fa-check-double mr-1"></i>Đã cấp số: ${hs.so_nha_de_xuat || 'Xong'}
                    </span>
                `}
            </div>
        `;

        container.appendChild(card);
    });

    if (statPending) statPending.textContent = pending;
    if (statReviewing) statReviewing.textContent = reviewing;
    if (statDone) statDone.textContent = done;
}

// Gọi Qwen3 thẩm định hồ sơ
async function triggerAIReview(id_yeu_cau) {
    try {
        showToast("Đang kích hoạt Tầng 1 (Local Qwen3) thẩm định hồ sơ...", "info");
        const res = await fetch(`${API_BASE}/api/ho-so/${id_yeu_cau}/ai-review`, {
            method: "POST"
        });
        const data = await res.json();
        if (data.ai_review) {
            showToast("AI Qwen3 đã hoàn tất thẩm định!", "success");
            // Cập nhật local
            const hs = AppState.hoSos.find(x => x.id_yeu_cau === id_yeu_cau);
            if (hs) {
                hs.ai_feedback = data.ai_review;
                renderDossierList();
            }
        }
    } catch (e) {
        showToast("Lỗi thẩm định AI: " + e.message, "error");
    }
}

// Cán bộ duyệt cấp biển
async function promptApprove(id_yeu_cau, defaultSoNha) {
    const approvedSoNha = prompt("Nhập số nhà chính thức muốn cấp cho hồ sơ này:", defaultSoNha || "14 Đường Cách Mạng");
    if (!approvedSoNha || approvedSoNha.trim() === "") return;

    try {
        showToast("Đang duyệt hồ sơ, kiểm tra Jev Score và xuất Giấy chứng nhận...", "info");
        const res = await fetch(`${API_BASE}/api/ho-so/${id_yeu_cau}/approve?so_nha_cap=${encodeURIComponent(approvedSoNha.trim())}`, {
            method: "POST"
        });
        const data = await res.json();
        if (!res.ok) {
            showToast("Lỗi duyệt: " + (data.detail || "Không thể phê duyệt"), "error");
            return;
        }

        showToast(data.message, "success");
        // Reload dữ liệu
        await loadInitialData();
        renderDossierList();

        if (data.certificate_url) {
            window.open(data.certificate_url, "_blank");
        }
    } catch (e) {
        showToast("Lỗi phê duyệt: " + e.message, "error");
    }
}

window.renderDossierList = renderDossierList;
window.triggerAIReview = triggerAIReview;
window.promptApprove = promptApprove;
