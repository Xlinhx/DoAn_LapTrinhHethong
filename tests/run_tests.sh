#!/usr/bin/env bash
# ==============================================================================
# tests/run_tests.sh
# Bộ kiểm thử tự động 15 kịch bản đối chiếu trực tiếp với GNU ls (LC_ALL=C ls)
# trên hệ thống tệp Linux thật (/tmp) của Ubuntu WSL2.
# ==============================================================================

set -u

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MYLS_BIN="${PROJECT_ROOT}/myls"

if [[ ! -x "${MYLS_BIN}" ]]; then
    echo "[ERROR] Binary ${MYLS_BIN} not found or not executable. Run 'make' first." >&2
    exit 2
fi

TEST_ROOT="$(mktemp -d /tmp/myls_test_XXXXXX)"
OUT_DIR="$(mktemp -d /tmp/myls_out_XXXXXX)"
trap 'chmod -R u+rwx "${TEST_ROOT}" 2>/dev/null || true; rm -rf "${TEST_ROOT}" "${OUT_DIR}"' EXIT

# ------------------------------------------------------------------------------
# 1. Khởi tạo cây thư mục mẫu (Fixtures) trên Linux filesystem (/tmp)
# ------------------------------------------------------------------------------
setup_fixtures() {
    mkdir -p "${TEST_ROOT}/alpha_dir/nested_deep"
    mkdir -p "${TEST_ROOT}/beta_dir/.hidden_subdir"
    mkdir -p "${TEST_ROOT}/empty_dir"

    # Tạo các tệp có kích thước khác nhau và tệp trùng kích thước (test tie-break -S)
    dd if=/dev/zero of="${TEST_ROOT}/file_10k.bin" bs=1 count=10240 2>/dev/null
    dd if=/dev/zero of="${TEST_ROOT}/file_2k.bin"  bs=1 count=2048  2>/dev/null
    dd if=/dev/zero of="${TEST_ROOT}/same_512_b.dat" bs=1 count=512 2>/dev/null
    dd if=/dev/zero of="${TEST_ROOT}/same_512_a.dat" bs=1 count=512 2>/dev/null
    : > "${TEST_ROOT}/empty_0b.txt"

    # Tệp ẩn ở thư mục gốc và thư mục con
    printf "secret config\n" > "${TEST_ROOT}/.hidden_cfg"
    dd if=/dev/zero of="${TEST_ROOT}/.hidden_big" bs=1 count=4096 2>/dev/null
    printf "nested hidden\n" > "${TEST_ROOT}/beta_dir/.hidden_subdir/inside.txt"

    # Tệp bên trong thư mục con
    dd if=/dev/zero of="${TEST_ROOT}/alpha_dir/sub_3k.bin" bs=1 count=3072 2>/dev/null
    printf "hello system programming\n" > "${TEST_ROOT}/alpha_dir/nested_deep/leaf.txt"

    # Tệp có mtime cũ hơn 6 tháng (test định dạng Năm thay vì Giờ:Phút)
    touch -t 202205150945 "${TEST_ROOT}/old_archive_2022.log"

    # Các bit quyền đặc biệt: SUID (4755, 4644), SGID (2755, 2640), Sticky (1777, 1644)
    touch "${TEST_ROOT}/perm_suid_x" "${TEST_ROOT}/perm_suid_nox" \
          "${TEST_ROOT}/perm_sgid_x" "${TEST_ROOT}/perm_sticky_t"
    chmod 4755 "${TEST_ROOT}/perm_suid_x"
    chmod 4644 "${TEST_ROOT}/perm_suid_nox"
    chmod 2755 "${TEST_ROOT}/perm_sgid_x"
    chmod 1777 "${TEST_ROOT}/perm_sticky_t"

    # Hard link (tăng st_nlink > 1)
    ln "${TEST_ROOT}/file_2k.bin" "${TEST_ROOT}/file_2k_hardlink.bin"

    # Symbolic links: tới tệp, tới thư mục, và broken symlink
    ln -s "file_10k.bin" "${TEST_ROOT}/symlink_to_file"
    ln -s "alpha_dir"    "${TEST_ROOT}/symlink_to_dir"
    ln -s "non_existent_target_xyz" "${TEST_ROOT}/broken_symlink"
}

PASS_COUNT=0
FAIL_COUNT=0
TOTAL_TESTS=15

