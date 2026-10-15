/*
 * src/sorting.c
 * Module sắp xếp danh sách FileEntry.
 *
 * Giải thích các quyết định kỹ thuật quan trọng:
 * 1. Mặc định (không bật -S):
 *    Sắp xếp theo thứ tự từ điển ASCII tăng dần bằng strcmp(a->name, b->name),
 *    tương đương hoàn toàn với hành vi của `LC_ALL=C ls`.
 * 2. Khi bật cờ -S (Sắp xếp theo kích thước giảm dần):
 *    - TẠI SAO KHÔNG DÙNG `return b->st.st_size - a->st.st_size;`?
 *      Vì `st_size` có kiểu `off_t` (số nguyên có dấu 64-bit trên hệ thống 64-bit),
 *      trong khi hàm so sánh của `qsort()` trả về kiểu `int` (32-bit). Nếu hiệu kích thước
 *      giữa 2 tệp vượt quá 2^31 - 1 (~2 GB), phép trừ trực tiếp sẽ bị TRÀN SỐ NGUYÊN
 *      (Integer Overflow) làm đảo ngược kết quả sắp xếp!
 *    - Do đó, ta bắt buộc dùng phép so sánh quan hệ (`>` và `<`) để trả về -1 hoặc 1.
 *    - Khi 2 tệp có cùng kích thước (`a->st.st_size == b->st.st_size`), ta dùng `strcmp()`
 *      trên tên tệp làm tiêu chí phụ (tie-breaker) để thứ tự đầu ra luôn ổn định (deterministic)
 *      và khớp 100% với GNU ls.
 */

#include "myls.h"

#include <stdlib.h>
#include <string.h>

static int cmp_by_name_asc(const void *pa, const void *pb)
{
    const FileEntry *a = (const FileEntry *)pa;
    const FileEntry *b = (const FileEntry *)pb;
    return strcmp(a->name, b->name);
}

static int cmp_by_size_desc(const void *pa, const void *pb)
{
    const FileEntry *a = (const FileEntry *)pa;
    const FileEntry *b = (const FileEntry *)pb;

    if (a->st.st_size > b->st.st_size) {
        return -1; /* Tệp lớn hơn đứng trước */
    }
    if (a->st.st_size < b->st.st_size) {
        return 1;  /* Tệp nhỏ hơn đứng sau */
    }

    /* Nếu kích thước bằng nhau: phân định thứ tự (tie-break) bằng tên A -> Z */
    return strcmp(a->name, b->name);
}

void sort_entries(EntryList *list, const LsOptions *opts)
{
    if (list == NULL || list->count <= 1 || opts == NULL) {
        return;
    }

    if (opts->opt_S) {
        qsort(list->items, list->count, sizeof(FileEntry), cmp_by_size_desc);
    } else {
        qsort(list->items, list->count, sizeof(FileEntry), cmp_by_name_asc);
    }
}
