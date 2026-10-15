# `myls` — Tự Cài Đặt Lệnh `ls` (`-a`, `-l`, `-R`, `-S`) Bằng POSIX C

> **Học phần:** Lập trình Hệ thống (System Programming) – Trường Đại học Công nghệ Thông tin và Truyền thông Việt - Hàn (VKU)  
> **Đề tài 17:** Implement `ls` with `-a`, `-l`, `-R`, `-S`  
> **Sinh viên thực hiện:** Nguyễn Xuân Lĩnh  
> **Môi trường chuẩn:** Linux (Ubuntu 24.04 LTS / WSL2) · `gcc 13.3.0` · Chuẩn `C11` + `POSIX.1-2008` (`_XOPEN_SOURCE=700`)

---

## Mục Lục Nhanh

1. [Tổng quan Bài toán: `myls` làm gì và tại sao không dùng `system("ls")`?](#1-tổng-quan-bài-toán-myls-làm-gì-và-tại-sao-không-dùng-systemls)
2. [Giải thích từ gốc đến ngọn (Đánh số tuần tự 1 → 8: Tại sao A bắt buộc phải dùng B?)](#2-giải-thích-từ-gốc-đến-ngọn-đánh-số-tuần-tự-1--8-tại-sao-a-bắt-buộc-phải-dùng-b)
3. [Cấu trúc Thư mục Dự án](#3-cấu-trúc-thư-mục-dự-án)
4. [Hướng dẫn Biên dịch, Chạy Demo & Kiểm thử trên Ubuntu / WSL2](#4-hướng-dẫn-biên-dịch-chạy-demo--kiểm-thử-trên-ubuntu--wsl2)
5. [Bảng Đối chiếu các Lời gọi Hệ thống (System Calls) & Thư viện POSIX](#5-bảng-đối-chiếu-các-lời-gọi-hệ-thống-system-calls--thư-viện-posix)
6. [Giới hạn Kỹ thuật Hiện tại (Known Boundaries)](#6-giới-hạn-kỹ-thuật-hiện-tại-known-boundaries)

---

## 1. Tổng quan Bài toán: `myls` làm gì và tại sao không dùng `system("ls")`?

Trong Linux, `ls` là công cụ liệt kê nội dung thư mục. Ở môn **Lập trình Hệ thống**, mục tiêu của Đề tài 17 là tự viết chương trình `./myls` bằng ngôn ngữ C hỗ trợ 4 tùy chọn cốt lõi (đứng riêng hoặc kết hợp tự do như `-alRS`):

| Cờ (Option) | Chức năng | Cơ chế Hệ thống Cốt lõi |
| :--- | :--- | :--- |
| **`-a`** | Hiển thị **tất cả** entry, bao gồm tệp/thư mục ẩn bắt đầu bằng dấu `.` (như `.`, `..`, `.env`) | Không bỏ qua các entry có `d_name[0] == '.'` khi đọc `readdir()` |
| **`-l`** | Hiển thị **danh sách chi tiết** (Long format): loại tệp, 9 bit quyền + `SUID/SGID/Sticky`, số hard link, tên chủ sở hữu, tên nhóm, kích thước (bytes), thời gian sửa đổi và đích của symlink | Đọc siêu dữ liệu từ Inode bằng `lstat()`, giải mã `st_mode`, tra cứu `getpwuid()`/`getgrgid()`, định dạng `localtime_r()` và đọc symlink bằng `readlink()` |
| **`-R`** | Duyệt **đệ quy** (Recursive) vào toàn bộ các thư mục con nhiều tầng | Tiền thứ tự (*Pre-order*): liệt kê hết thư mục hiện tại rồi mới đệ quy xuống các thư mục con thật (`S_ISDIR`), loại trừ `.`, `..` và symlink |
| **`-S`** | Sắp xếp các entry theo **kích thước tệp giảm dần** (từ lớn nhất đến nhỏ nhất) | Dùng `qsort()` so sánh trường `st_size` (`off_t` 64-bit), nếu bằng nhau thì phân định thứ tự phụ (tie-break) bằng tên ASCII (`strcmp`) |

> [!IMPORTANT]
> **Tại sao tuyệt đối không gọi `system("ls")`?**  
> Gọi `system("ls")` chỉ là nhờ shell chạy hộ chương trình có sẵn của hệ điều hành chứ không can thiệp vào hệ thống tệp. Chương trình `myls` trong dự án này giao tiếp trực tiếp với nhân Linux (Linux Kernel VFS) thông qua các POSIX System Calls (`lstat`, `readlink`) và thư viện chuẩn (`opendir`, `readdir`, `closedir`).

---

## 2. Giải thích từ gốc đến ngọn (Đánh số tuần tự 1 → 8: Tại sao A bắt buộc phải dùng B?)

Dưới đây là chuỗi giải thích tuần tự từng bước từ cơ bản nhất (dành cho người chưa biết gì về Linux) đến các quyết định kỹ thuật chuyên sâu trong mã nguồn:

```mermaid
flowchart LR
    D["1. Thư mục (Directory)<br/>Chỉ lưu: Tên file -> Số Inode"] -->|readdir()| N["2. Biết được Tên file<br/>(d_name)"]
    N -->|join_path() + lstat()| I["3. Đọc bảng Inode<br/>(Quyền, Chủ sở hữu, Size, Giờ)"]
    I -->|qsort()| S["4. Sắp xếp danh sách<br/>(-S theo Size hoặc A-Z)"]
    S -->|display_entries()| P["5. Giải mã Bit & Căn cột<br/>In ra màn hình"]
    P -->|Nếu bật -R| R["6. Đệ quy xuống thư mục con<br/>(Bỏ qua '.', '..' và Symlink)"]
```

### Bước 1: Tại sao chỉ gọi `readdir()` thì KHÔNG THỂ làm được cờ `-l` và `-S`?
- **Bản chất cơ bản:** Nhiều người lầm tưởng một "thư mục" (Directory) chứa toàn bộ thông tin của tệp. Thực tế trong hệ thống tệp Linux (ext4), **Thư mục chỉ là một cuốn danh bạ mỏng** gồm 2 cột: `Tên tệp (d_name)` $\leftrightarrow$ `Mã số định danh Inode (d_ino)`.
- **Hệ quả:** Khi gọi `readdir()`, hệ điều hành chỉ trả về tên tệp (ví dụ `"main.c"`). Nó **không hề biết** tệp đó nặng bao nhiêu byte, của ai, hay có quyền `rwx` như thế nào.
- **Giải pháp bắt buộc:** Toàn bộ thông tin về kích thước (`st_size`), quyền hạn (`st_mode`), chủ sở hữu (`st_uid`) nằm ở một vùng dữ liệu riêng gọi là **Inode**. Vì vậy, sau khi lấy được tên tệp từ `readdir()`, chương trình bắt buộc phải ghép đường dẫn đầy đủ (`join_path`) rồi gọi tiếp hàm hệ thống **`lstat()`** để lấy thông tin từ Inode.

### Bước 2: Tại sao bắt buộc phải dùng `lstat()` mà KHÔNG ĐƯỢC dùng `stat()`?
- **Bản chất cơ bản:** Trong Linux có loại tệp đặc biệt gọi là **Symbolic Link (Symlink)** — giống như một "shortcut" trỏ sang tệp hoặc thư mục khác.
- **Tại sao `stat()` gây lỗi?** Hàm `stat()` tự động đi xuyên qua symlink để đọc tệp đích. Điều này gây ra **2 thảm họa**:
  1. Nếu tệp đích đã bị xóa (*Broken Symlink*), `stat()` trả về lỗi `No such file or directory` khiến chương trình không thể hiển thị được symlink đó.
  2. Nếu có một symlink trỏ ngược lên thư mục cha (`ln -s .. loop_link`), `stat()` sẽ báo đó là một thư mục thật (`S_ISDIR`). Khi chạy đệ quy `-R`, chương trình sẽ đi vào `loop_link` và **lặp vô hạn đến khi treo máy**!
- **Giải pháp của `myls`:** Dùng **`lstat()`** ([src/directory.c](file:///p:/DoAn_Laptrinhhethong/src/directory.c#L126-L150)). Hàm này đọc thông tin của **chính bản thân symlink** (`S_ISLNK`), giúp:
  - Vẫn hiển thị được broken symlink bình thường.
  - Nhận diện chính xác đây là symlink để gọi `readlink()` lấy đường dẫn đích in ra kiểu `latest_data.lnk -> dataset_large.bin`.
  - Khi duyệt đệ quy `-R`, loại trừ hoàn toàn symlink để không bao giờ bị lặp vô hạn.

### Bước 3: Tại sao phải dùng Mảng động (`EntryList` với `realloc`) thay vì mảng cố định `FileEntry list[1000]`?
- **Tại sao mảng tĩnh sai?** Nếu khai báo cứng `FileEntry list[1000]`, khi gặp thư mục nhỏ (3 tệp) thì lãng phí bộ nhớ, nhưng khi gặp thư mục lớn (như `/usr/bin` có hơn 2.000 tệp) thì chương trình sẽ bị tràn mảng (*Buffer Overflow*) hoặc bỏ sót tệp. Also, để sắp xếp được toàn bộ tệp bằng `-S` hoặc căn lề các cột trong `-l` thẳng hàng nhau, chương trình **bắt buộc phải đọc hết toàn bộ tệp của thư mục đó vào bộ nhớ trước, rồi mới sắp xếp và in**.
- **Giải pháp của `myls`:** Thiết kế cấu trúc `EntryList` ([include/myls.h](file:///p:/DoAn_Laptrinhhethong/include/myls.h#L47-L56)) khởi tạo với sức chứa `capacity = 64` và tự động nhân đôi (`capacity * 2`) bằng `realloc()` mỗi khi đầy ([src/directory.c](file:///p:/DoAn_Laptrinhhethong/src/directory.c#L48-L60)).

### Bước 4: Tại sao phải gọi `closedir()` NGAY TRƯỚC KHI đệ quy `-R` xuống thư mục con?
- **Tại sao đóng muộn lại nguy hiểm?** Mỗi khi gọi `opendir()`, nhân Linux cấp cho chương trình 1 **File Descriptor (FD)**. Một tiến trình thường chỉ được phép mở tối đa `1024` FD cùng lúc (`ulimit -n`). Nếu vừa `readdir()` vừa gọi đệ quy ngay trong vòng lặp mà chưa `closedir()`, các thư mục cha vẫn giữ FD mở trên ngăn xếp. Với cây thư mục sâu hoặc lớn, chương trình sẽ chạm trần `Too many open files (EMFILE)`.
- **Giải pháp của `myls`:** Trong `process_directory()` ([src/directory.c](file:///p:/DoAn_Laptrinhhethong/src/directory.c#L170-L234)), chương trình đọc hết tên tệp vào `EntryList`, **gọi `closedir(dir)` ngay lập tức**, sau đó mới sắp xếp, in kết quả và gọi đệ quy. Nhờ vậy, tại bất kỳ thời điểm nào, toàn bộ chương trình chỉ mở **tối đa 1 File Descriptor duy nhất**.

### Bước 5: Tại sao khi chạy `./myls -aR` phải có chốt chặn chặn riêng `.` và `..`?
- **Tại sao dễ lặp vô hạn?** Mọi thư mục trong Linux đều có 2 mục ẩn đặc biệt: `.` (trỏ vào chính thư mục hiện tại) và `..` (trỏ lên thư mục cha). Khi không bật `-a`, chúng bị bỏ qua vì bắt đầu bằng dấu chấm. Nhưng khi người dùng gõ `./myls -aR` (vừa hiện file ẩn `-a`, vừa đệ quy `-R`), cả `.` và `..` đều nằm trong danh sách và đều là thư mục thật (`S_ISDIR == true`).
- **Giải pháp của `myls`:** Hàm `is_recursible_subdir()` ([src/directory.c](file:///p:/DoAn_Laptrinhhethong/src/directory.c#L152-L168)):
  1. Phải là thư mục thật (`S_ISDIR(entry->st.st_mode)`).
  2. Tên **khác `"."`** và **khác `".."`**.
  Chỉ khi thỏa mãn đồng thời cả hai điều kiện thì mới gọi đệ quy.

### Bước 6: Tại sao trong hàm sắp xếp `-S` (`qsort`) không được viết `return b->size - a->size`?
- **Tại sao phép trừ gây lỗi ngầm?** Kích thước tệp `st_size` có kiểu `off_t` — trên hệ điều hành 64-bit, nó là số nguyên **64-bit** (lên tới hàng Exabyte). Trong khi đó, hàm so sánh của `qsort()` có kiểu trả về là `int` (**32-bit**, tối đa $\approx 2.14\text{ tỷ}$ byte $\approx 2\text{ GB}$). Nếu lấy kích thước tệp $3\text{ GB}$ trừ đi tệp $0\text{ B}$ rồi ép kiểu về `int` 32-bit, số dương sẽ bị **tràn bit dấu (Integer Overflow)** biến thành số âm, làm tệp $3\text{ GB}$ bị đẩy xuống cuối danh sách!
- **Giải pháp của `myls`:** Trong `cmp_by_size_desc()` ([src/sorting.c](file:///p:/DoAn_Laptrinhhethong/src/sorting.c#L32-L46)), so sánh trực tiếp bằng toán tử `>` (trả về `-1`) và `<` (trả về `1`). Khi hai tệp có kích thước bằng nhau (`==`), gọi tiếp `strcmp(a->name, b->name)` để phân định thứ tự phụ theo bảng chữ cái giống hệt GNU `ls`.

### Bước 7: Tại sao 10 ký tự quyền trong `-l` đôi khi xuất hiện chữ `s`, `S`, `t`, `T` thay vì `x`? Và tại sao dòng `total` phải chia đôi `st_blocks`?
- **Giải mã 16-bit `st_mode` ([src/display.c](file:///p:/DoAn_Laptrinhhethong/src/display.c#L37-L90)):**
  Ngoài 9 bit quyền cơ bản `rwxrwxrwx`, Linux còn có 3 bit quyền đặc biệt:
  - **SUID (`04000`)** ở vị trí thực thi của User: hiển thị `'s'` (nếu có quyền `'x'`) hoặc `'S'` (nếu không có `'x'`).
  - **SGID (`02000`)** ở vị trí thực thi của Group: hiển thị `'s'` hoặc `'S'`.
  - **Sticky Bit (`01000`)** ở vị trí thực thi của Others (rất phổ biến ở thư mục `/tmp` có quyền `drwxrwxrwt`): hiển thị `'t'` (nếu có `'x'`) hoặc `'T'` (nếu không có `'x'`).
- **Tại sao `total = sum(st_blocks) / 2`?**
  Theo chuẩn POSIX, trường `st_blocks` trong `struct stat` luôn đếm số khối đĩa theo đơn vị **512 bytes**. Trong khi đó, lệnh `ls -l` của GNU hiển thị dòng `total` ở đầu thư mục theo đơn vị **1024 bytes (1 KB)**. Do đó phải chia tổng `st_blocks` cho `2` ([src/display.c](file:///p:/DoAn_Laptrinhhethong/src/display.c#L194-L197)) mới ra đúng con số của GNU `ls`.

### Bước 8: Tại sao khi kiểm thử trên WSL2 phải tạo dữ liệu test trong `/tmp` thay vì `/mnt/p`?
- **Bản chất WSL2:** Ổ đĩa Windows `P:\` khi gắn vào Ubuntu WSL2 tại `/mnt/p` sử dụng trình điều khiển `DrvFs` (chuyển tiếp sang NTFS của Windows). Vì NTFS không dùng hệ thống quyền POSIX của Linux nên mọi tệp trên `/mnt/p` đều bị hiển thị giả lập thành `rwxrwxrwx` (`0777`), lệnh `chmod 0000` hay `chmod 4755` không có tác dụng thật.
- **Giải pháp thực nghiệm chuẩn:** Script `tests/run_tests.sh` tự động tạo thư mục kiểm thử trong `/tmp/myls_test_XXXXXX` — đây là hệ thống tệp gốc của nhân Linux trong WSL2. Tại đây, mọi bit quyền `SUID`, `SGID`, `Sticky bit`, `chmod 0000`, hard link, broken symlink và `st_blocks` đều hoạt động chuẩn xác 100% như trên máy chủ Ubuntu vật lý.

---

## 3. Cấu trúc Thư mục Dự án

```text
vku-system-programming-ls/
├── src/                        # Mã nguồn C chia làm 5 module độc lập
│   ├── main.c                  # Điểm vào, phân tách đối số tệp đơn lẻ vs thư mục
│   ├── options.c               # Phân tích cờ -a, -l, -R, -S bằng getopt()
│   ├── directory.c             # Quản lý EntryList động, lstat/readlink và đệ quy -R
│   ├── sorting.c               # Sắp xếp qsort() theo tên ASCII và kích thước -S
│   └── display.c               # Giải mã st_mode, UID/GID, mtime 6 tháng, căn cột -l
├── include/
│   └── myls.h                  # Định nghĩa struct và giao diện hàm giữa các module
├── tests/
│   ├── run_tests.sh            # Bộ kiểm thử tự động 15 kịch bản đối chiếu GNU ls
│   └── run_demo.sh             # Kịch bản chạy demo tự động và trích xuất minh chứng
├── docs/
│   ├── TECHNICAL_DEEP_DIVE.md  # Tài liệu giải phẫu chi tiết từng dòng code & thuật toán
│   ├── BaoCao.docx             # Báo cáo học thuật chuẩn VKU (Word)
│   ├── BaoCao.pdf              # Báo cáo học thuật chuẩn VKU (PDF)
│   └── Slides.pptx             # Slide thuyết trình nền sáng, đa dạng bố cục
├── evidence/                   # Minh chứng chạy thực tế trên Ubuntu 24.04 WSL2
│   ├── demo_session_output.txt
│   ├── test_suite_report.txt
│   └── memory_sanitizer_report.txt
├── Makefile                    # Tự động hóa build, test, demo, log, dist
├── CHECKLIST.md                # Bảng đối chiếu nghiệm thu toàn bộ yêu cầu đề tài
├── LOG                         # Lịch sử commit Git xuất tự động qua `make log`
└── .gitignore
```

---

## 4. Hướng dẫn Biên dịch, Chạy Demo & Kiểm thử trên Ubuntu / WSL2

### 4.1. Quy trình chuẩn (Clone -> Build -> Demo -> Test)

Mở terminal Ubuntu (hoặc WSL2 trên Windows) và chạy:

```bash
# 1. Clone kho mã nguồn và di chuyển vào thư mục dự án
git clone https://github.com/Xlinhx/DoAn_LapTrinhHethong.git vku-system-programming-ls
cd vku-system-programming-ls

# 2. Dọn sạch và biên dịch với cờ nghiêm ngặt (-Wall -Wextra -Werror -pedantic)
make clean
make

# 3. Chạy thử từng tùy chọn và tổ hợp tùy chọn
./myls
./myls -a
./myls -l
./myls -R
./myls -S
./myls -alRS

# 4. Chạy bộ kiểm thử tự động 15 kịch bản đối chiếu 1:1 với GNU ls
make test

# 5. Đóng gói bản nộp (.tar và .tar.gz kèm lịch sử Git LOG)
make dist
```

---

## 5. Bảng Đối chiếu các Lời gọi Hệ thống (System Calls) & Thư viện POSIX

| Hàm API / System Call | Thư viện Header | Vị trí sử dụng | Mục đích trong `myls` |
| :--- | :--- | :--- | :--- |
| `getopt()` | `<unistd.h>` | [src/options.c](file:///p:/DoAn_Laptrinhhethong/src/options.c#L60) | Tách các cờ `-a`, `-l`, `-R`, `-S` (hỗ trợ viết rời hoặc viết gộp `-alRS`) |
| `opendir()` | `<dirent.h>` | [src/directory.c](file:///p:/DoAn_Laptrinhhethong/src/directory.c#L173) | Mở luồng đọc thư mục (`DIR *`) từ đường dẫn |
| `readdir()` | `<dirent.h>` | [src/directory.c](file:///p:/DoAn_Laptrinhhethong/src/directory.c#L192) | Đọc tuần tự từng `struct dirent` để lấy tên entry `d_name` |
| `closedir()` | `<dirent.h>` | [src/directory.c](file:///p:/DoAn_Laptrinhhethong/src/directory.c#L213) | Đóng luồng thư mục ngay trước khi đệ quy để giải phóng File Descriptor |
| `lstat()` | `<sys/stat.h>` | [src/directory.c](file:///p:/DoAn_Laptrinhhethong/src/directory.c#L129) | Đọc Inode của tệp/thư mục/symlink mà không đi xuyên qua symlink |
| `stat()` | `<sys/stat.h>` | [src/main.c](file:///p:/DoAn_Laptrinhhethong/src/main.c#L43) | Kiểm tra đích của symlink truyền trực tiếp trên CLI khi không bật `-l` |
| `readlink()` | `<unistd.h>` | [src/directory.c](file:///p:/DoAn_Laptrinhhethong/src/directory.c#L139) | Đọc đường dẫn đích của Symbolic Link để in `-> target` trong `-l` |
| `getpwuid()` | `<pwd.h>` | [src/display.c](file:///p:/DoAn_Laptrinhhethong/src/display.c#L94) | Ánh xạ mã số `st_uid` sang tên người dùng (`pw_name`) |
| `getgrgid()` | `<grp.h>` | [src/display.c](file:///p:/DoAn_Laptrinhhethong/src/display.c#L104) | Ánh xạ mã số `st_gid` sang tên nhóm (`gr_name`) |
| `localtime_r()` | `<time.h>` | [src/display.c](file:///p:/DoAn_Laptrinhhethong/src/display.c#L131) | Chuyển đổi `st_mtime` (`time_t`) sang `struct tm` an toàn luồng |
| `qsort()` | `<stdlib.h>` | [src/sorting.c](file:///p:/DoAn_Laptrinhhethong/src/sorting.c#L54) | Sắp xếp mảng động `EntryList` với độ phức tạp $O(N \log N)$ |

---

## 6. Giới hạn Kỹ thuật Hiện tại (Known Boundaries)

Để đảm bảo tính trung thực học thuật, chương trình xác định rõ phạm vi đã cài đặt và các giới hạn so với bản thương mại đầy đủ của GNU `coreutils ls`:
1. **Quy tắc sắp xếp theo Locale (`LC_COLLATE`):** `myls` sử dụng `strcmp()` chuẩn C (sắp xếp theo mã ASCII, tương đương `LC_ALL=C ls`), không sử dụng `strcoll()` phụ thuộc vào từ điển ngôn ngữ vùng miền.
2. **Danh sách kiểm soát truy cập mở rộng (POSIX ACL & SELinux):** Chuỗi quyền hiển thị 10 ký tự chuẩn POSIX (`drwxr-xr-x`), chưa kiểm tra ký tự thứ 11 (`+` cho `getxattr` ACL hoặc `.` cho SELinux security context).
3. **Định dạng khi không có `-l`:** Xuất 1 entry trên mỗi dòng (tương đương hành vi chuẩn của `ls` khi kết nối qua đường ống `pipe` hoặc `ls -1`), giúp đầu ra nhất quán trên mọi kích thước cửa sổ terminal.
