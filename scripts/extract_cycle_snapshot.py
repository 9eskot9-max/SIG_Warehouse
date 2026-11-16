"""Extract selected cycle data from a local mysqldump to stdout, without writes.

The caller must protect output: it contains operational records. This parser
accepts the standard one-line INSERT format; unexpected shapes fail closed.
"""
import argparse
import gzip
import json
import re
import sys

TABLES = {"tabSIG Site Cycle", "tabSIG Evidence Event", "tabSIG Field Visit"}


def rows(text):
    row, val = [], []
    inside = quoted = escape = was_quoted = False
    for char in text:
        if quoted:
            if escape:
                val.append({"n": "\n", "r": "\r", "t": "\t", "0": "\0", "Z": "\x1a"}.get(char, char))
                escape = False
            elif char == "\\":
                escape = True
            elif char == "'":
                quoted = False
            else:
                val.append(char)
        elif char == "'":
            quoted = True
            was_quoted = True
        elif char == "(" and not inside:
            row, val = [], []
            inside = True
        elif inside and char in ",)":
            value = "".join(val)
            row.append(None if not was_quoted and value == "NULL" else value)
            val, was_quoted = [], False
            if char == ")":
                inside = False
                yield row
        elif inside:
            val.append(char)
    if quoted or inside or escape:
        raise ValueError("Incomplete SQL INSERT; only single-line statements are supported")


def extract(path):
    columns, collected = {}, {table: [] for table in TABLES}
    active = None
    with gzip.open(path, "rt", encoding="utf-8", errors="strict") as source:
        for line in source:
            match = re.match(r"CREATE TABLE `([^`]+)`", line)
            if match:
                active = match.group(1) if match.group(1) in TABLES else None
                if active:
                    if active in columns:
                        raise ValueError("Duplicate table definition")
                    columns[active] = []
                continue
            if active:
                match = re.match(r"\s*`([^`]+)`\s", line)
                if match:
                    columns[active].append(match.group(1))
                if line.startswith(") ENGINE="):
                    active = None
                continue
            match = re.match(r"INSERT INTO `([^`]+)` VALUES ", line)
            if match and match.group(1) in TABLES:
                table = match.group(1)
                if table not in columns:
                    raise ValueError("INSERT before table definition")
                for row in rows(line[match.end():]):
                    if len(row) != len(columns[table]):
                        raise ValueError(f"Unexpected column count for {table}")
                    collected[table].append(dict(zip(columns[table], row)))
    if set(columns) != TABLES:
        raise ValueError("Required tables missing from dump")
    return collected


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dump")
    args = parser.parse_args()
    json.dump(extract(args.dump), sys.stdout, ensure_ascii=False)
