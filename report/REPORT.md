# Báo cáo Lab: Self evolving Agentic

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Hoàng Đức Minh | 2A202602362 | Harness, coordinator/message queue, worker, tool và kiểm tra offline |

- Nhà cung cấp và mô hình trong cấu hình: `openai:gpt-4o-mini`; nhiệt độ `0`; `recursion_limit` `60`. Không ghi khóa API.
- Deep Agents `0.7.21`; Windows; chạy trực tiếp, không dùng Docker.
- Đã chạy 3 tác vụ học ở điều kiện `baseline`: tổng `445,525` token và `326.7` giây. Chưa có lần chạy `subagents`, `skills-auto` hoặc tác vụ đánh giá.
- Chưa tạo commit/tag `freeze`.

## 2. Giả thuyết

Chưa tạo tag `freeze`, vì vậy không ghi giả thuyết sau thời điểm thực nghiệm để tránh làm sai quy trình. Các giả thuyết cần được chốt trước khi chạy tập đánh giá.

- H1 (`subagents` so với `baseline`): chưa kiểm tra.
- H2 (`skills-auto` so với `baseline`): chưa kiểm tra.
- H3 (tác vụ học so với tác vụ đánh giá): chưa kiểm tra.

## 3. Làm quen Deep Agents

1. Tác tử mặc định có các công cụ tệp `ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep`; shell `execute`; và subagent `task`. `execute` là công cụ chạy lệnh.
2. `general-purpose` là subagent đa dụng cho nghiên cứu nhiều bước và thực thi tác vụ. Mỗi lần gọi độc lập, chỉ nhận prompt giao việc và không tự kế thừa hội thoại của tác tử chính.
3. Hướng dẫn đã dùng: “Put full detail in the prompt and state exactly what it should return” cho `task`; “Use absolute paths and avoid `cd` so the working directory stays stable” cho `execute`.

## 4. Đường cơ sở và phân loại lỗi

Chỉ có dữ liệu của ba tác vụ học `baseline`. Điểm tổng hợp: kỹ thuật `4/18`, quy ước `0/9`, token trung bình `148,508`, không lần nào đọc skill.

| Tác vụ | Check thất bại | Nhóm lỗi | Bằng chứng |
|---|---|---|---|
| `code-learn` | `tests_not_modified` | C | Bộ chấm báo “original files in tests/ must not be modified”. |
| `code-learn` | `parse_price_all_formats` | A | Sai với định dạng `'(12.00)'`. |
| `code-learn` | `csv_quoting_follows_docstring` | A | `to_csv_row` trả chuỗi chưa escape quote đúng quy ước CSV. |
| `code-learn` | `rule_type_hints` | E | Thiếu annotation cho public function. |
| `code-learn` | `rule_regression_tests` | E | Thiếu `tests/test_regressions.py` với ít nhất ba test. |
| `code-learn` | `rule_changelog` | E | Thiếu ba dòng `fix(...)` dưới `## Unreleased`. |
| `data-learn` | `north_q1_revenue` | B | Không tạo `workspace/answer.json`. |
| `data-learn` | `north_q1_orders` | B | Không tạo `workspace/answer.json`. |
| `data-learn` | `top_region` | B | Không tạo `workspace/answer.json`. |
| `data-learn` | `missing_amount_orders` | B | Không tạo `workspace/answer.json`. |
| `data-learn` | `duplicate_rows_removed` | B | Không tạo `workspace/answer.json`. |
| `data-learn` | `rule_money_in_cents` | E | Thiếu đầu ra số tiền theo cents. |
| `data-learn` | `rule_meta_block` | E | Thiếu metadata trong `answer.json`. |
| `data-learn` | `rule_clean_csv` | E | Thiếu `clean.csv` đúng schema/UTC/canonical region. |
| `logs-learn` | `valid_structure` | B | Không tạo `workspace/errors.json`. |
| `logs-learn` | `entry_count` | B | Không tạo `workspace/errors.json`. |
| `logs-learn` | `timestamps_utc` | B | Không tạo `workspace/errors.json`. |
| `logs-learn` | `exception_fields` | B | Không tạo `workspace/errors.json`. |
| `logs-learn` | `repeat_counts` | B | Không tạo `workspace/errors.json`. |
| `logs-learn` | `counts_by_service` | B | Không tạo `workspace/errors.json`. |
| `logs-learn` | `rule_service_names` | E | Không tạo `errors.json` để kiểm tra tên service. |
| `logs-learn` | `rule_sorted_errors` | E | Không tạo `errors.json` để kiểm tra thứ tự. |
| `logs-learn` | `rule_schema_header` | E | Không tạo `errors.json` để kiểm tra schema header. |

Nhóm B và E chiếm đa số. Một skill tổng quát có thể yêu cầu kiểm tra đầu ra bắt buộc trước khi kết thúc và rà soát các check `rule_`; tuy nhiên chưa có skill nào được sinh/chạy nên đây chỉ là hướng xử lý cần kiểm chứng.

## 5. Điều kiện `subagents`

- Đã định nghĩa `explorer`, `implementer`, `reviewer` trong harness; vai trò lần lượt là khảo sát, thực hiện thay đổi có phạm vi rõ, và rà soát độc lập.
- Chưa chạy điều kiện `subagents`. Ba lần `baseline` đều có `subagent_calls = 0`.
- Vì chưa có lần gọi subagent, chưa có bằng chứng về thông tin thiếu/thừa khi giao việc hoặc chi phí token/thời gian của phương án này.

