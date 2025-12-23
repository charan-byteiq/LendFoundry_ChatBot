from services import get_gemini_client
from logger import logger


def tag_query(query: str, tag_prompt_path: str) -> list[str]:
    try:
        with open(tag_prompt_path, "r") as f:
            prompt_template = f.read()

        final_prompt = prompt_template.replace("{question}", query.strip())

        gemini = get_gemini_client()
        response = gemini.generate(final_prompt).strip()

        # Look for "Tag(s):" line
        tag_line = next((line for line in response.splitlines() if line.startswith("Tag(s):")), "")
        if tag_line:
            return [tag.strip() for tag in tag_line.replace("Tag(s):", "").split(",") if tag.strip()]
        return []
    except Exception as e:
        logger.error(f"Error tagging query: {e}")
        return []
