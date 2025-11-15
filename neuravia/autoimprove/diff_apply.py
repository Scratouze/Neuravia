from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

@dataclass
class Hunk:
    old_start: int
    old_len: int
    new_start: int
    new_len: int
    lines: List[Tuple[str, str]]  # (tag, text) where tag in {" ", "+", "-"}

@dataclass
class PatchFile:
    path: str
    hunks: List[Hunk]

def parse_unified_patch(patch_text: str) -> List[PatchFile]:
    """
    Very small unified diff parser supporting a common subset:
    --- a/path
    +++ b/path
    @@ -old_start,old_len +new_start,new_len @@
     context
    -removed
    +added
    """
    lines = patch_text.splitlines()
    i = 0
    out: List[PatchFile] = []
    cur_path = None
    cur_hunks: List[Hunk] = []
    while i < len(lines):
        line = lines[i]
        if line.startswith('--- '):
            # next line should be +++
            i += 1
            if i >= len(lines) or not lines[i].startswith('+++ '):
                raise ValueError("Malformed patch: expected +++ after ---")
            # store previous file if any
            if cur_path is not None:
                out.append(PatchFile(cur_path, cur_hunks))
                cur_hunks = []
            plus = lines[i][4:].strip()
            # path after 'b/' if present
            path = plus
            if plus.startswith('b/'):
                path = plus[2:]
            cur_path = path
            i += 1
            continue
        if line.startswith('@@ '):
            # parse hunk header
            # format: @@ -l,s +l2,s2 @@
            import re
            m = re.match(r"@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@", line)
            if not m:
                raise ValueError("Malformed hunk header: " + line)
            ostart = int(m.group(1))
            olen = int(m.group(2) or "1")
            nstart = int(m.group(3))
            nlen = int(m.group(4) or "1")
            i += 1
            h_lines: List[Tuple[str,str]] = []
            while i < len(lines):
                l = lines[i]
                if l.startswith('@@ ') or l.startswith('--- ') or l.startswith('+++ '):
                    break
                if l and l[0] in (' ', '+', '-'):
                    tag = l[0]
                    text = l[1:]
                    h_lines.append((tag, text))
                    i += 1
                else:
                    # treat as context
                    h_lines.append((' ', l))
                    i += 1
            cur_hunks.append(Hunk(ostart, olen, nstart, nlen, h_lines))
            continue
        i += 1
    if cur_path is not None:
        out.append(PatchFile(cur_path, cur_hunks))
    return out

def apply_hunks_to_text(original: str, hunks: List[Hunk]) -> str:
    """
    Apply hunks to a text. Lines are 1-based in diff headers.
    We ignore header counts and trust the sequence of context/removals/additions.
    """
    old_lines = original.splitlines()
    # Work line-by-line applying hunks in order
    idx = 0  # current index in old_lines
    new_lines: List[str] = []
    for h in hunks:
        # Copy unaffected lines up to the expected old_start-1 (best effort)
        target = h.old_start - 1
        while idx < target and idx < len(old_lines):
            new_lines.append(old_lines[idx])
            idx += 1
        # Now apply hunk lines
        for tag, txt in h.lines:
            if tag == ' ':
                # context: must match if possible
                if idx < len(old_lines):
                    # If mismatch, still proceed (best effort), but keep the incoming txt
                    idx += 1
                new_lines.append(txt)
            elif tag == '-':
                # removal: skip a line from old if available
                if idx < len(old_lines):
                    idx += 1
                # do not append
            elif tag == '+':
                new_lines.append(txt)
    # Append remaining old lines not touched by hunks
    while idx < len(old_lines):
        new_lines.append(old_lines[idx])
        idx += 1
    return "\n".join(new_lines) + ("" if original.endswith("\n") else "")
