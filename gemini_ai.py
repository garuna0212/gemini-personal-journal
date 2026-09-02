import time

from google import genai
from google.genai.errors import ServerError, ClientError

from guardian import protect_sensitive_data
from secret_manager import get_gemini_api_key


api_key = get_gemini_api_key()

print(
    "Loaded Gemini key ending in:",
    api_key[-4:]
)

client = genai.Client(
    api_key=api_key
)


def analyze_journal(entry):
    guardian_result = protect_sensitive_data(entry)

    safe_entry = guardian_result["protected_text"]
    detected = guardian_result["detected"]

    prompt = f"""
Analyze this journal entry briefly.

Return the response in clean Markdown using exactly this structure:

### Mood
A short mood description.

### Summary
A concise summary.

### Reflection
A short reflective insight.

### Questions
1. One thoughtful question.
2. Another thoughtful question.

Keep the response concise.
Do not include any extra sections.

Journal entry:
{safe_entry}
"""

    print("Starting Gemini request...")

    max_attempts = 1

    for attempt in range(1, max_attempts + 1):

        try:
            start = time.time()

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt
            )

            elapsed = time.time() - start

            print(
                f"Gemini request completed in "
                f"{elapsed:.2f} seconds"
            )

            if not response.text:
                raise ValueError(
                    "Gemini returned an empty response"
                )

            return {
                "analysis": response.text,
                "detected": detected,
                "protected_text": safe_entry,
                "error": None
            }

        except ServerError as e:

            print(
                f"Gemini temporary error "
                f"(attempt {attempt}/{max_attempts}):",
                str(e)
            )

            

            return {
                "analysis": None,
                "detected": detected,
                "protected_text": safe_entry,
                "error":
                    "Gemini is temporarily busy. "
                    "Please try again in a moment."
            }

        except ClientError as e:

            print(
                "Gemini client error:",
                str(e)
            )

            return {
                "analysis": None,
                "detected": detected,
                "protected_text": safe_entry,
                "error":
                    "Gemini could not process the request. "
                    "Please try again later."
            }

        except Exception as e:

            print(
                "Unexpected Gemini error:",
                type(e).__name__,
                str(e)
            )

            return {
                "analysis": None,
                "detected": detected,
                "protected_text": safe_entry,
                "error":
                    "Something went wrong while analyzing "
                    "the journal entry."
            }