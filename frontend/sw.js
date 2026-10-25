/**
 * Service Worker — WebApp Biển Số Nhà, Xã Tân Phú
 * =================================================
 * Mục tiêu: hỗ trợ "Thêm vào màn hình chính" (Add to Home Screen) chạy như
 * app di động và mở được giao diện khi mất mạng (chỉ lớp vẽ tĩnh).
 *
 * Chiến lược an toàn dữ liệu hiện trường:
 *   - /api/**          → LUÔN đi mạng, tuyệt đối KHÔNG cache (dữ liệu hộ dân,
 *                        thửa đất, GPS phải mới nhất cho cán bộ đi thực địa).
 *   - Trang & /static/** → mạng trước (network-first), khi offline mới dùng
 *                        bản đã cache của lần mở gần nhất.
 */

const TEN_CACHE = "tanphu-so-v1";
const TINH_HIENU = ["/", "/static/manifest.json"];

self.addEventListener("install", (suKien) => {
    suKien.waitUntil(
        caches.open(TEN_CACHE).then((cache) => cache.addAll(TINH_HIENU))
    );
    self.skipWaiting();
});

self.addEventListener("activate", (suKien) => {
    suKien.waitUntil(
        caches.keys().then((danhSach) =>
            Promise.all(danhSach.filter((t) => t !== TEN_CACHE).map((t) => caches.delete(t)))
        ).then(() => self.clients.claim())
    );
});

self.addEventListener("fetch", (suKien) => {
    const yeuCau = suKien.request;
    const duongDan = new URL(yeuCau.url);

    // Chỉ xử lý cùng nguồn; API luôn đi mạng thẳng
    if (duongDan.origin !== self.location.origin) return;
    if (duongDan.pathname.startsWith("/api/")) return;
    if (yeuCau.method !== "GET") return;

    suKien.respondWith(
        fetch(yeuCau)
            .then((phanHoi) => {
                // Lưu lại bản mới cho lần offline sau (chỉ loại thành công)
                if (phanHoi && phanHoi.status === 200 && phanHoi.type === "basic") {
                    const banSao = phanHoi.clone();
                    caches.open(TEN_CACHE).then((cache) => cache.put(yeuCau, banSao));
                }
                return phanHoi;
            })
            .catch(() =>
                // Offline: trả bản cache gần nhất; nếu không có → về trang chủ đã cache
                caches.match(yeuCau).then((cache) =>
                    cache || caches.match("/") || new Response(
                        "<h1>Không có kết nối</h1><p>Vui lòng bật lại Internet để dùng tiếp Hệ thống Biển Số Nhà.</p>",
                        { headers: { "Content-Type": "text/html; charset=utf-8" }, status: 503 }
                    )
                )
            )
    );
});
