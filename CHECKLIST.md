# CHECKLIST NGHIỆM THU ĐỒ ÁN – ĐỀ TÀI 17 (`myls -a -l -R -S`)

Bảng kiểm tra đối chiếu toàn bộ yêu cầu kỹ thuật, kiểm thử, tài liệu và đóng gói của dự án.

## 1. Yêu cầu Chức năng Cốt lõi (Core Functional Requirements)

- [x] **Liệt kê mặc định (`./myls`)**: Liệt kê các tệp/thư mục không ẩn trong thư mục hiện tại (hoặc đường dẫn chỉ định), sắp xếp tăng dần theo bảng mã ASCII.
- [x] **Tùy chọn `-a` (`./myls -a`)**: Hiển thị đầy đủ các mục ẩn bắt đầu bằng dấu `.` (bao gồm `.`, `..`, và các tệp cấu hình ẩn).
- [x] **Tùy chọn `-l` (`./myls -l`)**:
  - [x] In dòng `total <1K-blocks>` chuẩn xác (`sum(st_blocks) / 2`) ở đầu mỗi thư mục.
  - [x] Giải mã đủ 7 loại tệp (`-`, `d`, `l`, `c`, `b`, `p`, `s`) và 9 bit quyền `rwx`.
  - [x] Giải mã chính xác 3 bit đặc biệt: `SUID` (`s`/`S`), `SGID` (`s`/`S`), `Sticky bit` (`t`/`T`).
  - [x] Hiển thị số lượng hard link (`st_nlink`), tên Owner (`getpwuid`), tên Group (`getgrgid`), kích thước tệp (`st_size`).
  - [x] Hiển thị thời gian sửa đổi (`st_mtime`) theo đúng quy tắc 6 tháng (`Tháng Ngày Giờ:Phút` hoặc `Tháng Ngày  Năm`).
  - [x] Hiển thị đích của Symbolic Link (`name -> target`) qua `readlink()`.
  - [x] Tự động tính độ rộng lớn nhất của từng cột để căn lề thẳng hàng tuyệt đối.
- [x] **Tùy chọn `-R` (`./myls -R`)**:
  - [x] Duyệt đệ quy toàn bộ cây thư mục con theo thứ tự đã sắp xếp.
  - [x] Chặn tuyệt đối `.` và `..` (kể cả khi bật kèm `-a`) để không lặp vô hạn.
  - [x] Không đi xuyên qua Symbolic Link trỏ tới thư mục khi đệ quy.
  - [x] Đóng `closedir()` ngay trước khi đệ quy xuống thư mục con để không rò rỉ File Descriptor.
- [x] **Tùy chọn `-S` (`./myls -S`)**:
  - [x] Sắp xếp giảm dần theo kích thước tệp (`st_size`) an toàn với kiểu 64-bit `off_t`.
  - [x] Phân định thứ tự phụ (tie-break) bằng tên tệp (`strcmp`) khi hai tệp có cùng kích thước.
- [x] **Kết hợp tùy chọn tự do (`-alRS`, `-la`, `-lS`, `-aR`...)**: Hoạt động chính xác ở mọi thứ tự kết hợp cờ.

## 2. Yêu cầu Kỹ thuật & Độ Bền Vững (Robustness & System Programming)

- [x] **100% POSIX System Calls & Libc APIs**: Không sử dụng `system("ls")` hay `popen()`.
- [x] **Cấp phát bộ nhớ động hoàn toàn (`EntryList`)**: Không giới hạn cứng số lượng tệp trong thư mục; giải phóng sạch 100% bộ nhớ (`0 bytes leaked` xác thực qua AddressSanitizer/LeakSanitizer).
- [x] **Xử lý lỗi chuẩn POSIX**:
  - [x] Đường dẫn không tồn tại: báo lỗi `stderr`, trả về mã thoát `1`.
  - [x] Thư mục con bị khóa quyền đọc (`chmod 000`): báo lỗi `stderr`, trả về mã thoát `1`, vẫn tiếp tục duyệt các thư mục còn lại.
  - [x] Cờ không hợp lệ (`-z`): báo lỗi `stderr`, in hướng dẫn sử dụng, trả về mã thoát `2`.
- [x] **Biên dịch sạch tuyệt đối**: `gcc -Wall -Wextra -Werror -pedantic -std=c11` đạt `0 warnings, 0 errors`.

## 3. Kiểm thử, Tài liệu & Đóng gói Nộp bài (Testing, Docs & Submission)

- [x] **Bộ kiểm thử tự động (`tests/run_tests.sh`)**: 15/15 kịch bản PASS tuyệt đối khi `diff -u` với `LC_ALL=C ls` của GNU coreutils 9.4 trên hệ thống tệp Linux `/tmp`.
- [x] **Minh chứng thực tế (`evidence/`)**: Có log phiên chạy demo (`demo_session_output.txt`), báo cáo kiểm thử (`test_suite_report.txt`), báo cáo bộ nhớ (`memory_sanitizer_report.txt`) và ảnh chụp minh chứng.
- [x] **Báo cáo học thuật (`docs/BaoCao.docx` & `docs/BaoCao.pdf`)**: Trình bày tuần tự, rõ ràng, giải thích nhân-quả từ cơ bản đến chuyên sâu.
- [x] **Slide thuyết trình (`docs/Slides.pptx`)**: Thiết kế nền sáng, 12 bố cục đa dạng, ít chữ, hình minh họa tách nền trong suốt, đã qua kiểm tra thị giác.
- [x] **Lịch sử Git (`LOG`) & Gói nộp (`make dist`)**: Đóng gói đầy đủ `.tar` / `.tar.gz` và đồng bộ lên GitHub repository `https://github.com/Xlinhx/DoAn_LapTrinhHethong`.
