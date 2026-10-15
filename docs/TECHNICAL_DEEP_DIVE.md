# GIẢI PHẪU KỸ THUẬT TUẦN TỰ (TỪ CƠ BẢN ĐẾN CHUYÊN SÂU): `myls` (`-a`, `-l`, `-R`, `-S`)

Tài liệu này được thiết kế theo phương pháp **Chuỗi Nhân - Quả Đánh Số Tuần Tự ($1 \rightarrow 2 \rightarrow 3\dots$)**. Ngay cả khi bạn chưa từng học về nhân hệ điều hành Linux, chỉ cần đọc lần lượt từ số `1` đến số `16`, bạn sẽ hiểu trọn vẹn **tại sao từng dòng code C lại bắt buộc phải viết như vậy**.

---

## PHẦN I: NỀN TẢNG GỐC RỄ (3 Sự Thật Về Hệ Thống Tệp Linux)

Trước khi đọc code, hãy nắm vững 3 sự thật cơ bản nhất về cách Linux lưu trữ tệp trên đĩa cứng:

### 1. Sự thật số 1: "Thư mục" (Directory) KHÔNG chứa nội dung hay thông tin chi tiết của tệp
- **Ví dụ đời thực:** Hãy tưởng tượng một **Danh bạ điện thoại**. Danh bạ chỉ ghi: `"Nguyễn Văn A -> Số căn cước 1052"`. Danh bạ **không hề ghi** ông A cao bao nhiêu, nặng bao nhiêu, sinh ngày nào. Muốn biết thông tin đó, bạn phải cầm số căn cước `1052` tra vào **Hồ sơ gốc**.
- **Trong Linux:**
  - **Thư mục (Directory)** chính là cuốn danh bạ mỏng đó. Mỗi dòng trong thư mục được gọi là một **Dentry (`struct dirent`)**, chỉ lưu đúng 2 thứ: **Tên tệp (`d_name`)** và **Mã số hồ sơ (`d_ino` - Inode Number)**.
  - **Bảng Inode (`struct stat`)** mới là **Hồ sơ gốc** nằm trên ổ đĩa. Inode lưu: tệp này nặng bao nhiêu byte (`st_size`), thuộc về ai (`st_uid`, `st_gid`), ai được quyền đọc/ghi/chạy (`st_mode`), sửa lần cuối lúc nào (`st_mtime`), chiếm bao nhiêu khối đĩa (`st_blocks`).

```text
+-----------------------------------+          +---------------------------------------------+
|   THƯ MỤC (Đọc bằng readdir)      |          |      BẢNG INODE (Đọc bằng lstat)            |
+-----------------------------------+          +---------------------------------------------+
| d_name: "main.c"  | d_ino: #40912 | -------> | Inode #40912:                               |
| d_name: ".env"    | d_ino: #40915 |          | - Loại & Quyền (st_mode): -rwxr-xr-x        |
| d_name: "docs"    | d_ino: #40920 |          | - Số tên cùng trỏ vào (st_nlink): 1         |
+-----------------------------------+          | - Chủ sở hữu (st_uid): 1000 (linhnx)        |
                                               | - Kích thước (st_size): 8192 bytes          |
                                               | - Sửa lần cuối (st_mtime): Oct 16 01:41     |
                                               +---------------------------------------------+
```

- **Tại sao điều này quyết định cách viết code?**
  - Nếu người dùng chỉ gõ `./myls` (in tên tệp): về lý thuyết chỉ cần đọc "Danh bạ" (`readdir()`).
  - Nhưng nếu người dùng gõ `./myls -l` (in chi tiết) hoặc `./myls -S` (sắp xếp theo kích thước tệp): cái tên tệp từ `readdir()` **không có kích thước và quyền hạn**! Vì vậy, chương trình **bắt buộc phải gọi thêm hàm `lstat()`** để mở "Hồ sơ gốc" (Inode) của từng tệp ra đọc.

---

