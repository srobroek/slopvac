from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TomlComment:
    line: int
    column: int
    body: str
    end_column: int

def _newline_at(text: str, index: int) -> int:
    return index + 2 if text[index:index + 2] == "\r\n" else index + 1

def extract_comments(text: str) -> list[TomlComment]:
    comments = []
    state = "plain"
    index = line = 0
    line_start = 0
    comment_start = -1
    while index < len(text):
        char = text[index]
        if state == "comment":
            if char in "\r\n":
                comments.append(TomlComment(line + 1, comment_start - line_start + 1, text[comment_start + 1:index], index - line_start + 1))
                index = _newline_at(text, index)
                line += 1
                line_start = index
                state = "plain"
            else:
                index += 1
            continue
        if state == "basic":
            if char == "\\":
                index += 2
            else:
                state = "plain" if char == chr(34) else state
                index += 1
            continue
        if state == "literal":
            state = "plain" if char == chr(39) else state
            index += 1
            continue
        if state == "basic_multi":
            if char == chr(34):
                run_end = index
                while run_end < len(text) and text[run_end] == char:
                    run_end += 1
                if run_end - index >= 3:
                    state, index = "plain", run_end
                else:
                    index = run_end
            elif char == "\\":
                next_index = index + 1
                if next_index < len(text) and text[next_index] in "\r\n":
                    index = _newline_at(text, next_index)
                    line += 1
                    line_start = index
                else:
                    index += 2
            elif char in "\r\n":
                index = _newline_at(text, index)
                line += 1
                line_start = index
            else:
                index += 1
            continue
        if state == "literal_multi":
            if char == chr(39):
                run_end = index
                while run_end < len(text) and text[run_end] == char:
                    run_end += 1
                if run_end - index >= 3:
                    state, index = "plain", run_end
                else:
                    index = run_end
            elif char in "\r\n":
                index = _newline_at(text, index)
                line += 1
                line_start = index
            else:
                index += 1
            continue
        if text.startswith(chr(34) * 3, index):
            state, index = "basic_multi", index + 3
        elif text.startswith(chr(39) * 3, index):
            state, index = "literal_multi", index + 3
        elif char == chr(34):
            state, index = "basic", index + 1
        elif char == chr(39):
            state, index = "literal", index + 1
        elif char == "#":
            comment_start, state, index = index, "comment", index + 1
        elif char in "\r\n":
            index, line, line_start = (
                _newline_at(text, index),
                line + 1,
                _newline_at(text, index),
            )
        else:
            index += 1
    if state == "comment":
        comments.append(
            TomlComment(
                line + 1,
                comment_start - line_start + 1,
                text[comment_start + 1 :],
                len(text) - line_start + 1,
            )
        )
    return comments

def comment_projection(text: str) -> str:
    result = [char if char in "\r\n" else " " for char in text]
    line_starts = [0]
    for line in text.splitlines(keepends=True):
        line_starts.append(line_starts[-1] + len(line))
    for comment in extract_comments(text):
        start = line_starts[comment.line - 1] + comment.column - 1
        end = start + len(comment.body) + 1
        result[start:end] = text[start:end]
    return "".join(result)

def is_toml_path(path) -> bool:
    return path.name == "mise.toml" or path.suffix.lower() == ".toml"
