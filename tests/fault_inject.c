/*
 * tests/fault_inject.c
 * Thư viện LD_PRELOAD hỗ trợ kiểm thử tiêm lỗi có giới hạn (Fault Injection) cho:
 * - MYLS_FAULT_MODE=readdir   : Giả lập readdir() trả về NULL kèm errno = EIO ở lần gọi thứ 2.
 * - MYLS_FAULT_MODE=readlink  : Giả lập readlink() trả về -1 kèm errno = EIO.
 * - MYLS_FAULT_MODE=closedir  : Đóng DIR* thật để không rò rỉ FD, sau đó trả về -1 kèm errno = EIO.
 * - MYLS_FAULT_MODE=alloc_grow: Giả lập realloc() thất bại (trả về NULL, errno = ENOMEM)
 *                               khi mảng EntryList mở rộng lên >= 128 phần tử.
 */

#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <dirent.h>
#include <dlfcn.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

struct dirent *readdir(DIR *dirp)
{
    static struct dirent *(*real_readdir)(DIR *) = NULL;
    if (real_readdir == NULL) {
        real_readdir = (struct dirent *(*)(DIR *))dlsym(RTLD_NEXT, "readdir");
    }

    const char *mode = getenv("MYLS_FAULT_MODE");
    if (mode != NULL && strcmp(mode, "readdir") == 0) {
        static int call_count = 0;
        call_count++;
        if (call_count >= 2) {
            errno = EIO;
            return NULL;
        }
    }

    return real_readdir(dirp);
}

ssize_t readlink(const char *pathname, char *buf, size_t bufsiz)
{
    static ssize_t (*real_readlink)(const char *, char *, size_t) = NULL;
    if (real_readlink == NULL) {
        real_readlink = (ssize_t (*)(const char *, char *, size_t))dlsym(RTLD_NEXT, "readlink");
    }

    const char *mode = getenv("MYLS_FAULT_MODE");
    if (mode != NULL && strcmp(mode, "readlink") == 0) {
        errno = EIO;
        return -1;
    }

    return real_readlink(pathname, buf, bufsiz);
}

ssize_t __readlink_chk(const char *pathname, char *buf, size_t len, size_t buflen)
{
    (void)buflen;
    return readlink(pathname, buf, len);
}

int closedir(DIR *dirp)
{
    static int (*real_closedir)(DIR *) = NULL;
    if (real_closedir == NULL) {
        real_closedir = (int (*)(DIR *))dlsym(RTLD_NEXT, "closedir");
    }

    int rc = real_closedir(dirp);
    const char *mode = getenv("MYLS_FAULT_MODE");
    if (mode != NULL && strcmp(mode, "closedir") == 0) {
        errno = EIO;
        return -1;
    }
    return rc;
}

void *realloc(void *ptr, size_t size)
{
    static void *(*real_realloc)(void *, size_t) = NULL;
    if (real_realloc == NULL) {
        real_realloc = (void *(*)(void *, size_t))dlsym(RTLD_NEXT, "realloc");
    }

    const char *mode = getenv("MYLS_FAULT_MODE");
    if (mode != NULL && strcmp(mode, "alloc_grow") == 0 && ptr != NULL && size >= 128 * 64) {
        errno = ENOMEM;
        return NULL;
    }

    return real_realloc(ptr, size);
}
