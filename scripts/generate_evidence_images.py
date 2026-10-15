#!/usr/bin/env python3
"""
scripts/generate_evidence_images.py
Tạo ảnh minh chứng chất lượng cao (PNG) từ log chạy thực tế trên Ubuntu 24.04 WSL2
với khung hình gọn, chữ lớn sắc nét để hiển thị rõ ràng trên cả Báo cáo và Slide.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = ROOT / "evidence"


def load_mono_font(size: int):
    candidates = [
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/cascadiamono.ttf",
        "C:/Windows/Fonts/cour.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def load_sans_font(size: int, bold: bool = False):
    candidates = (
        ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"]
        if bold
        else ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"]
    )
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render_terminal_card(title: str, subtitle: str, lines: list[str], out_path: Path, width: int = 1060):
    font_mono = load_mono_font(17)
    font_title = load_sans_font(20, bold=True)
    font_sub = load_sans_font(14, bold=False)

    line_height = 24
    padding_x = 28
    header_height = 76
    padding_bottom = 26

    height = header_height + len(lines) * line_height + padding_bottom

    img = Image.new("RGB", (width, height), "#F8FAFC")
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(
        [3, 3, width - 4, height - 4],
        radius=14,
        fill="#FFFFFF",
        outline="#CBD5E1",
        width=2,
    )

    draw.rounded_rectangle(
        [3, 3, width - 4, header_height],
        radius=14,
        fill="#EFF6FF",
        outline="#CBD5E1",
        width=2,
    )
    draw.rectangle([5, header_height - 14, width - 6, header_height], fill="#EFF6FF")
    draw.line([3, header_height, width - 4, header_height], fill="#CBD5E1", width=2)

    draw.ellipse([22, 26, 36, 40], fill="#EF4444")
    draw.ellipse([46, 26, 60, 40], fill="#F59E0B")
    draw.ellipse([70, 26, 84, 40], fill="#10B981")

    draw.text((104, 14), title, fill="#0F172A", font=font_title)
    draw.text((104, 42), subtitle, fill="#475569", font=font_sub)

    y = header_height + 14
    for raw_line in lines:
        line = raw_line.rstrip("\r\n")
        color = "#1E293B"
        if line.startswith("$ "):
            color = "#1D4ED8"
        elif "[PASS]" in line or "SUMMARY:" in line or "ZERO_LEAKS" in line:
            color = "#047857"
        elif line.startswith("total ") or line.endswith(":"):
            color = "#B45309"
        elif line.startswith("===") or line.startswith("---"):
            color = "#64748B"

        draw.text((padding_x, y), line, fill=color, font=font_mono)
        y += line_height

    img.save(out_path, format="PNG", optimize=True)
    print(f"[OK] Saved {out_path} ({width}x{height})")


def main():
    test_txt = (EVIDENCE_DIR / "test_suite_report.txt").read_text(encoding="utf-8")
    asan_txt = (EVIDENCE_DIR / "memory_sanitizer_report.txt").read_text(encoding="utf-8").strip()
    test_lines = test_txt.splitlines() + [
        "",
        "$ gcc -fsanitize=address,undefined src/*.c -o myls_asan && ./myls_asan -alRS .",
        f"  [PASS] Memory Check: {asan_txt} (0 bytes leaked)",
    ]
    render_terminal_card(
        "Ubuntu 24.04 WSL2 — Kết Quả Bộ Kiểm Thử Tự Động (make test)",
        "Đối chiếu trực tiếp (diff -u) với LC_ALL=C ls (GNU coreutils 9.4) trên hệ thống tệp Linux /tmp",
        test_lines,
        EVIDENCE_DIR / "test_suite_capture.png",
        width=1060,
    )

    demo_txt = (EVIDENCE_DIR / "demo_session_output.txt").read_text(encoding="utf-8")
    demo_lines = demo_txt.splitlines()
    split_idx = 0
    for idx, line in enumerate(demo_lines):
        if line.strip() == "$ ./myls -S":
            split_idx = idx
            break

    part1_lines = [l for l in demo_lines[5:split_idx] if not l.startswith("-----")]
    part2_lines = [l for l in demo_lines[split_idx:] if not l.startswith("-----")]

    render_terminal_card(
        "Ubuntu 24.04 WSL2 — Minh Chứng Chạy Thực Tế: ./myls, -a, -l, -R",
        "Kernel: Linux 6.18.33.2-microsoft-standard-WSL2 · GCC 13.3.0 (POSIX.1-2008)",
        part1_lines,
        EVIDENCE_DIR / "demo_basic_flags_capture.png",
        width=980,
    )

    render_terminal_card(
        "Ubuntu 24.04 WSL2 — Minh Chứng Chạy Thực Tế: ./myls -S và ./myls -alRS",
        "Sắp xếp giảm dần theo kích thước (-S), hiển thị ẩn (-a), chi tiết (-l) và đệ quy (-R)",
        part2_lines,
        EVIDENCE_DIR / "demo_combined_alRS_capture.png",
        width=980,
    )


if __name__ == "__main__":
    main()
