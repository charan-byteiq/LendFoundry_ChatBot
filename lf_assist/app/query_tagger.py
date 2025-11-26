import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini

model = genai.GenerativeModel("gemini-2.5-flash")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def tag_query(query: str, tag_prompt_path: str) -> list[str]:
    try:
        with open(tag_prompt_path, "r") as f:
            prompt_template = f.read()

        final_prompt = prompt_template.replace("{question}", query.strip())

        response = model.generate_content(final_prompt).text.strip()

        # Look for "Tag(s):" line
        tag_line = next((line for line in response.splitlines() if line.startswith("Tag(s):")), "")
        if tag_line:
            return [tag.strip() for tag in tag_line.replace("Tag(s):", "").split(",") if tag.strip()]
        return []
    except Exception as e:
        print(f"⚠️ Error tagging query: {e}")
        return []
