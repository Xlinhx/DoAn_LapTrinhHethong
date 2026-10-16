"""
scripts/metadata_loader.py
Bộ nạp và kiểm tra tính hợp lệ của thông tin hành chính/nhóm từ docs/project_metadata.json
và kết quả thực nghiệm từ evidence/test_results.json.

Quy tắc:
- Chế độ "draft": Cho phép trường chưa cung cấp, tự động hiển thị nhãn rõ ràng
  như "[Chưa cung cấp danh sách nhóm]", "[Chưa cung cấp GVHD]", không tự suy đoán.
- Chế độ "final": Kiểm tra nghiêm ngặt các trường bắt buộc (faculty, instructor, members
  gồm name/student_id/class_name). Nếu thiếu bất kỳ trường nào, báo lỗi chi tiết và dừng xuất bản.
"""

from __future__ import annotations

import json
import sys
import hashlib
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
METADATA_PATH = PROJECT_ROOT / "docs" / "project_metadata.json"
TEST_RESULTS_PATH = PROJECT_ROOT / "evidence" / "test_results.json"


def member_role(member: dict, allocations: list) -> str:
    if member.get("role"):
        return str(member["role"]).strip()
    for item in allocations:
        same_id = item.get("student_id") and item["student_id"] == member.get("student_id")
        same_name = item.get("member") and item["member"] == member.get("name")
        if same_id or same_name:
            tasks = item.get("role") or item.get("tasks") or item.get("task") or ""
            return "; ".join(tasks) if isinstance(tasks, list) else str(tasks).strip()
    return ""


def source_fingerprint() -> str:
    """Bind a verification run to the exact C sources, tests, and build contract."""
    files = sorted([*PROJECT_ROOT.glob("src/*.c"), *PROJECT_ROOT.glob("include/*.h"),
                    *PROJECT_ROOT.glob("tests/*.c"), *PROJECT_ROOT.glob("tests/*.sh"),
                    PROJECT_ROOT / "Makefile"])
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(PROJECT_ROOT).as_posix().encode("utf-8"))
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def load_project_metadata(override_mode: str | None = None) -> dict[str, Any]:
    if not METADATA_PATH.exists():
        raise FileNotFoundError(f"Missing metadata file: {METADATA_PATH}")

    raw = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    mode = (override_mode or raw.get("mode") or "draft").strip().lower()
    if mode not in ("draft", "final"):
        raise ValueError(f"Invalid metadata mode '{mode}'. Expected 'draft' or 'final'.")

    missing_fields: list[str] = []

    faculty = (raw.get("faculty") or "").strip()
    if not faculty:
        missing_fields.append("faculty (Khoa quản lý học phần)")

    instructor = (raw.get("instructor") or "").strip()
    if not instructor:
        missing_fields.append("instructor (Giảng viên hướng dẫn)")

    academic_term = (raw.get("academic_term") or "").strip()
    if not academic_term:
        missing_fields.append("academic_term (Học kỳ / Năm học)")

    members = raw.get("members") or []
    allocations = raw.get("task_allocation") or []
    if not isinstance(members, list) or any(not isinstance(m, dict) for m in members):
        raise ValueError("members must be a list of member objects")
    if not isinstance(allocations, list) or any(not isinstance(a, dict) for a in allocations):
        raise ValueError("task_allocation must be a list of allocation objects")
    if not isinstance(members, list) or len(members) == 0:
        missing_fields.append("members (Danh sách thành viên nhóm: họ tên, MSSV, lớp)")
    else:
        for idx, m in enumerate(members, start=1):
            name = (m.get("name") or "").strip()
            sid = (m.get("student_id") or "").strip()
            cls = (m.get("class_name") or "").strip()
            if not name or not sid or not cls:
                missing_fields.append(
                    f"members[{idx}] thiếu trường bắt buộc (name='{name}', student_id='{sid}', class_name='{cls}')"
                )
            if not member_role(m, allocations):
                missing_fields.append(f"members[{idx}] thiếu phân công thực tế (role hoặc task_allocation)")

    if mode == "final" and missing_fields:
        msg = (
            "[ERROR] Không thể xuất bản ở chế độ 'final' vì thiếu thông tin hành chính/nhóm trong "
            f"{METADATA_PATH}:\n  - " + "\n  - ".join(missing_fields)
        )
        raise RuntimeError(msg)

    # Chuẩn hóa giá trị hiển thị cho chế độ draft (không tự bịa đặt tên hay số lượng thành viên)
    resolved: dict[str, Any] = {
        "mode": mode,
        "is_draft": (mode == "draft"),
        "missing_fields": missing_fields,
        "university_parent": raw.get("university_parent") or "ĐẠI HỌC ĐÀ NẴNG",
        "university_name": raw.get("university_name")
        or "TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN VÀ TRUYỀN THÔNG VIỆT - HÀN",
        "faculty_display": faculty if faculty else "[Chưa cung cấp tên Khoa]",
        "course_name": raw.get("course_name") or "Lập trình Hệ thống (System Programming)",
        "topic_code": raw.get("topic_code") or "Đề tài 17",
        "topic_title": raw.get("topic_title") or "Implement ls with -a, -l, -R, -S",
        "topic_title_vi": raw.get("topic_title_vi")
        or "Cài đặt lệnh ls với các tùy chọn -a, -l, -R, -S trên Linux",
        "academic_term_display": academic_term if academic_term else "[Chưa cung cấp Học kỳ / Năm học]",
        "instructor_display": instructor if instructor else "[Chưa cung cấp Giảng viên hướng dẫn]",
        "group_display": (raw.get("group_name") or "").strip() or "[Chưa cung cấp danh sách nhóm]",
        "location": raw.get("location") or "Đà Nẵng",
        "year": str(raw.get("year") or "2026"),
        "repository_url": raw.get("repository_url") or "",
        "members": members,
        "task_allocation": allocations,
    }
    return resolved


def load_test_results() -> dict[str, Any]:
    if not TEST_RESULTS_PATH.exists():
        raise FileNotFoundError(
            f"Missing structured test results at {TEST_RESULTS_PATH}. "
            "Run scripts/collect_evidence.py first."
        )
    data = json.loads(TEST_RESULTS_PATH.read_text(encoding="utf-8"))
    if data.get("source_sha256") != source_fingerprint():
        raise ValueError("Evidence does not match current sources/tests. Run scripts/collect_evidence.py.")
    for key in ("regular_suite", "sanitizer_suite"):
        suite = data[key]
        counts = [suite[k] for k in ("passed", "failed", "skipped")]
        if suite["exit_code"] != 0 or suite["failed"] or suite["total"] < 1 or sum(counts) != suite["total"]:
            raise ValueError(f"Invalid or failing verification: {key}")
        cases = suite.get("cases", [])
        ids = [c["id"] for c in cases]
        if (len(cases) != suite["total"] or ids != list(range(1, suite["total"] + 1))
            or any(sum(c["status"] == status for c in cases) != suite[count]
                   for status, count in (("PASS", "passed"), ("FAIL", "failed"), ("SKIP", "skipped")))):
            raise ValueError(f"Case list inconsistent with summary: {key}")
    if data["demo_run"]["exit_code"] != 0:
        raise ValueError("Demo did not succeed")
    return data


if __name__ == "__main__":
    mode_arg = sys.argv[1] if len(sys.argv) > 1 else None
    meta = load_project_metadata(mode_arg)
    print(f"[OK] Loaded metadata in '{meta['mode']}' mode.")
    if meta["missing_fields"]:
        print("Pending administrative fields:")
        for f in meta["missing_fields"]:
            print(f"  - {f}")
