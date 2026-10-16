"""
scripts/collect_evidence.py
Thực thi bộ kiểm thử thường (make test), bộ kiểm thử Sanitizer (make sanitize) và
kịch bản demo (make demo) trên Ubuntu 24.04 WSL2, sau đó:
1. Ghi 3 file log chuẩn vào evidence/ kèm đầy đủ thông tin môi trường:
   - Lệnh build/chạy và exit code thực tế
   - Phiên bản compiler (gcc), OS/kernel (uname), GNU coreutils (ls --version)
   - Git revision và trạng thái working tree tại thời điểm chạy
   - Tổng số PASS / FAIL / SKIP và diagnostics thực tế
2. Xuất dữ liệu có cấu trúc ra evidence/test_results.json để bộ sinh Word và Slides
   đọc trực tiếp từ một nguồn duy nhất.
3. Sinh 3 ảnh PNG trình bày lại từ log (ghi rõ nhãn "Đầu ra thực nghiệm trình bày lại từ log",
   không chèn thông số thời gian giả hoặc lệnh chưa chạy).
"""

from __future__ import annotations

import json
import re
import subprocess
import os
import shlex
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from metadata_loader import source_fingerprint

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = PROJECT_ROOT / "evidence"


@contextmanager
def isolated_workspace():
    # /mnt/* may have clock skew and Windows permission semantics. Build a copy
    # on Linux instead of touching the user's sources or trusting stale binaries.
    rc, out, err = run_wsl_bash('''
set -e
workspace=$(mktemp -d /tmp/myls_evidence_XXXXXX)
cp -R src include tests "$workspace/"
cp Makefile "$workspace/"
find "$workspace" -type f -exec touch {} +
printf '%s\\n' "$workspace"
''')
    workspace = out.strip()
    if rc or not re.fullmatch(r"/tmp/myls_evidence_[A-Za-z0-9]+", workspace):
        raise RuntimeError(f"Cannot prepare isolated verification workspace: {err}")
    try:
        yield workspace
    finally:
        run_wsl_bash("rm -rf -- " + shlex.quote(workspace))


def run_wsl_bash(script: str) -> tuple[int, str, str]:
    clean_script = script.replace("\r\n", "\n").replace("\r", "\n")
    if os.name == "nt":
        resolved = subprocess.run(["wsl", "-d", "Ubuntu-24.04", "--", "bash", "-s"], input=("wslpath -u " + shlex.quote(str(PROJECT_ROOT)) + "\n").encode(), capture_output=True, check=True)
        cwd = resolved.stdout.decode("utf-8").strip()
        command = ["wsl", "-d", "Ubuntu-24.04", "--", "bash", "-s"]
    else:
        cwd = str(PROJECT_ROOT)
        command = ["bash", "-s"]
    res = subprocess.run(
        command,
        input=("cd " + shlex.quote(cwd) + " || exit 2\n" + clean_script).encode("utf-8"),
        capture_output=True,
        timeout=240,
    )
    return (
        res.returncode,
        res.stdout.decode("utf-8", errors="replace"),
        res.stderr.decode("utf-8", errors="replace"),
    )


def get_env_info() -> dict[str, str]:
    script = """
echo "GCC_VER=$(gcc --version | head -n 1)"
echo "KERNEL_VER=$(uname -srvm)"
echo "OS_NAME=$(grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '\"')"
echo "COREUTILS_VER=$(ls --version | head -n 1)"
echo "GIT_REV=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
    echo "GIT_TREE=modified (working tree has uncommitted changes)"
else
    echo "GIT_TREE=clean"
fi
"""
    rc, out, err = run_wsl_bash(script)
    if rc != 0:
        raise RuntimeError(f"Cannot inspect execution environment: {err}")
    info: dict[str, str] = {}
    for line in out.strip().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            info[k.strip()] = v.strip()
    return info