### 2. Sự thật số 2: Sự khác biệt sống còn giữa Hard Link và Symbolic Link
- **Hard Link (Liên kết cứng):** Là việc tạo thêm một dòng tên mới trong Danh bạ nhưng **cùng chỉ vào một Mã số Inode gốc**. Khi đó con số `st_nlink` (số tên cùng trỏ vào Inode đó) tăng lên `2`. Xóa 1 tên thì tệp gốc vẫn còn nguyên.
- **Symbolic Link (Liên kết mềm / Symlink):** Là một tệp hoàn toàn mới (có Inode riêng mang ký hiệu `'l'`), bên trong chỉ chứa một chuỗi văn bản là **đường dẫn trỏ sang tệp/thư mục khác** (giống Shortcut trên Windows).
- **Tại sao điều này dẫn đến quyết định chọn `lstat()` thay vì `stat()`?**
  - Linux cung cấp 2 hàm đọc Inode: `stat()` và `lstat()`.
  - **`stat(path)`:** Nếu `path` là một Symlink, `stat()` sẽ tự động nhảy sang đọc tệp đích.
    - *Hậu quả 1:* Nếu tệp đích đã bị xóa (*Broken Symlink*), `stat()` báo lỗi không tìm thấy và làm chương trình bỏ sót chính cái Symlink đang nằm sờ sờ trong thư mục!
    - *Hậu quả 2:* Nếu Symlink trỏ vào một thư mục cha (`ln -s .. loop`), `stat()` báo đó là một thư mục thật. Khi bật cờ đệ quy `-R`, chương trình sẽ chui vào `loop` $\rightarrow$ quay lại thư mục cha $\rightarrow$ chui vào `loop` $\rightarrow$ **lặp vô hạn đến khi sập chương trình**!
  - **`lstat(path)`:** Không nhảy sang đích mà đọc trực tiếp Inode của chính cái Symlink đó. Nhờ vậy, `myls` biết ngay đây là Symlink (`S_ISLNK`), vẫn hiển thị được Broken Symlink, dùng thêm `readlink()` để lấy tên đích in ra sau mũi tên `->`, và **tuyệt đối không đệ quy `-R` vào bên trong Symlink**.

---

### 3. Sự thật số 3: Tại sao không được vừa đọc thư mục vừa in ngay ra màn hình?
- **Vấn đề:** Hàm `readdir()` trả về các tệp theo thứ tự lưu trữ thô trên ổ đĩa (lộn xộn, không theo bảng chữ cái và cũng không theo kích thước).
- **Hệ quả:**
  1. Muốn sắp xếp từ A $\rightarrow$ Z hoặc sắp xếp từ tệp nặng nhất đến nhẹ nhất (`-S`), bạn **phải biết mặt toàn bộ các tệp trong thư mục đó trước** rồi mới so sánh được tệp nào đứng đầu.
  2. Trong chế độ `-l`, các cột (Số link, Chủ sở hữu, Kích thước) phải **căn lề thẳng hàng từ trên xuống dưới**. Nếu tệp thứ 1 nặng `12` bytes (2 chữ số), nhưng tệp thứ 50 nặng `1048576` bytes (7 chữ số), bạn phải đọc hết cả 50 tệp mới biết cột kích thước cần chừa trống `7` ký tự!
- **Quyết định thiết kế bắt buộc:** Phải mengikuti quy trình 3 pha cho mỗi thư mục:
  **Pha 1: Gom toàn bộ vào mảng động (`EntryList`)** $\rightarrow$ **Pha 2: Sắp xếp (`qsort`)** $\rightarrow$ **Pha 3: Tính độ rộng cột & Hiển thị (`display_entries`)**.

---

## PHẦN II: LUỒNG CHẠY 16 BƯỚC TUẦN TỰ TRONG MÃ NGUỒN `myls`

Dưới đây là hành trình chính xác từ lúc bạn gõ lệnh `./myls -alRS` trên Terminal cho đến khi chương trình kết thúc:

### Bước 1: Nhận tham số tại `main(argc, argv)` ([src/main.c](file:///p:/DoAn_Laptrinhhethong/src/main.c#L51))
Hệ điều hành trao cho hàm `main` mảng chuỗi `argv` (ví dụ `argv[0] = "./myls"`, `argv[1] = "-alRS"`, `argv[2] = "src"`).

### Bước 2: Bóc tách các cờ tùy chọn bằng `getopt()` ([src/options.c](file:///p:/DoAn_Laptrinhhethong/src/options.c#L60))
- **Tại sao dùng `getopt(argc, argv, "alRS")` mà không tự viết vòng lặp `if (strcmp(argv[i], "-a"))`?**
  - Vì người dùng Linux có quyền gõ cờ theo hàng chục cách khác nhau: gõ rời (`-a -l -R -S`), gõ gộp (`-alRS`, `-la`, `-SR`), hoặc dùng `--` để báo kết thúc phần cờ.
  - Tự viết `strcmp` sẽ thất bại ngay khi gặp `-alRS`. Hàm chuẩn POSIX `getopt()` giải quyết triệt để mọi cách gộp cờ chỉ trong 1 vòng lặp `while`.
