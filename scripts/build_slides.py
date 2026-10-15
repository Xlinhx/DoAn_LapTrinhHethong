#!/usr/bin/env python3
"""
scripts/build_slides.py
Thiết kế bộ Slide thuyết trình Đồ án Lập trình Hệ thống (Đề tài 17: myls -a -l -R -S)
Lưu tại: docs/Slides.pptx và xuất ảnh từng slide ra docs/slide_previews/ để review thị giác.

Nguyên tắc thiết kế (Tuân thủ yêu cầu người dùng & slide-maker):
1. NỀN SÁNG 100% (Light Editorial Theme: Warm Ivory #FAF8F5 / Soft Alabaster #F4F7FB),
   tuyệt đối không dùng slide nền tối.
2. 12 SLIDES = 12 LAYOUT KHÁC NHAU HOÀN TOÀN (Không lặp lại bố cục nhàm chán).
3. Ít chữ, cô đọng, giải thích đánh số tuần tự "Tại sao A phải B", chữ và ảnh bổ trợ chặt chẽ.
4. Sử dụng các vật thể 3D minh họa đã tách nền trong suốt (transparent PNG) trong docs/assets/cutouts/
   và ảnh chụp kết quả chạy thực tế trong evidence/.
"""

from pathlib import Path
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
CUTOUTS_DIR = DOCS_DIR / "assets" / "cutouts"
EVIDENCE_DIR = ROOT / "evidence"
PREVIEW_DIR = DOCS_DIR / "slide_previews"

# Bảng màu Light Editorial Palette (Sáng, rõ nét, tương phản cao)
BG_WARM_IVORY = RGBColor(0xFA, 0xF8, 0xF5)
BG_SOFT_BLUE = RGBColor(0xF4, 0xF7, 0xFB)
SURFACE_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
SURFACE_TINT_BLUE = RGBColor(0xEF, 0xF6, 0xFF)
SURFACE_TINT_AMBER = RGBColor(0xFF, 0xFB, 0xEB)
SURFACE_TINT_GREEN = RGBColor(0xEC, 0xFD, 0xF5)
SURFACE_TINT_RED = RGBColor(0xFE, 0xF2, 0xF2)
SURFACE_SLATE = RGBColor(0xF1, 0xF5, 0xF9)

INK_NAVY = RGBColor(0x0F, 0x17, 0x2A)
INK_BODY = RGBColor(0x33, 0x41, 0x55)
INK_MUTED = RGBColor(0x64, 0x74, 0x8B)
INK_WHITE = RGBColor(0xFF, 0xFF, 0xFF)

ACCENT_BLUE = RGBColor(0x1E, 0x40, 0xAF)
ACCENT_BLUE_LIGHT = RGBColor(0x3B, 0x82, 0xF6)
ACCENT_AMBER = RGBColor(0xD9, 0x77, 0x06)
ACCENT_GREEN = RGBColor(0x05, 0x96, 0x69)
ACCENT_RED = RGBColor(0xDC, 0x26, 0x26)
ACCENT_PURPLE = RGBColor(0x6D, 0x28, 0xD9)
BORDER_LIGHT = RGBColor(0xCB, 0xD5, 0xE1)

FONT_SANS = "Segoe UI"
FONT_MONO = "Consolas"


def set_slide_bg(slide, color: RGBColor):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_box(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    fill_color: RGBColor | None = SURFACE_WHITE,
    border_color: RGBColor | None = BORDER_LIGHT,
    border_pt: float = 1.0,
    shape_type=MSO_SHAPE.ROUNDED_RECTANGLE,
    corner_radius: float = 0.04,
):
    sh = slide.shapes.add_shape(
        shape_type, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    if shape_type == MSO_SHAPE.ROUNDED_RECTANGLE and len(sh.adjustments) > 0:
        sh.adjustments[0] = corner_radius
    if fill_color is not None:
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill_color
    else:
        sh.fill.background()

    if border_color is not None and border_pt > 0:
        sh.line.color.rgb = border_color
        sh.line.width = Pt(border_pt)
    else:
        sh.line.fill.background()
    return sh


def add_text(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    text: str,
    font_size: float = 14,
    bold: bool = False,
    italic: bool = False,
    color: RGBColor = INK_NAVY,
    font_name: str = FONT_SANS,
    align=PP_ALIGN.LEFT,
    valign=MSO_ANCHOR.TOP,
    line_spacing: float = 1.15,
):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = valign
    tf.margin_left = Inches(0.04)
    tf.margin_right = Inches(0.04)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)

    lines = text.split("\n")
    for idx, line in enumerate(lines):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        p.space_after = Pt(3 if len(lines) > 1 else 0)
        r = p.add_run()
        r.text = line
        r.font.name = font_name
        r.font.size = Pt(font_size)
        r.font.bold = bold
        r.font.italic = italic
        r.font.color.rgb = color
    return tb


def add_rich_bullets(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    items: list[tuple[str, str]],
    font_size: float = 13.5,
    lead_color: RGBColor = ACCENT_BLUE,
    body_color: RGBColor = INK_BODY,
    space_after_pt: float = 6,
):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.04)
    tf.margin_right = Inches(0.04)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)

    for idx, (lead, body) in enumerate(items):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.line_spacing = 1.18
        p.space_after = Pt(space_after_pt)

        r1 = p.add_run()
        r1.text = lead
        r1.font.name = FONT_SANS
        r1.font.size = Pt(font_size)
        r1.font.bold = True
        r1.font.color.rgb = lead_color

        r2 = p.add_run()
        r2.text = body
        r2.font.name = FONT_SANS
        r2.font.size = Pt(font_size)
        r2.font.bold = False
        r2.font.color.rgb = body_color
    return tb


def add_header_chrome(
    slide,
    slide_num: int,
    section_tag: str,
    title: str,
    subtitle: str,
    tag_color: RGBColor = ACCENT_BLUE,
):
    # Thanh điều hướng phía trên (đủ rộng để luôn nằm trên 1 dòng duy nhất)
    add_box(
        slide,
        0.55,
        0.34,
        3.65,
        0.32,
        fill_color=tag_color,
        border_color=None,
        corner_radius=0.5,
    )
    add_text(
        slide,
        0.62,
        0.36,
        3.50,
        0.28,
        f"SLIDE {slide_num:02d}/12  ·  {section_tag}",
        font_size=9.5,
        bold=True,
        color=INK_WHITE,
        align=PP_ALIGN.CENTER,
        valign=MSO_ANCHOR.MIDDLE,
    )

    # Chuỗi tiến trình 4 chặng ở góc phải trên (mỗi pill rộng 1.48 inch, luôn 1 dòng)
    stages = ["1. Nền tảng", "2. Kiến trúc", "3. Giải phẫu C", "4. Thực nghiệm WSL2"]
    active_stage = 0 if slide_num <= 3 else (1 if slide_num <= 4 else (2 if slide_num <= 7 else 3))
    sx = 6.65
    for idx, st_name in enumerate(stages):
        is_act = idx == active_stage
        add_box(
            slide,
            sx,
            0.34,
            1.48,
            0.32,
            fill_color=SURFACE_TINT_BLUE if is_act else SURFACE_WHITE,
            border_color=ACCENT_BLUE if is_act else BORDER_LIGHT,
            border_pt=1.5 if is_act else 0.75,
            corner_radius=0.4,
        )
        add_text(
            slide,
            sx,
            0.36,
            1.48,
            0.28,
            st_name,
            font_size=8.8,
            bold=is_act,
            color=ACCENT_BLUE if is_act else INK_MUTED,
            align=PP_ALIGN.CENTER,
            valign=MSO_ANCHOR.MIDDLE,
        )
        sx += 1.54

    # Tiêu đề chính và phụ đề dẫn nhập
    add_text(
        slide,
        0.55,
        0.74,
        12.2,
        0.48,
        title,
        font_size=22,
        bold=True,
        color=INK_NAVY,
    )
    add_text(
        slide,
        0.55,
        1.18,
        12.2,
        0.34,
        subtitle,
        font_size=12.5,
        italic=False,
        color=INK_MUTED,
    )


def add_picture_contain(slide, img_path: Path, box_l: float, box_t: float, box_w: float, box_h: float):
    if not img_path.exists():
        return None
    from PIL import Image

    with Image.open(img_path) as im:
        iw, ih = im.size
    aspect = iw / float(ih)
    box_aspect = box_w / float(box_h)

    if aspect > box_aspect:
        w = box_w
        h = box_w / aspect
        l = box_l
        t = box_t + (box_h - h) / 2.0
    else:
        h = box_h
        w = box_h * aspect
        t = box_t
        l = box_l + (box_w - w) / 2.0

    return slide.shapes.add_picture(str(img_path), Inches(l), Inches(t), Inches(w), Inches(h))


