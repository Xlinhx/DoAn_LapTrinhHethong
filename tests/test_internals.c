/*
 * tests/test_internals.c
 * Kiểm thử đơn vị (Unit Test) trực tiếp cho các hàm định dạng và cấu trúc dữ liệu nội bộ:
 * 1. Block device (S_IFBLK) và Character device (S_IFCHR) với major/minor tổng hợp
 *    (không yêu cầu quyền root mknod) khi trộn chung với tệp thường.
 * 2. Làm tròn dòng `total` theo đơn vị 1 KiB từ tổng số khối 512-byte lẻ.
 * 3. Kiểm tra chống tràn số nguyên (SIZE_MAX) khi tăng sức chứa EntryList.
 * 4. Kiểm tra quy tắc giữ mức lỗi cao nhất của elevate_status().
 */

#include "myls.h"

#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/sysmacros.h>
#include <unistd.h>

static int test_block_and_char_device_formatting(void)
{
    EntryList list;
    entry_list_init(&list);

    struct stat st_blk;
    memset(&st_blk, 0, sizeof(st_blk));
    st_blk.st_mode = S_IFBLK | 0660;
    st_blk.st_nlink = 1;
    st_blk.st_uid = getuid();
    st_blk.st_gid = getgid();
    st_blk.st_rdev = makedev(8, 16);
    st_blk.st_blocks = 0;
    st_blk.st_mtime = 1700000000;

    struct stat st_chr;
    memset(&st_chr, 0, sizeof(st_chr));
    st_chr.st_mode = S_IFCHR | 0666;
    st_chr.st_nlink = 1;
    st_chr.st_uid = getuid();
    st_chr.st_gid = getgid();
    st_chr.st_rdev = makedev(136, 2);
    st_chr.st_blocks = 0;
    st_chr.st_mtime = 1700000000;

    struct stat st_reg;
    memset(&st_reg, 0, sizeof(st_reg));
    st_reg.st_mode = S_IFREG | 0644;
    st_reg.st_nlink = 1;
    st_reg.st_uid = getuid();
    st_reg.st_gid = getgid();
    st_reg.st_size = 1048576; /* 7 chữ số */
    st_reg.st_blocks = 3;     /* 3 khối 512B -> làm tròn lên 2 KiB */
    st_reg.st_mtime = 1700000000;

    if (!entry_list_push(&list, "sda1", "/dev/sda1", &st_blk, true, NULL) ||
        !entry_list_push(&list, "pts2", "/dev/pts/2", &st_chr, true, NULL) ||
        !entry_list_push(&list, "kernel.img", "/boot/kernel.img", &st_reg, true, NULL)) {
        entry_list_free(&list);
        return 1;
    }

    char mode_blk[11];
    format_mode_string(st_blk.st_mode, mode_blk);
    if (strcmp(mode_blk, "brw-rw----") != 0) {
        fprintf(stderr, "FAIL: Expected brw-rw----, got %s\n", mode_blk);
        entry_list_free(&list);
        return 1;
    }

    ColumnWidths widths;
    compute_column_widths(&list, &widths);
    /* Regular file size "1048576" = 7 chars; minor_width = 2 ("16"); major_width padded = 7 - 2 - 2 = 3 */
    if (!widths.has_device || widths.size_width != 7 || widths.minor_width != 2 || widths.major_width != 3) {
        fprintf(stderr, "FAIL: Unexpected widths: size=%d major=%d minor=%d\n",
                widths.size_width, widths.major_width, widths.minor_width);
        entry_list_free(&list);
        return 1;
    }

    /* Chuyển hướng stdout tạm thời sang tmpfile để kiểm tra nội dung xuất của display_entries */
    char tmp_path[] = "/tmp/myls_unit_out_XXXXXX";
    int fd = mkstemp(tmp_path);
    if (fd < 0) {
        entry_list_free(&list);
        return 1;
    }

    int saved_stdout = dup(STDOUT_FILENO);
    dup2(fd, STDOUT_FILENO);
    close(fd);

    LsOptions opts = { .opt_a = false, .opt_l = true, .opt_R = false, .opt_S = false };
    bool ok = display_entries(&list, &opts, true);
    fflush(stdout);

    dup2(saved_stdout, STDOUT_FILENO);
    close(saved_stdout);
    entry_list_free(&list);

    if (!ok) {
        unlink(tmp_path);
        return 1;
    }

    FILE *fp = fopen(tmp_path, "r");
    unlink(tmp_path);
    if (fp == NULL) {
        return 1;
    }

    char buf[2048];
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    fclose(fp);

    /* Kiểm tra dòng total làm tròn lên: (3 + 1) / 2 = 2 */
    if (strstr(buf, "total 2\n") == NULL) {
        fprintf(stderr, "FAIL: Expected 'total 2', got:\n%s\n", buf);
        return 1;
    }
    /* Kiểm tra định dạng major, minor có căn lề */
    if (strstr(buf, "  8, 16 ") == NULL || strstr(buf, "136,  2 ") == NULL || strstr(buf, "1048576 ") == NULL) {
        fprintf(stderr, "FAIL: Expected aligned major/minor and size in output:\n%s\n", buf);
        return 1;
    }

    return 0;
}

static int test_overflow_and_status_elevation(void)
{
    /* Kiểm tra elevate_status không làm giảm mã lỗi 2 xuống 1 */
    int status = EXIT_LS_OK;
    elevate_status(&status, EXIT_LS_MINOR_ERR);
    if (status != EXIT_LS_MINOR_ERR) {
        return 1;
    }
    elevate_status(&status, EXIT_LS_SERIOUS_ERR);
    if (status != EXIT_LS_SERIOUS_ERR) {
        return 1;
    }
    elevate_status(&status, EXIT_LS_MINOR_ERR);
    if (status != EXIT_LS_SERIOUS_ERR) {
        fprintf(stderr, "FAIL: elevate_status downgraded 2 to %d\n", status);
        return 1;
    }

    /* Kiểm tra bảo vệ tràn số nguyên khi capacity vượt SIZE_MAX / 2 */
    EntryList list;
    entry_list_init(&list);
    list.capacity = (SIZE_MAX / 2) + 1;
    list.count = list.capacity;

    struct stat st;
    memset(&st, 0, sizeof(st));
    bool pushed = entry_list_push(&list, "overflow_test", "/tmp/overflow_test", &st, true, NULL);
    if (pushed || errno != ENOMEM) {
        fprintf(stderr, "FAIL: Expected overflow protection to reject push with ENOMEM\n");
        return 1;
    }

    return 0;
}

int main(void)
{
    if (test_block_and_char_device_formatting() != 0) {
        return 1;
    }
    if (test_overflow_and_status_elevation() != 0) {
        return 1;
    }
    printf("UNIT_TESTS_OK\n");
    return 0;
}