## 6. Self-evolving: skill do curator sinh

- Chưa chạy curator; chưa có skill tự sinh, skill bị xóa hoặc `skills_read` khác 0.

| Skill | Tổng quát hay riêng cho tác vụ học? | Đúng hay sai | Độ dài/`description`/`skills_read` |
|---|---|---|---|
| Chưa có | Chưa đánh giá | Chưa đánh giá | `skills_read = 0/3` ở baseline |

## 7. Kết quả so sánh

Kết quả `python scripts/check_breakdown.py`:

```text
condition     role    technical  house rules  mean tokens  read a skill
baseline      learn     4/18         0/9          148,508      0/3
(evaluation rows are hidden until the git tag `freeze` exists)
```

| Tác vụ | Điều kiện | Điểm | Token | Thời gian | Tool call | Lỗi runtime |
|---|---:|---:|---:|---:|---:|---|
| `code-learn` | baseline | `4/10` (`0.40`) | 28,107 | 24.6 s | 12 | Không |
| `data-learn` | baseline | `0/8` (`0.00`) | 388,278 | 119.5 s | 0 | `GraphRecursionError` ở limit 60 |
| `logs-learn` | baseline | `0/9` (`0.00`) | 29,140 | 182.6 s | 2 | Không, nhưng không tạo output |

Không có lần chạy nào `skills_modified = true`. `data-learn` có `error`, còn `logs-learn` kết thúc không có `error` nhưng vẫn không tạo `errors.json`.

## 8. Phân tích

1. Chưa thể kết luận điều kiện nào cải thiện điểm học/đánh giá vì chỉ có `baseline` trên tập học.
2. `baseline` đạt `4/18` check kỹ thuật và `0/9` check quy ước. Không có dữ liệu để đánh giá skill có giúp quy ước mới của tập đánh giá hay không.
3. Chưa có `skills_read`, nên không thể nêu check được/không được skill hỗ trợ. Bằng chứng baseline cho thấy yêu cầu kiểm chứng output là điểm yếu chính.
4. Token trung bình baseline là `148,508`; chưa có token của `subagents` hoặc `skills-auto`, nên chưa tính được hiệu quả điểm/token.
5. Chưa có skill sinh ra, do đó chưa có bằng chứng rò rỉ dữ liệu hoặc quá khớp. Quy trình dự kiến vẫn phải đóng băng skill trước khi đọc/chạy tập đánh giá.
6. Chưa có số liệu trước/sau đóng băng; chưa thể định lượng nhiễu.

## 9. Hạn chế và tính hợp lệ

1. Mỗi cấu hình/tác vụ mới chạy một lần; nhiễu của model có thể lớn hơn chênh lệch quan sát được.
2. Chưa có `freeze`, tập đánh giá, `subagents` hoặc `skills-auto`; không thể đưa ra kết luận so sánh các điều kiện.
3. `data-learn` gặp `GraphRecursionError`, làm số liệu token cao (`388,278`) nhưng không tạo đầu ra; nó không đại diện cho một lần hoàn thành tác vụ bình thường.
4. Các test coordinator/worker/tool/integration bên dưới dùng mock offline; chúng xác minh giao diện và luồng điều khiển, không đo chất lượng mô hình thật.

## 10. Kết luận

Harness hiện qua toàn bộ test offline, gồm coordinator, worker, tool và integration. Kết quả baseline học hiện chưa tốt (`4/27` check) và không đủ để so sánh các điều kiện. Lỗi quan trọng nhất là không tạo/kiểm chứng file đầu ra và bỏ sót quy ước. Bước tiếp theo là chốt giả thuyết, chạy `subagents` trên ba tác vụ học, sinh skill, tạo tag `freeze`, rồi mới chạy tập đánh giá.

## Phụ lục: kết quả kiểm tra implementation

| Hạng mục | Lệnh | Kết quả |
|---|---|---|
| Coordinator | `pytest tests/test_02_coordinator.py -v` | `5 passed` |
| Worker | `pytest tests/test_03_workers.py -v` | `4 passed` |
| Tool | `pytest tests/test_04_tools.py -v` | `4 passed` |
| Integration | `pytest tests/test_05_integration.py -v` | `5 passed` |
| Nhóm test 2–5 chạy lại | `pytest test_02... test_05... -v` | `18 passed` |
| Toàn bộ suite | `pytest tests/ --durations=10` | `50 passed` |
| Coordinator standalone | `python scripts/test_coordinator_standalone.py` | `3/3 passed` |
| Tool integration | `python scripts/test_tool_integration.py` | `3/3 passed` |
| Debug | `python scripts/debug_system.py "Analyze Q3 sales and create report" --log-level WARNING` | `success`; data, code, evaluation đều có kết quả |
| Profile | `python scripts/profile_system.py --requests 1 --limit 5` | `2,298` function calls trong `0.004 s` |

Benchmark offline (`results/benchmark_results.json`, 3 lần/case):

| Case | Thành công | Min | Median | Trung bình | Max |
|---|---:|---:|---:|---:|---:|
| Simple data query | `3/3` | 1.60 ms | 2.22 ms | 2.26 ms | 2.96 ms |
| Code generation | `3/3` | 1.04 ms | 1.27 ms | 1.54 ms | 2.32 ms |
| Complex workflow | `3/3` | 1.68 ms | 1.81 ms | 1.77 ms | 1.82 ms |

Các benchmark này dùng `demo_system` offline, nên chỉ phản ánh overhead của coordinator/message queue/mock worker; không phản ánh latency API hay tool bên ngoài.
