"""PreToolUse hook: block shell deletes outside the allowed folders.

Claude Code runs this before every Bash / PowerShell command, passing the
tool call as JSON on stdin. Exit code 2 blocks the command and shows the
stderr message to the model; exit code 0 lets it run.

Why (2026-09-25): the Claude Code sandbox does not run on native Windows,
and permission rules only restrict the file tools, not shell commands. So
nothing mechanical stopped e.g. `rm` on a file outside the projects
folder. This guard is that mechanical layer for *direct* delete/move
commands. It does not see files deleted from inside a program (a Python
script calling os.remove, for example) - it is a second layer, not
isolation.

Allowed: paths strictly inside a project folder under C:\\ai (never C:\\ai
itself or a whole project folder) and the user's temp folder. Anything
it can't resolve (an unknown $VARIABLE, `xargs rm` with paths from a
pipe) is blocked - fail closed.
"""

from __future__ import annotations

import json
import ntpath
import os
import re
import shlex
import sys

DELETE_VERBS = {
    "rm", "rmdir", "unlink", "shred", "del", "erase", "rd",
    "remove-item", "ri", "rni", "move-item", "mi", "mv", "move",
}
PROJECTS_ROOT = "c:\\ai"
_ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
_VAR = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|env:([A-Za-z_][A-Za-z0-9_]*)|([A-Za-z_][A-Za-z0-9_]*))")
_VERB_WORD = re.compile(
    r"(?i)(?<![\w-])(" + "|".join(sorted(map(re.escape, DELETE_VERBS), key=len, reverse=True)) + r")(?![\w-])"
)
# PowerShell parameters that take a value which is not a path.
_PS_VALUE_PARAMS = {"-filter", "-include", "-exclude", "-credential", "-stream"}


def split_segments(command: str) -> list[tuple[str, str]]:
    """Split a command line into (delimiter_before, segment) pairs on
    ; | & && || outside quotes, and on every newline. Quote-aware so a
    nested bash -c "cd X; ..." string stays one token for the recursive
    pass, which then sees the cd."""
    segments: list[tuple[str, str]] = []
    current: list[str] = []
    quote = ""
    before = ""
    index = 0
    while index < len(command):
        char = command[index]
        if quote:
            if char == "\n":
                # Unbalanced quote (e.g. an apostrophe in a heredoc): reset.
                quote = ""
                segments.append((before, "".join(current)))
                current, before = [], "\n"
                index += 1
                continue
            if char == quote:
                quote = ""
            current.append(char)
        elif char in "'\"":
            quote = char
            current.append(char)
        elif char in ";|&\n":
            pair = command[index:index + 2]
            delimiter = pair if pair in ("&&", "||") else char
            segments.append((before, "".join(current)))
            current, before = [], delimiter
            index += len(delimiter)
            continue
        else:
            current.append(char)
        index += 1
    segments.append((before, "".join(current)))
    return segments


def temp_root() -> str:
    base = os.environ.get("LOCALAPPDATA") or ntpath.join(
        os.environ.get("USERPROFILE", "C:\\Users\\Default"), "AppData", "Local"
    )
    return ntpath.normcase(ntpath.normpath(ntpath.join(base, "Temp")))


def to_windows_path(path: str, cwd: str | None, variables: dict[str, str]) -> str | None:
    """Resolve a shell path argument to a normalized Windows path, or None
    when it depends on something we can't know."""
    unresolved = False

    def expand(match: re.Match) -> str:
        nonlocal unresolved
        name = match.group(1) or match.group(2) or match.group(3)
        for key in (name, name.upper()):
            if key in variables:
                return variables[key]
            if key in os.environ:
                return os.environ[key]
        if name.upper() == "HOME":
            return os.environ.get("USERPROFILE", "")
        unresolved = True
        return ""

    path = _VAR.sub(expand, path)

    def expand_cmd(match: re.Match) -> str:
        nonlocal unresolved
        value = os.environ.get(match.group(1))
        if value is None:
            unresolved = True
            return ""
        return value

    path = re.sub(r"%([A-Za-z_][A-Za-z0-9_]*)%", expand_cmd, path)
    if unresolved or "$(" in path or "`" in path:
        return None
    if path.startswith("~"):
        path = os.environ.get("USERPROFILE", "") + path[1:]
    path = path.replace("/", "\\")
    # Git Bash style drive paths: \c\ai\x -> c:\ai\x ; \tmp -> temp folder
    drive = re.match(r"^\\([a-zA-Z])(\\|$)", path)
    if drive:
        path = f"{drive.group(1)}:\\" + path[3:]
    elif path.lower() == "\\tmp" or path.lower().startswith("\\tmp\\"):
        path = temp_root() + path[4:]
    # Wildcards: judge the fixed part in front of the first wildcard.
    wildcard = re.search(r"[*?\[]", path)
    if wildcard:
        path = path[: wildcard.start()]
        path = path.rsplit("\\", 1)[0] if "\\" in path else ""
    if not ntpath.isabs(path) or not ntpath.splitdrive(path)[0]:
        base = to_windows_path(cwd, "C:\\", {}) if cwd else None
        if base is None:
            return None
        path = ntpath.join(base, path)
    return ntpath.normcase(ntpath.normpath(path))