- Nếu gặp một chữ cái lạ không nằm trong `"alRS"` (ví dụ `-z`), chương trình in lỗi ra luồng lỗi chuẩn `stderr` và trả về **mã thoát `2`** (`EXIT_LS_SERIOUS_ERR`).

### Bước 3: Xác định danh sách đường dẫn cần liệt kê ([src/main.c](file:///p:/DoAn_Laptrinhhethong/src/main.c#L62-L67))
- Sau khi `getopt()` chạy xong, biến toàn cục `optind` chỉ chính xác vào vị trí đường dẫn đầu tiên trong `argv`.
- **Tại sao phải kiểm tra `argc - optind == 0`?** Vì khi người dùng chỉ gõ `./myls` hoặc `./myls -l` mà không truyền tên thư mục nào, chương trình phải tự động lấy thư mục hiện tại `"."` làm mục tiêu mặc định.

### Bước 4: Kiểm tra sự tồn tại của từng đường dẫn đầu vào ([src/main.c](file:///p:/DoAn_Laptrinhhethong/src/main.c#L75-L83))
- Chương trình gọi `lstat()` trên từng đường dẫn người dùng truyền vào.
- **Tại sao khi 1 đường dẫn bị lỗi (ví dụ gõ nhầm tên file không tồn tại) chương trình KHÔNG `exit(1)` ngay lập tức?**
  - Giả sử người dùng gõ `./myls file_sai.txt thu_muc_dung`. Chuẩn POSIX quy định: báo lỗi cho `file_sai.txt` ra `stderr`, ghi nhớ trạng thái lỗi `exit_status = 1`, nhưng **vẫn phải tiếp tục liệt kê `thu_muc_dung`** cho người dùng!

### Bước 5: Phân loại đối số thành `file_list` và `dir_list` ([src/main.c](file:///p:/DoAn_Laptrinhhethong/src/main.c#L85-L99))
- **Tại sao phải tách riêng tệp đơn lẻ (`file_list`) và thư mục (`dir_list`)?**
  - Khi bạn gõ `ls main.c Makefile src include`, chuẩn `ls` luôn gom tất cả các tệp đơn lẻ (`Makefile`, `main.c`) in ra ở nhóm đầu tiên (và **không in dòng `total`**), sau đó mới xuống dòng in nội dung của từng thư mục (`include:`, `src:`).
