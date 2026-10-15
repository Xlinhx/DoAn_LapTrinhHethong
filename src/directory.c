/*
 * src/directory.c
 * Module quản lý bộ nhớ động, đọc thư mục, thu thập Inode và duyệt đệ quy (-R).
 *
 * Giải thích tuần tự 5 quyết định kỹ thuật sống còn:
 * 1. TẠI SAO DÙNG `lstat()` MÀ KHÔNG DÙNG `stat()`?
 *    - `stat()` tự động đi xuyên qua (dereference) symbolic link tới tệp đích.
 *      Nếu symlink bị đứt (broken symlink trỏ tới tệp không tồn tại), `stat()` báo lỗi
 *      ENOENT làm mất khả năng hiển thị symlink đó. Nguy hiểm hơn, nếu symlink trỏ ngược
 *      lên thư mục cha, `-R` dùng `stat()` sẽ nhận nhầm là thư mục thật và LẶP VÔ HẠN!
 *    - `lstat()` đọc trực tiếp Inode của chính symlink đó (`S_ISLNK`), vừa hiển thị được
 *      broken symlink, vừa ngăn `-R` đi nhầm vào vòng lặp symlink.
 * 2. TẠI SAO PHẢI GỌI `closedir()` TRƯỚC KHI ĐỆ QUY `-R`?
 *    - Mỗi tiến trình có giới hạn số lượng File Descriptor mở cùng lúc (ulimit -n ~ 1024).
 *    - Bằng cách đọc toàn bộ entry của thư mục hiện tại vào mảng động `EntryList` rồi gọi
 *      `closedir(dir)` NGAY LẬP TỨC trước khi đệ quy xuống các thư mục con, tại mọi thời điểm
 *      chương trình chỉ mở tối đa 1 File Descriptor duy nhất!
 * 3. CHỐT CHẶN CHỐNG LẶP VÔ HẠN `.` VÀ `..`:
 *    - Khi bật cả `-a` và `-R` (`./myls -aR`), danh sách tệp trong thư mục có mặt cả `.`
 *      (chính nó) và `..` (thư mục cha). Hàm `is_recursible_subdir()` bắt buộc loại trừ
 *      hai tên này trước khi gọi đệ quy.
 */

#include "myls.h"

#include <dirent.h>
#include <errno.h>
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
    size_t len = strlen(s) + 1;
    char *copy = (char *)malloc(len);
    if (copy != NULL) {
        memcpy(copy, s, len);
    }
    return copy;
}

void entry_list_init(EntryList *list)
{
    list->items = NULL;
    list->count = 0;
    list->capacity = 0;
}

bool entry_list_push(EntryList *list, const char *name, const char *full_path,
                     const struct stat *st, bool stat_ok, const char *link_target)
{
    if (list->count >= list->capacity) {
        size_t new_cap = (list->capacity == 0) ? INITIAL_LIST_CAPACITY : (list->capacity * 2);
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
    if (e->name == NULL || e->full_path == NULL) {
        free(e->name);
        free(e->full_path);
        fprintf(stderr, "myls: memory allocation failed\n");
        return false;
    }

    if (stat_ok && st != NULL) {
        e->st = *st;
        e->stat_ok = true;
    } else {
        memset(&e->st, 0, sizeof(struct stat));
        e->stat_ok = false;
    }

    if (link_target != NULL && link_target[0] != '\0') {
        snprintf(e->link_target, sizeof(e->link_target), "%s", link_target);
    } else {
        e->link_target[0] = '\0';
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
    }
    free(list->items);
    list->items = NULL;
    list->count = 0;
    list->capacity = 0;
}

char *join_path(const char *dir_path, const char *entry_name)
{
    size_t dir_len = strlen(dir_path);
    size_t name_len = strlen(entry_name);
    bool has_trailing_slash = (dir_len > 0 && dir_path[dir_len - 1] == '/');

    size_t total_len = dir_len + (has_trailing_slash ? 0 : 1) + name_len + 1;
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

bool populate_file_entry(const char *display_name, const char *full_path,
                         bool need_link_target, EntryList *list)
{
    struct stat st;
    if (lstat(full_path, &st) != 0) {
        fprintf(stderr, "myls: cannot access '%s': %s\n", full_path, strerror(errno));
        return false;
    }

    char link_buf[PATH_MAX];
    link_buf[0] = '\0';

    if (need_link_target && S_ISLNK(st.st_mode)) {
        ssize_t len = readlink(full_path, link_buf, sizeof(link_buf) - 1);
        if (len >= 0) {
            link_buf[len] = '\0';
        } else {
            fprintf(stderr, "myls: cannot read symbolic link '%s': %s\n",
                    full_path, strerror(errno));
        }
    }

    return entry_list_push(list, display_name, full_path, &st, true, link_buf);
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
    /* Chặn tuyệt đối '.' và '..' để không lặp vô hạn */
    if (strcmp(entry->name, ".") == 0 || strcmp(entry->name, "..") == 0) {
        return false;
    }
    return true;
}

void process_directory(const char *dir_path, const LsOptions *opts,
                       bool print_header, bool *first_section, int *exit_status)
{
    DIR *dir = opendir(dir_path);
    if (dir == NULL) {
        fprintf(stderr, "myls: cannot open directory '%s': %s\n", dir_path, strerror(errno));
        if (*exit_status == EXIT_LS_OK) {
            *exit_status = EXIT_LS_MINOR_ERR;
        }
        return;
    }

    if (!(*first_section)) {
        printf("\n");
    }
    *first_section = false;

    if (print_header) {
        printf("%s:\n", dir_path);
    }

    EntryList list;
    entry_list_init(&list);

    struct dirent *de;
    while ((de = readdir(dir)) != NULL) {
        /* Nếu không bật cờ -a: bỏ qua mọi tệp ẩn bắt đầu bằng dấu '.' */
        if (!opts->opt_a && de->d_name[0] == '.') {
            continue;
        }

        char *child_path = join_path(dir_path, de->d_name);
        if (child_path == NULL) {
            *exit_status = EXIT_LS_SERIOUS_ERR;
            break;
        }

        if (!populate_file_entry(de->d_name, child_path, opts->opt_l, &list)) {
            if (*exit_status == EXIT_LS_OK) {
                *exit_status = EXIT_LS_MINOR_ERR;
            }
        }
        free(child_path);
    }

    /* Đóng ngay thư mục hiện tại để giải phóng File Descriptor trước khi đệ quy */
    closedir(dir);

    /* Sắp xếp danh sách theo cờ (-S hoặc tên A-Z) */
    sort_entries(&list, opts);

    /* Hiển thị toàn bộ các entry trong thư mục hiện tại */
    display_entries(&list, opts, true);

    /* Nếu bật cờ -R: duyệt đệ quy xuống các thư mục con theo đúng thứ tự đã sắp xếp */
    if (opts->opt_R) {
        for (size_t i = 0; i < list.count; i++) {
            const FileEntry *e = &list.items[i];
            if (is_recursible_subdir(e)) {
                process_directory(e->full_path, opts, true, first_section, exit_status);
            }
        }
    }

    entry_list_free(&list);
}
