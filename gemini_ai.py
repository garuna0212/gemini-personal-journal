import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from guardian import protect_sensitive_data


env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(api_key=api_key)


def analyze_journal(entry):
    guardian_result = protect_sensitive_data(entry)

    safe_entry = guardian_result["protected_text"]
    detected = guardian_result["detected"]

    prompt = f"""
Analyze this journal entry briefly.

Return only:
Mood:
Summary:
Reflection:
Questions:
1.
2.

Keep the response concise.

Journal entry:
{safe_entry}
"""

    print("Starting Gemini request...")
    start = time.time()

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    print(
        "Gemini finished in",
        round(time.time() - start, 2),
        "seconds"
    )

    print("Gemini output:", response.text)

    return {
        "analysis": response.text,
        "detected": detected,
        "protected_text": safe_entry
    }


if __name__ == "__main__":
    result = analyze_journal(
        "Today I worked on my journal app and I am happy with the progress."
    )

    print(result)