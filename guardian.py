import re


def protect_sensitive_data(text):
    protected_text = text
    detected = []

    # Email addresses
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"

    if re.search(email_pattern, protected_text):
        detected.append("Email address")
        protected_text = re.sub(
            email_pattern,
            "[EMAIL]",
            protected_text
        )

    # Indian phone numbers
    phone_pattern = r"\b(?:\+91[\-\s]?)?[6-9]\d{9}\b"

    if re.search(phone_pattern, protected_text):
        detected.append("Phone number")
        protected_text = re.sub(
            phone_pattern,
            "[PHONE_NUMBER]",
            protected_text
        )

    # Aadhaar-like 12 digit numbers
    aadhaar_pattern = r"\b\d{4}\s?\d{4}\s?\d{4}\b"

    if re.search(aadhaar_pattern, protected_text):
        detected.append("12-digit ID number")
        protected_text = re.sub(
            aadhaar_pattern,
            "[SENSITIVE_ID]",
            protected_text
        )

    # URLs
    url_pattern = r"https?://[^\s]+|www\.[^\s]+"

    if re.search(url_pattern, protected_text):
        detected.append("Website URL")
        protected_text = re.sub(
            url_pattern,
            "[URL]",
            protected_text
        )

    return {
        "protected_text": protected_text,
        "detected": detected
    }