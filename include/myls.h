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

/* Mã thoát (Exit status) theo chuẩn POSIX / GNU coreutils ls */
#define EXIT_LS_OK          0   /* Thành công hoàn toàn */
#define EXIT_LS_MINOR_ERR   1   /* Lỗi nhỏ (không mở được thư mục con, file không tồn tại...) */
#define EXIT_LS_SERIOUS_ERR 2   /* Lỗi nghiêm trọng (sai cờ dòng lệnh, hết bộ nhớ...) */

/*
 * 1. Cấu trúc LsOptions:
 * Lưu trữ trạng thái bật/tắt của 4 cờ chức năng cốt lõi.
 */
typedef struct {
    bool opt_a; /* -a: Hiển thị tất cả các tệp, kể cả tệp ẩn bắt đầu bằng dấu '.' */
    bool opt_l; /* -l: Hiển thị định dạng danh sách chi tiết (Long listing format) */
    bool opt_R; /* -R: Duyệt đệ quy (Recursive) toàn bộ các thư mục con */
    bool opt_S; /* -S: Sắp xếp theo kích thước tệp (st_size) giảm dần */
} LsOptions;

/*
 * 2. Cấu trúc FileEntry:
 * Đại diện cho một đối tượng hệ thống tệp (Regular file, Directory, Symlink, FIFO...)
 * kèm theo dữ liệu Inode thu được từ lời gọi hệ thống lstat().
 */
typedef struct {
    char *name;                 /* Tên hiển thị (ví dụ: "main.c" hoặc đối số CLI) */
    char *full_path;            /* Đường dẫn đầy đủ để gọi lstat/readlink/đệ quy */
    struct stat st;             /* Siêu dữ liệu (Metadata) từ Inode qua lstat() */
    bool stat_ok;               /* Đánh dấu lstat() thành công hay thất bại */
    char link_target[PATH_MAX]; /* Đích trỏ tới nếu đối tượng là Symbolic Link */
} FileEntry;

/*
 * 3. Cấu trúc EntryList:
 * Mảng động (Dynamic Array) tự mở rộng bằng realloc() để không bị giới hạn cứng
 * số lượng tệp trong một thư mục.
 */
typedef struct {
    FileEntry *items;           /* Con trỏ tới vùng nhớ chứa các FileEntry */
    size_t count;               /* Số lượng phần tử hiện có */
    size_t capacity;            /* Sức chứa tối đa hiện tại trước khi cần realloc */
} EntryList;

/*
 * 4. Cấu trúc ColumnWidths:
 * Lưu độ rộng lớn nhất của từng trường trong chế độ -l để căn lề các cột thẳng hàng.
 */
typedef struct {
    int nlink_width;            /* Độ rộng cột số lượng hard link */
    int owner_width;            /* Độ rộng cột tên chủ sở hữu (UID/Username) */
    int group_width;            /* Độ rộng cột tên nhóm (GID/Groupname) */
    int size_width;             /* Độ rộng cột kích thước tệp (bytes) */
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
bool populate_file_entry(const char *display_name, const char *full_path,
                         bool need_link_target, EntryList *list);
void process_directory(const char *dir_path, const LsOptions *opts,
                       bool print_header, bool *first_section, int *exit_status);

/* --- Nguyên mẫu hàm module sorting.c --- */
void sort_entries(EntryList *list, const LsOptions *opts);

/* --- Nguyên mẫu hàm module display.c --- */
void format_mode_string(mode_t mode, char out_str[11]);
void display_entries(const EntryList *list, const LsOptions *opts, bool is_directory_listing);

#endif /* MYLS_H */
