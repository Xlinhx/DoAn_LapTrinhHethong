/*
 * include/myls.h
 * Đề tài 17: Implement ls with -a, -l, -R, -S (Lập trình Hệ thống - VKU)
 *
 * Header trung tâm định nghĩa các cấu trúc dữ liệu và giao diện hàm (API)
 * giữa 5 module: main.c, options.c, directory.c, sorting.c, display.c.
 */

#ifndef MYLS_H
#define MYLS_H

#include <stdbool.h>
#include <stddef.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <limits.h>

#ifndef PATH_MAX
#define PATH_MAX 4096
#endif

/* Mã thoát (Exit status) theo hợp đồng hành vi POSIX / GNU coreutils ls */
#define EXIT_LS_OK          0   /* Thành công hoàn toàn */
#define EXIT_LS_MINOR_ERR   1   /* Lỗi entry hoặc thư mục con trong quá trình duyệt */
#define EXIT_LS_SERIOUS_ERR 2   /* Lỗi CLI operand, sai cờ, hết bộ nhớ hoặc lỗi ghi stdout */

/*
 * Nâng mức mã thoát nhưng không bao giờ làm giảm mức lỗi nghiêm trọng đã ghi nhận trước đó.
 */
static inline void elevate_status(int *exit_status, int new_code)
{
    if (exit_status != NULL && new_code > *exit_status) {
        *exit_status = new_code;
    }
}

/*
 * 1. Cấu trúc LsOptions:
 * Lưu trữ trạng thái bật/tắt của 4 cờ chức năng cốt lõi.
 */
typedef struct {
    bool opt_a; /* -a: Hiển thị tất cả các mục, kể cả mục ẩn bắt đầu bằng dấu '.' */
    bool opt_l; /* -l: Hiển thị định dạng danh sách chi tiết (Long listing format) */
    bool opt_R; /* -R: Duyệt đệ quy (Recursive) các thư mục con thực sự */
    bool opt_S; /* -S: Sắp xếp theo kích thước (st_size) giảm dần, tie-break theo tên */
} LsOptions;

/*
 * 2. Cấu trúc FileEntry:
 * Đại diện cho một mục trong thư mục hoặc một đối số CLI kèm siêu dữ liệu từ lstat().
 * Chuỗi đích symlink (link_target) chỉ được cấp phát động khi đối tượng là symlink và cần in -l.
 */
typedef struct {
    char *name;                 /* Tên hiển thị (ví dụ: "main.c" hoặc đối số CLI) */
    char *full_path;            /* Đường dẫn đầy đủ để gọi lstat/readlink/đệ quy */
    struct stat st;             /* Siêu dữ liệu thu được từ lstat() (hoặc stat() cho CLI dir symlink) */
    bool stat_ok;               /* Đánh dấu đọc metadata thành công */
    char *link_target;          /* Chuỗi đích trỏ tới của Symbolic Link (cấp phát động khi cần, hoặc NULL) */
} FileEntry;

/*
 * 3. Cấu trúc EntryList:
 * Mảng động (Dynamic Array) tự mở rộng bằng realloc() có kiểm tra tràn số nguyên.
 */
typedef struct {
    FileEntry *items;           /* Con trỏ tới vùng nhớ chứa các FileEntry */
    size_t count;               /* Số lượng phần tử hiện có */
    size_t capacity;            /* Sức chứa hiện tại của mảng động */
} EntryList;

/*
 * 4. Cấu trúc ColumnWidths:
 * Lưu độ rộng lớn nhất của từng trường trong chế độ -l để căn lề các cột thẳng hàng.
 */
typedef struct {
    int nlink_width;            /* Độ rộng cột số lượng hard link */
    int owner_width;            /* Độ rộng cột tên chủ sở hữu (UID/Username) */
    int group_width;            /* Độ rộng cột tên nhóm (GID/Groupname) */
    int size_width;             /* Độ rộng cột kích thước hoặc tổng độ rộng "major, minor" */
    int major_width;            /* Độ rộng lớn nhất của major(st_rdev) khi có device */
    int minor_width;            /* Độ rộng lớn nhất của minor(st_rdev) khi có device */
    bool has_device;            /* Danh sách có chứa character/block device hay không */
    blkcnt_t total_blocks_512;  /* Tổng số khối 512-byte của các entry trong thư mục */
} ColumnWidths;

/* --- Nguyên mẫu hàm module options.c --- */
int parse_options(int argc, char *argv[], LsOptions *opts, int *first_path_idx);
void print_usage(const char *prog_name, bool to_stderr);

/* --- Nguyên mẫu hàm module directory.c --- */
void entry_list_init(EntryList *list);
bool entry_list_push(EntryList *list, const char *name, const char *full_path,
                     const struct stat *st, bool stat_ok, const char *link_target);
void entry_list_free(EntryList *list);
char *join_path(const char *dir_path, const char *entry_name);
int populate_file_entry(const char *display_name, const char *full_path,
                        bool need_link_target, int err_code_on_fail, EntryList *list);
void process_directory(const char *dir_path, const LsOptions *opts,
                       bool print_header, bool is_cli_operand,
                       bool *first_section, int *exit_status);

/* --- Nguyên mẫu hàm module sorting.c --- */
void sort_entries(EntryList *list, const LsOptions *opts);

/* --- Nguyên mẫu hàm module display.c --- */
void format_mode_string(mode_t mode, char out_str[11]);
void compute_column_widths(const EntryList *list, ColumnWidths *widths);
bool display_entries(const EntryList *list, const LsOptions *opts, bool is_directory_listing);
bool display_cli_files(const EntryList *file_list, const EntryList *dir_list, const LsOptions *opts);
bool flush_and_check_stdout(void);

#endif /* MYLS_H */
