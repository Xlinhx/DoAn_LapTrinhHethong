#!/usr/bin/env bash
# ==============================================================================
# tests/run_tests.sh
# Bộ kiểm thử tự động toàn diện đối chiếu với GNU ls (LC_ALL=C ls -N)
# trên hệ thống tệp Linux (/tmp) của Ubuntu WSL2.
# Hỗ trợ truyền đường dẫn binary qua tham số $1 hoặc biến môi trường MYLS_BIN.
# ==============================================================================

set -u

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW_BIN="${1:-${MYLS_BIN:-${PROJECT_ROOT}/myls}}"
MYLS_BIN="$(realpath "${RAW_BIN}" 2>/dev/null || echo "${RAW_BIN}")"

if [[ ! -x "${MYLS_BIN}" ]]; then
    echo "[ERROR] Binary '${MYLS_BIN}' not found or not executable. Run 'make' first." >&2
    exit 2
fi

# Cố định môi trường để kết quả đối chiếu với GNU ls luôn tất định (deterministic)
export LC_ALL=C
export TZ=UTC0
unset LS_COLORS BLOCK_SIZE BLOCKSIZE DF_BLOCK_SIZE TIME_STYLE QUOTING_STYLE POSIXLY_CORRECT
export ASAN_OPTIONS="verify_asan_link_order=0:detect_leaks=1:halt_on_error=1"
export UBSAN_OPTIONS="print_stacktrace=1:halt_on_error=1"

TEST_ROOT="$(mktemp -d /tmp/myls_test_XXXXXX)"
SPECIAL_ROOT="$(mktemp -d /tmp/myls_spec_XXXXXX)"
OUT_DIR="$(mktemp -d /tmp/myls_out_XXXXXX)"

cleanup() {
    chmod -R u+rwx "${TEST_ROOT}" "${SPECIAL_ROOT}" 2>/dev/null || true
    rm -rf "${TEST_ROOT}" "${SPECIAL_ROOT}" "${OUT_DIR}"
}
trap cleanup EXIT

# Biên dịch các công cụ test phụ trợ (unit test nội bộ & thư viện fault injection)
mkdir -p "${PROJECT_ROOT}/build"
HELPER_SAN_FLAGS=()
if [[ "${MYLS_TEST_SANITIZE:-0}" == 1 ]]; then
    HELPER_SAN_FLAGS=(-fsanitize=address,undefined -fno-omit-frame-pointer)
fi
gcc -Wall -Wextra -Werror -pedantic -std=c11 -D_POSIX_C_SOURCE=200809L -D_XOPEN_SOURCE=700 \
    -I"${PROJECT_ROOT}/include" -O2 -g "${HELPER_SAN_FLAGS[@]}" \
    "${PROJECT_ROOT}/tests/test_internals.c" \
    "${PROJECT_ROOT}/src/directory.c" \
    "${PROJECT_ROOT}/src/sorting.c" \
    "${PROJECT_ROOT}/src/display.c" \
    -o "${PROJECT_ROOT}/build/test_internals" || {
    echo "[FATAL] Failed to compile build/test_internals" >&2
    exit 2
}

gcc -Wall -Wextra -Werror -std=c11 -D_GNU_SOURCE -shared -fPIC -O2 \
    "${PROJECT_ROOT}/tests/fault_inject.c" \
    -o "${PROJECT_ROOT}/build/fault_inject.so" -ldl || {
    echo "[FATAL] Failed to compile build/fault_inject.so" >&2
    exit 2
}