# ==============================================================================
# SLIDE 1: HERO COVER (Bố cục Bất đối xứng + Vật thể 3D Tách nền Trong suốt)
# ==============================================================================
def build_slide_01(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_WARM_IVORY)

    # Vòng tròn trang trí nền sáng phía sau vật thể 3D
    add_box(
        slide,
        7.35,
        0.65,
        5.4,
        5.4,
        fill_color=SURFACE_TINT_BLUE,
        border_color=RGBColor(0xBF, 0xDB, 0xFE),
        border_pt=1.5,
        shape_type=MSO_SHAPE.OVAL,
    )
    add_box(
        slide,
        8.05,
        1.35,
        4.0,
        4.0,
        fill_color=SURFACE_WHITE,
        border_color=RGBColor(0xDB, 0xE9, 0xFE),
        border_pt=1.0,
        shape_type=MSO_SHAPE.OVAL,
    )

    # Thanh accent dọc bên trái
    add_box(
        slide,
        0.60,
        0.75,
        0.10,
        5.8,
        fill_color=ACCENT_BLUE,
        border_color=None,
        shape_type=MSO_SHAPE.RECTANGLE,
    )

    # Huy hiệu trường & môn học
    add_box(
        slide,
        0.90,
        0.75,
        5.2,
        0.38,
        fill_color=SURFACE_TINT_BLUE,
        border_color=ACCENT_BLUE,
        border_pt=1.0,
        corner_radius=0.5,
    )
    add_text(
        slide,
        1.02,
        0.79,
        5.0,
        0.30,
        "VKU · HỌC PHẦN LẬP TRÌNH HỆ THỐNG · ĐỀ TÀI 17",
        font_size=10.5,
        bold=True,
        color=ACCENT_BLUE,
        valign=MSO_ANCHOR.MIDDLE,
    )

    add_text(
        slide,
        0.90,
        1.28,
        6.3,
        1.75,
        "Tự Cài Đặt Lệnh ls\nVới -a, -l, -R, -S\nBằng POSIX C Trên Linux",
        font_size=30,
        bold=True,
        color=INK_NAVY,
        line_spacing=1.08,
    )

    add_text(
        slide,
        0.90,
        3.22,
        6.1,
        0.85,
        "Giải phẫu từ bản chất Dentry & Inode trong nhân Linux đến kiến trúc 5 module C chuẩn POSIX.1-2008, vượt qua 15/15 kịch bản đối chiếu trực tiếp với GNU ls trên Ubuntu 24.04 WSL2.",
        font_size=13.0,
        color=INK_BODY,
        line_spacing=1.22,
    )

    # 3 Thẻ thông tin nhanh ở góc dưới trái
    cards = [
        ("SINH VIÊN THỰC HIỆN", "Nguyễn Xuân Lĩnh", ACCENT_BLUE, SURFACE_WHITE),
        ("CHUẨN BIÊN DỊCH", "C11 · POSIX.1-2008\nGCC 13.3 (Ubuntu WSL2)", ACCENT_AMBER, SURFACE_WHITE),
        ("KIỂM THỬ THỰC NGHIỆM", "15/15 PASS (GNU ls)\n0 Memory Leaks", ACCENT_GREEN, SURFACE_WHITE),
    ]
    cx = 0.90
    for label, val, col, bg in cards:
        add_box(slide, cx, 4.30, 2.02, 1.08, fill_color=bg, border_color=BORDER_LIGHT, border_pt=1.0, corner_radius=0.08)
        add_box(slide, cx, 4.30, 2.02, 0.08, fill_color=col, border_color=None, shape_type=MSO_SHAPE.RECTANGLE)
        add_text(slide, cx + 0.12, 4.42, 1.80, 0.24, label, font_size=8.5, bold=True, color=col)
        add_text(slide, cx + 0.12, 4.68, 1.80, 0.62, val, font_size=10.8, bold=True, color=INK_NAVY, line_spacing=1.12)
        cx += 2.14

    # Thanh repo GitHub phía dưới
    add_box(
        slide,
        0.90,
        5.62,
        6.30,
        0.58,
        fill_color=SURFACE_WHITE,
        border_color=BORDER_LIGHT,
        border_pt=1.0,
        corner_radius=0.12,
    )
    add_text(
        slide,
        1.08,
        5.73,
        6.0,
        0.36,
        "GitHub Repository:  https://github.com/Xlinhx/DoAn_LapTrinhHethong",
        font_size=11.5,
        bold=True,
        font_name=FONT_MONO,
        color=ACCENT_BLUE,
    )

    # Vật thể 3D tách nền trong suốt bên phải
    add_picture_contain(slide, CUTOUTS_DIR / "hero_inode_tree.png", 7.45, 0.78, 5.2, 5.1)

    # Nhãn chú thích nổi dưới hình minh họa
    add_box(
        slide,
        7.85,
        6.05,
        4.45,
        0.52,
        fill_color=SURFACE_WHITE,
        border_color=ACCENT_BLUE,
        border_pt=1.2,
        corner_radius=0.2,
    )
    add_text(
        slide,
        7.95,
        6.13,
        4.25,
        0.36,
        "Mô hình Cây thư mục (Dentry) liên kết trực tiếp Bảng Inode",
        font_size=10.5,
        bold=True,
        color=INK_NAVY,
        align=PP_ALIGN.CENTER,
    )


# ==============================================================================
# SLIDE 2: BÀI TOÁN & 4 TRỤ CỘT (Layout Top Contrast Banner + 2x2 Bento Grid)
# ==============================================================================
def build_slide_02(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_SOFT_BLUE)
    add_header_chrome(
        slide,
        2,
        "PHẦN 1 · BÀI TOÁN & YÊU CẦU",
        "1. Tại Sao Phải Tự Viết myls Bằng System Calls Thay Vì Gọi system(\"ls\")?",
        "Đi từ yêu cầu đề tài 17 đến 4 cờ cốt lõi (-a, -l, -R, -S) giao tiếp trực tiếp với nhân Linux.",
    )

    # Banner đối chiếu ở trên: Cách làm sai (Shell Wrapper) vs Cách làm đúng (POSIX System Calls)
    add_box(slide, 0.55, 1.65, 5.95, 1.25, fill_color=SURFACE_TINT_RED, border_color=ACCENT_RED, border_pt=1.2, corner_radius=0.06)
    add_text(slide, 0.75, 1.75, 5.6, 0.30, "CÁCH LÀM SAI TRONG MÔN LẬP TRÌNH HỆ THỐNG", font_size=11, bold=True, color=ACCENT_RED)
    add_text(
        slide,
        0.75,
        2.06,
        5.6,
        0.72,
        "Gọi hàm system(\"ls -alRS\") hoặc popen(): Chỉ nhờ Shell chạy hộ chương trình có sẵn của OS, không đụng tới Inode hay cây thư mục (mất điểm phần thuật toán).",
        font_size=12,
        color=INK_BODY,
    )

    add_box(slide, 6.80, 1.65, 5.95, 1.25, fill_color=SURFACE_TINT_GREEN, border_color=ACCENT_GREEN, border_pt=1.2, corner_radius=0.06)
    add_text(slide, 7.00, 1.75, 5.6, 0.30, "GIẢI PHÁP CỦA DỰ ÁN: 100% POSIX SYSTEM CALLS & LIBC", font_size=11, bold=True, color=ACCENT_GREEN)
    add_text(
        slide,
        7.00,
        2.06,
        5.6,
        0.72,
        "Tự cài đặt toàn bộ bằng opendir(), readdir(), closedir(), lstat(), readlink(), getpwuid(), getgrgid(), localtime_r() và qsort() chuẩn POSIX.1-2008.",
        font_size=12,
        color=INK_BODY,
    )

    # 2x2 Bento Grid cho 4 cờ -a, -l, -R, -S
    bento = [
        (
            0.55,
            3.12,
            "-a",
            "Hiển Thị Tệp Ẩn (All Entries)",
            ACCENT_BLUE,
            SURFACE_TINT_BLUE,
            [
                ("• Quy ước Linux: ", "Mọi tệp bắt đầu bằng dấu '.' (như '.', '..', '.env') là tệp ẩn."),
                ("• Cơ chế cài đặt: ", "Mặc định bỏ qua d_name[0] == '.'; khi bật -a thì nạp toàn bộ vào danh sách."),
            ],
        ),
        (
            6.80,
            3.12,
            "-l",
            "Danh Sách Chi Tiết (Long Format)",
            ACCENT_AMBER,
            SURFACE_TINT_AMBER,
            [
                ("• Giải mã Inode: ", "10 ký tự quyền (rwx + SUID/SGID/Sticky), số hard link, Owner, Group, Size."),
                ("• Chuẩn GNU ls: ", "In 'total = sum(st_blocks)/2', quy tắc mtime 6 tháng và đọc đích Symlink '->'."),
            ],
        ),
        (
            0.55,
            5.15,
            "-R",
            "Duyệt Đệ Quy Đa Tầng (Recursive)",
            ACCENT_GREEN,
            SURFACE_TINT_GREEN,
            [
                ("• Thứ tự duyệt: ", "In hết toàn bộ mục của thư mục hiện tại rồi mới đệ quy xuống thư mục con."),
                ("• An toàn tuyệt đối: ", "Đóng closedir() trước khi đệ quy; chặn '.', '..' và Symlink để chống lặp vô hạn."),
            ],
        ),
        (
            6.80,
            5.15,
            "-S",
            "Sắp Xếp Theo Kích Thước (Size Sort)",
            ACCENT_PURPLE,
            SURFACE_SLATE,
            [
                ("• Thứ tự giảm dần: ", "Tệp nặng nhất đứng đầu dựa trên trường st_size (kiểu 64-bit off_t)."),
                ("• Phân định trùng: ", "Nếu 2 tệp bằng kích thước, tie-break bằng strcmp(name) từ A -> Z."),
            ],
        ),
    ]

    for bx, by, flag, heading, col, badge_bg, bullets in bento:
        add_box(slide, bx, by, 5.95, 1.82, fill_color=SURFACE_WHITE, border_color=BORDER_LIGHT, border_pt=1.0, corner_radius=0.06)
        add_box(slide, bx + 0.20, by + 0.20, 0.90, 0.52, fill_color=col, border_color=None, corner_radius=0.18)
        add_text(slide, bx + 0.20, by + 0.23, 0.90, 0.45, flag, font_size=18, bold=True, font_name=FONT_MONO, color=INK_WHITE, align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE)
        add_text(slide, bx + 1.25, by + 0.24, 4.5, 0.40, heading, font_size=15.5, bold=True, color=INK_NAVY)
        add_rich_bullets(slide, bx + 0.20, by + 0.82, 5.55, 0.92, bullets, font_size=12.0, lead_color=col, space_after_pt=4)


