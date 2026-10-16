# Checklist nộp Đề tài 17 — myls

Kết quả kỹ thuật phải đối chiếu với lần chạy trong [test_results.json](evidence/test_results.json), không suy từ dấu tích trong tài liệu này.

## Sản phẩm và bằng chứng

- [x] Bốn cờ `-a`, `-l`, `-R`, `-S`, 16 tổ hợp và cờ viết rời/đổi thứ tự: suite GNU differential.
- [x] Chi tiết `-l`: quyền thường/đặc biệt, owner/group, time cũ/gần/tương lai, symlink, hard link, FIFO/socket và character device.
- [x] Block device và total làm tròn: helper với metadata tổng hợp, không tuyên bố đã tạo block device thật.
- [x] Mảng hơn 64 mục, sparse file > 2 GiB, tên có khoảng trắng và tiếng Việt.
- [x] Phân biệt lỗi CLI 2 và lỗi khi duyệt 1; giữ mức lỗi cao nhất; tiếp tục operand/nhánh hợp lệ.
- [x] Fault injection cho `readdir`, `readlink`, `closedir`, `realloc`; lỗi ghi/flush `/dev/full`.
- [x] Đóng luồng thư mục trước đệ quy; giải phóng EntryList và chuỗi theo ownership. Sanitizer không phát hiện lỗi trong các ca đã chạy.
- [x] Lần chạy hiện tại: 37/37 ở bản thường và 37/37 ở bản sanitizer, 0 FAIL, 0 SKIP. 26 ca differential GNU, 11 ca hợp đồng/helper/fault.
- [x] 9 regression test cho chốt dữ liệu: summary thiếu/sai, SKIP, source hash cũ, JSON lỗi, demo lỗi, nhóm nhiều thành viên và phân công.
- [x] Log đầy đủ có môi trường/lệnh/exit; JSON ràng buộc source/tests/Makefile. Ảnh ghi rõ trích log, không giả ảnh terminal.

## Tài liệu và trình bày

- [x] README gọn, tập trung build/chạy/test/demo và liên kết tài liệu.
- [x] Tài liệu kỹ thuật 11 mục: bài toán → nền tảng → API → trace → cờ → tài nguyên → lỗi → test → câu hỏi.
- [x] Word tham khảo quy cách VKU: A4, lề 3–2–2–2 cm, TNR 13, dòng 1.3, chữ đen, heading thật, mục lục và danh mục hình/bảng có số trang.
- [x] Báo cáo phân biệt mô hình minh họa và log thật; nêu giới hạn WSL, Unicode/collation, ACL/SELinux, ký tự điều khiển và chu trình bind mount.
- [x] Deck 22 trang: 16 chính khoảng 18 phút gồm demo 3 phút, 6 dự phòng; speaker notes, sơ đồ native, cây thư mục, timeline và biểu đồ size.
- [ ] Bản nộp hành chính: đầy đủ Khoa, giảng viên, học kỳ, **mọi** thành viên/MSSV/lớp/phân công; `metadata_loader.py final` phải chạy thành công.
- [ ] Nhóm tự tập trình bày và phân chia lời nói; kiểm demo trên máy dùng khi bảo vệ.

Khi sửa sản phẩm, collect lại và kiểm từng trang sau khi sinh. Chạy `make log`, `make dist`, giải nén sang thư mục sạch và build/test/demo theo [MAINTENANCE](docs/MAINTENANCE.md). Chưa có đủ danh tính nhóm nên bộ Word/slides hiện là bản thảo về thông tin hành chính.