# ------------------------------------------------------------------------------
# 1. Khởi tạo cây thư mục mẫu (Fixtures) trên Linux filesystem (/tmp)
#    Mọi bước tạo fixture đều kiểm tra lỗi nghiêm ngặt (fail-fast).
# ------------------------------------------------------------------------------
setup_fixtures() {
    (
        set -e
        mkdir -p "${TEST_ROOT}/alpha_dir/nested_deep"
        mkdir -p "${TEST_ROOT}/beta_dir/.hidden_subdir"
        mkdir -p "${TEST_ROOT}/empty_dir"

        # Tệp thường với kích thước khác nhau và bằng nhau (kiểm tra tie-break -S)
        dd if=/dev/zero of="${TEST_ROOT}/file_10k.bin"   bs=1024 count=10 status=none
        dd if=/dev/zero of="${TEST_ROOT}/file_2k.bin"    bs=1024 count=2  status=none
        dd if=/dev/zero of="${TEST_ROOT}/same_512_b.dat" bs=512  count=1  status=none
        dd if=/dev/zero of="${TEST_ROOT}/same_512_a.dat" bs=512  count=1  status=none
        : > "${TEST_ROOT}/empty_0b.txt"

        # Sparse file > 2 GiB (kiểm tra so sánh off_t 64-bit không bị tràn int 32-bit)
        truncate -s 2500000000 "${TEST_ROOT}/sparse_2_5gb.img"

        # Tệp ẩn ở thư mục gốc và thư mục con ẩn
        printf "secret config\n" > "${TEST_ROOT}/.hidden_cfg"
        dd if=/dev/zero of="${TEST_ROOT}/.hidden_big" bs=1024 count=4 status=none
        printf "nested hidden\n" > "${TEST_ROOT}/beta_dir/.hidden_subdir/inside.txt"

        # Tệp có khoảng trắng và ký tự tiếng Việt UTF-8
        dd if=/dev/zero of="${TEST_ROOT}/alpha_dir/sub_3k.bin" bs=1024 count=3 status=none
        printf "hello system programming\n" > "${TEST_ROOT}/alpha_dir/nested_deep/leaf.txt"
        printf "space name\n" > "${TEST_ROOT}/alpha_dir/file with spaces.txt"
        printf "utf8 name\n"  > "${TEST_ROOT}/alpha_dir/báo cáo tiếng Việt.txt"

        # Mtime: cũ (> 6 tháng), gần hiện tại (~2 ngày trước), và tương lai (1 năm sau)
        touch -t 202205150945 "${TEST_ROOT}/mtime_old_2022.log"
        touch -d "2 days ago" "${TEST_ROOT}/mtime_recent.log"
        touch -d '1 year' "${TEST_ROOT}/mtime_future.log"

        # Đủ 6 nhánh bit quyền đặc biệt: SUID (s/S), SGID (s/S), Sticky (t/T)
        touch "${TEST_ROOT}/perm_suid_x"   "${TEST_ROOT}/perm_suid_nox" \
              "${TEST_ROOT}/perm_sgid_x"   "${TEST_ROOT}/perm_sgid_nox" \
              "${TEST_ROOT}/perm_sticky_x" "${TEST_ROOT}/perm_sticky_nox"
        chmod 4755 "${TEST_ROOT}/perm_suid_x"
        chmod 4644 "${TEST_ROOT}/perm_suid_nox"
        chmod 2755 "${TEST_ROOT}/perm_sgid_x"
        chmod 2644 "${TEST_ROOT}/perm_sgid_nox"
        chmod 1755 "${TEST_ROOT}/perm_sticky_x"
        chmod 1644 "${TEST_ROOT}/perm_sticky_nox"

        # Hard link (st_nlink > 1)
        ln "${TEST_ROOT}/file_2k.bin" "${TEST_ROOT}/file_2k_hardlink.bin"

        # Symbolic links: tới tệp, tới thư mục, broken symlink, và symlink quay ngược về cha (..)
        ln -s "file_10k.bin"            "${TEST_ROOT}/symlink_to_file"
        ln -s "alpha_dir"               "${TEST_ROOT}/symlink_to_dir"
        ln -s "non_existent_target_xyz" "${TEST_ROOT}/broken_symlink"
        ln -s ".."                      "${TEST_ROOT}/alpha_dir/symlink_loop_up"

        # FIFO và Unix domain socket trong thư mục riêng (SPECIAL_ROOT)
        mkdir -p "${SPECIAL_ROOT}/many_entries_dir"
        mkfifo "${SPECIAL_ROOT}/named_pipe.fifo"
        python3 -c "import socket, sys; s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.bind(sys.argv[1])" \
            "${SPECIAL_ROOT}/ipc_endpoint.sock"

        # Tên bắt đầu bằng dấu '-'
        printf "leading dash\n" > "${SPECIAL_ROOT}/-dash_file.txt"

        # Tạo > 64 entries (80 tệp) để đi qua nhánh nhân đôi capacity (64 -> 128)
        for idx in $(seq -w 1 80); do
            printf "entry %s\n" "${idx}" > "${SPECIAL_ROOT}/many_entries_dir/item_${idx}.txt"
        done
    )
    if [[ $? -ne 0 ]]; then
        echo "[FATAL] Fixture setup failed!" >&2
        exit 2
    fi
}

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0
TOTAL_COUNT=0

