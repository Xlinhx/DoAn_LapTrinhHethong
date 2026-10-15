/*
 * src/display.c
 * Module giải mã siêu dữ liệu Inode và hiển thị kết quả ra stdout.
 *
 * Giải thích tuần tự các cơ chế cốt lõi:
 * 1. Giải mã 16-bit `st_mode` thành chuỗi 10 ký tự (ví dụ: "-rwxr-xr-x", "drwxrwsr-t"):
 *    - 4 bit cao (S_IFMT) xác định loại tệp: '-', 'd', 'l', 'c', 'b', 'p', 's'.
 *    - 9 bit thấp xác định quyền rwx cho User, Group, Others.
 *    - 3 bit đặc biệt (S_ISUID = 04000, S_ISGID = 02000, S_ISVTX = 01000) ghi đè lên
 *      vị trí 'x' tương ứng thành 's'/'S' hoặc 't'/'T'.
 * 2. Chuyển đổi UID/GID sang tên người dùng và tên nhóm:
 *    - Dùng `getpwuid()` và `getgrgid()`. Nếu UID/GID không có trong `/etc/passwd`
 *      hoặc `/etc/group` (trả về NULL), tự động in mã số nguyên để không bao giờ bị lỗi
 *      Segmentation Fault.
 * 3. Quy tắc định dạng thời gian 6 tháng của POSIX:
 *    - Nếu thời gian sửa đổi `st_mtime` cách thời điểm hiện tại chưa quá 6 tháng:
 *      in "Tháng Ngày Giờ:Phút" (ví dụ: "Oct 16 01:30").
 *    - Nếu tệp cũ hơn 6 tháng hoặc có timestamp trong tương lai:
 *      in "Tháng Ngày  Năm" (ví dụ: "Jan  5  2024").
 * 4. Đơn vị khối `total` trong chế độ `-l`:
 *    - Trường `st_blocks` trong `struct stat` của Linux luôn đếm theo đơn vị 512-byte.
 *    - Lệnh `ls -l` chuẩn GNU hiển thị `total` theo đơn vị 1024-byte (1K blocks).
 *    - Do đó: `total_1k = total_blocks_512 / 2`.
 */

#include "myls.h"

#include <grp.h>
#include <pwd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* Khoảng thời gian 6 tháng tính bằng giây theo chuẩn GNU coreutils (~365.2425 / 2 ngày) */
#define SIX_MONTHS_SECONDS (15778476L)

/* Bảng tên tháng chuẩn C Locale để không bị phụ thuộc biến môi trường LC_TIME */
static const char *const MONTH_NAMES[12] = {
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
};

void format_mode_string(mode_t mode, char out_str[11])
{
    /* Ký tự 0: Loại tệp (File type) */
    if (S_ISREG(mode)) {
        out_str[0] = '-';
    } else if (S_ISDIR(mode)) {
        out_str[0] = 'd';
    } else if (S_ISLNK(mode)) {
        out_str[0] = 'l';
    } else if (S_ISCHR(mode)) {
        out_str[0] = 'c';
    } else if (S_ISBLK(mode)) {
        out_str[0] = 'b';
    } else if (S_ISFIFO(mode)) {
        out_str[0] = 'p';
    } else if (S_ISSOCK(mode)) {
        out_str[0] = 's';
    } else {
        out_str[0] = '?';
    }

    /* Ký tự 1..3: Quyền của Chủ sở hữu (User) + SUID bit */
    out_str[1] = (mode & S_IRUSR) ? 'r' : '-';
    out_str[2] = (mode & S_IWUSR) ? 'w' : '-';
    if (mode & S_ISUID) {
        out_str[3] = (mode & S_IXUSR) ? 's' : 'S';
    } else {
        out_str[3] = (mode & S_IXUSR) ? 'x' : '-';
    }

    /* Ký tự 4..6: Quyền của Nhóm (Group) + SGID bit */
    out_str[4] = (mode & S_IRGRP) ? 'r' : '-';
    out_str[5] = (mode & S_IWGRP) ? 'w' : '-';
    if (mode & S_ISGID) {
        out_str[6] = (mode & S_IXGRP) ? 's' : 'S';
    } else {
        out_str[6] = (mode & S_IXGRP) ? 'x' : '-';
    }

    /* Ký tự 7..9: Quyền của Người khác (Others) + Sticky bit (S_ISVTX) */
    out_str[7] = (mode & S_IROTH) ? 'r' : '-';
    out_str[8] = (mode & S_IWOTH) ? 'w' : '-';
    if (mode & S_ISVTX) {
        out_str[9] = (mode & S_IXOTH) ? 't' : 'T';
    } else {
        out_str[9] = (mode & S_IXOTH) ? 'x' : '-';
    }

    out_str[10] = '\0';
}

static void get_owner_name(uid_t uid, char *buf, size_t buf_size)
{
    struct passwd *pw = getpwuid(uid);
    if (pw != NULL && pw->pw_name != NULL) {
        snprintf(buf, buf_size, "%s", pw->pw_name);
    } else {
        snprintf(buf, buf_size, "%lu", (unsigned long)uid);
    }
}

