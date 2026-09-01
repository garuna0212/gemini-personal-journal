import time

from google import genai

from guardian import protect_sensitive_data
from secret_manager import get_gemini_api_key


api_key = get_gemini_api_key()

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

    

    return {
        "analysis": response.text,
        "detected": detected,
        "protected_text": safe_entry
    }