import re

def sanitize_text(text: str) -> str:
    """Replace phone numbers with 'WFPB member' or strip them for privacy."""
    if not text or not isinstance(text, str):
        return text
        
    # Regex for common phone formats: +1 (123) 456-7890, +91 ..., 123-456-7890 etc.
    # Matches strings of 7+ digits potentially separated by common delimiters
    phone_pattern = r'(\+?\(?\d[\d\s\-\.\(\)]{5,}\d)'
    
    def replacer(match):
        val = match.group(0)
        # Verify it's likely a phone number (at least 7 digits)
        digits = re.sub(r'\D', '', val)
        if len(digits) >= 7:
            return "WFPB member"
        return val

    # First, handle the specific case where the string IS just a phone number
    # If the text is ONLY a phone number (or near enough), return 'WFPB member'
    digits_only = re.sub(r'\D', '', text)
    if digits_only and len(digits_only) >= 7 and len(digits_only) / len(text) > 0.5:
        return "WFPB member"

    # Otherwise, replace phone numbers within the text
    return re.sub(phone_pattern, replacer, text)