# ==============================================================================
# SLIDE 3: BẢN CHẤT DENTRY VS INODE (Layout 3-Column Diagram + Cutout Kính Lúp)
# ==============================================================================
def build_slide_03(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_WARM_IVORY)
    add_header_chrome(
        slide,
        3,
        "PHẦN 1 · CƠ SỞ HỆ THỐNG",
        "2. Tại Sao Chỉ Gọi readdir() Thì Không Thể Làm Được Cờ -l Và -S?",
        "Bản chất tách biệt giữa 'Danh bạ tên tệp' (Directory Entry) và 'Hồ sơ gốc' (Inode) trong Linux.",
    )

    # Cột 1: Thư mục (Danh bạ mỏng)
    add_box(slide, 0.55, 1.70, 4.15, 4.35, fill_color=SURFACE_WHITE, border_color=ACCENT_BLUE, border_pt=1.5, corner_radius=0.06)
    add_box(slide, 0.55, 1.70, 4.15, 0.55, fill_color=ACCENT_BLUE, border_color=None, shape_type=MSO_SHAPE.RECTANGLE)
    add_text(slide, 0.70, 1.80, 3.85, 0.36, "BƯỚC 1: THƯ MỤC (Đọc bằng readdir)", font_size=13.5, bold=True, color=INK_WHITE)
    add_text(
        slide,
        0.75,
        2.38,
        3.75,
        0.85,
        "Thư mục trong Linux chỉ là một 'cuốn danh bạ mỏng' gồm đúng 2 cột: Tên tệp và Mã số Inode.",
        font_size=12.5,
        color=INK_BODY,
    )
    # Bảng giả lập Dentry (đủ độ rộng cho cả 2 cột trên 1 dòng)
    dentries = [
        ("d_name (Tên tệp)", "d_ino (Inode)"),
        ("dataset_large.bin", "#40912"),
        (".env.hidden", "#40915"),
        ("latest_data.lnk", "#40918"),
        ("src_module", "#40920"),
    ]
    dy = 3.30
    for idx, (dn, dino) in enumerate(dentries):
        is_hdr = idx == 0
        add_box(slide, 0.75, dy, 3.75, 0.42, fill_color=SURFACE_TINT_BLUE if is_hdr else SURFACE_SLATE, border_color=BORDER_LIGHT, border_pt=0.75, shape_type=MSO_SHAPE.RECTANGLE)
        add_text(slide, 0.85, dy + 0.08, 2.05, 0.28, dn, font_size=10.5, bold=is_hdr, font_name=FONT_MONO, color=ACCENT_BLUE if is_hdr else INK_NAVY)
        add_text(slide, 2.95, dy + 0.08, 1.50, 0.28, dino, font_size=10.5, bold=is_hdr, font_name=FONT_MONO, color=ACCENT_AMBER if not is_hdr else ACCENT_BLUE)
        dy += 0.44
    add_text(slide, 0.75, 5.58, 3.75, 0.36, "⚠ Không hề có Kích thước, Quyền hay Ngày giờ!", font_size=11.5, bold=True, color=ACCENT_RED)

    # Cột 2 (Giữa): Vật thể 3D Kính lúp tách nền + Mũi tên nối nhân quả
    add_picture_contain(slide, CUTOUTS_DIR / "dentry_magnifier.png", 4.95, 1.95, 3.40, 3.20)
    add_box(slide, 4.90, 5.22, 3.50, 0.82, fill_color=SURFACE_TINT_AMBER, border_color=ACCENT_AMBER, border_pt=1.2, corner_radius=0.12)
    add_text(
        slide,
        5.02,
        5.30,
        3.26,
        0.68,
        "Phải ghép đường dẫn join_path()\nrồi gọi tiếp lstat(full_path, &st)!",
        font_size=12,
        bold=True,
        color=ACCENT_AMBER,
        align=PP_ALIGN.CENTER,
    )

    # Cột 3: Bảng Inode (Hồ sơ gốc)
    add_box(slide, 8.65, 1.70, 4.10, 4.35, fill_color=SURFACE_WHITE, border_color=ACCENT_GREEN, border_pt=1.5, corner_radius=0.06)
    add_box(slide, 8.65, 1.70, 4.10, 0.55, fill_color=ACCENT_GREEN, border_color=None, shape_type=MSO_SHAPE.RECTANGLE)
    add_text(slide, 8.80, 1.80, 3.80, 0.36, "BƯỚC 2: BẢNG INODE (Đọc bằng lstat)", font_size=13.5, bold=True, color=INK_WHITE)

    inode_fields = [
        ("st_mode : ", "Loại tệp & 12 bit quyền (-rwxr-xr-x)"),
        ("st_nlink : ", "Số tên (Hard links) cùng trỏ vào Inode"),
        ("st_uid / gid : ", "Mã số Chủ sở hữu & Nhóm (1000)"),
        ("st_size : ", "Kích thước thực (8192 bytes) -> Dùng cho -S"),
        ("st_blocks : ", "Số khối đĩa 512B -> Chia 2 ra dòng 'total'"),
        ("st_mtime : ", "Thời điểm sửa đổi cuối -> In ngày giờ -l"),
    ]
    add_rich_bullets(slide, 8.85, 2.40, 3.75, 3.45, inode_fields, font_size=12.0, lead_color=ACCENT_GREEN, space_after_pt=8)

    # Thanh Kết luận Nhân - Quả ở đáy
    add_box(slide, 0.55, 6.22, 12.20, 0.68, fill_color=SURFACE_TINT_BLUE, border_color=ACCENT_BLUE, border_pt=1.0, corner_radius=0.08)
    add_text(
        slide,
        0.75,
        6.34,
        11.80,
        0.44,
        "KẾT LUẬN NHÂN - QUẢ:  readdir() chỉ cho biết TÊN TỆP  ──►  Muốn in chi tiết (-l) hoặc sắp xếp kích thước (-S), bắt buộc phải gọi lstat() để đọc INODE.",
        font_size=13,
        bold=True,
        color=ACCENT_BLUE,
        align=PP_ALIGN.CENTER,
    )


