import re
import sqlglot
from functools import lru_cache


def get_col_roles(sql_script):

    def split_preserving_groups(s):
        pattern = r"\S*\[[^\]]*\]|[^\s']*'[^']*'|[^\s\"]*\"[^\"]*\"|\S+"
        return re.findall(pattern, s)

    tree = sqlglot.parse_one(sql_script, read="duckdb")

    column_roles = {}
    for exp in tree.find(sqlglot.exp.Select).expressions:
        if exp.expression:
            col_name = exp.alias or str(exp)
        else:
            col_name = exp.alias_or_name

        if col_name and exp.comments:
            column_roles[col_name] = split_preserving_groups(" ".join(exp.comments))

    # Global roles are specified in the top of the query, and are assignments only.
    global_roles = [
        role
        for role in (tree.find(sqlglot.exp.From).comments or [])
        + (tree.find(sqlglot.exp.Select).comments or [])
        if "=" in role
    ]
    if global_roles:
        column_roles["__global__"] = [split_preserving_groups(c) for c in global_roles]

    return column_roles


@lru_cache(maxsize=512)
def parse_tag(tag: str):
    if "=" not in tag:
        return (tag.strip(), None)

    key, val = tag.split("=", 1)

    def tokenize(s):
        tokens, i = [], 0
        while i < len(s):
            if s[i].isspace():
                i += 1
            elif s[i] in "\"'":
                quote = s[i]
                i += 1
                start = i
                while i < len(s) and s[i] != quote:
                    i += 1
                tokens.append(s[start:i])
                i += 1
            elif s[i] in "[({":
                tokens.append(s[i])
                i += 1
            elif s[i] in "])}":
                tokens.append(s[i])
                i += 1
            else:
                start = i
                while i < len(s) and s[i] not in " \t\n[({])}\"'":
                    i += 1
                tokens.append(s[start:i])
        return tokens

    def parse_tokens(tokens, i=0):
        if i >= len(tokens):
            return None, i

        token = tokens[i]

        if token == "":
            return "", i + 1

        if token in "[({":
            close = {"[": "]", "(": ")", "{": "}"}[token]
            items, i = [], i + 1
            while i < len(tokens) and tokens[i] != close:
                val, i = parse_tokens(tokens, i)
                items.append(val)
            return items, i + 1

        clean = token.replace("_", "")
        if clean.replace(".", "", 1).replace("-", "", 1).isdigit():
            return (float(clean) if "." in clean else int(clean)), i + 1
        if token.lower() in ("true", "false"):
            return token.lower() == "true", i + 1
        if token.lower() == "null":
            return None, i + 1
        return token, i + 1

    tokens = tokenize(val.strip())
    result, _ = parse_tokens(tokens)
    return key.strip(), result


def get_tag_value(
    path: str, tags: list[str], bool_tags: list[str] | set[str] | None = None
):
    if bool_tags is None:
        bool_tags = []

    bool_tags_set = set(bool_tags)

    tag_dict = {}
    tag_sequence = []
    all_tag_names = set()

    plain_count = 0
    for tag in tags:
        if "=" in tag:
            key, value = parse_tag(tag)
            tag_dict.setdefault(key, []).append((plain_count, value))
            all_tag_names.add(key)
        else:
            all_tag_names.add(tag)
            if tag not in bool_tags_set:
                tag_sequence.append(tag)
                plain_count += 1

    path_components = path.split(" ")
    tag_idx = 0
    has_wildcard = any(c == "*" for c in path_components)

    for _, component in enumerate(path_components):
        if component == "*":
            if tag_idx >= len(tag_sequence):
                return None
            tag_idx += 1
        elif component in bool_tags_set:
            if component not in all_tag_names:
                return None
        elif component in tag_dict:
            if not has_wildcard:
                positions = [pos for pos, _ in tag_dict[component]]
                if tag_idx not in positions:
                    return None
        else:
            if tag_idx >= len(tag_sequence) or tag_sequence[tag_idx] != component:
                return None
            tag_idx += 1

    last_component = path_components[-1]

    if last_component in tag_dict:
        if has_wildcard:
            return tag_dict[last_component][-1][1]
        for pos, val in tag_dict[last_component]:
            if pos == tag_idx:
                return val
        return None

    return True
