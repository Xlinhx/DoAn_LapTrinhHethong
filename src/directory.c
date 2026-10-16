/*
 * src/directory.c
 * Module quản lý bộ nhớ động, đọc thư mục, thu thập metadata và duyệt đệ quy (-R).
 *
 * Các quyết định kỹ thuật trọng tâm:
 * 1. Dùng `lstat()` thay vì `stat()` khi đọc các entry trong thư mục:
 *    - `lstat()` đọc siêu dữ liệu của bản thân symbolic link (`S_ISLNK`), cho phép
 *      hiển thị cả broken symlink và ngăn `-R` đi nhầm vào symlink trỏ tới thư mục.
 * 2. Đóng directory stream (`closedir()`) ngay sau khi thu thập xong danh sách entry
 *    của thư mục hiện tại trước khi đệ quy `-R`:
 *    - Giảm số lượng File Descriptor (FD) mở đồng thời xuống tối đa 1 FD cho việc đọc thư mục,
 *      nhưng lưu ý các `EntryList` của các mức cha vẫn tồn tại trên bộ nhớ cho tới khi nhánh
 *      đệ quy đó hoàn tất.
 * 3. Kiểm tra đầy đủ các đường lỗi hệ thống và bộ nhớ:
 *    - Đặt `errno = 0` trước mỗi lần gọi `readdir()` để phân biệt kết thúc thư mục (EOF)
 *      với lỗi đọc thư mục thực sự.
 *    - Kiểm tra giá trị trả về của `closedir()`.
 *    - Truyền lỗi `readlink()` về caller: vẫn giữ metadata đã đọc từ `lstat()` để hiển thị
 *      nhưng nâng mã thoát để không báo thành công giả.
 *    - Chỉ cấp phát động `link_target` khi entry là symlink và cần hiển thị `-l`;
 *      kiểm tra tràn số nguyên (`SIZE_MAX`) khi nhân đôi sức chứa mảng động.
 */

#include "myls.h"

#include <dirent.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define INITIAL_LIST_CAPACITY 64

static char *dup_string(const char *s)
{
    if (s == NULL) {
        return NULL;
    }
    size_t len = strlen(s);
    if (len == SIZE_MAX) {
        errno = ENOMEM;
        return NULL;
    }
    char *copy = (char *)malloc(len + 1);
    if (copy != NULL) {
        memcpy(copy, s, len + 1);
    }
    return copy;
}

void entry_list_init(EntryList *list)
{
    if (list == NULL) {
        return;
    }
    list->items = NULL;
    list->count = 0;
    list->capacity = 0;
}

bool entry_list_push(EntryList *list, const char *name, const char *full_path,
                     const struct stat *st, bool stat_ok, const char *link_target)
{
    if (list == NULL || name == NULL || full_path == NULL) {
        return false;
    }

    if (list->count >= list->capacity) {
        size_t new_cap;
        if (list->capacity == 0) {
            new_cap = INITIAL_LIST_CAPACITY;
        } else {
            if (list->capacity > SIZE_MAX / 2) {
                errno = ENOMEM;
                fprintf(stderr, "myls: memory allocation failed\n");
                return false;
            }
            new_cap = list->capacity * 2;
        }

        if (new_cap > SIZE_MAX / sizeof(FileEntry)) {
            errno = ENOMEM;
            fprintf(stderr, "myls: memory allocation failed\n");
            return false;
        }

        FileEntry *new_items = (FileEntry *)realloc(list->items, new_cap * sizeof(FileEntry));
        if (new_items == NULL) {
            fprintf(stderr, "myls: memory allocation failed\n");
            return false;
        }
        list->items = new_items;
        list->capacity = new_cap;
    }

    FileEntry *e = &list->items[list->count];
    e->name = dup_string(name);
    e->full_path = dup_string(full_path);
    e->link_target = NULL;

    if (e->name == NULL || e->full_path == NULL) {
        free(e->name);
        free(e->full_path);
        e->name = NULL;
        e->full_path = NULL;
        fprintf(stderr, "myls: memory allocation failed\n");
        return false;
    }

    if (link_target != NULL) {
        e->link_target = dup_string(link_target);
        if (e->link_target == NULL) {
            free(e->name);
            free(e->full_path);
            e->name = NULL;
            e->full_path = NULL;
            fprintf(stderr, "myls: memory allocation failed\n");
            return false;
        }
    }

    if (stat_ok && st != NULL) {
        e->st = *st;
        e->stat_ok = true;
    } else {
        memset(&e->st, 0, sizeof(struct stat));
        e->stat_ok = false;
    }

    list->count++;
    return true;
}

void entry_list_free(EntryList *list)
{
    if (list == NULL || list->items == NULL) {
        return;
    }
    for (size_t i = 0; i < list->count; i++) {
        free(list->items[i].name);
        free(list->items[i].full_path);
        free(list->items[i].link_target);
    }
    free(list->items);
    list->items = NULL;
    list->count = 0;
    list->capacity = 0;
}

char *join_path(const char *dir_path, const char *entry_name)
{
    if (dir_path == NULL || entry_name == NULL) {
        return NULL;
    }

    size_t dir_len = strlen(dir_path);
    size_t name_len = strlen(entry_name);
    bool has_trailing_slash = (dir_len > 0 && dir_path[dir_len - 1] == '/');
    size_t sep_len = has_trailing_slash ? 0 : 1;

    if (dir_len > SIZE_MAX - sep_len - 1 || name_len > SIZE_MAX - dir_len - sep_len - 1) {
        errno = ENOMEM;
        return NULL;
    }

    size_t total_len = dir_len + sep_len + name_len + 1;
    char *joined = (char *)malloc(total_len);
    if (joined == NULL) {
        return NULL;
    }

    if (has_trailing_slash) {
        snprintf(joined, total_len, "%s%s", dir_path, entry_name);
    } else {
        snprintf(joined, total_len, "%s/%s", dir_path, entry_name);
    }
    return joined;
}