# ==============================================================================
# SLIDE 4: KIẾN TRÚC 5 MODULE & LUỒNG DỮ LIỆU (Layout 5-Step Pipeline + Dynamic Vector)
# ==============================================================================
def build_slide_04(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_SOFT_BLUE)
    add_header_chrome(
        slide,
        4,
        "PHẦN 2 · KIẾN TRÚC HỆ THỐNG",
        "3. Kiến Trúc 5 Module Độc Lập & Tại Sao Phải Gom Vào Mảng Động Trước Khi In?",
        "Thiết kế tách biệt trách nhiệm (Separation of Concerns) và cơ chế tự nhân đôi bộ nhớ bằng realloc().",
    )

    # Dải 5 bước Pipeline ngang
    steps = [
        ("01", "src/options.c", "Phân tích Cờ", "Dùng getopt() tách -a, -l, -R, -S (kể cả viết gộp -alRS). Bắt lỗi cờ sai -> exit(2).", ACCENT_BLUE),
        ("02", "src/main.c", "Tách Đối Số", "Phân loại đường dẫn thành file_list (in trước) và dir_list (in sau) đúng chuẩn POSIX.", ACCENT_PURPLE),
        ("03", "src/directory.c", "Đọc & Nạp Inode", "opendir -> readdir -> lstat -> readlink. Đóng closedir() ngay lập tức trước khi đệ quy.", ACCENT_GREEN),
        ("04", "src/sorting.c", "Sắp Xếp qsort()", "Mặc định: strcmp() A-Z.\nBật -S: st_size giảm dần + tie-break tên A-Z.", ACCENT_AMBER),
        ("05", "src/display.c", "Giải Mã & Căn Cột", "Quét độ rộng cột lớn nhất, in 'total', giải mã 16-bit st_mode & mtime 6 tháng.", ACCENT_RED),
    ]

    sx = 0.55
    for num, mod, name, desc, col in steps:
        add_box(slide, sx, 1.72, 2.30, 2.55, fill_color=SURFACE_WHITE, border_color=BORDER_LIGHT, border_pt=1.0, corner_radius=0.06)
        add_box(slide, sx, 1.72, 2.30, 0.42, fill_color=col, border_color=None, shape_type=MSO_SHAPE.RECTANGLE)
        add_text(slide, sx + 0.12, 1.78, 2.06, 0.30, f"BƯỚC {num} · {mod}", font_size=10.0, bold=True, font_name=FONT_MONO, color=INK_WHITE)
        add_text(slide, sx + 0.14, 2.24, 2.02, 0.34, name, font_size=14, bold=True, color=INK_NAVY)
        add_text(slide, sx + 0.14, 2.62, 2.02, 1.50, desc, font_size=11.5, color=INK_BODY, line_spacing=1.2)
        sx += 2.47

    # Nửa dưới: Giải thích Tại sao không vừa đọc vừa in ngay mà phải dùng EntryList động
    add_box(slide, 0.55, 4.50, 12.20, 2.40, fill_color=SURFACE_WHITE, border_color=ACCENT_BLUE, border_pt=1.2, corner_radius=0.05)
    add_text(
        slide,
        0.80,
        4.64,
        11.7,
        0.38,
        "TẠI SAO KHÔNG VỪA readdir() VỪA printf() NGAY MÀ PHẢI GOM VÀO MẢNG ĐỘNG EntryList?",
        font_size=14.5,
        bold=True,
        color=ACCENT_BLUE,
    )

    reasons = [
        (
            "Lý do 1: Phục vụ Sắp xếp (-S & A-Z)",
            "readdir() trả về thứ tự lưu trữ thô lộn xộn trên đĩa. Phải đọc hết 100% tệp trong thư mục vào RAM thì qsort() mới biết tệp nào nặng nhất để đưa lên đầu.",
            0.80,
        ),
        (
            "Lý do 2: Căn lề thẳng hàng trong -l",
            "Nếu tệp thứ 1 nặng 12B nhưng tệp thứ 50 nặng 1048576B, phải quét hết cả 50 tệp trước mới biết cột Size cần chừa trống 7 ký tự để các dòng thẳng cột.",
            4.80,
        ),
        (
            "Lý do 3: Tự nhân đôi bằng realloc()",
            "Không dùng mảng tĩnh a[1000] (dễ tràn khi gặp /usr/bin có >2000 tệp). EntryList khởi tạo capacity = 64 -> 128 -> 256... và giải phóng sạch 0 leak.",
            8.80,
        ),
    ]
    for rtitle, rbody, rx in reasons:
        add_box(slide, rx, 5.12, 3.70, 1.56, fill_color=SURFACE_TINT_BLUE, border_color=BORDER_LIGHT, border_pt=0.8, corner_radius=0.06)
        add_text(slide, rx + 0.16, 5.22, 3.38, 0.34, rtitle, font_size=12.5, bold=True, color=INK_NAVY)
        add_text(slide, rx + 0.16, 5.58, 3.38, 1.00, rbody, font_size=11.5, color=INK_BODY, line_spacing=1.18)


# ==============================================================================
# SLIDE 5: GIẢI PHẪU DÒNG -l & 16-BIT st_mode (Layout Callout Breakdown + Switchboard)
# ==============================================================================
def build_slide_05(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_WARM_IVORY)
    add_header_chrome(
        slide,
        5,
        "PHẦN 3 · GIẢI PHẪU KỸ THUẬT (-l)",
        "4. Giải Phẫu Một Dòng Xuất Của Cờ -l & Bảng Giải Mã 16-Bit st_mode",
        "Cách src/display.c biến các con số nguyên thô trong Inode thành chuỗi hiển thị chuẩn GNU ls.",
        tag_color=ACCENT_AMBER,
    )

    # Khung Specimen lớn ở giữa trên: Mổ xẻ từng thành phần của 1 dòng ls -l (trên 1 dòng duy nhất)
    add_box(slide, 0.55, 1.68, 12.20, 1.18, fill_color=SURFACE_WHITE, border_color=ACCENT_BLUE, border_pt=1.5, corner_radius=0.06)
    add_text(
        slide,
        0.75,
        1.74,
        11.8,
        0.26,
        "MỔ XẺ TRỰC QUAN 7 TRƯỜNG TRONG MỘT DÒNG XUẤT CỦA ./myls -l:",
        font_size=10.5,
        bold=True,
        color=ACCENT_BLUE,
    )
    add_text(
        slide,
        0.75,
        2.04,
        11.8,
        0.36,
        "lrwxrwxrwx   1   linhnxdeveloper   linhnxdeveloper    17   Oct 15 18:41   latest_data.lnk -> dataset_large.bin",
        font_size=13.2,
        bold=True,
        font_name=FONT_MONO,
        color=INK_NAVY,
    )
    add_text(
        slide,
        0.75,
        2.44,
        11.8,
        0.30,
        "[1. Loại & Quyền]  [2. Links]     [3. Owner]          [4. Group]       [5. Size]   [6. mtime 6 tháng]      [7. Tên & Đích Symlink (readlink)]",
        font_size=10.2,
        bold=True,
        font_name=FONT_MONO,
        color=ACCENT_AMBER,
    )

    # 4 Thẻ giải thích chi tiết bên trái (chiếm 7.55 inch)
    cards = [
        (
            "1. Giải mã 16-bit st_mode -> 10 ký tự ('-rwxr-sr-t')",
            "• Ký tự 0 (S_IFMT): '-' (File), 'd' (Dir), 'l' (Symlink), 'c', 'b', 'p', 's'.\n"
            "• Ký tự 1..9: 9 bit rwx kết hợp 3 bit đặc biệt SUID (s/S), SGID (s/S), Sticky bit (t/T).",
            ACCENT_BLUE,
        ),
        (
            "2. Tại sao dòng 'total' phải lấy tổng st_blocks chia 2?",
            "• Kernel Linux luôn đếm st_blocks theo đơn vị khối 512 Bytes.\n"
            "• GNU ls -l hiển thị dòng 'total' theo đơn vị khối 1024 Bytes (1 KB)  ──►  total = sum(st_blocks) / 2.",
            ACCENT_AMBER,
        ),
        (
            "3. Quy tắc Thời gian 6 Tháng của POSIX (st_mtime)",
            "• Nếu tệp sửa đổi trong vòng 6 tháng (< 15.778.476 giây): in 'Tháng Ngày Giờ:Phút' (Oct 15 18:41).\n"
            "• Nếu tệp cũ hơn 6 tháng (hoặc ở tương lai): tự động đổi sang in 'Tháng Ngày  Năm' (May 15  2022).",
            ACCENT_GREEN,
        ),
        (
            "4. Tra cứu UID/GID an toàn & Kết thúc chuỗi readlink()",
            "• Nếu getpwuid()/getgrgid() trả về NULL (UID mồ côi), tự động fallback in mã số nguyên UID/GID.\n"
            "• POSIX readlink() không tự thêm '\\0' -> bắt buộc gán tường minh link_buf[len] = '\\0'.",
            ACCENT_PURPLE,
        ),
    ]

    cy = 3.04
    for ctitle, cbody, col in cards:
        add_box(slide, 0.55, cy, 7.55, 0.92, fill_color=SURFACE_WHITE, border_color=BORDER_LIGHT, border_pt=1.0, corner_radius=0.06)
        add_box(slide, 0.55, cy, 0.12, 0.92, fill_color=col, border_color=None, shape_type=MSO_SHAPE.RECTANGLE)
        add_text(slide, 0.80, cy + 0.06, 7.15, 0.28, ctitle, font_size=12.5, bold=True, color=col)
        add_text(slide, 0.80, cy + 0.34, 7.15, 0.54, cbody, font_size=11.0, color=INK_BODY, line_spacing=1.15)
        cy += 0.99

    # Bên phải: Vật thể 3D Bảng công tắc 16-bit tách nền trong suốt + Sơ đồ Bit
    add_box(slide, 8.35, 3.04, 4.40, 3.89, fill_color=SURFACE_WHITE, border_color=BORDER_LIGHT, border_pt=1.0, corner_radius=0.06)
    add_picture_contain(slide, CUTOUTS_DIR / "bitmask_decoder.png", 8.55, 3.14, 4.00, 2.55)
    add_box(slide, 8.55, 5.78, 4.00, 0.98, fill_color=SURFACE_TINT_BLUE, border_color=ACCENT_BLUE, border_pt=1.0, corner_radius=0.08)
    add_text(
        slide,
        8.65,
        5.86,
        3.80,
        0.82,
        "Cấu trúc 16-bit st_mode:\n[15..12: Loại] [11..9: SUID/SGID/Sticky]\n[8..6: User] [5..3: Group] [2..0: Other]",
        font_size=11.0,
        bold=True,
        font_name=FONT_MONO,
        color=ACCENT_BLUE,
        align=PP_ALIGN.CENTER,
    )


