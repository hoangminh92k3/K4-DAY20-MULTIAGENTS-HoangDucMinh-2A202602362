"""GUIDE Phần 1 - Định nghĩa subagent (tác tử con).   >>> SINH VIÊN CÀI ĐẶT <<<

Pseudo-code: guides/pseudocode/02_subagents.md
Kiểm tra:    pytest tests/test_02_agent.py
"""


def get_subagents() -> list[dict]:
    """Trả về danh sách subagent (ít nhất 2, tên khác nhau).

    Mỗi phần tử là một dict có các khóa bắt buộc:
      "name":          tên duy nhất (chữ thường, có thể có dấu gạch ngang)
      "description":   khi nào tác tử chính nên giao việc cho subagent này (viết như một hướng dẫn hành động)
      "system_prompt": chỉ dẫn cho subagent
    Gợi ý vai trò: explorer (đọc và báo cáo), implementer (thực hiện), reviewer (kiểm tra độc lập).
    """
    return [
      {
        "name": "explorer",
        "description": "Use before a non-trivial change when repository instructions, code paths, or input data need investigation.",
        "system_prompt": "Inspect the task instructions and relevant files. Do not modify files. Return concise findings, paths, and any uncertainties.",
      },
      {
        "name": "implementer",
        "description": "Use for a well-scoped implementation task that can be completed independently and verified with tests.",
        "system_prompt": "Implement only the requested change, run the relevant tests, and report changed files and exact test results.",
      },
      {
        "name": "reviewer",
        "description": "Use after a non-trivial implementation when an independent check for defects or missed requirements is useful.",
        "system_prompt": "Review the proposed changes against the task and relevant tests. Do not edit files. Report concrete findings with evidence, or state that none were found.",
      },
    ]