int populate_file_entry(const char *display_name, const char *full_path,
                        bool need_link_target, int err_code_on_fail, EntryList *list)
{
    struct stat st;
    if (lstat(full_path, &st) != 0) {
        fprintf(stderr, "myls: cannot access '%s': %s\n", full_path, strerror(errno));
        return err_code_on_fail;
    }

    int rc = EXIT_LS_OK;
    char *link_buf = NULL;

    if (need_link_target && S_ISLNK(st.st_mode)) {
        size_t buf_sz = PATH_MAX;
        if (st.st_size > 0 && (size_t)st.st_size < SIZE_MAX - 1 && (size_t)st.st_size + 1 > buf_sz) {
            buf_sz = (size_t)st.st_size + 1;
        }

        link_buf = (char *)malloc(buf_sz);
        if (link_buf == NULL) {
            fprintf(stderr, "myls: memory allocation failed\n");
            return EXIT_LS_SERIOUS_ERR;
        }

        ssize_t len = readlink(full_path, link_buf, buf_sz - 1);
        if (len >= 0) {
            link_buf[len] = '\0';
        } else {
            fprintf(stderr, "myls: cannot read symbolic link '%s': %s\n",
                    full_path, strerror(errno));
            free(link_buf);
            link_buf = NULL;
            rc = err_code_on_fail;
        }
    }

    bool pushed = entry_list_push(list, display_name, full_path, &st, true, link_buf);
    free(link_buf);

    if (!pushed) {
        return EXIT_LS_SERIOUS_ERR;
    }
    return rc;
}

static bool is_recursible_subdir(const FileEntry *entry)
{
    if (!entry->stat_ok) {
        return false;
    }
    /* Chỉ đệ quy vào thư mục thật (lstat trả về S_ISDIR, không phải S_ISLNK) */
    if (!S_ISDIR(entry->st.st_mode)) {
        return false;
    }
    /* Chặn '.' và '..' để không lặp vô hạn */
    if (strcmp(entry->name, ".") == 0 || strcmp(entry->name, "..") == 0) {
        return false;
    }
    return true;
}

void process_directory(const char *dir_path, const LsOptions *opts,
                       bool print_header, bool is_cli_operand,
                       bool *first_section, int *exit_status)
{
    DIR *dir = opendir(dir_path);
    if (dir == NULL) {
        fprintf(stderr, "myls: cannot open directory '%s': %s\n", dir_path, strerror(errno));
        elevate_status(exit_status, is_cli_operand ? EXIT_LS_SERIOUS_ERR : EXIT_LS_MINOR_ERR);
        return;
    }

    if (!(*first_section)) {
        if (printf("\n") < 0) {
            elevate_status(exit_status, EXIT_LS_SERIOUS_ERR);
        }
    }
    *first_section = false;

    if (print_header) {
        if (printf("%s:\n", dir_path) < 0) {
            elevate_status(exit_status, EXIT_LS_SERIOUS_ERR);
        }
    }

    EntryList list;
    entry_list_init(&list);

    for (;;) {
        errno = 0;
        struct dirent *de = readdir(dir);
        if (de == NULL) {
            if (errno != 0) {
                fprintf(stderr, "myls: reading directory '%s': %s\n", dir_path, strerror(errno));
                elevate_status(exit_status, EXIT_LS_MINOR_ERR);
            }
            break;
        }

        /* Nếu không bật cờ -a: bỏ qua mọi mục ẩn bắt đầu bằng dấu '.' */
        if (!opts->opt_a && de->d_name[0] == '.') {
            continue;
        }

        char *child_path = join_path(dir_path, de->d_name);
        if (child_path == NULL) {
            fprintf(stderr, "myls: memory allocation failed\n");
            elevate_status(exit_status, EXIT_LS_SERIOUS_ERR);
            break;
        }

        int pop_rc = populate_file_entry(de->d_name, child_path, opts->opt_l,
                                         EXIT_LS_MINOR_ERR, &list);
        free(child_path);

        if (pop_rc != EXIT_LS_OK) {
            elevate_status(exit_status, pop_rc);
            if (pop_rc == EXIT_LS_SERIOUS_ERR) {
                break;
            }
        }
    }

    /* Đóng ngay directory stream hiện tại và kiểm tra lỗi closedir() */
    if (closedir(dir) != 0) {
        fprintf(stderr, "myls: closing directory '%s': %s\n", dir_path, strerror(errno));
        elevate_status(exit_status, EXIT_LS_MINOR_ERR);
    }

    /* Sắp xếp danh sách theo cờ (-S hoặc tên từ điển byte-wise) */
    sort_entries(&list, opts);

    /* Hiển thị toàn bộ các entry trong thư mục hiện tại */
    if (!display_entries(&list, opts, true)) {
        elevate_status(exit_status, EXIT_LS_SERIOUS_ERR);
    }

    /* Nếu bật cờ -R: duyệt đệ quy xuống các thư mục con theo đúng thứ tự đã sắp xếp */
    if (opts->opt_R) {
        for (size_t i = 0; i < list.count; i++) {
            const FileEntry *e = &list.items[i];
            if (is_recursible_subdir(e)) {
                process_directory(e->full_path, opts, true, false, first_section, exit_status);
            }
        }
    }

    entry_list_free(&list);
}