# ==============================================================================
# SLIDE 6: TẠI SAO DÙNG lstat() THAY VÌ stat()? (Layout Dual-Track Visual Comparison)
# ==============================================================================
def build_slide_06(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_SOFT_BLUE)
    add_header_chrome(
        slide,
        6,
        "PHẦN 3 · QUYẾT ĐỊNH SỐNG CÒN",
        "5. Tại Sao Bắt Buộc Phải Dùng lstat() Mà Tuyệt Đối Không Dùng stat()?",
        "Phân tích đối chiếu 2 kịch bản thực tế khiến chương trình dùng stat() bị sập hoặc lặp vô tận.",
        tag_color=ACCENT_BLUE,
    )

    # Cột Trái: Chuyện gì xảy ra nếu dùng stat()?
    add_box(slide, 0.55, 1.72, 5.95, 5.15, fill_color=SURFACE_WHITE, border_color=ACCENT_RED, border_pt=1.5, corner_radius=0.05)
    add_box(slide, 0.55, 1.72, 5.95, 0.55, fill_color=ACCENT_RED, border_color=None, shape_type=MSO_SHAPE.RECTANGLE)
    add_text(slide, 0.75, 1.82, 5.55, 0.35, "NẾU DÙNG stat(path, &st)  ──►  ĐI XUYÊN QUA SYMLINK", font_size=13.5, bold=True, color=INK_WHITE)

    add_box(slide, 0.80, 2.48, 5.45, 1.95, fill_color=SURFACE_TINT_RED, border_color=ACCENT_RED, border_pt=1.0, corner_radius=0.06)
    add_text(slide, 0.98, 2.58, 5.10, 0.32, "Thảm họa 1: Khi gặp Broken Symlink (Đích đã bị xóa)", font_size=13, bold=True, color=ACCENT_RED)
    add_text(
        slide,
        0.98,
        2.95,
        5.10,
        1.35,
        "• Giả sử có: broken_symlink -> non_existent_target\n"
        "• stat() cố đi tìm 'non_existent_target' và trả về lỗi -1 (ENOENT: No such file or directory).\n"
        "• Hậu quả: Chương trình báo lỗi và làm biến mất luôn broken_symlink khỏi danh sách hiển thị!",
        font_size=12,
        color=INK_BODY,
    )

    add_box(slide, 0.80, 4.65, 5.45, 1.98, fill_color=SURFACE_TINT_RED, border_color=ACCENT_RED, border_pt=1.0, corner_radius=0.06)
    add_text(slide, 0.98, 4.75, 5.10, 0.32, "Thảm họa 2: Khi gặp Symlink trỏ ngược lên Thư mục cha", font_size=13, bold=True, color=ACCENT_RED)
    add_text(
        slide,
        0.98,
        5.12,
        5.10,
        1.38,
        "• Giả sử trong thư mục con có: ln -s .. loop_back\n"
        "• stat() đọc đích '..' và báo S_ISDIR(st_mode) == true (là thư mục thật).\n"
        "• Hậu quả: Khi chạy đệ quy -R, chương trình chui vào loop_back -> quay lại cha -> lặp vô hạn!",
        font_size=12,
        color=INK_BODY,
    )

    # Cột Phải: Giải pháp chuẩn với lstat() trong myls
    add_box(slide, 6.80, 1.72, 5.95, 5.15, fill_color=SURFACE_WHITE, border_color=ACCENT_GREEN, border_pt=1.5, corner_radius=0.05)
    add_box(slide, 6.80, 1.72, 5.95, 0.55, fill_color=ACCENT_GREEN, border_color=None, shape_type=MSO_SHAPE.RECTANGLE)
    add_text(slide, 7.00, 1.82, 5.55, 0.35, "GIẢI PHÁP CỦA myls: DÙNG lstat(path, &st)", font_size=13.5, bold=True, color=INK_WHITE)

    add_box(slide, 7.05, 2.48, 5.45, 1.95, fill_color=SURFACE_TINT_GREEN, border_color=ACCENT_GREEN, border_pt=1.0, corner_radius=0.06)
    add_text(slide, 7.23, 2.58, 5.10, 0.32, "Ưu điểm 1: Đọc trực tiếp Inode của chính Symlink", font_size=13, bold=True, color=ACCENT_GREEN)
    add_text(
        slide,
        7.23,
        2.95,
        5.10,
        1.35,
        "• Kể cả khi tệp đích không tồn tại, bản thân file symlink vẫn tồn tại trên đĩa.\n"
        "• lstat() thành công 100%, trả về S_ISLNK(st_mode) == true.\n"
        "• Kết hợp readlink() để in chuẩn xác:\n  lrwxrwxrwx 1 ... broken_symlink -> non_existent_target",
        font_size=12,
        color=INK_BODY,
    )

    add_box(slide, 7.05, 4.65, 5.45, 1.98, fill_color=SURFACE_TINT_GREEN, border_color=ACCENT_GREEN, border_pt=1.0, corner_radius=0.06)
    add_text(slide, 7.23, 4.75, 5.10, 0.32, "Ưu điểm 2: Miễn nhiễm vòng lặp Symlink khi đệ quy (-R)", font_size=13, bold=True, color=ACCENT_GREEN)
    add_text(
        slide,
        7.23,
        5.12,
        5.10,
        1.38,
        "• Vì lstat() trả về kiểu S_ISLNK (không phải S_ISDIR), hàm kiểm tra đệ quy is_recursible_subdir() loại bỏ ngay lập tức.\n"
        "• Ngoại lệ tinh tế trên CLI (main.c): Nếu gõ './myls symlink_to_dir' (không có -l) thì dùng stat() để liệt kê thư mục đích đúng chuẩn POSIX!",
        font_size=12,
        color=INK_BODY,
    )