def parse_summary(output: str) -> dict[str, int]:
    m = re.search(r"SUMMARY:\s*(\d+)\s*PASSED,\s*(\d+)\s*FAILED,\s*(\d+)\s*SKIPPED\s*\(TOTAL:\s*(\d+)\)", output)
    if not m:
        raise ValueError("Test output has no summary; refusing a synthetic 0/0 result")
    result = {
        "passed": int(m.group(1)),
        "failed": int(m.group(2)),
        "skipped": int(m.group(3)),
        "total": int(m.group(4)),
    }
    if result["total"] == 0 or sum(result[k] for k in ("passed", "failed", "skipped")) != result["total"]:
        raise ValueError("Inconsistent test summary")
    return result


def parse_individual_tests(output: str) -> list[dict[str, str | int]]:
    items: list[dict[str, str | int]] = []
    for line in output.splitlines():
        m = re.match(r"^\s*\[(PASS|FAIL|SKIP)\]\s+Test\s+(\d+):\s+(.+)$", line)
        if m:
            items.append({
                "status": m.group(1),
                "id": int(m.group(2)),
                "description": m.group(3).strip(),
            })
    return items


def format_log_header(env: dict[str, str], command_str: str, exit_code: int, timestamp_utc: str) -> str:
    return (
        "======================================================================\n"
        "  THÔNG TIN MÔI TRƯỜNG & PHIÊN THỰC NGHIỆM (EXPERIMENTAL METADATA)\n"
        "======================================================================\n"
        f"  Thời điểm ghi nhận (UTC) : {timestamp_utc}\n"
        f"  Hệ điều hành             : {env.get('OS_NAME', 'Ubuntu 24.04 LTS')}\n"
        f"  Nhân Linux (Kernel)      : {env.get('KERNEL_VER', 'Linux WSL2')}\n"
        f"  Trình biên dịch (C)      : {env.get('GCC_VER', 'gcc')}\n"
        f"  Đối chuẩn tham chiếu     : {env.get('COREUTILS_VER', 'GNU coreutils ls')}\n"
        f"  Git Revision             : {env.get('GIT_REV', 'unknown')} ({env.get('GIT_TREE', 'modified')})\n"
        f"  Lệnh thực thi            : {command_str}\n"
        f"  Mã thoát (Exit Code)     : {exit_code}\n"
        "======================================================================\n\n"
    )


def render_log_image(title: str, lines: list[str], out_png: Path) -> None:
    font_paths = [
        r"C:\Windows\Fonts\consola.ttf",
        r"C:\Windows\Fonts\cour.ttf",
    ]
    font_bold_paths = [
        r"C:\Windows\Fonts\consolab.ttf",
        r"C:\Windows\Fonts\courbd.ttf",
    ]
    font = ImageFont.load_default()
    font_bold = ImageFont.load_default()
    for fp in font_paths:
        if Path(fp).exists():
            font = ImageFont.truetype(fp, 15)
            break
    for fp in font_bold_paths:
        if Path(fp).exists():
            font_bold = ImageFont.truetype(fp, 15)
            break

    pad_x = 28
    pad_y = 24
    line_h = 22
    header_h = 46
    width = 1120
    height = header_h + pad_y * 2 + len(lines) * line_h

    img = Image.new("RGB", (width, height), (248, 250, 252))
    draw = ImageDraw.Draw(img)

    # Viền ngoài và thanh tiêu đề ghi rõ "Đầu ra thực nghiệm trình bày lại từ log"
    draw.rectangle([0, 0, width - 1, height - 1], outline=(203, 213, 225), width=2)
    draw.rectangle([2, 2, width - 3, header_h], fill=(226, 232, 240))
    draw.line([(2, header_h), (width - 3, header_h)], fill=(203, 213, 225), width=1)

    banner_text = f"ĐẦU RA THỰC NGHIỆM TRÌNH BÀY LẠI TỪ LOG — {title}"
    draw.text((pad_x, 14), banner_text, font=font_bold, fill=(15, 23, 42))

    y = header_h + pad_y
    for line in lines:
        color = (30, 41, 59)
        use_font = font
        if "[PASS]" in line or "SUMMARY:" in line:
            color = (21, 128, 61)
            use_font = font_bold
        elif "[FAIL]" in line:
            color = (185, 28, 28)
            use_font = font_bold
        elif line.startswith("$ ") or line.startswith("-> Exit code:"):
            color = (30, 64, 175)
            use_font = font_bold
        elif line.startswith("===") or line.startswith("---"):
            color = (100, 116, 139)

        draw.text((pad_x, y), line, font=use_font, fill=color)
        y += line_h

    img.save(out_png)


