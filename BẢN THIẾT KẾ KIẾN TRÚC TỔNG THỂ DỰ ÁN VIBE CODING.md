Dưới đây là toàn bộ tài liệu báo cáo kỹ thuật chi tiết được đóng gói chuẩn định dạng **Markdown (`.md`)** để bạn đưa thẳng vào **Antigravity IDE** hoặc bất kỳ AI Coding Agent nào tự động phân tích và sinh mã nguồn:

```markdown
# BẢN THIẾT KẾ KIẾN TRÚC TỔNG THỂ DỰ ÁN VIBE CODING
## Hệ Thống AI Agent Mở Rộng Độc Lập Module (Modular Vibe Coding Architecture)

> **Mục đích**: Báo cáo kỹ thuật chi tiết dùng cho Antigravity IDE / AI Coding Agent tự động xây dựng và triển khai dự án Vibe Coding theo kiến trúc phân tách 3 tầng độc lập, tích hợp Jev (System 1) và MCP Gateway. Thiết kế giúp tải module mới theo dạng Plug-and-Play mà không gãy hệ thống hay phải đập đi xây lại.

---

## I. TỔNG QUAN KIẾN TRÚC 3 TẦNG (3-LAYER ARCHITECTURE)

Nguyên tắc cốt lõi: **LLM suy nghĩ, Jev quyết định, Code thực thi.**

```
┌─────────────────────────────────────────────────────────────┐
│                TẦNG 1: LLM (THINKING LAYER)                 │
│  - Phân tích ngữ cảnh phức tạp, tóm tắt, diễn giải          │
│  - Xử lý System 2 (Suy luận sâu)                            │
│  - Tuyệt đối không điều phối luồng (Control Flow)           │
└──────────────────────────────┬──────────────────────────────┘
                               │ State / Context
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              TẦNG 2: JEV (DECISION LAYER)                   │
│  - Xử lý System 1 (Phản xạ nhanh 70–150ms, non-generative)   │
│  - Trả về Typed Decision Objects (Choice, Score, Noul)      │
│  - Tỷ lệ ảo giác (Hallucination) = 0%, chi phí $0 output    │
└──────────────────────────────┬──────────────────────────────┘
                               │ Typed Decision Object
                               ▼
┌─────────────────────────────────────────────────────────────┐
│            TẦNG 3: MCP GATEWAY & EXECUTION LAYER            │
│  - Cổng điều phối duy nhất (Single Entry Point Gateway)      │
│  - Middleware đánh chặn & phân quyền (Read/Write/Delete)    │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │ Module Auth  │    │ Module DB    │    │ Module MCP   │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
└──────────────────────────────┴──────────────┴───────────────┘
```

### 1.1. Tầng 1: LLM (Thinking Layer - System 2)
* **Chức năng**: Đảm nhận công việc suy luận phức tạp, tổng hợp thông tin, diễn giải ngôn ngữ tự nhiên, tóm tắt tài liệu.
* **Nguyên tắc đóng gói**: Không cấp quyền trực tiếp gọi code hay điều hướng luồng chính nhằm tránh tình trạng vòng lặp vô tận (infinite loop) và bùng nổ chi phí token output.

### 1.2. Tầng 2: Jev (Decision Layer - System 1)
* **Chức năng**: Bộ não phản xạ nhanh (70–150ms), chi phí cực thấp (\$0.042 / 1M input tokens, \$0.00 output tokens), xử lý tính toán xác xuất song song.
* **Nguyên tắc đóng gói**: Chỉ tiếp nhận trạng thái hệ thống (`system state`) và trả về các đối tượng dữ liệu có kiểu định nghĩa trước (`Typed Decision Objects`), không sinh văn bản tự do.

### 1.3. Tầng 3: MCP Gateway & Execution Layer (System Execution)
* **Chức năng**: Nơi chứa toàn bộ logic nghiệp vụ, API, kết nối cơ sở dữ liệu và các module/tool độc lập.
* **Cơ chế**: Sử dụng kiến trúc MCP Gateway tập trung kết nối chuẩn JSON-RPC 2.0.

---

## II. QUY CÁCH DỮ LIỆU QUYẾT ĐỊNH (TYPED DECISION SPECIFICATION)

Để đảm bảo Antigravity IDE xây dựng code kiểm soát 100% luồng xử lý, Jev chỉ trả về 3 đối tượng dữ liệu có cấu trúc:

```typescript
// 1. Choice: Chọn 1 hành động/module từ danh sách Enum định nghĩa trước
export type ChoiceDecision<T extends string> = {
  type: "choice";
  selected: T;                           // Tên Enum của Module/Action được chọn
  confidence: number;                    // Mức độ tin cậy được hiệu chỉnh (0.0 -> 1.0)
  probabilities: Record<T, number>;      // Bảng phân bổ xác suất cho tất cả các phương án
};

// 2. Score: Chấm điểm chất lượng output hoặc thang điểm rủi ro
export type ScoreDecision = {
  type: "score";
  score: number;                         // Giá trị số thực (0.0 -> 1.0 hoặc thang điểm N)
  confidence: number;                    // Độ tự tin của phán đoán
};