record_pass() {
    local desc="$1"
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    PASS_COUNT=$((PASS_COUNT + 1))
    printf "  [PASS] Test %02d: %s\n" "${TOTAL_COUNT}" "${desc}"
}

record_fail() {
    local desc="$1"
    local reason="$2"
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    FAIL_COUNT=$((FAIL_COUNT + 1))
    printf "  [FAIL] Test %02d: %s (%s)\n" "${TOTAL_COUNT}" "${desc}" "${reason}"
}

record_skip() {
    local desc="$1"
    local reason="$2"
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    SKIP_COUNT=$((SKIP_COUNT + 1))
    printf "  [SKIP] Test %02d: %s (%s)\n" "${TOTAL_COUNT}" "${desc}" "${reason}"
}

compare_in_dir() {
    local work_dir="$1"
    local desc="$2"
    shift 2

    local id=$((TOTAL_COUNT + 1))
    local gnu_out="${OUT_DIR}/gnu_out_${id}"
    local my_out="${OUT_DIR}/my_out_${id}"

    (cd "${work_dir}" && timeout 5s ls -N "$@" > "${gnu_out}" 2>"${OUT_DIR}/gnu_err_${id}")
    local gnu_rc=$?
    (cd "${work_dir}" && timeout 5s "${MYLS_BIN}" "$@" > "${my_out}" 2>"${OUT_DIR}/my_err_${id}")
    local my_rc=$?

    if [[ ${gnu_rc} -eq 124 || ${my_rc} -eq 124 ]]; then
        record_fail "${desc}" "timeout (not a matching result)"
        return
    fi
    if [[ ${gnu_rc} -ne ${my_rc} ]]; then
        record_fail "${desc}" "exit code mismatch: GNU=${gnu_rc}, myls=${my_rc}"
        return
    fi
    if [[ -s "${OUT_DIR}/my_err_${id}" ]]; then
        record_fail "${desc}" "unexpected stderr"
        cat "${OUT_DIR}/my_err_${id}"
        return
    fi

    if diff -u "${gnu_out}" "${my_out}" > "${OUT_DIR}/diff_${id}"; then
        record_pass "${desc}"
    else
        record_fail "${desc}" "stdout diff mismatch"
        cat "${OUT_DIR}/diff_${id}"
    fi
}

echo "======================================================================"
echo "  VKU SYSTEM PROGRAMMING - TOPIC 17: AUTOMATED TEST SUITE"
echo "  Target Binary : ${MYLS_BIN}"
echo "  Fixture Root  : ${TEST_ROOT}"
echo "======================================================================"

setup_fixtures

# ------------------------------------------------------------------------------
# Nhóm 1 (Tests 01..16): Đủ 16 tổ hợp của 4 cờ (-a, -l, -R, -S)
# ------------------------------------------------------------------------------
compare_in_dir "${TEST_ROOT}" "Flag combo 01/16: (none) default listing"
compare_in_dir "${TEST_ROOT}" "Flag combo 02/16: -a (all entries)"                        -a
compare_in_dir "${TEST_ROOT}" "Flag combo 03/16: -l (long format)"                        -l
compare_in_dir "${TEST_ROOT}" "Flag combo 04/16: -R (recursive)"                          -R
compare_in_dir "${TEST_ROOT}" "Flag combo 05/16: -S (size sort descending)"               -S
compare_in_dir "${TEST_ROOT}" "Flag combo 06/16: -al"                                     -al
compare_in_dir "${TEST_ROOT}" "Flag combo 07/16: -aR (with . / .. / loop symlink guard)"  -aR
compare_in_dir "${TEST_ROOT}" "Flag combo 08/16: -aS"                                     -aS
compare_in_dir "${TEST_ROOT}" "Flag combo 09/16: -lR"                                     -lR
compare_in_dir "${TEST_ROOT}" "Flag combo 10/16: -lS (sparse 2.5GiB + tie-break)"         -lS
compare_in_dir "${TEST_ROOT}" "Flag combo 11/16: -RS"                                     -RS
compare_in_dir "${TEST_ROOT}" "Flag combo 12/16: -alR"                                    -alR
compare_in_dir "${TEST_ROOT}" "Flag combo 13/16: -alS"                                    -alS
compare_in_dir "${TEST_ROOT}" "Flag combo 14/16: -aRS"                                    -aRS
compare_in_dir "${TEST_ROOT}" "Flag combo 15/16: -lRS"                                    -lRS
compare_in_dir "${TEST_ROOT}" "Flag combo 16/16: -alRS (all four flags)"                  -alRS

