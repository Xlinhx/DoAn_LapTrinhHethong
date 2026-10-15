#!/usr/bin/env bash
# ==============================================================================
# tests/run_demo.sh
# Chạy kịch bản demo chuẩn trên Ubuntu WSL2 và lưu kết quả vào thư mục evidence/
# ==============================================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MYLS_BIN="${PROJECT_ROOT}/myls"
EVIDENCE_DIR="${PROJECT_ROOT}/evidence"

mkdir -p "${EVIDENCE_DIR}"

DEMO_WS="$(mktemp -d /tmp/myls_demo_XXXXXX)"
trap 'rm -rf "${DEMO_WS}"' EXIT

# Tạo dữ liệu mẫu trực quan để chạy bộ lệnh demo
mkdir -p "${DEMO_WS}/src_module" "${DEMO_WS}/docs_sub"
printf "int main(void) { return 0; }\n" > "${DEMO_WS}/main_sample.c"
dd if=/dev/zero of="${DEMO_WS}/dataset_large.bin" bs=1 count=8192 2>/dev/null
dd if=/dev/zero of="${DEMO_WS}/config_medium.cfg" bs=1 count=1024 2>/dev/null
printf "hidden_env=production\n" > "${DEMO_WS}/.env.hidden"
printf "# Header doc\n" > "${DEMO_WS}/docs_sub/guide.md"
dd if=/dev/zero of="${DEMO_WS}/src_module/engine.o" bs=1 count=4096 2>/dev/null
ln -s "dataset_large.bin" "${DEMO_WS}/latest_data.lnk"
chmod 0755 "${DEMO_WS}/main_sample.c"

DEMO_LOG="${EVIDENCE_DIR}/demo_session_output.txt"

{
    echo "======================================================================"
    echo "  DEMO THỰC TẾ TRÊN UBUNTU 24.04 WSL2 - ĐỀ TÀI 17 (myls -a -l -R -S)"
    echo "  Kernel : $(uname -sr)"
    echo "  GCC    : $(gcc --version | head -n 1)"
    echo "======================================================================"
    echo ""

    for cmd in "./myls" "./myls -a" "./myls -l" "./myls -R" "./myls -S" "./myls -alRS"; do
        echo "$ ${cmd}"
        echo "----------------------------------------------------------------------"
        (
            cd "${DEMO_WS}"
            # Chạy thông qua binary đã biên dịch
            eval "${cmd/#.\/myls/${MYLS_BIN}}"
        )
        echo ""
    done
} | tee "${DEMO_LOG}"

bash "${PROJECT_ROOT}/tests/run_tests.sh" | tee "${EVIDENCE_DIR}/test_suite_report.txt"