// 3. Noul: Kiểm tra hoàn thành mục tiêu (Goal completion)
export type NoulDecision = {
  type: "noul";
  isCompleted: boolean;                  // true = kết thúc vòng lặp; false = tiếp tục
  confidence: number;                    // Mức độ tin cậy
};
```

---

## III. THIẾT KẾ CỔNG ĐIỀU PHỐI MODULE (MCP GATEWAY ARCHITECTURE)

### 3.1. Cơ chế Single Entry Point
Mọi kết nối từ ứng dụng đến các dịch vụ bên ngoài (GitHub, Slack, Database, Mail) phải đi qua một **MCP Gateway** duy nhất.

```
[Agent Engine] ──(JSON-RPC 2.0)──► [MCP Gateway]
                                         │
                   ┌─────────────────────┼─────────────────────┐
                   ▼                     ▼                     ▼
             [Module GitHub]       [Module Database]     [Module Payment]
```

### 3.2. Middleware Security & Interception Rules
* **Thao tác READ (Get/Search)**: Cho phép chuyển tiếp thẳng (Pass-through) xuống Module xử lý.
* **Thao tác WRITE / UPDATE / DELETE**: Đánh chặn bắt buộc qua Middleware Jev Score.
  * `Score ≥ 0.95` (Safe): Tự động cho phép thực thi down-stream.
  * `0.70 ≤ Score < 0.95` (Warning): Gắn cảnh báo / Yêu cầu xác nhận người dùng.
  * `Score < 0.70` (Danger): Ngăn chặn (Block) lập tức, ghi vết hệ thống.

---

## IV. QUY TRÌNH VẬN HÀNH VÒNG LẶP CHUẨN (5-STEP AGENT LOOP)

```python
# Pseudo-code chuẩn dành cho Antigravity IDE triển khai vòng lặp Agent

def run_agent_loop(initial_state: dict):
    state = initial_state
    
    while True:
        # Step 1: Ingest State (Đọc trạng thái hệ thống)
        current_state = read_system_state(state)
        
        # Step 2: Decision Out (Gọi Jev Choice để lấy Module/Action tiếp theo)
        action_decision = jev.choice(
            state=current_state,
            options=["CALL_AUTH_MODULE", "CALL_DB_MODULE", "CALL_API_MODULE", "ESCALATE_LLM"]
        )
        
        # Step 3: Execute Action (Tầng Code/Gateway thực thi)
        execution_result = execute_action(action_decision.selected, current_state)
        
        # Step 4: Evaluate Output (Gọi Jev Score để kiểm tra chất lượng/rủi ro)
        eval_score = jev.score(result=execution_result, criteria="quality_and_risk")
        if eval_score.score < 0.70:
            execution_result = handle_fallback_or_retry(current_state, execution_result)
            
        # Step 5: Check Goal (Gọi Jev Noul để kiểm tra hoàn thành)
        goal_check = jev.noul(state=current_state, result=execution_result)
        if goal_check.isCompleted:
            break # Kết thúc vòng lặp sạch sẽ
            
        # Cập nhật trạng thái cho vòng tiếp theo
        state = update_system_state(current_state, execution_result)
        
    return state
```

---

## V. REGISTRY QUY TRÌNH PLUG-AND-PLAY MỞ RỘNG MODULE

Khi Antigravity IDE cần thêm một Module mới vào dự án, chỉ cần làm 3 bước chuẩn hoá:

1. **Thêm Enum Action**: Đăng ký tên Enum hành động của Module mới vào danh sách `Choice` options của Jev.
2. **Khai báo MCP Handler**: Đăng ký Tool/Service mới vào cổng `MCP Gateway`.
3. **Cấu hình Rule Middleware**: Đặt ngưỡng `Score` cho các thao tác thay đổi dữ liệu của Module mới.

> **Tác dụng**: Giữ nguyên Core Loop, không thay đổi prompt của LLM, đảm bảo tính ổn định 100% cho các module cũ.

---

## VI. BẢNG THANG ĐIỂM VÀ PHÂN LUỒNG XỬ LÝ (RISK MATRIX)

| Ngưỡng Điểm (Score) | Trạng Thái | Hành Động Hệ Thống |
| :--- | :--- | :--- |
| **0.95 - 1.00** | Green (An toàn) | Cho phép thực thi tự động lập tức qua MCP Gateway |
| **0.70 - 0.94** | Yellow (Cảnh báo) | Chuyển luồng, gắn thẻ cảnh báo hoặc xin xác nhận từ người dùng |
| **< 0.70** | Red (Nguy hiểm) | Ngăn chặn thực thi (Block), đẩy lên LLM xử lý hoặc báo log |

---

## VII. MẪU FILE CẤU HÌNH BIẾN MÔI TRƯỜNG (.env.template)

```env
# Credentials & Server Endpoints for Antigravity IDE
TYPESAFE_API_KEY="your_typesafe_api_key_here"
JEV_MODEL_ENDPOINT="https://typesafe.ai/api/v1/jev"
MCP_GATEWAY_URL="http://localhost:8080/mcp-gateway"
RISK_THRESHOLD_SAFE=0.95
RISK_THRESHOLD_WARN=0.70
```

---
*Tài liệu được thiết kế dạng chuẩn Markdown để Antigravity IDE tự đọc, phân tích và sinh mã nguồn tự động.*
```

🛠️ Bạn có muốn mình tạo thêm mẫu boilerplate code chi tiết cho tệp cấu hình MCP Gateway hoặc tệp khởi tạo Jev Skill để Antigravity ghép nối dễ hơn không?