# ==============================================================================
# SLIDE 7: 3 CẠM BẪY HỆ THỐNG Ở -R VÀ -S (Layout Left Cutout Shield + 3 Cause-Effect Cards)
# ==============================================================================
def build_slide_07(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_WARM_IVORY)
    add_header_chrome(
        slide,
        7,
        "PHẦN 3 · THUẬT TOÁN -R & -S",
        "6. Hóa Giải 3 Cạm Bẫy Hệ Thống Nguy Hiểm Nhất Khi Cài Đặt -R Và -S",
        "Chống lặp vô hạn '.'/'..', chống cạn kiệt File Descriptor và chống tràn số nguyên 64-bit.",
        tag_color=ACCENT_GREEN,
    )

    # Khung bên trái: Hình minh họa 3D Khiên bảo vệ cây thư mục đệ quy (tách nền trong suốt)
    add_box(slide, 0.55, 1.72, 4.20, 5.15, fill_color=SURFACE_WHITE, border_color=BORDER_LIGHT, border_pt=1.0, corner_radius=0.06)
    add_picture_contain(slide, CUTOUTS_DIR / "recursion_shield.png", 0.75, 1.82, 3.80, 3.52)
    add_box(slide, 0.80, 5.48, 3.70, 1.18, fill_color=SURFACE_TINT_GREEN, border_color=ACCENT_GREEN, border_pt=1.0, corner_radius=0.08)
    add_text(
        slide,
        0.94,
        5.55,
        3.42,
        1.04,
        "3 Chốt chặn bảo vệ Tiến trình:\n• Không lặp vô hạn Stack\n• Tối đa 1 FD mở cùng lúc\n• An toàn số 64-bit (> 2 GB)",
        font_size=10.8,
        bold=True,
        color=ACCENT_GREEN,
        line_spacing=1.12,
    )

    # Bên phải: 3 Thẻ ngang phân tích Nhân - Quả - Giải pháp
    traps = [
        (
            "CẠM BẪY 1 · Tổ hợp ./myls -aR gây lặp vô hạn tại '.' và '..'",
            "• Tại sao xảy ra? Khi bật -a, danh sách nạp cả '.' (chính nó) và '..' (thư mục cha). Cả hai đều là thư mục thật (S_ISDIR).\n"
            "• Giải pháp (src/directory.c): Hàm is_recursible_subdir() bắt buộc kiểm tra:\n"
            "  S_ISDIR(st.st_mode) && strcmp(name, \".\") != 0 && strcmp(name, \"..\") != 0.",
            ACCENT_BLUE,
        ),
        (
            "CẠM BẪY 2 · Cạn kiệt File Descriptor (EMFILE: Too many open files)",
            "• Tại sao xảy ra? Mỗi tiến trình chỉ mở được ~1024 FD (ulimit -n). Nếu gọi đệ quy ngay trong vòng lặp readdir() trước khi closedir(), hàng trăm FD bị treo.\n"
            "• Giải pháp (src/directory.c): Đọc hết vào EntryList ──► Gọi closedir(dir) NGAY LẬP TỨC ──► Sort & In ──► Mới đệ quy xuống thư mục con.",
            ACCENT_AMBER,
        ),
        (
            "CẠM BẪY 3 · Tràn số nguyên 64-bit khi viết 'return b->st_size - a->st_size' (-S)",
            "• Tại sao xảy ra? st_size có kiểu off_t (64-bit), nhưng comparator của qsort() trả về int (32-bit, tối đa ~2 GB). Trừ trực tiếp tệp > 2 GB sẽ tràn bit dấu!\n"
            "• Giải pháp (src/sorting.c): Dùng phép so sánh '>' (trả về -1) và '<' (trả về 1). Nếu kích thước bằng nhau, gọi strcmp(a->name, b->name) để tie-break.",
            ACCENT_GREEN,
        ),
    ]

    ty = 1.72
    for ttitle, tbody, col in traps:
        add_box(slide, 5.00, ty, 7.75, 1.60, fill_color=SURFACE_WHITE, border_color=BORDER_LIGHT, border_pt=1.0, corner_radius=0.06)
        add_box(slide, 5.00, ty, 7.75, 0.38, fill_color=col, border_color=None, shape_type=MSO_SHAPE.RECTANGLE)
        add_text(slide, 5.18, ty + 0.05, 7.40, 0.28, ttitle, font_size=12.0, bold=True, color=INK_WHITE)
        add_text(slide, 5.18, ty + 0.46, 7.40, 1.06, tbody, font_size=11.5, color=INK_BODY, line_spacing=1.18)
        ty += 1.77


# ==============================================================================
# SLIDE 8: BẪY MÔI TRƯỜNG WSL2 (/mnt/p DrvFs vs /tmp Native Linux)
# ==============================================================================
def build_slide_08(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_SOFT_BLUE)
    add_header_chrome(
        slide,
        8,
        "PHẦN 4 · THỰC NGHIỆM TRÊN WSL2",
        "7. Tại Sao Phải Dựng Dữ Liệu Kiểm Thử (Fixtures) Trên /tmp Thay Vì /mnt/p?",
        "Phát hiện kỹ thuật quan trọng khi kiểm thử chương trình hệ thống Linux trên Windows Subsystem for Linux (WSL2).",
        tag_color=ACCENT_PURPLE,
    )

    # Sơ đồ Kiến trúc 2 vùng Filesystem trên WSL2
    add_box(slide, 0.55, 1.72, 5.80, 3.65, fill_color=SURFACE_WHITE, border_color=ACCENT_AMBER, border_pt=1.5, corner_radius=0.06)
    add_box(slide, 0.55, 1.72, 5.80, 0.52, fill_color=ACCENT_AMBER, border_color=None, shape_type=MSO_SHAPE.RECTANGLE)
    add_text(slide, 0.75, 1.82, 5.40, 0.32, "VÙNG 1: /mnt/p/DoAn_Laptrinhhethong (Windows DrvFs)", font_size=13, bold=True, color=INK_WHITE)

    drvfs_points = [
        ("• Bản chất: ", "Ổ đĩa Windows (NTFS) được mount vào WSL2 qua cầu nối 9P / DrvFs."),
        ("• Hạn chế quyền POSIX: ", "Mọi tệp bị giả lập quyền mặc định thành rwxrwxrwx (0777)."),
        ("• Không test được Edge Cases: ", "Lệnh chmod 0000 (khóa thư mục) hay chmod 4755 (SUID) không phản ánh đúng hành vi nhân Linux."),
        ("• Vai trò trong dự án: ", "Dùng để lưu mã nguồn C, Makefile, tài liệu và đồng bộ Git thuận tiện với IDE trên Windows."),
    ]
    add_rich_bullets(slide, 0.75, 2.38, 5.40, 2.80, drvfs_points, font_size=12.0, lead_color=ACCENT_AMBER, space_after_pt=6)

    # Mũi tên chuyển hướng ở giữa
    add_box(slide, 6.45, 3.10, 0.40, 0.80, fill_color=ACCENT_BLUE, border_color=None, shape_type=MSO_SHAPE.RIGHT_ARROW)

    # Hộp Phải: /tmp/myls_test_XXXXXX (Native Linux Filesystem)
    add_box(slide, 6.95, 1.72, 5.80, 3.65, fill_color=SURFACE_WHITE, border_color=ACCENT_GREEN, border_pt=1.5, corner_radius=0.06)
    add_box(slide, 6.95, 1.72, 5.80, 0.52, fill_color=ACCENT_GREEN, border_color=None, shape_type=MSO_SHAPE.RECTANGLE)
    add_text(slide, 7.15, 1.82, 5.40, 0.32, "VÙNG 2: /tmp/myls_test_XXXXXX (Native Linux FS)", font_size=13, bold=True, color=INK_WHITE)

    ext4_points = [
        ("• Bản chất: ", "Hệ thống tệp gốc bên trong máy ảo Ubuntu 24.04 (Kernel 6.18 WSL2)."),
        ("• Chuẩn 100% Inode POSIX: ", "Hỗ trợ đầy đủ SUID (4755), SGID (2755), Sticky bit (1777) và chmod 0000."),
        ("• Chuẩn Hard link & Symlink: ", "Đếm chính xác st_nlink, st_blocks (512B units) và broken symlink."),
        ("• Vai trò trong dự án: ", "make test tự động dựng Fixture trong /tmp và chạy diff -u với LC_ALL=C ls."),
    ]
    add_rich_bullets(slide, 7.15, 2.38, 5.40, 2.80, ext4_points, font_size=12.0, lead_color=ACCENT_GREEN, space_after_pt=6)

    # Dải quy trình 4 bước tự động hóa của tests/run_tests.sh ở dưới
    add_box(slide, 0.55, 5.58, 12.20, 1.32, fill_color=SURFACE_WHITE, border_color=ACCENT_BLUE, border_pt=1.2, corner_radius=0.06)
    add_text(slide, 0.75, 5.68, 11.8, 0.30, "QUY TRÌNH TỰ ĐỘNG HÓA TRONG LỆNH make test (tests/run_tests.sh):", font_size=11.5, bold=True, color=ACCENT_BLUE)

    flow = [
        ("Bước 1: mktemp -d /tmp/...", "Tạo không gian cô lập sạch trên Linux FS"),
        ("Bước 2: setup_fixtures()", "Tạo tệp 0B..10KB, ẩn, SUID, symlink, dir 0000"),
        ("Bước 3: diff -u (15 kịch bản)", "So sánh từng byte giữa ./myls và LC_ALL=C ls"),
        ("Bước 4: trap cleanup EXIT", "Tự động mở khóa và dọn sạch /tmp sau khi test"),
    ]
    fx = 0.75
    for ftitle, fsub in flow:
        add_box(slide, fx, 6.04, 2.82, 0.72, fill_color=SURFACE_TINT_BLUE, border_color=BORDER_LIGHT, border_pt=0.8, corner_radius=0.08)
        add_text(slide, fx + 0.10, 6.09, 2.62, 0.28, ftitle, font_size=10.5, bold=True, font_name=FONT_MONO, color=ACCENT_BLUE)
        add_text(slide, fx + 0.10, 6.38, 2.62, 0.30, fsub, font_size=10.0, color=INK_BODY)
        fx += 2.98


