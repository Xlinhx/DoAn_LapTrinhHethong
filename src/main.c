/*
 * src/main.c
 * Điểm vào chính (Entry Point) điều phối luồng thực thi của chương trình myls.
 *
 * Quy trình xử lý đa đường dẫn theo chuẩn POSIX:
 * 1. Phân tích các cờ dòng lệnh (-a, -l, -R, -S) qua `parse_options()`.
 * 2. Nếu người dùng không truyền đường dẫn nào, mặc định duyệt thư mục hiện tại `"."`.
 * 3. Nếu người dùng truyền 1 hoặc nhiều đường dẫn (hỗn hợp cả tệp và thư mục):
 *    - Kiểm tra từng đường dẫn bằng `lstat()`.
 *    - Nếu là Symbolic Link trỏ tới thư mục và KHÔNG bật cờ `-l`, chuẩn POSIX quy định
 *      đi vào liệt kê nội dung thư mục đích (dùng `stat()` để kiểm tra đích).
 *    - Phân tách thành 2 danh sách độc lập:
 *      + `file_list`: Chứa các tệp đơn lẻ (hiển thị trước, không in dòng `total`).
 *      + `dir_list`:  Chứa các thư mục (hiển thị sau, ngăn cách bằng dòng trống).
 * 4. Quyết định in tiêu đề `<dir_path>:`:
 *    - Chỉ in tiêu đề khi bật `-R` HOẶC khi tổng số đường dẫn truyền vào > 1.
 */

#include "myls.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static bool should_treat_arg_as_directory(const char *arg_path, const struct stat *lst,
                                          const LsOptions *opts, struct stat *effective_st)
{
    *effective_st = *lst;
    if (S_ISDIR(lst->st_mode)) {
        return true;
    }

    /*
     * Hành vi chuẩn POSIX cho đối số dòng lệnh là Symbolic Link:
     * - Nếu KHÔNG bật -l (hoặc đường dẫn có dấu '/' ở cuối), ta kiểm tra đích của symlink
     *   bằng stat(). Nếu đích là thư mục, liệt kê nội dung thư mục đó.
     * - Nếu BẬT -l và không có dấu '/' ở cuối, ta hiển thị chính symlink đó như 1 tệp.
     */
    size_t len = strlen(arg_path);
    bool ends_with_slash = (len > 0 && arg_path[len - 1] == '/');

    if (S_ISLNK(lst->st_mode) && (!opts->opt_l || ends_with_slash)) {
        struct stat target_st;
        if (stat(arg_path, &target_st) == 0 && S_ISDIR(target_st.st_mode)) {
            *effective_st = target_st;
            return true;
        }
    }

    return false;
}

int main(int argc, char *argv[])
{
    LsOptions opts;
    int first_path_idx = 1;

    int parse_rc = parse_options(argc, argv, &opts, &first_path_idx);
    if (parse_rc != EXIT_LS_OK) {
        return parse_rc;
    }

    int num_paths = argc - first_path_idx;
    char *default_paths[] = { "." };
    char **paths = (num_paths > 0) ? &argv[first_path_idx] : default_paths;
    if (num_paths == 0) {
        num_paths = 1;
    }

    EntryList file_list;
    EntryList dir_list;
    entry_list_init(&file_list);
    entry_list_init(&dir_list);

    int exit_status = EXIT_LS_OK;

    /* Phân loại từng đối số đường dẫn vào file_list hoặc dir_list */
    for (int i = 0; i < num_paths; i++) {
        const char *p = paths[i];
        struct stat lst;
        if (lstat(p, &lst) != 0) {
            fprintf(stderr, "myls: cannot access '%s': %s\n", p, strerror(errno));
            if (exit_status == EXIT_LS_OK) {
                exit_status = EXIT_LS_MINOR_ERR;
            }
            continue;
        }

        struct stat effective_st;
        if (should_treat_arg_as_directory(p, &lst, &opts, &effective_st)) {
            if (!entry_list_push(&dir_list, p, p, &effective_st, true, NULL)) {
                entry_list_free(&file_list);
                entry_list_free(&dir_list);
                return EXIT_LS_SERIOUS_ERR;
            }
        } else {
            if (!populate_file_entry(p, p, opts.opt_l, &file_list)) {
                if (exit_status == EXIT_LS_OK) {
                    exit_status = EXIT_LS_MINOR_ERR;
                }
            }
        }
    }

    bool first_section = true;

    /* 1. Hiển thị toàn bộ các tệp đơn lẻ trước (nếu có) */
    if (file_list.count > 0) {
        sort_entries(&file_list, &opts);
        display_entries(&file_list, &opts, false);
        first_section = false;
    }

    /* 2. Duyệt và hiển thị các thư mục (nếu có) */
    if (dir_list.count > 0) {
        sort_entries(&dir_list, &opts);
        bool print_headers = opts.opt_R || (num_paths > 1);

        for (size_t i = 0; i < dir_list.count; i++) {
            process_directory(dir_list.items[i].full_path, &opts,
                              print_headers, &first_section, &exit_status);
        }
    }

    entry_list_free(&file_list);
    entry_list_free(&dir_list);
    return exit_status;
}
