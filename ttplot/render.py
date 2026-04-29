import sqlglot


def plot(query: str, **kwargs):
    from .backends.plotly import plot as plotly_plot
    from duckdb import register
    
    for tbl_name, tbl in kwargs.items():
        register(tbl_name, tbl)

    return plotly_plot(query)


def parse_sql(sql_script: str):
    out, start = [], 0

    for t in sqlglot.tokenize(sql_script):
        if t.token_type is sqlglot.tokens.TokenType.SEMICOLON:
            chunk = sql_script[start:t.start].strip()
            if chunk:
                out.append((sqlglot.parse_one(chunk, dialect='duckdb'), chunk))
            start = t.start + 1  # skip exactly the ';'

    # Comments at the end of script
    # tail = sql_script[start:].strip()
    # if tail:
    #     out.append(tail)

    return out