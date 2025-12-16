import re

def extract_sql_query(llm_output: str, strip_comments: bool = False) -> str:
    """
    Extracts the raw SQL query from LLM output.
    Assumes the LLM has been instructed to return only valid SQL with no extra explanation.
    
    Args:
        llm_output (str): The raw output from the language model.
        strip_comments (bool): Whether to remove SQL comments (optional).

    Returns:
        str: The cleaned SQL query.
    """
    # Decode escaped characters if they exist (e.g., "\\n" → "\n")
    try:
        if "\\n" in llm_output or "\\t" in llm_output:
            llm_output = bytes(llm_output, "utf-8").decode("unicode_escape")
    except Exception:
        pass  # Don't break if decoding fails

    # Remove markdown-style code fences if they slipped in
    llm_output = re.sub(r"(?i)^```sql\s*", "", llm_output.strip())
    llm_output = re.sub(r"(?i)```$", "", llm_output.strip())

    # Remove generic headers (if present)
    llm_output = re.sub(
        r"(?i)^(sql|generated sql query|query output|here is your sql):?\s*",
        "",
        llm_output.strip()
    )

    # Remove lines that are purely comments, if enabled
    if strip_comments:
        # Remove single-line comments starting with --
        llm_output = re.sub(r"(?m)^\s*--.*$", "", llm_output)
        
        # Optionally remove inline -- comments
        llm_output = re.sub(r"--.*", "", llm_output)

        # Optionally remove multi-line /* */ comments
        llm_output = re.sub(r"/\*.*?\*/", "", llm_output, flags=re.DOTALL)

        # Clean up extra blank lines
        lines = llm_output.splitlines()
        llm_output = "\n".join(line for line in lines if line.strip())
        
    return llm_output.strip()