# ------------------------------------------------------------------------------
# Nhóm 2 (Tests 17..26): Viết rời/đổi thứ tự cờ, symlink CLI, thiết bị, >64 mục
# ------------------------------------------------------------------------------
compare_in_dir "${TEST_ROOT}"    "Separated and reordered flags (-S -R -l -a)"            -S -R -l -a
compare_in_dir "${TEST_ROOT}"    "Empty directory with -l and -la"                        -la empty_dir
compare_in_dir "${SPECIAL_ROOT}" "Directory > 64 entries (80 files capacity growth)"      -lS many_entries_dir
compare_in_dir "${SPECIAL_ROOT}" "Filename starting with '-' using '--' separator"        -l -- -dash_file.txt
compare_in_dir "${SPECIAL_ROOT}" "FIFO and Unix domain socket in -l"                      -l named_pipe.fifo ipc_endpoint.sock
compare_in_dir "${TEST_ROOT}"    "Symlink CLI operand without -l (follows to dir)"        symlink_to_dir
compare_in_dir "${TEST_ROOT}"    "Symlink CLI operand with -l vs trailing slash"          -l symlink_to_dir symlink_to_dir/
compare_in_dir "${TEST_ROOT}"    "Broken symlink CLI operand without trailing slash"      -l broken_symlink
compare_in_dir "${TEST_ROOT}"    "Character device /dev/null mixed with regular file"     -l /dev/null file_10k.bin
compare_in_dir "${TEST_ROOT}"    "Multiple mixed CLI operands (files + directories)"      -lS file_10k.bin same_512_a.dat alpha_dir beta_dir

# Test 27: Unit test nội bộ (Block device major/minor, làm tròn total 1 KiB, chống tràn SIZE_MAX)
if "${PROJECT_ROOT}/build/test_internals" > "${OUT_DIR}/unit_out" 2>&1; then
    record_pass "Internal unit tests (block device major/minor, 1KiB rounding, overflow guard)"
else
    record_fail "Internal unit tests (block device major/minor, 1KiB rounding, overflow guard)" "test_internals failed"
fi

# ------------------------------------------------------------------------------
# Nhóm 3 (Tests 28..37): Mã thoát lỗi, quyền truy cập, /dev/full, Fault Injection
# ------------------------------------------------------------------------------

# Test 28: CLI operand không tồn tại -> exit status 2 và thông báo stderr có tên đường dẫn
(cd "${TEST_ROOT}" && "${MYLS_BIN}" "does_not_exist_123" >/dev/null 2>"${OUT_DIR}/err_nonexist")
rc=$?
if [[ ${rc} -eq 2 ]] && grep -q "does_not_exist_123" "${OUT_DIR}/err_nonexist"; then
    record_pass "Non-existent CLI operand returns exit status 2 and stderr diagnostic"
else
    record_fail "Non-existent CLI operand returns exit status 2 and stderr diagnostic" "got exit=${rc}"
fi

# Test 29: Broken symlink có dấu '/' cuối trên CLI -> exit status 2
(cd "${TEST_ROOT}" && "${MYLS_BIN}" "broken_symlink/" >/dev/null 2>"${OUT_DIR}/err_brokenslash")
rc=$?
if [[ ${rc} -eq 2 ]] && grep -q "broken_symlink/" "${OUT_DIR}/err_brokenslash"; then
    record_pass "Broken symlink with trailing slash (broken_symlink/) returns exit status 2"
else
    record_fail "Broken symlink with trailing slash (broken_symlink/) returns exit status 2" "got exit=${rc}"
fi

