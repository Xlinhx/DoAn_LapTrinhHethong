# myls — Đề tài 17, Lập trình hệ thống VKU

Cài đặt `ls -a -l -R -S` bằng C11 trên Linux, tự đọc thư mục và metadata, không gọi chương trình `ls` để tạo kết quả.

## Build và chạy

Cần Linux hoặc Ubuntu WSL2, GCC và Make. Để chạy test cần thêm Bash, GNU coreutils, `diff` và Python 3. Trên Ubuntu:

```bash
sudo apt install build-essential coreutils diffutils python3
make
./myls
./myls -alRS /tmp
./myls -l -- -ten-tep
```

Cú pháp: `./myls [-alRS] [file...]`. Bỏ đường dẫn thì dùng thư mục hiện tại.

| Cờ | Tác dụng |
| --- | --- |
| `-a` | Hiện mục ẩn, kể cả `.` và `..`. |
| `-l` | In chi tiết quyền, links, owner/group, size, mtime và đích symlink. |
| `-R` | Duyệt thư mục con; không đi vào `.`, `..` hoặc symlink gặp trong cây. |
| `-S` | Size giảm dần; cùng size thì tên tăng dần. |

Mỗi tên một dòng khi không có `-l`; sắp tên theo byte (`LC_ALL=C`). Exit status: `0` thành công, `1` lỗi khi duyệt, `2` lỗi nghiêm trọng. `./myls --help` xem hướng dẫn.

## Kiểm tra và demo

```bash
make test       # GNU differential, helper nội bộ và đường lỗi
make sanitize   # Cùng suite với ASan/UBSan/LSan
make demo       # Demo bốn bước; fixture riêng trong /tmp
make dist       # Gói .tar và .tar.gz
```

Chạy bằng user thường để kiểm được quyền thư mục; suite báo SKIP nếu chạy root. `make clean` xóa binary, `build/` và gói nén. `make log` cập nhật lịch sử Git trong `LOG` khi chuẩn bị nộp.

## Tài liệu

- [Giải thích từ nền tảng đến triển khai](docs/TECHNICAL_DEEP_DIVE.md): đọc tuần tự 11 mục; có giới hạn hành vi và đường dẫn tới code.
- [Báo cáo Word](docs/BaoCao.docx), [PDF](docs/BaoCao.pdf), [Slides](docs/Slides.pptx).
- [Bảo trì và tái tạo tài liệu](docs/MAINTENANCE.md): thông tin nhóm, thu log, xuất Word/slides và đóng gói.
- [Kết quả thực nghiệm](evidence/test_results.json) và [checklist nộp bài](CHECKLIST.md).

Thông tin nhóm hiện còn ở chế độ bản thảo; cập nhật `docs/project_metadata.json` trước khi nộp.