def path_is_allowed(path: str) -> bool:
    temp = temp_root()
    if path.startswith(temp + "\\"):
        return True
    if path.startswith(PROJECTS_ROOT + "\\"):
        # Strictly inside a project: C:\ai\<project>\<something>.
        rest = path[len(PROJECTS_ROOT) + 1:]
        return "\\" in rest.strip("\\")
    return False


def _tokens(segment: str, powershell: bool) -> list[str]:
    try:
        if powershell:
            raw = shlex.split(segment, posix=False)
            return [t[1:-1] if len(t) > 1 and t[0] == t[-1] and t[0] in "'\"" else t for t in raw]
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def problems_in(command: str, cwd: str | None, powershell: bool, depth: int = 0) -> list[str]:
    """Return a human-readable reason for every blocked target."""
    problems: list[str] = []
    variables: dict[str, str] = {}
    for delimiter, segment in split_segments(command):
        tokens = _tokens(segment, powershell)
        # Simple VAR=value assignments earlier in the same command line.
        while tokens and _ASSIGNMENT.match(tokens[0]):
            name, value = _ASSIGNMENT.match(tokens[0]).groups()
            variables[name] = value
            tokens = tokens[1:]
        if not tokens:
            continue
        if tokens[0].lower() in ("cd", "chdir", "set-location", "sl", "pushd"):
            target = tokens[1] if len(tokens) > 1 else "~"
            # "cd -" or an unresolvable target: cwd unknown from here on, so
            # every later relative path is blocked (fail closed).
            cwd = None if target == "-" else to_windows_path(target, cwd, variables)
            continue
        for index, token in enumerate(tokens):
            # Nested command strings: bash -c "...", powershell -Command "..."
            if depth < 3 and " " in token and _VERB_WORD.search(token):
                problems += problems_in(token, cwd, powershell or "-command" in segment.lower(), depth + 1)
                continue
            verb = ntpath.basename(token.replace("/", "\\")).lower()
            verb = verb.removesuffix(".exe")
            if verb not in DELETE_VERBS:
                continue
            args, skip_next = [], False
            for arg in tokens[index + 1:]:
                if skip_next:
                    skip_next = False
                    continue
                if arg.startswith("-") or (arg.startswith("/") and len(arg) <= 3 and not powershell and verb in ("del", "erase", "rd", "rmdir", "move")):
                    if arg.lower() in _PS_VALUE_PARAMS:
                        skip_next = True
                    continue
                args.append(arg)
            if not args and ("xargs" in (t.lower() for t in tokens[:index]) or delimiter == "|"):
                problems.append(f"'{verb}' takes its targets from a pipe - targets unknown")
            for arg in args:
                resolved = to_windows_path(arg, cwd, variables)
                if resolved is None:
                    problems.append(f"'{verb} {arg}' - cannot resolve the path")
                elif not path_is_allowed(resolved):
                    problems.append(f"'{verb} {arg}' -> {resolved}")
            break
        if tokens and ntpath.basename(tokens[0]).lower() in ("find", "find.exe") and (
            "-delete" in tokens or "-exec" in tokens
        ):
            for arg in tokens[1:]:
                if arg.startswith("-") or arg in ("(", "!"):
                    break
                resolved = to_windows_path(arg, cwd, variables)
                if resolved is None or not path_is_allowed(resolved):
                    problems.append(f"'find {arg} -delete/-exec' -> {resolved or 'unresolved'}")
    return problems


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
        command = str(payload.get("tool_input", {}).get("command", ""))
        powershell = payload.get("tool_name") == "PowerShell"
        cwd = str(payload.get("cwd") or os.getcwd())
        problems = problems_in(command, cwd, powershell)
    except Exception as error:  # noqa: BLE001 - fail closed only for delete-looking input
        if _VERB_WORD.search(raw):
            print(f"delete guard could not analyse the command ({type(error).__name__}); blocked", file=sys.stderr)
            return 2
        return 0
    if problems:
        print(
            "Blocked by the delete guard (.claude/hooks/guard_deletes.py): deleting or "
            "moving files is allowed only inside a project under C:\\ai or in the temp "
            "folder. Blocked targets:\n- " + "\n- ".join(problems) + "\nIf this is really "
            "needed, ask the user to do it themselves.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
