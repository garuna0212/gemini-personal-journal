from google import genai
from google.genai.errors import ClientError

from secret_manager import get_gemini_api_key
from guardian import protect_sensitive_data


api_key = get_gemini_api_key()

client = genai.Client(api_key=api_key)


def generate_chat_reply(messages):
    conversation_text = []

    for message in messages:
        role = message["role"]
        content = message["content"]

        if role == "user":
            protected = protect_sensitive_data(content)
            content = protected["protected_text"]

        conversation_text.append(
            f"{role.upper()}: {content}"
        )

    prompt = f"""
You are a supportive journaling and brainstorming assistant.

Continue this conversation naturally.

Rules:
- Remember the context from previous messages.
- Be concise but helpful.
- Ask useful follow-up questions when appropriate.
- Do not diagnose medical or mental health conditions.
- Do not reveal unnecessary sensitive information.

Conversation:

{chr(10).join(conversation_text)}

ASSISTANT:
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )

       
        return response.text

    except ClientError as e:
        print("GEMINI CLIENT ERROR:", e)

        if e.code == 429:
            return (
                "Gemini is temporarily rate-limited. "
                "Please wait and try again later."
            )

        raise


def summarize_conversation(messages):
    conversation_text = []

    for message in messages:
        role = message["role"]
        content = message["content"]

        if role == "user":
            protected = protect_sensitive_data(content)
            content = protected["protected_text"]

        conversation_text.append(
            f"{role.upper()}: {content}"
        )

    prompt = f"""
Summarize this journaling or brainstorming conversation.

Return only:

Summary:
Key Themes:
Important Takeaways:
Possible Next Steps:

Keep it concise.

Conversation:

{chr(10).join(conversation_text)}
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )

        return response.text

    except ClientError as e:
        print("GEMINI SUMMARY ERROR:", e)

        if e.code == 429:
            return (
                "Gemini is temporarily rate-limited. "
                "Please try again later."
            )

        raise