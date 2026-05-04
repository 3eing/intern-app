import re
from typing import Dict, List


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


def split_paragraphs(raw_text: str) -> List[str]:
    if not raw_text:
        return []

    text = str(raw_text).replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    blocks = re.split(r"\n\s*\n+", text)

    paragraphs = []
    for block in blocks:
        block = re.sub(r"\s+", " ", block).strip()
        if block:
            paragraphs.append(block)

    return paragraphs


def parse_structured_text(raw_text: str, mode: str = "description") -> Dict[str, Any]:
    """
    mode='description' -> returns:
    {
        "intro": "...",
        "bullets": [{"text": "...", "subitems": ["..."]}]
    }

    mode='context' -> returns:
    {
        "paragraphs": ["...", "..."]
    }
    """
    if not raw_text:
        if mode == "context":
            return {"paragraphs": []}
        return {"intro": "", "bullets": []}

    if mode == "context":
        return {
            "paragraphs": split_paragraphs(raw_text)
        }

    lines = str(raw_text).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = [line.rstrip() for line in lines if line.strip()]

    intro_parts: List[str] = []
    bullets: List[Dict[str, List[str]]] = []
    current_bullet = None
    intro_done = False

    for raw_line in lines:
        line = raw_line.strip()

        if line.startswith("•"):
            intro_done = True
            bullet_text = clean_end_punctuation(normalize_line(line[1:].strip()))
            current_bullet = {
                "text": bullet_text,
                "subitems": []
            }
            bullets.append(current_bullet)

        elif re.match(r"^[oO]\s+", line) or line.startswith("o\t") or line.startswith("o "):
            subitem_text = clean_end_punctuation(normalize_line(re.sub(r"^[oO]\s*", "", line)))
            if current_bullet is not None:
                current_bullet["subitems"].append(subitem_text)

        else:
            if not intro_done:
                intro_parts.append(normalize_line(line))
            else:
                if current_bullet is not None:
                    current_bullet["text"] += " " + clean_end_punctuation(normalize_line(line))

    intro = " ".join(intro_parts).strip()
    intro = ensure_terminal_punctuation(intro, for_intro=True)

    for bullet in bullets:
        has_subitems = len(bullet["subitems"]) > 0
        bullet["text"] = ensure_terminal_punctuation(
            clean_end_punctuation(bullet["text"]),
            has_subitems=has_subitems
        )
        bullet["subitems"] = [
            ensure_terminal_punctuation(clean_end_punctuation(normalize_line(subitem)))
            for subitem in bullet["subitems"]
        ]

    return {
        "intro": intro,
        "bullets": bullets
    }



if __name__ == "__main__":
    print(normalize_address("""
    Direction du service maritime
    +1 418 559-6646 
    josianne.pusterla@wsp.com
    """))
    print(parse_structured_text("""3E Ing. was commissioned to conduct a diagnostic of the electricity distribution network and design a detailed master plan to help STEG achieve the objectives of its performance contract. The mission focused on reducing technical and commercial losses. The technical experts from 3E Ing. carried out the following tasks:

• Correction of the network database (DB);

• Integration of the DB into the Cymdist simulation software;

• Simulation of the distribution network;

• Calculation of technical losses in the medium and low voltage networks;

• Identification of solutions to correct network issues and reduce losses;

• Preparation of a technical report to:

  o Explain the simulation approach;

  o Identify the encountered problems;

  o Define the calculation of medium and low voltage distribution losses."""))

