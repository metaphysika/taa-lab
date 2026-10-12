"""Owner-amended B parser: one complete outer JSON object, no partial/XML repair.

Introduced after H55's failed first block, before other held-out B runs. Original
parser and all historical labels stay unchanged. Text surrounding the single JSON
object is ignored; original action schema/duplicate-field checks still apply.
"""
import json
from formation.study_b_v0227 import parse_action as strict_action


def reject_constant(value):
    raise ValueError("non-JSON numeric constant")


def parse_action(text):
    spans=[];stack=[];start=None;quoted=False;escaped=False
    for i,ch in enumerate(text):
        if not stack:
            if ch in '{[':start=i;stack=[ch];quoted=False;escaped=False
            continue
        if quoted:
            if escaped:escaped=False
            elif ch=='\\':escaped=True
            elif ch=='"':quoted=False
            continue
        if ch=='"':quoted=True
        elif ch in '{[':stack.append(ch)
        elif ch in '}]':
            if (ch=='}' and stack[-1]!='{') or (ch==']' and stack[-1]!='['):raise ValueError('malformed_reply')
            stack.pop()
            if not stack:
                raw=text[start:i+1]
                try:value=json.loads(raw,parse_constant=reject_constant)
                except ValueError:continue # Non-JSON surrounding text is not an action.
                spans.append((raw,value))
    if stack:raise ValueError('malformed_reply') # Never find a nested action inside an incomplete container.
    if len(spans)!=1 or not isinstance(spans[0][1],dict):raise ValueError('malformed_reply')
    # Preserve the established schema labels, including malformed_action, and
    # reject duplicate JSON fields with the unchanged strict validator.
    return strict_action(spans[0][0])