- **Xử lý tinh tế cho Symlink trỏ tới thư mục trên dòng lệnh ([src/main.c](file:///p:/DoAn_Laptrinhhethong/src/main.c#L26-L49)):**
  - Nếu gõ `./myls symlink_to_dir` (không có `-l`): người dùng muốn xem bên trong thư mục đích $\rightarrow$ xếp vào `dir_list`.
  - Nếu gõ `./myls -l symlink_to_dir` (có `-l` và không có dấu `/` cuối): người dùng muốn xem thông tin của bản thân cái symlink $\rightarrow$ xếp vào `file_list` để in `symlink_to_dir -> alpha_dir`.

### Bước 6: Sắp xếp và hiển thị nhóm Tệp đơn lẻ trước ([src/main.c](file:///p:/DoAn_Laptrinhhethong/src/main.c#L104-L109))
- Nếu `file_list` có phần tử, gọi `sort_entries()` và `display_entries(..., is_directory_listing = false)`. Tham số `false` báo cho hàm hiển thị biết đây là các tệp rời nên không in dòng `total <blocks>`.

### Bước 7: Quyết định quy tắc in tiêu đề `<tên_thư_mục>:` ([src/main.c](file:///p:/DoAn_Laptrinhhethong/src/main.c#L114))
- **Tại sao lúc thì có dòng `.:`, lúc thì không?**
  - Khi chỉ duyệt 1 thư mục duy nhất và không đệ quy (`./myls` hoặc `./myls src`), GNU `ls` không in dòng tiêu đề để giao diện gọn gàng.
  - Nhưng khi bật đệ quy `-R` (có nhiều thư mục con) HOẶC khi người dùng truyền từ 2 đối số trở lên trên dòng lệnh (`num_paths > 1`), chương trình **bắt buộc phải in tiêu đề `<dir_path>:`** ở đầu mỗi thư mục để người đọc phân biệt được tệp nào thuộc thư mục nào.

### Bước 8: Mở thư mục bằng `opendir()` và xử lý lỗi quyền truy cập ([src/directory.c](file:///p:/DoAn_Laptrinhhethong/src/directory.c#L173-L180))
- Khi bước vào một thư mục trong `process_directory()`, chương trình gọi `opendir(dir_path)`.
- Nếu thư mục đó bị khóa quyền đọc (`chmod 0000`, `errno == EACCES`), `opendir()` trả về `NULL`. Chương trình in thông báo `myls: cannot open directory '...': Permission denied` lên `stderr`, đặt `exit_status = 1`, và quay lui an toàn để tiếp tục duyệt các thư mục khác.

### Bước 9: Đọc từng mục bằng `readdir()` và lọc tệp ẩn theo cờ `-a` ([src/directory.c](file:///p:/DoAn_Laptrinhhethong/src/directory.c#L192-L197))
- Vòng lặp `while ((de = readdir(dir)) != NULL)` lấy ra từng tên tệp `de->d_name`.
- **Quy tắc cờ `-a`:** Trong Linux, bất kỳ tệp/thư mục nào có ký tự đầu tiên là dấu chấm (`de->d_name[0] == '.'`) được quy ước là tệp ẩn.
  - Nếu `opts->opt_a == false`: gặp `de->d_name[0] == '.'` thì `continue` (bỏ qua ngay lập tức, không tốn công gọi `lstat`).
  - Nếu `opts->opt_a == true`: giữ lại toàn bộ (bao gồm cả `.`, `..`, `.gitignore`...).

### Bước 10: Ghép đường dẫn an toàn bằng `join_path()` ([src/directory.c](file:///p:/DoAn_Laptrinhhethong/src/directory.c#L104-L124))
- **Tại sao không được truyền thẳng `de->d_name` vào `lstat()`?**
  - Vì `de->d_name` chỉ là tên ngắn (ví dụ `"guide.md"`). Nếu chương trình đang đứng ở thư mục gốc nhưng đang duyệt thư mục con `"./docs_sub"`, gọi `lstat("guide.md")` sẽ tìm ở thư mục gốc và báo lỗi không tồn tại!
  - Do đó phải ghép thành `"./docs_sub/guide.md"`. Hàm `join_path()` còn kiểm tra xem `dir_path` đã có sẵn dấu `'/'` ở cuối chưa (như khi duyệt `"/"` hoặc `"src/"`) để tránh sinh ra hai dấu gạch chéo liền nhau `"//"` làm sai lệch kết quả đối chiếu với GNU `ls`.

### Bước 11: Thu thập Inode bằng `lstat()`, đọc đích Symlink bằng `readlink()` và đẩy vào Mảng động ([src/directory.c](file:///p:/DoAn_Laptrinhhethong/src/directory.c#L126-L150))
- Gọi `lstat(child_path, &st)` để nạp toàn bộ thông tin Inode vào `struct stat`.
- Nếu đang bật cờ `-l` **và** kiểm tra thấy `S_ISLNK(st.st_mode)` là đúng, gọi tiếp `readlink()` để đọc đường dẫn đích mà symlink trỏ tới.
  - **Lưu ý kỹ thuật cực kỳ quan trọng về `readlink()`:** Hàm `readlink()` của POSIX **KHÔNG tự động thêm ký tự kết thúc chuỗi `'\0'`** vào cuối mảng! Do đó sau khi nhận số byte đọc được `len`, code bắt buộc phải gán `link_buf[len] = '\0';` ([src/directory.c](file:///p:/DoAn_Laptrinhhethong/src/directory.c#L141)), nếu không khi in ra màn hình sẽ bị in kèm rác bộ nhớ (garbage bytes).
- Lưu phần tử vào `EntryList`. Nếu mảng đầy (`count >= capacity`), tự động nhân đôi kích thước bằng `realloc()`.

### Bước 12: Đóng thư mục bằng `closedir()` NGAY LẬP TỨC ([src/directory.c](file:///p:/DoAn_Laptrinhhethong/src/directory.c#L213))
- Ngay khi vòng lặp `readdir()` kết thúc, toàn bộ dữ liệu cần thiết đã nằm gọn trong bộ nhớ RAM (`EntryList`).
- Gọi `closedir(dir)` ngay tại dòng này (trước khi sắp xếp, trước khi in, và **trước khi gọi đệ quy `-R`**) để trả lại File Descriptor cho hệ điều hành. Nhờ vậy dù đệ quy sâu 500 tầng thư mục, chương trình cũng chỉ dùng đúng 1 File Descriptor tại một thời điểm!

### Bước 13: Sắp xếp danh sách bằng `qsort()` theo cờ `-S` hoặc Tên ([src/sorting.c](file:///p:/DoAn_Laptrinhhethong/src/sorting.c#L48-L59))
- **Khi không bật `-S`:** Dùng `cmp_by_name_asc` gọi `strcmp(a->name, b->name)` để sắp xếp tăng dần theo bảng mã ASCII.
- **Khi bật `-S`:** Dùng `cmp_by_size_desc`:
  1. So sánh `if (a->st.st_size > b->st.st_size) return -1;` (tệp lớn hơn đứng trước).
  2. So sánh `if (a->st.st_size < b->st.st_size) return 1;` (tệp nhỏ hơn đứng sau).
  3. **Tại sao không dùng phép trừ `b->st.st_size - a->st.st_size`?** Để tránh tràn số nguyên 32-bit `int` khi so sánh các tệp lớn hơn $2\text{ GB}$ (`off_t` 64-bit).
  4. **Tại sao khi bằng nhau phải gọi `return strcmp(a->name, b->name);`?** Nếu 2 tệp cùng nặng `512` bytes, thuật toán Quicksort (`qsort`) không đảm bảo giữ nguyên thứ tự ban đầu (unstable sort). Phân định thứ tự phụ (tie-break) bằng tên tệp giúp kết quả luôn cố định và khớp 100% với GNU `ls`.

### Bước 14: Giải mã Bit, Căn cột động và Hiển thị ra màn hình ([src/display.c](file:///p:/DoAn_Laptrinhhethong/src/display.c#L181-L234))
- **Nếu không bật `-l`:** Duyệt mảng đã sắp xếp và in từng tên tệp.
- **Nếu bật `-l`:**
  1. **Quét lượt 1 (`compute_column_widths`):** Tính tổng `total_blocks_512 += st.st_blocks` và tìm số chữ số dài nhất của cột `st_nlink`, độ dài chữ dài nhất của `owner`, `group`, và `st_size`.
  2. **In dòng `total`:** Đổi từ đơn vị khối 512-byte của nhân Linux sang đơn vị khối 1024-byte (1K) của GNU `ls` bằng phép chia `total_blocks_512 / 2`.
  3. **Giải mã 16-bit `st_mode` (`format_mode_string`):**

```text
Bit trường st_mode (16-bit):
[ 15..12: Loại tệp ] [ 11: SUID | 10: SGID | 9: Sticky ] [ 8..6: User ] [ 5..3: Group ] [ 2..0: Other ]
       |                              |                        |              |               |
       v                              +------------------------+--------------+---------------+
 Ký tự 0: '-', 'd', 'l'...                     Ký tự 1..9: rwxr-xr-x (hoặc s/S, t/T)
```

  4. **Định dạng thời gian 6 tháng (`format_mtime_string`):**
     So sánh `st_mtime` với thời gian hiện tại `now = time(NULL)`. Nếu $|\text{now} - \text{mtime}| < 6\text{ tháng}$ ($15.778.476\text{ giây}$), in `"Tháng Ngày Giờ:Phút"`; nếu cũ hơn 6 tháng, in `"Tháng Ngày  Năm"`.

### Bước 15: Duyệt đệ quy `-R` an toàn xuống các thư mục con ([src/directory.c](file:///p:/DoAn_Laptrinhhethong/src/directory.c#L222-L230))
- Khi `opts->opt_R == true`, chương trình duyệt lại danh sách `list` (lúc này đã được sắp xếp theo đúng thứ tự `-S` hoặc chữ cái).
- Với mỗi phần tử, hàm `is_recursible_subdir()` kiểm tra 3 chốt chặn an toàn:
  1. `lstat` thành công (`stat_ok == true`).
  2. Là thư mục thật (`S_ISDIR(e->st.st_mode)` — tự động loại bỏ Symlink vì Symlink có mode `S_ISLNK`).
  3. Tên khác `"."` và khác `".."` (`strcmp(e->name, ".") != 0 && strcmp(e->name, "..") != 0`).
- Nếu vượt qua cả 3 chốt chặn, chương trình gọi đệ quy `process_directory(e->full_path, ...)` để đi sâu xuống tầng tiếp theo.

### Bước 16: Giải phóng bộ nhớ (`entry_list_free`) và kết thúc ([src/directory.c](file:///p:/DoAn_Laptrinhhethong/src/directory.c#L87-L102))
- Trước khi thoát khỏi mỗi tầng thư mục (và trước khi kết thúc `main`), hàm `entry_list_free()` giải phóng từng chuỗi `name`, `full_path` và vùng nhớ mảng `items`.
- Đảm bảo **0 bytes rò rỉ bộ nhớ (Zero Memory Leaks)** khi kiểm tra bằng công cụ `AddressSanitizer` / `LeakSanitizer`.