def collect(workspace: str) -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    ts_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    env_info = get_env_info()
    fingerprint = source_fingerprint()
    prefix = "cd " + shlex.quote(workspace) + " && "
    # A failed recollection must not leave an older success eligible for publication.
    (EVIDENCE_DIR / "test_results.json").unlink(missing_ok=True)

    # Rebuild without deleting unrelated previews in build/.
    cmd_test = "make -B && make test"
    rc_test, out_test, err_test = run_wsl_bash(
        prefix + "make -B && make test"
    )
    full_test_log = (
        format_log_header(env_info, cmd_test, rc_test, ts_utc)
        + out_test
        + (f"\n[STDERR]\n{err_test}" if err_test.strip() else "")
    )
    (EVIDENCE_DIR / "test_suite_report.txt").write_text(full_test_log, encoding="utf-8")
    test_summary = parse_summary(out_test)
    test_cases = parse_individual_tests(out_test)

    # 2. Chạy make sanitize (ASan + UBSan + LSan trên toàn bộ bộ kiểm thử)
    cmd_san = "make sanitize"
    rc_san, out_san, err_san = run_wsl_bash(prefix + "make sanitize")
    (EVIDENCE_DIR / "memory_sanitizer_report.txt").write_text(
        format_log_header(env_info, cmd_san, rc_san, ts_utc) + out_san + "\n[STDERR]\n" + err_san, encoding="utf-8")
    san_summary = parse_summary(out_san)
    san_diagnostics = err_san.strip() if err_san.strip() else "Không có cảnh báo hoặc lỗi phát sinh từ ASan/UBSan/LSan trên stderr."

    full_san_log = (
        format_log_header(env_info, cmd_san, rc_san, ts_utc)
        + out_san
        + "\n----------------------------------------------------------------------\n"
        + "  CHẨN ĐOÁN BỘ NHỚ & HÀNH VI BẤT ĐỊNH (SANITIZER DIAGNOSTICS)\n"
        + "----------------------------------------------------------------------\n"
        + f"  Công cụ   : GCC AddressSanitizer (ASan), UndefinedBehaviorSanitizer (UBSan), LeakSanitizer (LSan)\n"
        + f"  Cờ biên dịch: -fsanitize=address,undefined -fno-omit-frame-pointer -O2 -g\n"
        + f"  Phạm vi   : Chạy toàn bộ {san_summary['total']} kịch bản trong tests/run_tests.sh bằng binary ./myls_sanitize\n"
        + f"  Diagnostics: {san_diagnostics}\n"
        + f"  Kết quả   : {san_summary['passed']}/{san_summary['total']} đạt; {san_summary['failed']} lỗi; {san_summary['skipped']} bỏ qua; mã thoát {rc_san}. Xem diagnostics và từng ca ở trên.\n"
    )
    (EVIDENCE_DIR / "memory_sanitizer_report.txt").write_text(full_san_log, encoding="utf-8")

    # 3. Chạy make demo
    cmd_demo = "make demo"
    rc_demo, out_demo, err_demo = run_wsl_bash(prefix + "make demo")
    full_demo_log = (
        format_log_header(env_info, cmd_demo, rc_demo, ts_utc)
        + out_demo
        + (f"\n[STDERR]\n{err_demo}" if err_demo.strip() else "")
    )
    (EVIDENCE_DIR / "demo_session_output.txt").write_text(full_demo_log, encoding="utf-8")

    # 4. Xuất file JSON có cấu trúc làm nguồn số liệu duy nhất cho Báo cáo và Slides
    if rc_test != 0 or rc_san != 0 or rc_demo != 0 or test_summary['failed'] or san_summary['failed']:
        raise RuntimeError("Verification failed; logs saved, no structured success published")
    if len(test_cases) != test_summary['total']:
        raise ValueError("Individual cases do not match test summary")
    san_cases = parse_individual_tests(out_san)
    if len(san_cases) != san_summary['total']:
        raise ValueError("Sanitizer cases do not match test summary")
    if fingerprint != source_fingerprint():
        raise RuntimeError("Sources changed during verification; collect again")
    structured_data = {
        "execution_root": "isolated Linux /tmp copy of src, include, tests and Makefile",
        "source_sha256": fingerprint,
        "timestamp_utc": ts_utc,
        "environment": env_info,
        "regular_suite": {
            "command": cmd_test,
            "exit_code": rc_test,
            "passed": test_summary["passed"],
            "failed": test_summary["failed"],
            "skipped": test_summary["skipped"],
            "total": test_summary["total"],
            "cases": test_cases,
        },
        "sanitizer_suite": {
            "cases": san_cases,
            "command": cmd_san,
            "exit_code": rc_san,
            "passed": san_summary["passed"],
            "failed": san_summary["failed"],
            "skipped": san_summary["skipped"],
            "total": san_summary["total"],
            "diagnostics": san_diagnostics,
            "statement": (
                "Không phát hiện lỗi bộ nhớ trong các kịch bản đã chạy bằng "
                "GCC AddressSanitizer, LeakSanitizer và UndefinedBehaviorSanitizer "
                f"trên toàn bộ {san_summary['total']} kịch bản kiểm thử."
            ),
        },
        "demo_run": {
            "command": cmd_demo,
            "exit_code": rc_demo,
            "raw_output": out_demo,
        },
    }
    (EVIDENCE_DIR / "test_results.json").write_text(
        json.dumps(structured_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 5. Sinh 3 ảnh PNG trình bày lại từ log thực nghiệm
    # Excerpts stay readable on paper; complete, unedited output remains in .txt/.json.
    selected_ids = {1, 16, 18, 22, 26, 27, 28, 32, 33, 34, 35, 36, 37}
    test_lines = ["$ make test", "[Trich doan; log day du: evidence/test_suite_report.txt]"]
    test_lines += [line for line in out_test.splitlines() if
                   (re.search(r"Test\s+(\d+):", line) and int(re.search(r"Test\s+(\d+):", line).group(1)) in selected_ids)
                   or "SUMMARY:" in line]
    render_log_image(
        "evidence/test_suite_report.txt (make test)",
        test_lines,
        EVIDENCE_DIR / "test_suite_capture.png",
    )

    demo_lines = out_demo.splitlines()
    # Chia demo_lines thành phần cơ bản (-a, -lS) và phần đệ quy/lỗi (-alRS, operand lỗi)
    split_idx = 0
    for idx, l in enumerate(demo_lines):
        if l.strip().startswith("$ ./myls -alRS"):
            split_idx = idx
            break

    if split_idx > 0:
        start_idx = next(i for i, line in enumerate(demo_lines) if line == "$ ./myls")
        basic_lines = demo_lines[start_idx:split_idx]
        combined_lines = demo_lines[split_idx:]
    else:
        basic_lines = demo_lines
        combined_lines = demo_lines

    render_log_image(
        "evidence/demo_session_output.txt (Mặc định, -a, -lS)",
        basic_lines,
        EVIDENCE_DIR / "demo_basic_flags_capture.png",
    )
    render_log_image(
        "evidence/demo_session_output.txt (-alRS và xử lý đối số lỗi)",
        combined_lines,
        EVIDENCE_DIR / "demo_combined_alRS_capture.png",
    )

    print(f"[OK] Collected evidence: {test_summary['passed']}/{test_summary['total']} regular, {san_summary['passed']}/{san_summary['total']} sanitizer; skipped={test_summary['skipped']}/{san_summary['skipped']}.")


def main() -> None:
    with isolated_workspace() as workspace:
        collect(workspace)


if __name__ == "__main__":
    main()
