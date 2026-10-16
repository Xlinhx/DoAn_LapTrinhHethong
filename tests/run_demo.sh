#!/usr/bin/env bash
# ==============================================================================
# tests/run_demo.sh
# Kịch bản trình diễn (Demo) sử dụng cây fixture cô lập trên Linux filesystem (/tmp)
# theo đúng 4 bước bảo vệ đồ án:
#   Bước 1: So sánh liệt kê mặc định (./myls) với hiển thị tệp ẩn (./myls -a)
#   Bước 2: Chạy ./myls -lS giải thích quyền hạn, kích thước và thứ tự giảm dần
#   Bước 3: Chạy ./myls -alRS chứng minh duyệt thư mục ẩn nhưng chặn vòng lặp . / .. / symlink
#   Bước 4: Minh họa xử lý đối số lỗi đi kèm đối số hợp lệ (báo lỗi stderr, trả mã thoát 2)
# ==============================================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MYLS_BIN="${PROJECT_ROOT}/myls"

if [[ ! -x "${MYLS_BIN}" ]]; then
    make -C "${PROJECT_ROOT}"
fi

export LC_ALL=C
export TZ=UTC0
unset LS_COLORS BLOCK_SIZE BLOCKSIZE POSIXLY_CORRECT QUOTING_STYLE TIME_STYLE || true

DEMO_DIR="$(mktemp -d /tmp/myls_demo_XXXXXX)"
trap 'chmod -R u+rwx "${DEMO_DIR}" 2>/dev/null || true; rm -rf "${DEMO_DIR}"' EXIT

# Tạo cây dữ liệu mẫu nhỏ gọn, trực quan cho buổi bảo vệ
mkdir -p "${DEMO_DIR}/src_module" "${DEMO_DIR}/.config_hidden"
dd if=/dev/zero of="${DEMO_DIR}/database.bin" bs=1024 count=8 status=none
dd if=/dev/zero of="${DEMO_DIR}/README.txt"   bs=512  count=1 status=none
dd if=/dev/zero of="${DEMO_DIR}/notes.txt"    bs=512  count=1 status=none
printf "env=production\n" > "${DEMO_DIR}/.env"
printf "secret_key=42\n"  > "${DEMO_DIR}/.config_hidden/key.conf"
printf "int main(void) { return 0; }\n" > "${DEMO_DIR}/src_module/main.c"
chmod 4755 "${DEMO_DIR}/src_module/main.c"
ln -s "src_module" "${DEMO_DIR}/link_to_src"
ln -s ".."         "${DEMO_DIR}/src_module/loop_parent"

cd "${DEMO_DIR}" || exit 2

echo "======================================================================"
echo "  DEMO SCENARIO - VKU SYSTEM PROGRAMMING TOPIC 17 (myls -a -l -R -S)"
echo "  Fixture Directory: ${DEMO_DIR}"
echo "======================================================================"
echo ""
run_demo() {
    local expected="$1" actual=0
    shift
    printf '$ ./myls%s\n' "${*:+ $*}"
    "${MYLS_BIN}" "$@" 2>&1 || actual=$?
    printf '%s\n\n' "-> Exit code: ${actual}"
    if [[ "$actual" -ne "$expected" ]]; then
        printf 'DEMO FAILED: expected exit %s, got %s\n' "$expected" "$actual" >&2
        exit 1
    fi
}

run_demo 0
run_demo 0 -a
run_demo 0 -lS
run_demo 0 -alRS
run_demo 2 missing_path.txt src_module
