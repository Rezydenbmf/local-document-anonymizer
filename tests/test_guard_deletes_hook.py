"""The PreToolUse delete guard in .claude/hooks/guard_deletes.py."""

import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = PROJECT_ROOT / ".claude" / "hooks" / "guard_deletes.py"

_spec = importlib.util.spec_from_file_location("guard_deletes", HOOK_PATH)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)

CWD = "C:\\ai\\anonimizer"
ENV = {
    "LOCALAPPDATA": "C:\\Users\\tester\\AppData\\Local",
    "USERPROFILE": "C:\\Users\\tester",
}


def blocked(command: str, powershell: bool = False) -> bool:
    with mock.patch.dict(os.environ, ENV):
        return bool(guard.problems_in(command, CWD, powershell))


class BashCommandTests(unittest.TestCase):
    def test_deletes_inside_the_project_are_allowed(self) -> None:
        for command in (
            "rm -f tests/tmp_file.txt",
            "rm -rf build/",
            'rm -f "C:/ai/anonimizer/src/__pycache__/x.pyc"',
            "rm -rf /c/ai/anonimizer/dist",
            "cd /c/ai/anonimizer && rm -f out.txt",
            "rm -f /tmp/commit_msg.txt",
            'SP="/c/Users/tester/AppData/Local/Temp/claude/x"; rm -rf "$SP/out"',
            "rm -rf $LOCALAPPDATA/Temp/claude/scratch",
            "git status && ls -la",
            "ollama list",
        ):
            with self.subTest(command=command):
                self.assertFalse(blocked(command))

    def test_deletes_outside_are_blocked(self) -> None:
        for command in (
            "rm -f /c/Users/tester/Documents/plik.txt",
            'rm -rf "C:/Users/tester/Desktop"',
            "rm ~/notes.txt",
            "rm -rf /c/ai",
            "rm -rf /c/ai/anonimizer",
            "rm -rf C:/ai/../Windows/x",
            "cd /c/Users/tester && rm -f notes.txt",
            "rm -rf ../other_folder_outside",
            "mv src/app.py /c/Users/tester/Desktop/",
            "rm -rf $UNKNOWN_VAR/x",
            "find /c/Users/tester -name '*.tmp' -delete",
            "ls /c/Users | xargs rm",
            'bash -c "rm -rf /c/Users/tester/Documents"',
            "rm -f /c/Users/tester/Documents/*.pdf",
        ):
            with self.subTest(command=command):
                self.assertTrue(blocked(command))


class PowerShellCommandTests(unittest.TestCase):
    def test_inside_allowed(self) -> None:
        for command in (
            "Remove-Item -Recurse -Force .\\build",
            "Remove-Item 'C:\\ai\\anonimizer\\tmp.txt' -Confirm:$false",
            "Get-ChildItem C:\\Users",
        ):
            with self.subTest(command=command):
                self.assertFalse(blocked(command, powershell=True))

    def test_outside_blocked(self) -> None:
        for command in (
            "Remove-Item -Path 'C:\\Users\\tester\\Documents\\a.txt'",
            "Remove-Item C:\\ai -Recurse -Force",
            "ri \"$env:USERPROFILE\\Desktop\\x\" -Recurse",
            "Move-Item .\\a.txt C:\\Users\\tester\\a.txt",
            "del C:\\Users\\tester\\a.txt",
        ):
            with self.subTest(command=command):
                self.assertTrue(blocked(command, powershell=True))


class HookProcessTests(unittest.TestCase):
    def _run(self, tool: str, command: str) -> int:
        payload = {"tool_name": tool, "tool_input": {"command": command}, "cwd": CWD}
        env = dict(os.environ, **ENV)
        return subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        ).returncode

    def test_exit_codes(self) -> None:
        self.assertEqual(self._run("Bash", "rm -f tests/x.txt"), 0)
        self.assertEqual(self._run("Bash", "rm -f /c/Users/tester/x.txt"), 2)
        self.assertEqual(self._run("PowerShell", "Remove-Item C:\\Users\\tester\\x"), 2)

    def test_garbage_input_only_blocks_when_it_looks_like_a_delete(self) -> None:
        env = dict(os.environ, **ENV)
        for raw, expected in (("not json", 0), ("not json rm -rf", 2)):
            result = subprocess.run(
                [sys.executable, str(HOOK_PATH)], input=raw, capture_output=True,
                text=True, env=env, check=False,
            )
            self.assertEqual(result.returncode, expected, raw)


if __name__ == "__main__":
    unittest.main()
