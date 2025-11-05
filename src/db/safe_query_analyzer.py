import re
from langchain_core.tools import tool
DENY_RE = re.compile(r"\b(INSERT|UPDATE|DELETE|ALTER|DROP|CREATE|REPLACE|TRUNCATE)\b", re.I)
HAS_LIMIT_TAIL_RE = re.compile(r"(?is)\blimit\b\s+\d+(\s*,\s*\d+)?\s*;?\s*$")

def _safe_sql(q: str) -> str:
    # normalize
    q = q.strip()
    # block multiple statements (allow one optional trailing ;)
    if q.count(";") > 1 or (q.endswith(";") and ";" in q[:-1]):
        return "Error: multiple statements are not allowed."
    q = q.rstrip(";").strip()

    # read-only gate
    if not q.lower().startswith("select"):
        return "Error: only SELECT statements are allowed."
    if DENY_RE.search(q):
        return "Error: DML/DDL detected. Only read-only queries are permitted."

    # append LIMIT only if not already present at the end (robust to whitespace/newlines)
    if not HAS_LIMIT_TAIL_RE.search(q):
        q += " LIMIT 5"
    return q