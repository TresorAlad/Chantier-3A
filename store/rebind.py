"""Rewrite SQL placeholders from ``?`` (Go/sqlx style) to ``%s`` (psycopg)."""

def rebind_query(query: str, driver: str) -> str:
    """Rebind query."""
    if driver != "postgres":
        return query
    out: list[str] = []
    i = 0
    while i < len(query):
        ch = query[i]
        if ch == "?":
            out.append("%s")
            i += 1
            continue
        if ch == "'":
            out.append(ch)
            i += 1
            while i < len(query):
                out.append(query[i])
                if query[i] == "'" and (i + 1 >= len(query) or query[i + 1] != "'"):
                    i += 1
                    break
                if query[i] == "'" and i + 1 < len(query) and query[i + 1] == "'":
                    out.append(query[i + 1])
                    i += 2
                    continue
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)
