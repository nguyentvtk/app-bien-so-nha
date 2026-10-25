/**
 * AI Agent & MCP Gateway Monitor Controller (ai_monitor.js)
 * Giám sát trực quan hoá 3 tầng: LLM Thinking (Qwen3), Jev Decision và MCP Gateway Router.
 */

async function renderAIMonitor() {
    await fetchLogs();
    setupJevTester();
}

async function fetchLogs() {
    const tbody = document.getElementById("system-logs-body");
    if (!tbody) return;

    try {
        const res = await fetch(`${API_BASE}/api/system/logs`);
        const logs = await res.json();

        tbody.innerHTML = logs.map(l => `
            <tr class="border-b border-slate-100 text-xs hover:bg-slate-50">
                <td data-label="Thời gian" class="px-3 py-2 font-mono text-slate-400">${l.thoi_gian}</td>
                <td data-label="Hành động" class="px-3 py-2 font-bold text-blue-600">${l.hanh_dong}</td>
                <td data-label="Đối tượng" class="px-3 py-2 font-mono text-slate-700">${l.doi_tuong}</td>
                <td data-label="Thực hiện" class="px-3 py-2 text-slate-500">${l.nguoi_thuc_hien}</td>
                <td data-label="Chi tiết" class="px-3 py-2 text-slate-700">${l.chi_tiet || ''}</td>
            </tr>
        `).join("");
    } catch (e) {
        console.error("Lỗi lấy logs:", e);
    }
}

function setupJevTester() {
    const btn = document.getElementById("btn-test-jev");
    const inputSoNha = document.getElementById("jev-test-input");
    const resultBox = document.getElementById("jev-test-result");

    if (!btn || !inputSoNha || !resultBox) return;

    btn.onclick = async () => {
        const testNum = inputSoNha.value.trim();
        if (!testNum) {
            showToast("Vui lòng nhập số nhà muốn thử nghiệm", "warning");
            return;
        }

        const t0 = performance.now();
        try {
            // Thử nghiệm gọi cấp số qua MCP Gateway để xem Middleware Jev Score đánh chặn
            const res = await fetch(`${API_BASE}/mcp-gateway/rpc`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "sonha.assign",
                    params: {
                        id_nha: "SN_TEST_TMP",
                        so_nha_moi: testNum,
                        ten_chu_ho: "Kiểm tra Jev Score",
                        toado_gps: { lat: 10.7925, lng: 106.6300 },
                        id_tuyen_duong: AppState.selectedTuyenDuong,
                        loai_nha: "Thử nghiệm"
                    },
                    id: "test_jev_rpc"
                })
            });

            const t1 = performance.now();
            const latency = Math.round(t1 - t0);
            const data = await res.json();

            let statusClass = "bg-emerald-50 border-emerald-300 text-emerald-800";
            let icon = '<i class="fa-solid fa-circle-check text-emerald-600 text-xl"></i>';

            if (data.error) {
                statusClass = "bg-rose-50 border-rose-300 text-rose-800";
                icon = '<i class="fa-solid fa-ban text-rose-600 text-xl"></i>';
                const scoreData = data.error.data || {};
                resultBox.className = `p-4 rounded-xl border mt-3 transition-all ${statusClass}`;
                resultBox.innerHTML = `
                    <div class="flex items-start space-x-3">
                        ${icon}
                        <div class="flex-1">
                            <div class="flex items-center justify-between mb-1">
                                <span class="font-bold text-sm">Jev Score: ${scoreData.score !== undefined ? scoreData.score.toFixed(2) : '0.15'} (RED_DANGER - BLOCK)</span>
                                <span class="text-xs font-mono bg-white/70 px-2 py-0.5 rounded border">Phản xạ: ${latency}ms</span>
                            </div>
                            <p class="text-xs font-semibold mb-1">Hành động: BỊ CHẶN LẬP TỨC BỞI MIDDLEWARE</p>
                            <p class="text-xs leading-relaxed">${data.error.message}</p>
                        </div>
                    </div>
                `;
            } else {
                const jScore = data.result.jev_score || {};
                resultBox.className = `p-4 rounded-xl border mt-3 transition-all ${statusClass}`;
                resultBox.innerHTML = `
                    <div class="flex items-start space-x-3">
                        ${icon}
                        <div class="flex-1">
                            <div class="flex items-center justify-between mb-1">
                                <span class="font-bold text-sm">Jev Score: ${jScore.score !== undefined ? jScore.score.toFixed(2) : '0.96'} (GREEN_SAFE)</span>
                                <span class="text-xs font-mono bg-white/70 px-2 py-0.5 rounded border">Phản xạ: ${latency}ms</span>
                            </div>
                            <p class="text-xs font-semibold mb-1">Hành động: CHO PHÉP THỰC THI QUA MCP GATEWAY</p>
                            <p class="text-xs leading-relaxed">${data.result.message}</p>
                        </div>
                    </div>
                `;
            }
            resultBox.classList.remove("hidden");
        } catch (e) {
            showToast("Lỗi kiểm thử Jev: " + e.message, "error");
        }
    };
}

window.renderAIMonitor = renderAIMonitor;