# Test 30 & 31: Kiểm tra quyền đọc thư mục (chỉ chạy dưới user không đặc quyền)
if [[ $(id -u) -eq 0 ]]; then
    record_skip "Unreadable CLI directory operand returns exit status 2" "running as root (bypasses chmod 000)"
    record_skip "Unreadable subdirectory during -R returns exit status 1 and continues" "running as root (bypasses chmod 000)"
else
    mkdir -p "${TEST_ROOT}/locked_cli_dir"
    chmod 0000 "${TEST_ROOT}/locked_cli_dir"
    (cd "${TEST_ROOT}" && "${MYLS_BIN}" locked_cli_dir empty_dir >"${OUT_DIR}/out_lock_cli" 2>"${OUT_DIR}/err_lock_cli")
    rc_cli=$?
    chmod 0755 "${TEST_ROOT}/locked_cli_dir"
    rmdir "${TEST_ROOT}/locked_cli_dir"

    if [[ ${rc_cli} -eq 2 ]] && grep -q "locked_cli_dir" "${OUT_DIR}/err_lock_cli" && grep -q "empty_dir:" "${OUT_DIR}/out_lock_cli"; then
        record_pass "Unreadable CLI directory operand returns exit status 2 and continues remaining operands"
    else
        record_fail "Unreadable CLI directory operand returns exit status 2 and continues remaining operands" "got exit=${rc_cli}"
    fi

    mkdir -p "${TEST_ROOT}/alpha_dir/locked_sub"
    chmod 0000 "${TEST_ROOT}/alpha_dir/locked_sub"
    (cd "${TEST_ROOT}" && timeout 5s "${MYLS_BIN}" -R alpha_dir >"${OUT_DIR}/out_lock_sub" 2>"${OUT_DIR}/err_lock_sub")
    rc_sub=$?
    chmod 0755 "${TEST_ROOT}/alpha_dir/locked_sub"
    rmdir "${TEST_ROOT}/alpha_dir/locked_sub"

    if [[ ${rc_sub} -eq 1 ]] && grep -q "locked_sub" "${OUT_DIR}/err_lock_sub" && grep -q "nested_deep" "${OUT_DIR}/out_lock_sub"; then
        record_pass "Unreadable subdirectory during -R returns exit status 1 and continues traversal"
    else
        record_fail "Unreadable subdirectory during -R returns exit status 1 and continues traversal" "got exit=${rc_sub}"
    fi
fi

# Test 32: Tổ hợp lỗi CLI operand (2) đi trước lỗi thư mục con (1) -> giữ mức lỗi cao nhất (2)
if [[ $(id -u) -eq 0 ]]; then
    record_skip "Mixed CLI error (2) + subdirectory error (1) preserves highest exit status 2" "running as root"
else
    mkdir -p "${TEST_ROOT}/alpha_dir/locked_sub2"
    chmod 0000 "${TEST_ROOT}/alpha_dir/locked_sub2"
    (cd "${TEST_ROOT}" && timeout 5s "${MYLS_BIN}" -R missing_cli_arg alpha_dir >/dev/null 2>"${OUT_DIR}/err_mixed")
    rc_mix=$?
    chmod 0755 "${TEST_ROOT}/alpha_dir/locked_sub2"
    rmdir "${TEST_ROOT}/alpha_dir/locked_sub2"

    if [[ ${rc_mix} -eq 2 ]]; then
        record_pass "Mixed CLI error (2) + subdirectory error (1) preserves highest exit status 2"
    else
        record_fail "Mixed CLI error (2) + subdirectory error (1) preserves highest exit status 2" "got exit=${rc_mix}"
    fi
fi

# Test 33: Option sai (-z) -> exit status 2
"${MYLS_BIN}" -z >/dev/null 2>"${OUT_DIR}/err_opt"
rc=$?
if [[ ${rc} -eq 2 ]] && grep -q "invalid option" "${OUT_DIR}/err_opt"; then
    record_pass "Invalid option (-z) rejected with exit status 2"
else
    record_fail "Invalid option (-z) rejected with exit status 2" "got exit=${rc}"
fi

# Test 34: Lỗi ghi stdout qua /dev/full -> báo lỗi stderr và trả exit status 2
if [[ -w /dev/full ]]; then
    "${MYLS_BIN}" -l "${TEST_ROOT}" > /dev/full 2>"${OUT_DIR}/err_devfull"
    rc=$?
    if [[ ${rc} -eq 2 ]] && grep -q "write error" "${OUT_DIR}/err_devfull"; then
        record_pass "Stdout write error (/dev/full) detected on flush with exit status 2"
    else
        record_fail "Stdout write error (/dev/full) detected on flush with exit status 2" "got exit=${rc}"
    fi