# ==============================================================================
# SLIDE 9: KẾT QUẢ 15 TEST CASES & KIỂM TRA BỘ NHỚ (Layout KPI Stat Callouts + 3x5 Grid)
# ==============================================================================
def build_slide_09(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_WARM_IVORY)
    add_header_chrome(
        slide,
        9,
        "PHẦN 4 · KẾT QUẢ NGHIỆM THU",
        "8. Kết Quả Kiểm Thử Tự Động: 15/15 Kịch Bản Khớp Tuyệt Đối GNU ls",
        "Xác thực bằng diff -u với GNU coreutils 9.4 và kiểm tra rò rỉ bộ nhớ bằng AddressSanitizer / LeakSanitizer.",
        tag_color=ACCENT_GREEN,
    )

    # Hàng trên: 3 Big Number KPI Cards (không bị rớt dòng số)
    kpis = [
        ("15 / 15", "Kịch Bản Kiểm Thử Tự Động PASS", "Đối chiếu byte-for-byte (diff -u) với LC_ALL=C ls", ACCENT_GREEN, SURFACE_TINT_GREEN),
        ("0 Bytes", "Rò Rỉ Bộ Nhớ (Zero Memory Leaks)", "Xác thực bằng GCC -fsanitize=address,undefined", ACCENT_BLUE, SURFACE_TINT_BLUE),
        ("0 Lỗi/Cảnh báo", "Biên Dịch Chuẩn C11 Nghiêm Ngặt", "Cờ: -Wall -Wextra -Werror -pedantic -std=c11", ACCENT_AMBER, SURFACE_TINT_AMBER),
    ]
    kx = 0.55
    for big_num, ktitle, ksub, col, bg in kpis:
        add_box(slide, kx, 1.68, 3.90, 1.38, fill_color=SURFACE_WHITE, border_color=col, border_pt=1.5, corner_radius=0.06)
        add_box(slide, kx + 0.16, 1.84, 1.56, 1.06, fill_color=bg, border_color=None, corner_radius=0.08)
        fsize = 16.5 if len(big_num) > 8 else 20.5
        add_text(slide, kx + 0.16, 2.02, 1.56, 0.70, big_num, font_size=fsize, bold=True, color=col, align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE)
        add_text(slide, kx + 1.82, 1.86, 1.96, 0.52, ktitle, font_size=12.5, bold=True, color=INK_NAVY)
        add_text(slide, kx + 1.82, 2.42, 1.96, 0.50, ksub, font_size=10.2, color=INK_MUTED)
        kx += 4.15

    # Lưới 3x5 hiển thị toàn bộ 15 Test Cases
    tests = [
        ("Test 01", "./myls", "Mặc định A -> Z"),
        ("Test 02", "./myls -a", "Hiện tệp ẩn '.', '..'"),
        ("Test 03", "./myls -l", "Chi tiết + SUID/Sticky"),
        ("Test 04", "./myls -R", "Đệ quy đa tầng"),
        ("Test 05", "./myls -S", "Size giảm + Tie-break"),
        ("Test 06", "./myls -la", "Kết hợp Long + All"),
        ("Test 07", "./myls -lS", "Kết hợp Long + Size"),
        ("Test 08", "./myls -lR", "Kết hợp Long + Recurse"),
        ("Test 09", "./myls -aR", "Chống lặp '.' & '..'"),
        ("Test 10", "./myls -alRS", "Tổ hợp toàn diện 4 cờ"),
        ("Test 11", "Mixed Paths", "Tệp in trước, Dir in sau"),
        ("Test 12", "Symlinks", "Symlink dir & broken link"),
        ("Test 13", "ENOENT Path", "Báo stderr, Exit code = 1"),
        ("Test 14", "chmod 0000", "Báo lỗi, tiếp tục chạy"),
        ("Test 15", "Invalid -z", "Báo Usage, Exit code = 2"),
    ]

    start_x = 0.55
    start_y = 3.28
    col_w = 2.32
    row_h = 1.12
    gap_x = 0.15
    gap_y = 0.14

    for idx, (tcode, tcmd, tdesc) in enumerate(tests):
        r = idx // 5
        c = idx % 5
        bx = start_x + c * (col_w + gap_x)
        by = start_y + r * (row_h + gap_y)

        add_box(slide, bx, by, col_w, row_h, fill_color=SURFACE_WHITE, border_color=BORDER_LIGHT, border_pt=1.0, corner_radius=0.06)
        add_box(slide, bx + 0.12, by + 0.12, 0.78, 0.28, fill_color=SURFACE_TINT_GREEN, border_color=ACCENT_GREEN, border_pt=0.8, corner_radius=0.3)
        add_text(slide, bx + 0.12, by + 0.13, 0.78, 0.25, "PASS", font_size=9.0, bold=True, color=ACCENT_GREEN, align=PP_ALIGN.CENTER)
        add_text(slide, bx + 0.98, by + 0.12, 1.20, 0.26, tcode, font_size=10.0, bold=True, color=INK_MUTED)
        add_text(slide, bx + 0.12, by + 0.45, 2.08, 0.30, tcmd, font_size=11.5, bold=True, font_name=FONT_MONO, color=ACCENT_BLUE)
        add_text(slide, bx + 0.12, by + 0.76, 2.08, 0.28, tdesc, font_size=10.5, color=INK_BODY)


# ==============================================================================
# SLIDE 10: MINH CHỨNG CHẠY THỰC TẾ CÁC CỜ CƠ BẢN (Layout Left Terminal + Right Callouts)
# ==============================================================================
def build_slide_10(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_SOFT_BLUE)
    add_header_chrome(
        slide,
        10,
        "PHẦN 4 · MINH CHỨNG DEMO (1/2)",
        "9. Minh Chứng Thực Tế Trên Ubuntu 24.04 WSL2: ./myls, -a, -l, -R",
        "Ảnh chụp trực tiếp phiên chạy thực tế trên nhân Linux 6.18.33.2-microsoft-standard-WSL2.",
    )

    # Khung ảnh chụp Terminal bên trái
    add_box(slide, 0.55, 1.68, 7.65, 5.20, fill_color=SURFACE_WHITE, border_color=BORDER_LIGHT, border_pt=1.2, corner_radius=0.04)
    add_picture_contain(slide, EVIDENCE_DIR / "demo_basic_flags_capture.png", 0.65, 1.76, 7.45, 5.04)

    # 3 Thẻ phân tích điểm nhấn bên phải
    notes = [
        (
            "1. Đối chiếu ./myls và ./myls -a",
            "• Ở ./myls: Tệp ẩn '.env.hidden' cũng như '.' và '..' được lọc bỏ hoàn toàn.\n"
            "• Ở ./myls -a: Xuất hiện đầy đủ '.', '..', '.env.hidden' ở đầu danh sách theo thứ tự mã ASCII.",
            ACCENT_BLUE,
        ),
        (
            "2. Độ chính xác của ./myls -l",
            "• Dòng 'total 24' tính chuẩn xác từ tổng st_blocks / 2.\n"
            "• Phân biệt rõ thư mục ('drwxr-xr-x'), tệp thực thi ('-rwxr-xr-x' cho main_sample.c) và Symlink ('lrwxrwxrwx ... latest_data.lnk -> dataset_large.bin').",
            ACCENT_AMBER,
        ),
        (
            "3. Duyệt đệ quy ./myls -R",
            "• Tự động bật tiêu đề '.:', liệt kê toàn bộ thư mục gốc trước.\n"
            "• Sau đó lần lượt đi sâu vào './docs_sub:' và './src_module:', bỏ qua symlink 'latest_data.lnk'.",
            ACCENT_GREEN,
        ),
    ]

    ny = 1.68
    for ntitle, nbody, col in notes:
        add_box(slide, 8.45, ny, 4.30, 1.62, fill_color=SURFACE_WHITE, border_color=col, border_pt=1.2, corner_radius=0.06)
        add_text(slide, 8.65, ny + 0.12, 3.90, 0.32, ntitle, font_size=13, bold=True, color=col)
        add_text(slide, 8.65, ny + 0.46, 3.90, 1.08, nbody, font_size=11.2, color=INK_BODY, line_spacing=1.18)
        ny += 1.79


