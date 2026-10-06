"""GUIDE Phần 1 - Dựng tác tử (agent) bằng Deep Agents.   >>> SINH VIÊN CÀI ĐẶT make_backend VÀ build_agent <<<

Pseudo-code: guides/pseudocode/01_agent.md
Kiểm tra:    pytest tests/test_02_agent.py
"""
from pathlib import Path
import os
import re
import subprocess
import sys

# TODO 1: import các thành phần cần dùng, ví dụ:
#   from deepagents import create_deep_agent
#   from deepagents.backends import LocalShellBackend
#   from .model import make_model
#   from .subagents import get_subagents

# ---- CÓ SẴN, KHÔNG SỬA: system prompt dùng chung cho mọi sinh viên (để đường cơ sở so sánh được) ----
PATHS_NOTE = (
    "PATHS: every path is relative to the sandbox root and never starts with '/'. "
    "The task files are in the folder workspace/ (for example workspace/app.log). "
    "Use exactly this relative form both in the file tools and in the shell (execute); "
    "the shell starts in the sandbox root. "
)
BASE_PROMPT = (
    "You are an engineering assistant working in a sandbox. "
    + PATHS_NOTE
    + "Use the shell to run Python and tests. "
    "When you are done, reply with a short summary that mentions only files you really created or changed."
)
SKILLS_NOTE = (
    " Skills are in the folder skills/ (one sub-folder per skill with a SKILL.md). "
    "As your FIRST action, read the SKILL.md of every skill whose description could apply to the task, "
    "then follow them. Never modify skills/."
)
SUBAGENTS_NOTE = (
    " You have specialised subagents (see the description of the task tool). "
    "For anything beyond a trivial step, delegate to a suitable subagent and put ALL the task rules and file paths "
    "in the delegation message, because a subagent sees only what you send. "
    "Check what a subagent returns before you rely on it."
)
# --------------------------------------------------------------------------------------------------


class _PortableLocalShellBackendMixin:
    """Translate the small POSIX command vocabulary used by the lab on Windows.

    Deep Agents delegates to ``cmd.exe`` when Python runs on Windows, while the
    lab prompt and its offline checks use POSIX spellings.  The task agent still
    has Python and the file tools for all substantive work; this compatibility
    layer makes inspection commands behave consistently without inheriting the
    host environment (and therefore without exposing API keys).
    """

    def execute(self, command: str, *, timeout: int | None = None):
        if os.name == "nt":
            heredoc = re.fullmatch(
                r"\s*(?:python|python3)\s+-\s+<<['\"]?(?P<tag>\w+)['\"]?\s*\n"
                r"(?P<script>.*)\n(?P=tag)\s*",
                command,
                re.S,
            )
            if heredoc:
                from deepagents.backends.protocol import ExecuteResponse

                result = subprocess.run(
                    [sys.executable, "-"],
                    input=heredoc.group("script"),
                    capture_output=True,
                    text=True,
                    timeout=timeout or self._default_timeout,
                    env=self._env,
                    cwd=str(self.cwd),
                )
                output = result.stdout or ""
                if result.stderr:
                    output += "".join(f"[stderr] {line}\n" for line in result.stderr.rstrip().splitlines())
                if result.returncode:
                    output = f"{output.rstrip()}\n\nExit code: {result.returncode}"
                return ExecuteResponse(output=output or "<no output>", exit_code=result.returncode, truncated=False)
            command = command.replace("/", "\\")
            # ``where`` is unavailable in some minimal Windows environments;
            # the prompt only uses ``which`` for a presence check.
            command = re.sub(r"\bwhich\s+\S+", "echo python", command)
            command = re.sub(r"\bcat\s+", "type ", command)
            command = re.sub(r"\bls\s+", "dir /b ", command)
            command = re.sub(r"(?<!\S)env(?=\s*(?:&&|$))", "set", command)
        return super().execute(command, timeout=timeout)


def make_backend(sandbox: Path):
    """Tạo backend (môi trường thực thi) cho tác tử.

    Yêu cầu:
      - Thư mục gốc (root_dir) là `sandbox`; đường dẫn tương đối `workspace/...` và `skills/...`
        phải dùng được ở CẢ công cụ tệp lẫn shell (shell chạy với thư mục làm việc = `sandbox`).
      - Tác tử chạy được lệnh shell và gọi được `python` (cần đặt PATH).
      - KHÔNG chuyển biến môi trường của bạn vào shell của tác tử (khóa API không được lộ).
    """
    from deepagents.backends import LocalShellBackend

    class PortableLocalShellBackend(_PortableLocalShellBackendMixin, LocalShellBackend):
        pass

    path_entries = [str(Path(sys.executable).parent), "/usr/local/bin", "/usr/bin", "/bin"]
    if os.name == "nt":
        windows_root = Path(os.environ.get("SystemRoot", r"C:\\Windows"))
        path_entries.extend([str(windows_root / "System32"), str(windows_root)])

    env = {
      "PATH": os.pathsep.join(path_entries),
      "HOME": str(sandbox),
      "PYTHONDONTWRITEBYTECODE": "1",
    }
    if os.name == "nt":
      env["PATHEXT"] = ".COM;.EXE;.BAT;.CMD"
      env["SystemRoot"] = str(windows_root)
    return PortableLocalShellBackend(
      root_dir=sandbox,
      virtual_mode=True,
      inherit_env=False,
      env=env,
      timeout=120,
    )


def build_agent(sandbox: Path, mode: str = "single", use_skills: bool = False, model=None):
    """Tạo tác tử Deep Agents.

    Tham số:
      sandbox:    thư mục chứa `workspace/` (và `skills/` nếu có).
      mode:       "single"    -> tác tử mặc định (có subagent `general-purpose` sẵn của Deep Agents)
                  "subagents" -> thêm các subagent từ `get_subagents()` (nối PATHS_NOTE vào `system_prompt` của MỖI subagent,
                                 vì subagent không nhận BASE_PROMPT) và thêm SUBAGENTS_NOTE vào prompt chính
      use_skills: True -> nạp thư mục "/skills/" qua tham số `skills=` của create_deep_agent
                  và thêm SKILLS_NOTE vào prompt.
      model:      mô hình ngôn ngữ; None -> dùng `make_model()`.
    mode không hợp lệ -> ném ValueError.
    Trả về: đồ thị (graph) đã biên dịch, gọi bằng `.invoke({"messages": [...]})`.
    """
    from deepagents import create_deep_agent

    from .model import make_model
    from .subagents import get_subagents

    if mode not in {"single", "subagents"}:
      raise ValueError(f"unknown agent mode: {mode}")

    prompt = BASE_PROMPT
    kwargs = {}
    if mode == "subagents":
      kwargs["subagents"] = [
        {**subagent, "system_prompt": subagent["system_prompt"] + " " + PATHS_NOTE}
        for subagent in get_subagents()
      ]
      prompt += SUBAGENTS_NOTE
    if use_skills:
      kwargs["skills"] = ["/skills/"]
      prompt += SKILLS_NOTE

    return create_deep_agent(
      model=model if model is not None else make_model(),
      system_prompt=prompt,
      backend=make_backend(sandbox),
      **kwargs,
    )
