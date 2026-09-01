import re


def normalize_line(line: str) -> str:
    if line is None:
        return ""
    line = str(line).replace("\r", " ").replace("\n", " ").replace("\t", " ")
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def clean_end_punctuation(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[;:]+$", "", text).rstrip()
    return text


def ensure_terminal_punctuation(text: str, for_intro: bool = False, has_subitems: bool = False) -> str:
    text = text.strip()
    if not text:
        return text

    if for_intro or has_subitems:
        if text.endswith(":"):
            return text
        if text[-1] in ".;":
            return text[:-1] + ":"
        return text + ":"

    if text[-1] not in ".!?":
        return text + "."
    return text


def normalize_address(raw_address: str) -> str:
    if not raw_address:
        return ""

    text = str(raw_address)

    # Normalize line endings and tabs
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")

    # Remove obvious bad OCR / encoding artifacts
    text = text.replace("¬", "")
    text = text.replace("­", "")  # soft hyphen sometimes pasted invisibly

    # Trim spaces around each line
    lines = [re.sub(r"\s+", " ", line).strip(" ,") for line in text.split("\n")]

    # Remove empty lines
    lines = [line for line in lines if line]

    # Rebuild with clean line breaks
    return "\n".join(lines)