# ==============================================================================
# SLIDE 11: MINH CHỨNG TỔ HỢP -S VÀ -alRS (Layout Left Analysis + Right Terminal)
# ==============================================================================
def build_slide_11(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_WARM_IVORY)
    add_header_chrome(
        slide,
        11,
        "PHẦN 4 · MINH CHỨNG DEMO (2/2)",
        "10. Minh Chứng Thực Tế Tổ Hợp Cờ Đầy Đủ: ./myls -S Và ./myls -alRS",
        "Kiểm chứng sự phối hợp đồng thời cả 4 cờ (-a, -l, -R, -S) và kết quả chạy bộ kiểm thử tự động.",
        tag_color=ACCENT_AMBER,
    )

    # Bên trái: 3 hộp phân tích kết quả
    left_cards = [
        (
            "1. Thứ tự kích thước giảm dần (-S)",
            "• dataset_large.bin (8192 B) đứng đầu.\n"
            "• Tiếp theo là các thư mục '.', '..', 'docs_sub', 'src_module' (cùng 4096 B, được tie-break theo tên ASCII: '.' -> '..' -> 'docs_sub' -> 'src_module').\n"
            "• Cuối cùng là config_medium.cfg (1024 B), main_sample.c (29 B), .env.hidden (22 B) và latest_data.lnk (17 B).",
            ACCENT_AMBER,
        ),
        (
            "2. Đệ quy kèm sắp xếp kích thước (-alRS)",
            "• Tại mỗi thư mục con (./docs_sub và ./src_module), chương trình đều tính lại độ rộng cột động, in dòng 'total 12' và sắp xếp các mục bên trong theo kích thước giảm dần.",
            ACCENT_BLUE,
        ),
        (
            "3. Đối chiếu tự động (test_suite_capture)",
            "• Toàn bộ 15/15 kịch bản kiểm thử tự động đạt PASS tuyệt đối chỉ trong < 0.2 giây thực thi trên Ubuntu 24.04 WSL2.",
            ACCENT_GREEN,
        ),
    ]

    ly = 1.68
    for ltitle, lbody, col in left_cards:
        h = 2.02 if ly == 1.68 else 1.45
        add_box(slide, 0.55, ly, 4.45, h, fill_color=SURFACE_WHITE, border_color=col, border_pt=1.2, corner_radius=0.06)
        add_text(slide, 0.75, ly + 0.12, 4.05, 0.32, ltitle, font_size=13, bold=True, color=col)
        add_text(slide, 0.75, ly + 0.46, 4.05, h - 0.54, lbody, font_size=11.0, color=INK_BODY, line_spacing=1.16)
        ly += h + 0.14

    # Bên phải: Ảnh chụp Terminal thực tế ./myls -S và ./myls -alRS
    add_box(slide, 5.25, 1.68, 7.50, 5.20, fill_color=SURFACE_WHITE, border_color=BORDER_LIGHT, border_pt=1.2, corner_radius=0.04)
    add_picture_contain(slide, EVIDENCE_DIR / "demo_combined_alRS_capture.png", 5.35, 1.76, 7.30, 5.04)


# ==============================================================================
# SLIDE 12: GIỚI HẠN KỸ THUẬT, TỔNG KẾT & CÂU HỎI VẤN ĐÁP (Layout 3 Pillars + Q&A Grid)
# ==============================================================================
def build_slide_12(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_SOFT_BLUE)
    add_header_chrome(
        slide,
        12,
        "TỔNG KẾT & BẢO VỆ ĐỒ ÁN",
        "11. Giới Hạn Kỹ Thuật Hiện Tại, Hướng Mở Rộng & Trọng Tâm Vấn Đáp",
        "Đánh giá trung thực phạm vi đã hoàn thành và tóm tắt các câu trả lời bảo vệ đồ án trước giảng viên.",
        tag_color=ACCENT_BLUE,
    )

    # Hàng trên: 3 Giới hạn kỹ thuật & Hướng mở rộng
    limits = [
        ("Giới hạn 1 · Locale Collation", "Hiện dùng strcmp() chuẩn ASCII (LC_ALL=C). Hướng mở rộng: tích hợp setlocale() + strcoll()."),
        ("Giới hạn 2 · POSIX ACL & SELinux", "Hiện giải mã 10 ký tự chuẩn POSIX. Hướng mở rộng: đọc getxattr() để hiển thị dấu '+' hoặc '.'."),
        ("Giới hạn 3 · Multi-Column & ANSI Color", "Hiện xuất 1 mục/dòng chuẩn pipe. Hướng mở rộng: dùng ioctl(TIOCGWINSZ) chia lưới cột & tô màu."),
    ]
    lx = 0.55
    for ltitle, lbody in limits:
        add_box(slide, lx, 1.68, 3.90, 1.18, fill_color=SURFACE_WHITE, border_color=BORDER_LIGHT, border_pt=1.0, corner_radius=0.06)
        add_text(slide, lx + 0.16, 1.78, 3.58, 0.30, ltitle, font_size=12.5, bold=True, color=ACCENT_BLUE)
        add_text(slide, lx + 0.16, 2.10, 3.58, 0.68, lbody, font_size=11.0, color=INK_BODY)
        lx += 4.15

    # Nửa dưới: 3 Câu hỏi vấn đáp trọng tâm + Vật thể 3D trang trí góc phải
    add_box(slide, 0.55, 3.08, 8.65, 3.80, fill_color=SURFACE_WHITE, border_color=ACCENT_BLUE, border_pt=1.2, corner_radius=0.05)
    add_text(slide, 0.78, 3.20, 8.20, 0.34, "TÓM TẮT 3 CÂU HỎI VẤN ĐÁP TRỌNG TÂM KHI BẢO VỆ:", font_size=13.5, bold=True, color=ACCENT_BLUE)

    qa_items = [
        (
            "Hỏi 1: Tại sao trong directory.c phải dùng lstat() mà không dùng stat()?\n",
            "Đáp: Vì stat() đi xuyên qua symlink khiến broken symlink báo lỗi ENOENT và làm cờ đệ quy -R bị lặp vô hạn nếu gặp symlink trỏ ngược lên thư mục cha.",
        ),
        (
            "Hỏi 2: Làm sao chương trình tránh bị tràn File Descriptor và lặp vô hạn khi chạy ./myls -aR?\n",
            "Đáp: Đọc hết tên tệp vào EntryList rồi gọi closedir() ngay lập tức trước khi đệ quy (chỉ tốn 1 FD). Khi đệ quy, hàm is_recursible_subdir() chặn chặt '.' và '..'.",
        ),
        (
            "Hỏi 3: Tại sao dòng total trong -l phải chia đôi st_blocks và hàm sort -S không dùng phép trừ?\n",
            "Đáp: st_blocks của Linux tính theo khối 512B còn GNU ls hiển thị khối 1024B nên phải chia 2. Hàm sort -S dùng '>' và '<' để không bị tràn số 64-bit off_t sang int 32-bit.",
        ),
    ]
    add_rich_bullets(slide, 0.78, 3.62, 8.20, 3.10, qa_items, font_size=11.5, lead_color=INK_NAVY, space_after_pt=8)

    # Khung cảm ơn & Vật thể 3D bên phải dưới
    add_box(slide, 9.45, 3.08, 3.30, 3.80, fill_color=SURFACE_TINT_BLUE, border_color=ACCENT_BLUE, border_pt=1.2, corner_radius=0.06)
    add_picture_contain(slide, CUTOUTS_DIR / "hero_inode_tree.png", 9.65, 3.22, 2.90, 2.35)
    add_text(
        slide,
        9.60,
        5.68,
        3.00,
        0.55,
        "Cảm ơn Thầy/Cô đã theo dõi!",
        font_size=14,
        bold=True,
        color=ACCENT_BLUE,
        align=PP_ALIGN.CENTER,
    )
    add_text(
        slide,
        9.60,
        6.18,
        3.00,
        0.55,
        "SV: Nguyễn Xuân Lĩnh\nĐề tài 17 · myls (-a, -l, -R, -S)",
        font_size=11,
        bold=False,
        color=INK_BODY,
        align=PP_ALIGN.CENTER,
    )


def export_slides_to_png(pptx_path: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        import win32com.client  # type: ignore

        app = win32com.client.DispatchEx("PowerPoint.Application")
        try:
            pres = app.Presentations.Open(str(pptx_path.resolve()), WithWindow=False)
            try:
                for idx, slide in enumerate(pres.Slides, start=1):
                    out_png = out_dir / f"slide_{idx:02d}.png"
                    slide.Export(str(out_png.resolve()), "PNG", 1920, 1080)
                print(f"[OK] Exported {pres.Slides.Count} slide PNG previews to {out_dir}")
            finally:
                pres.Close()
        finally:
            app.Quit()
    except Exception as exc:
        print(f"[WARN] PowerPoint COM export failed: {exc}")


def main():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    build_slide_01(prs)
    build_slide_02(prs)
    build_slide_03(prs)
    build_slide_04(prs)
    build_slide_05(prs)
    build_slide_06(prs)
    build_slide_07(prs)
    build_slide_08(prs)
    build_slide_09(prs)
    build_slide_10(prs)
    build_slide_11(prs)
    build_slide_12(prs)

    out_pptx = DOCS_DIR / "Slides.pptx"
    out_pptx.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_pptx))
    print(f"[OK] Saved presentation: {out_pptx}")

    export_slides_to_png(out_pptx, PREVIEW_DIR)


if __name__ == "__main__":
    main()
