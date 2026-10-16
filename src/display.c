/*
 * src/display.c
 * Module giải mã siêu dữ liệu và hiển thị kết quả ra stdout.
 *
 * Giải thích tuần tự các cơ chế cốt lõi:
 * 1. Giải mã các bit loại tệp và quyền truy cập trong `st_mode` thành chuỗi 10 ký tự:
 *    - Phần loại tệp (`S_IFMT`) xác định ký tự đầu: '-', 'd', 'l', 'c', 'b', 'p', 's'.
 *    - 9 bit quyền cơ bản xác định rwx cho User, Group, Others.
 *    - 3 bit đặc biệt (S_ISUID = 04000, S_ISGID = 02000, S_ISVTX = 01000) kết hợp với
 *      bit thực thi tương ứng tạo thành 's'/'S' hoặc 't'/'T'.
 * 2. Chuyển đổi UID/GID sang tên người dùng và tên nhóm:
 *    - Dùng `getpwuid()` và `getgrgid()`. Nếu không tìm thấy tên trong cơ sở dữ liệu
 *      hệ thống (trả về NULL), in mã số UID/GID nguyên bản.
 * 3. Hiển thị kích thước hoặc cặp `major, minor` cho tệp thiết bị:
 *    - Tệp thông thường in `st_size`.
 *    - Character device (`S_ISCHR`) và Block device (`S_ISBLK`) in `major(st_rdev), minor(st_rdev)`
 *      và tự động đồng bộ độ rộng cột khi trộn chung với tệp thường.
 * 4. Đơn vị khối `total` trong chế độ `-l`:
 *    - `st_blocks` trong `struct stat` đếm theo đơn vị 512-byte.
 *    - Chốt hiển thị `total` theo đơn vị 1 KiB (1024-byte) có làm tròn lên:
 *      `total_1k = (total_blocks_512 + 1) / 2`.
 * 5. Kiểm tra lỗi ghi stdout (`ferror` và `fflush`):
 *    - Phát hiện lỗi ghi thiết bị (như `/dev/full` báo `ENOSPC`), thông báo ra `stderr`
 *      và trả mã thoát nghiêm trọng `2`.
 */

#include "myls.h"

#include <errno.h>
#include <grp.h>
#include <pwd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/sysmacros.h>
#include <time.h>

/* Khoảng thời gian 6 tháng tính bằng giây (~365.2425 / 2 ngày) */
#define SIX_MONTHS_SECONDS (15778476L)

static int g_stdout_errno = 0;

static void record_stdout_error(void)
{
    if (g_stdout_errno == 0) {
        g_stdout_errno = (errno != 0) ? errno : EIO;
    }
}

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

static void accumulate_list_widths(const EntryList *list, ColumnWidths *widths, bool count_blocks)
{
    if (list == NULL) {
        return;
    }

    char owner_buf[64];
    char group_buf[64];

    for (size_t i = 0; i < list->count; i++) {
        const FileEntry *e = &list->items[i];
        if (!e->stat_ok) {
            continue;
        }

        if (count_blocks) {
            widths->total_blocks_512 += e->st.st_blocks;
        }

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

        if (S_ISCHR(e->st.st_mode) || S_ISBLK(e->st.st_mode)) {
            widths->has_device = true;
            unsigned int maj = (unsigned int)major(e->st.st_rdev);
            unsigned int min = (unsigned int)minor(e->st.st_rdev);
            int maj_w = num_digits_ull((unsigned long long)maj);
            int min_w = num_digits_ull((unsigned long long)min);
            if (maj_w > widths->major_width) {
                widths->major_width = maj_w;
            }
            if (min_w > widths->minor_width) {
                widths->minor_width = min_w;
            }
        } else {
            int sz_w = num_digits_ll((long long)e->st.st_size);
            if (sz_w > widths->size_width) {
                widths->size_width = sz_w;
            }
        }
    }
}

