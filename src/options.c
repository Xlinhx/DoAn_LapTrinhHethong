/*
 * src/options.c
 * Module phân tích tham số dòng lệnh (CLI Options Parser).
 *
 * Giải thích nguyên lý:
 * 1. Sử dụng hàm chuẩn POSIX getopt(argc, argv, "alRS") để hỗ trợ linh hoạt:
 *    - Các cờ viết rời: ./myls -a -l -R -S
 *    - Các cờ viết gộp: ./myls -alRS, ./myls -la, ./myls -SR
 *    - Ký hiệu "--" để báo kết thúc phần cờ (hỗ trợ liệt kê tệp có tên bắt đầu bằng '-').
 * 2. Nếu người dùng truyền cờ không thuộc {a, l, R, S}, chương trình in thông báo lỗi
 *    ra stderr và trả về mã thoát EXIT_LS_SERIOUS_ERR (2).
 */

#include "myls.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

void print_usage(const char *prog_name, bool to_stderr)
{
    FILE *out = to_stderr ? stderr : stdout;
    fprintf(out, "Usage: %s [-alRS] [file...]\n", prog_name);
    if (!to_stderr) {
        fprintf(out,
                "\nPOSIX ls implementation for VKU System Programming (Topic 17).\n"
                "\nOptions:\n"
                "  -a    do not ignore entries starting with .\n"
                "  -l    use a long listing format (permissions, links, owner, group, size, time)\n"
                "  -R    list subdirectories recursively\n"
                "  -S    sort by file size, largest first (tie-break by name)\n"
                "  --help display this help and exit\n");
    }
}

int parse_options(int argc, char *argv[], LsOptions *opts, int *first_path_idx)
{
    if (opts == NULL || first_path_idx == NULL) {
        return EXIT_LS_SERIOUS_ERR;
    }

    /* Khởi tạo toàn bộ cờ ở trạng thái tắt (false) */
    opts->opt_a = false;
    opts->opt_l = false;
    opts->opt_R = false;
    opts->opt_S = false;

    /* Kiểm tra nhanh cờ --help trước khi đưa vào getopt */
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--") == 0) {
            break;
        }
        if (strcmp(argv[i], "--help") == 0) {
            print_usage(argv[0], false);
            if (!flush_and_check_stdout()) {
                exit(EXIT_LS_SERIOUS_ERR);
            }
            exit(EXIT_LS_OK);
        }
    }

    /* Đặt opterr = 0 để tự kiểm soát thông báo lỗi rõ ràng trên stderr */
    opterr = 0;
    optind = 1;

    int opt;
    while ((opt = getopt(argc, argv, "alRS")) != -1) {
        switch (opt) {
        case 'a':
            opts->opt_a = true;
            break;
        case 'l':
            opts->opt_l = true;
            break;
        case 'R':
            opts->opt_R = true;
            break;
        case 'S':
            opts->opt_S = true;
            break;
        case '?':
        default:
            fprintf(stderr, "%s: invalid option -- '%c'\n", argv[0], optopt);
            print_usage(argv[0], true);
            return EXIT_LS_SERIOUS_ERR;
        }
    }

    /* optind trỏ tới đối số đường dẫn (path) đầu tiên sau các cờ */
    *first_path_idx = optind;
    return EXIT_LS_OK;
}