compare_with_gnu_ls() {
    local test_num="$1"
    local desc="$2"
    shift 2

    local gnu_out="${OUT_DIR}/gnu_out_${test_num}"
    local my_out="${OUT_DIR}/my_out_${test_num}"

    (cd "${TEST_ROOT}" && LC_ALL=C ls "$@" > "${gnu_out}" 2>/dev/null)
    (cd "${TEST_ROOT}" && LC_ALL=C "${MYLS_BIN}" "$@" > "${my_out}" 2>/dev/null)

    if diff -u "${gnu_out}" "${my_out}" > "${OUT_DIR}/diff_${test_num}"; then
        printf "  [PASS] Test %02d: %s\n" "${test_num}" "${desc}"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        printf "  [FAIL] Test %02d: %s\n" "${test_num}" "${desc}"
        cat "${OUT_DIR}/diff_${test_num}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
}

echo "======================================================================"
echo "  VKU SYSTEM PROGRAMMING - TOPIC 17: AUTOMATED TEST SUITE (myls)"
echo "  Fixture Directory (Native Linux FS): ${TEST_ROOT}"
echo "======================================================================"

setup_fixtures

# Test 01..12: Đối chiếu 1:1 (diff -u) với LC_ALL=C ls
compare_with_gnu_ls 1  "Default listing (./myls)"
compare_with_gnu_ls 2  "Show hidden entries (-a)"                     -a
compare_with_gnu_ls 3  "Long listing format with permissions/time (-l)" -l
compare_with_gnu_ls 4  "Recursive directory traversal (-R)"           -R
compare_with_gnu_ls 5  "Sort by file size descending + tie-break (-S)" -S
compare_with_gnu_ls 6  "Combined flags: Long + All (-la)"             -la
compare_with_gnu_ls 7  "Combined flags: Long + Size sort (-lS)"       -lS
compare_with_gnu_ls 8  "Combined flags: Long + Recursive (-lR)"       -lR
compare_with_gnu_ls 9  "Combined flags: All + Recursive (-aR)"        -aR
compare_with_gnu_ls 10 "Full combination: -alRS"                      -alRS
compare_with_gnu_ls 11 "Multiple mixed CLI arguments (files + dirs)"  -lS file_10k.bin same_512_a.dat alpha_dir beta_dir
compare_with_gnu_ls 12 "Symlink to directory: -l vs non -l"           -l symlink_to_dir symlink_to_file broken_symlink

# Test 13: Đường dẫn không tồn tại -> phải in lỗi ra stderr và trả về exit code = 1
(cd "${TEST_ROOT}" && "${MYLS_BIN}" "does_not_exist_123" >/dev/null 2>"${OUT_DIR}/err13")
rc13=$?
if [[ ${rc13} -eq 1 ]] && grep -q "cannot access" "${OUT_DIR}/err13"; then
    printf "  [PASS] Test 13: Non-existent path returns exit status 1 and stderr message\n"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    printf "  [FAIL] Test 13: Expected exit code 1, got %d\n" "${rc13}"
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Test 14: Thư mục bị khóa quyền đọc (chmod 000) -> báo lỗi stderr, exit code 1, vẫn tiếp tục chạy
mkdir -p "${TEST_ROOT}/locked_dir"
chmod 0000 "${TEST_ROOT}/locked_dir"
(cd "${TEST_ROOT}" && "${MYLS_BIN}" locked_dir empty_dir >"${OUT_DIR}/out14" 2>"${OUT_DIR}/err14")
rc14=$?
chmod 0755 "${TEST_ROOT}/locked_dir"
if [[ ${rc14} -eq 1 ]] && grep -q "cannot open directory" "${OUT_DIR}/err14" && grep -q "empty_dir:" "${OUT_DIR}/out14"; then
    printf "  [PASS] Test 14: Unreadable directory (chmod 000) handled gracefully without crash\n"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    printf "  [FAIL] Test 14: Expected graceful continuation and exit status 1 (got %d)\n" "${rc14}"
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Test 15: Cờ dòng lệnh không hợp lệ (-z) -> báo lỗi stderr và trả về exit code = 2
"${MYLS_BIN}" -z >/dev/null 2>"${OUT_DIR}/err15"
rc15=$?
if [[ ${rc15} -eq 2 ]] && grep -q "invalid option" "${OUT_DIR}/err15"; then
    printf "  [PASS] Test 15: Invalid option (-z) rejected with exit status 2\n"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    printf "  [FAIL] Test 15: Expected exit code 2 for invalid flag, got %d\n" "${rc15}"
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi

echo "----------------------------------------------------------------------"
printf "  SUMMARY: %d / %d TESTS PASSED (%d FAILED)\n" "${PASS_COUNT}" "${TOTAL_TESTS}" "${FAIL_COUNT}"
echo "======================================================================"

if [[ ${FAIL_COUNT} -ne 0 ]]; then
    exit 1
fi
exit 0
