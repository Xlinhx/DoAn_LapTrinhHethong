# Bảo trì và tái tạo bộ nộp

Tài liệu này dành cho người cập nhật sản phẩm. Người muốn chạy chương trình đọc [README](../README.md); người muốn học cách cài đặt đọc [tài liệu kỹ thuật](TECHNICAL_DEEP_DIVE.md).

## 1. Điền đúng thông tin nhóm

Chỉnh [project_metadata.json](project_metadata.json), nguồn chung cho Word và slides. Không lấy tên Git author làm tên đại diện nhóm.

- `faculty`, `instructor`, `academic_term`: thông tin đã xác nhận của học phần.
- `group_name`: tên nhóm nếu lớp có quy định.
- `members`: thêm **một object cho mỗi thành viên thực tế**, gồm `name`, `student_id`, `class_name` và `role` (phân công thực tế). Không giả định nhóm có một, ba hay bốn người.
- Có thể giữ phân công trong `task_allocation`: mỗi object có `student_id` hoặc `member` khớp thành viên, cùng `role`. Không dùng hai nguồn phân công mâu thuẫn; `members[].role` được ưu tiên nếu đã điền.

`mode: "draft"` cho phép thiếu thông tin: Word hiện nhãn nhắc, slides ghi trạng thái trong notes trang bìa. Chỉ hiện tên trên bìa slide khi đã có danh sách nhóm. `mode: "final"` yêu cầu đủ Khoa, giảng viên, học kỳ, danh sách thành viên, MSSV, lớp và phân công từng người. Chạy kiểm tra trước khi xuất:

```bash
python scripts/metadata_loader.py draft
python scripts/metadata_loader.py final
```

Lệnh thứ hai **phải thất bại** khi còn trường bắt buộc thiếu. Chỉ đổi `mode` sang `final` khi thông tin là thật và đầy đủ.

## 2. Chuẩn bị môi trường

Phần C và kiểm thử chạy trên Linux/Ubuntu WSL2 với GCC, Make, Bash, GNU coreutils, diff và Python 3. Dùng user thường; chạy root sẽ bỏ qua một số ca quyền.

Để sinh tài liệu, dùng Python 3.10+ trên Windows:

```powershell
python -m pip install -r requirements-docs.txt
```

Cần Microsoft Word để cập nhật mọi mục lục/số trang và xuất PDF; cần PowerPoint để xuất slide thành PNG/PDF kiểm tra. Script dùng PowerShell COM, **không cần pywin32**. Trên Windows, collector mặc định gọi distro `Ubuntu-24.04`; nếu distro khác, đổi tên trong `run_wsl_bash()` của `scripts/collect_evidence.py`. Đường dẫn repo được chuyển bằng `wslpath`, không cố định vào ổ P.

## 3. Từ log đến Word và slides

Chạy từ thư mục gốc repo trên Windows, theo thứ tự:

```powershell
python scripts/test_artifact_pipeline.py
python scripts/collect_evidence.py
python scripts/build_vku_report.py
python scripts/build_slides.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/export_office.ps1 -Kind PowerPoint -InputPath docs/Slides.pptx -OutputPath build/slide-preview
Copy-Item build/slide-preview/Slides.pdf docs/Slides.pdf
```

Collector cũng chạy trực tiếp trên Linux (`python3 scripts/collect_evidence.py` sau khi cài Pillow). Nó chép source/header/tests/Makefile sang thư mục tạm trên Linux, build và chạy ở đó để tránh clock skew của ổ Windows; không sửa source trong repo. Sau khi chạy test thường, sanitizer và demo, nó ghi:

- Ba log `.txt` đầy đủ trong `evidence/`, có môi trường, lệnh, thời gian UTC, Git revision và exit code.
- `test_results.json`: từng ca, số PASS/FAIL/SKIP, đầu ra demo và SHA-256 của source C, header, test và Makefile. CRLF được chuẩn hóa khi hash để không sai khác do checkout Windows.
- Ba ảnh **trích log** để đưa vào báo cáo. Đây là ảnh trình bày lại, không phải ảnh chụp terminal; log đầy đủ là nguồn đối chiếu.

Nếu recollect lỗi, JSON thành công cũ bị vô hiệu hóa; log lỗi vẫn được giữ. Builder từ chối dữ liệu thiếu summary, fail hoặc sai hash nguồn. Khi chỉnh C/test/Makefile, phải collect lại trước khi sinh tài liệu. Thêm test làm thay đổi nhóm coverage thì cập nhật phần phân loại ở slide 13 và báo cáo; số kết quả được đọc từ JSON nhưng diễn giải nhóm không được suy đoán tự động.

Word generator tự sinh bốn sơ đồ trắng đen, tạo DOCX tạm, cập nhật ba mục lục qua Word và xuất PDF. Chỉ thay bộ DOCX/PDF đích sau khi xuất thành công. Thiếu Word là lỗi xuất, không được coi DOCX chưa cập nhật là bản hoàn tất.

## 4. Kiểm tra thành phẩm

Mở `docs/BaoCao.pdf` và PNG trong `build/slide-preview`, kiểm **từng trang**: ngắt trang, bảng kéo dài, chú thích, số trang, mục lục, chữ tràn và độ đọc khi chiếu. Có file xuất ra chưa chứng minh bố cục đạt.

Word tham khảo **quy cách trình bày** Mẫu 3, QĐ 675/QĐ-ĐHVH ngày 03/04/2024: A4, lề trái 3 cm, các lề khác 2 cm, Times New Roman 13, giãn dòng 1.3, chữ đen. Đây là báo cáo học phần, không áp đặt số trang của khóa luận; mẫu riêng giảng viên giao được ưu tiên. [Văn bản VKU](https://daotao.vku.udn.vn/uploads/daotao/675-qd-ban-hanh-quy-dinh-trien-khai-do-an-khoa-luan-tot-nghiep-trong-cac-ctdt-dh-cua-vku-0001.pdf).

Slides có 16 trang chính, 6 trang dự phòng và speaker notes. Trình bày khoảng 18 phút đã tính demo 3 phút; không đọc cả 6 trang dự phòng trong luồng chính. Nền ngà sáng, xanh lam bụi, sage và đất nung; footer chỉ giữ số trang. Các sơ đồ, biểu đồ, chữ và log là native shapes, có thể chỉnh trực tiếp trong PowerPoint. Chín ảnh minh họa imagegen nằm trong `docs/assets/illustrations/`, mỗi ảnh dùng một lần; prompt gốc và nguồn tạo nằm trong `manifest.json`. Ảnh chỉ hỗ trợ hình dung, không thay thế bằng chứng chạy thật. Nếu sửa file thủ công, cần đồng bộ lại generator để lần build sau không mất thay đổi.

## 5. Kiểm gói nộp từ thư mục sạch

Trên Linux/WSL:

```bash
make log
make dist
verify_dir=$(mktemp -d /tmp/myls_submission_XXXXXX)
tar -xzf vku-system-programming-ls.tar.gz -C "$verify_dir"
cd "$verify_dir"
make && make test && make sanitize && make demo
```

Kiểm gói có source, header, tests, tài liệu, ảnh và script tái tạo, `requirements-docs.txt`, `LOG`. Không đưa binary hay output `build/` vào gói nộp. Kiểm lại `metadata_loader.py final` và danh sách thành viên trên cả bìa Word lẫn slide trước khi nộp.