static void finalize_device_widths(ColumnWidths *widths)
{
    if (widths->has_device) {
        int dev_w = widths->major_width + 2 + widths->minor_width;
        if (dev_w > widths->size_width) {
            widths->size_width = dev_w;
        }
        int padded_major = widths->size_width - 2 - widths->minor_width;
        if (padded_major > widths->major_width) {
            widths->major_width = padded_major;
        }
    }
}

void compute_column_widths(const EntryList *list, ColumnWidths *widths)
{
    widths->nlink_width = 1;
    widths->owner_width = 1;
    widths->group_width = 1;
    widths->size_width = 1;
    widths->major_width = 1;
    widths->minor_width = 1;
    widths->has_device = false;
    widths->total_blocks_512 = 0;

    accumulate_list_widths(list, widths, true);
    finalize_device_widths(widths);
}

static bool display_entries_internal(const EntryList *list, const EntryList *aux_width_list,
                                     const LsOptions *opts, bool is_directory_listing)
{
    if (list == NULL || opts == NULL) {
        return true;
    }

    /* Chế độ mặc định (không bật -l): In một entry trên mỗi dòng */
    if (!opts->opt_l) {
        for (size_t i = 0; i < list->count; i++) {
            errno = 0;
            if (printf("%s\n", list->items[i].name) < 0) {
                record_stdout_error();
                return false;
            }
        }
        return true;
    }

    /* Chế độ chi tiết (-l): Tính độ rộng từng cột và dòng total 1 KiB */
    ColumnWidths widths;
    compute_column_widths(list, &widths);
    if (aux_width_list != NULL) {
        accumulate_list_widths(aux_width_list, &widths, false);
        finalize_device_widths(&widths);
    }

    if (is_directory_listing) {
        long long total_1k = (long long)((widths.total_blocks_512 + 1) / 2);
        errno = 0;
        if (printf("total %lld\n", total_1k) < 0) {
            record_stdout_error();
            return false;
        }
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

        errno = 0;
        int rc;
        if (S_ISCHR(e->st.st_mode) || S_ISBLK(e->st.st_mode)) {
            unsigned int maj = (unsigned int)major(e->st.st_rdev);
            unsigned int min = (unsigned int)minor(e->st.st_rdev);
            rc = printf("%s %*lu %-*s %-*s %*u, %*u %s %s",
                        mode_str,
                        widths.nlink_width, (unsigned long)e->st.st_nlink,
                        widths.owner_width, owner_buf,
                        widths.group_width, group_buf,
                        widths.major_width, maj,
                        widths.minor_width, min,
                        time_buf,
                        e->name);
        } else {
            rc = printf("%s %*lu %-*s %-*s %*lld %s %s",
                        mode_str,
                        widths.nlink_width, (unsigned long)e->st.st_nlink,
                        widths.owner_width, owner_buf,
                        widths.group_width, group_buf,
                        widths.size_width, (long long)e->st.st_size,
                        time_buf,
                        e->name);
        }

        if (rc < 0) {
            record_stdout_error();
            return false;
        }

        if (S_ISLNK(e->st.st_mode) && e->link_target != NULL && e->link_target[0] != '\0') {
            errno = 0;
            if (printf(" -> %s", e->link_target) < 0) {
                record_stdout_error();
                return false;
            }
        }

        errno = 0;
        if (printf("\n") < 0) {
            record_stdout_error();
            return false;
        }
    }

    return true;
}

bool display_entries(const EntryList *list, const LsOptions *opts, bool is_directory_listing)
{
    return display_entries_internal(list, NULL, opts, is_directory_listing);
}

bool display_cli_files(const EntryList *file_list, const EntryList *dir_list, const LsOptions *opts)
{
    return display_entries_internal(file_list, dir_list, opts, false);
}

bool flush_and_check_stdout(void)
{
    errno = 0;
    int flush_rc = fflush(stdout);
    if (flush_rc != 0) {
        record_stdout_error();
    }
    if (ferror(stdout) || flush_rc != 0 || g_stdout_errno != 0) {
        int err = (g_stdout_errno != 0) ? g_stdout_errno : ((errno != 0) ? errno : EIO);
        fprintf(stderr, "myls: write error: %s\n", strerror(err));
        return false;
    }
    return true;
}