else
    record_skip "Stdout write error (/dev/full) detected on flush with exit status 2" "/dev/full not writable"
fi

# Test 35: Fault injection cho readdir() (EIO)
MYLS_FAULT_MODE=readdir LD_PRELOAD="${PROJECT_ROOT}/build/fault_inject.so" \
    "${MYLS_BIN}" "${TEST_ROOT}" >/dev/null 2>"${OUT_DIR}/err_fi_readdir"
rc=$?
if [[ ${rc} -eq 1 ]] && grep -q "reading directory" "${OUT_DIR}/err_fi_readdir"; then
    record_pass "Fault injection: readdir() EIO handled cleanly with exit status 1"
else
    record_fail "Fault injection: readdir() EIO handled cleanly with exit status 1" "got exit=${rc}"
fi

# Test 36: Fault injection cho readlink() (EIO) -> vẫn in metadata nhưng trả mã lỗi 1
MYLS_FAULT_MODE=readlink LD_PRELOAD="${PROJECT_ROOT}/build/fault_inject.so" \
    "${MYLS_BIN}" -l "${TEST_ROOT}" >"${OUT_DIR}/out_fi_readlink" 2>"${OUT_DIR}/err_fi_readlink"
rc=$?
if [[ ${rc} -eq 1 ]] && grep -q "cannot read symbolic link" "${OUT_DIR}/err_fi_readlink" && grep -q "symlink_to_file" "${OUT_DIR}/out_fi_readlink"; then
    record_pass "Fault injection: readlink() EIO retains entry metadata and returns exit status 1"
else
    record_fail "Fault injection: readlink() EIO retains entry metadata and returns exit status 1" "got exit=${rc}"
fi

# Test 37: Fault injection cho closedir() (EIO) và realloc() (ENOMEM khi tăng capacity > 64)
MYLS_FAULT_MODE=closedir LD_PRELOAD="${PROJECT_ROOT}/build/fault_inject.so" \
    "${MYLS_BIN}" "${TEST_ROOT}" >/dev/null 2>"${OUT_DIR}/err_fi_closedir"
rc_close=$?
MYLS_FAULT_MODE=alloc_grow LD_PRELOAD="${PROJECT_ROOT}/build/fault_inject.so" \
    "${MYLS_BIN}" "${SPECIAL_ROOT}/many_entries_dir" >/dev/null 2>"${OUT_DIR}/err_fi_alloc"
rc_alloc=$?
if [[ ${rc_close} -eq 1 ]] && grep -q "closing directory" "${OUT_DIR}/err_fi_closedir" && \
   [[ ${rc_alloc} -eq 2 ]] && grep -q "memory allocation failed" "${OUT_DIR}/err_fi_alloc"; then
    record_pass "Fault injection: closedir() EIO (exit 1) and realloc() ENOMEM (exit 2) handled safely"
else
    record_fail "Fault injection: closedir() EIO (exit 1) and realloc() ENOMEM (exit 2) handled safely" "close=${rc_close}, alloc=${rc_alloc}"
fi

# Detect sanitizer diagnostics even when an expected error exit masks them.
if grep -lE 'ERROR: (AddressSanitizer|LeakSanitizer)|runtime error:|AddressSanitizer:DEADLYSIGNAL' "${OUT_DIR}"/* >"${OUT_DIR}/diagnostic_paths" 2>/dev/null; then
    while IFS= read -r diagnostic_path; do cat "${diagnostic_path}"; done <"${OUT_DIR}/diagnostic_paths"
    record_fail "Sanitizer diagnostics scan" "instrumentation reported an error"
fi

echo "----------------------------------------------------------------------"
printf "  SUMMARY: %d PASSED, %d FAILED, %d SKIPPED (TOTAL: %d)\n" \
    "${PASS_COUNT}" "${FAIL_COUNT}" "${SKIP_COUNT}" "${TOTAL_COUNT}"
echo "======================================================================"

if [[ ${FAIL_COUNT} -ne 0 ]]; then
    exit 1
fi
exit 0