static void get_group_name(gid_t gid, char *buf, size_t buf_size)
{
    struct group *gr = getgrgid(gid);
    if (gr != NULL && gr->gr_name != NULL) {
        snprintf(buf, buf_size, "%s", gr->gr_name);
    } else {
        snprintf(buf, buf_size, "%lu", (unsigned long)gid);
    }
}

static int num_digits_ull(unsigned long long val)
{
    int digits = 1;
    while (val >= 10ULL) {
        val /= 10ULL;
        digits++;
    }
    return digits;
}

static int num_digits_ll(long long val)
{
    if (val < 0) {
        unsigned long long uval = (unsigned long long)(-(val + 1)) + 1ULL;
        return 1 + num_digits_ull(uval);
    }
    return num_digits_ull((unsigned long long)val);
}

static void format_mtime_string(time_t mtime, time_t now, char out_buf[32])
{
    struct tm tm_info;
    if (localtime_r(&mtime, &tm_info) == NULL) {
        snprintf(out_buf, 32, "??? ?? ?????");
        return;
    }

    const char *mon = (tm_info.tm_mon >= 0 && tm_info.tm_mon < 12)
                          ? MONTH_NAMES[tm_info.tm_mon]
                          : "???";

    /* Kiểm tra tệp có nằm trong khoảng 6 tháng gần đây hay không */
    bool is_recent = (mtime <= now) && ((now - mtime) < SIX_MONTHS_SECONDS);
    if (is_recent) {
        snprintf(out_buf, 32, "%s %2d %02d:%02d",
                 mon, tm_info.tm_mday, tm_info.tm_hour, tm_info.tm_min);
    } else {
        snprintf(out_buf, 32, "%s %2d  %4d",
                 mon, tm_info.tm_mday, tm_info.tm_year + 1900);
    }
}

static void compute_column_widths(const EntryList *list, ColumnWidths *widths)
{
    widths->nlink_width = 1;
    widths->owner_width = 1;
    widths->group_width = 1;
    widths->size_width = 1;
    widths->total_blocks_512 = 0;

    char owner_buf[64];
    char group_buf[64];

    for (size_t i = 0; i < list->count; i++) {
        const FileEntry *e = &list->items[i];
        if (!e->stat_ok) {
            continue;
        }

        widths->total_blocks_512 += e->st.st_blocks;

        int nl_w = num_digits_ull((unsigned long long)e->st.st_nlink);
        if (nl_w > widths->nlink_width) {
            widths->nlink_width = nl_w;
        }

        get_owner_name(e->st.st_uid, owner_buf, sizeof(owner_buf));
        int ow_w = (int)strlen(owner_buf);
        if (ow_w > widths->owner_width) {
            widths->owner_width = ow_w;
        }

        get_group_name(e->st.st_gid, group_buf, sizeof(group_buf));
        int gr_w = (int)strlen(group_buf);
        if (gr_w > widths->group_width) {
            widths->group_width = gr_w;
        }

        int sz_w = num_digits_ll((long long)e->st.st_size);
        if (sz_w > widths->size_width) {
            widths->size_width = sz_w;
        }
    }
}

void display_entries(const EntryList *list, const LsOptions *opts, bool is_directory_listing)
{
    if (list == NULL || opts == NULL) {
        return;
    }

    /* Chế độ mặc định (không bật -l): In danh sách tên tệp */
    if (!opts->opt_l) {
        for (size_t i = 0; i < list->count; i++) {
            printf("%s\n", list->items[i].name);
        }
        return;
    }

    /* Chế độ chi tiết (-l): Tính độ rộng từng cột và dòng total */
    ColumnWidths widths;
    compute_column_widths(list, &widths);

    if (is_directory_listing) {
        long long total_1k = (long long)(widths.total_blocks_512 / 2);
        printf("total %lld\n", total_1k);
    }

    time_t now = time(NULL);
    char mode_str[11];
    char owner_buf[64];
    char group_buf[64];
    char time_buf[32];

    for (size_t i = 0; i < list->count; i++) {
        const FileEntry *e = &list->items[i];
        if (!e->stat_ok) {
            continue;
        }

        format_mode_string(e->st.st_mode, mode_str);
        get_owner_name(e->st.st_uid, owner_buf, sizeof(owner_buf));
        get_group_name(e->st.st_gid, group_buf, sizeof(group_buf));
        format_mtime_string(e->st.st_mtime, now, time_buf);

        printf("%s %*lu %-*s %-*s %*lld %s %s",
               mode_str,
               widths.nlink_width, (unsigned long)e->st.st_nlink,
               widths.owner_width, owner_buf,
               widths.group_width, group_buf,
               widths.size_width, (long long)e->st.st_size,
               time_buf,
               e->name);

        if (S_ISLNK(e->st.st_mode) && e->link_target[0] != '\0') {
            printf(" -> %s", e->link_target);
        }
        printf("\n");
    }
}
