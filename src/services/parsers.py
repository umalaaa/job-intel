import re
import hashlib
from typing import List, Tuple, Optional, Iterable

from src.core.constants import SKILL_KEYWORDS, INNOVATION_KEYWORDS, WEIRD_KEYWORDS


def parse_salary_range(raw: str) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    if not raw:
        return None, None, None
    lowered = raw.lower()
    salary_indicators = [
        "$",
        "salary",
        "per hour",
        "hourly",
        "per year",
        "annually",
        "annual",
        "/hr",
        "/hour",
        "/year",
        "hour",
        "yr",
        "year",
    ]
    if not any(indicator in lowered for indicator in salary_indicators):
        return None, None, None
    cleaned = raw.replace(",", "")
    numbers = [int(n) for n in re.findall(r"\d+", cleaned)]
    if not numbers:
        return None, None, raw.strip()
    if len(numbers) == 1:
        return numbers[0], numbers[0], raw.strip()
    return min(numbers), max(numbers), raw.strip()


def parse_title_company(text: str) -> Tuple[str, Optional[str]]:
    text = text.strip()
    separators = [" at ", " @ ", " | ", " - ", " — ", " – "]
    for sep in separators:
        if sep in text:
            parts = [p.strip() for p in text.split(sep) if p.strip()]
            if len(parts) >= 2:
                return parts[0], parts[1]
    return text, None


def compute_skills(title: str, tags: Iterable[str]) -> List[str]:
    lower = f"{title} {', '.join([str(tag) for tag in tags])}".lower()
    skills = []
    for key, label in SKILL_KEYWORDS.items():
        if re.search(rf"\b{re.escape(key)}\b", lower):
            skills.append(label)
    return sorted(set(skills))


def compute_innovations(title: str, tags: Iterable[str]) -> List[str]:
    lower = f"{title} {', '.join([str(tag) for tag in tags])}".lower()
    innovations = []
    for key, label in INNOVATION_KEYWORDS.items():
        if re.search(rf"\b{re.escape(key)}\b", lower):
            innovations.append(label)
    return sorted(set(innovations))


def compute_weird_tags(title: str, tags: Iterable[str]) -> List[str]:
    lower = f"{title} {', '.join([str(tag) for tag in tags])}".lower()
    weird = []
    for key, label in WEIRD_KEYWORDS.items():
        if re.search(rf"\b{re.escape(key)}\b", lower):
            weird.append(label)
    return sorted(set(weird))


def build_external_id(url: str, title: str) -> str:
    seed = f"{url}|{title}".encode("utf-8")
    return hashlib.sha1(seed).hexdigest()


def tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9\+#\.]+", text)


def infer_location(text: str, query: str) -> str:
    lowered = f"{text} {query}".lower()
    if "remote" in lowered:
        return "Remote"
    if "canada" in lowered:
        return "Canada"
    return "Canada"
