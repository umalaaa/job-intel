#!/usr/bin/env python3
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import urllib.request
from typing import Dict, Iterable, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
WEB_DATA_DIR = os.path.join(BASE_DIR, "web", "data")
DB_PATH = os.path.join(DATA_DIR, "job-intel.db")
LOG_DIR = os.path.join(BASE_DIR, "logs")

TAVILY_URL = os.getenv("TAVILY_URL", "https://api.tavily.com/search")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_MAX_RESULTS = int(os.getenv("TAVILY_MAX_RESULTS", "25"))
TAVILY_SEARCH_DEPTH = os.getenv("TAVILY_SEARCH_DEPTH", "basic")
TAVILY_QUERIES = os.getenv(
    "TAVILY_QUERIES",
    'site:gc.ca "job posting" Canada;site:canada.ca "job posting" Canada;site:jobbank.gc.ca "job posting";site:jobs.gc.ca "job posting";Canada "job posting" "apply"',
)
RARE_TITLE_MAX_FREQ = int(os.getenv("RARE_TITLE_MAX_FREQ", "1"))

SOURCE_TAVILY = "tavily"
BLOCKLIST_DOMAINS = [
    "linkedin.com/jobs",
    "indeed.com",
    "careerjet",
    "workopolis",
    "jooble",
    "glassdoor",
    "himalayas",
    "drjobpro",
    "remoteok",
    "remotive",
]

SKILL_KEYWORDS = {
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "go": "Go",
    "golang": "Go",
    "java": "Java",
    "kotlin": "Kotlin",
    "swift": "Swift",
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "GCP",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "terraform": "Terraform",
    "react": "React",
    "node": "Node.js",
    "node.js": "Node.js",
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "data": "Data",
    "security": "Security",
    "devops": "DevOps",
    "cloud": "Cloud",
}

INNOVATION_KEYWORDS = {
    "genai": "GenAI",
    "generative ai": "GenAI",
    "llm": "LLM",
    "ai": "AI",
    "machine learning": "Machine Learning",
    "robot": "Robotics",
    "robotics": "Robotics",
    "autonomous": "Autonomous Systems",
    "quantum": "Quantum",
    "biotech": "Biotech",
    "bioinformatics": "Bioinformatics",
    "ar": "AR/VR",
    "vr": "AR/VR",
    "augmented reality": "AR/VR",
    "virtual reality": "AR/VR",
    "cybersecurity": "Cybersecurity",
    "security": "Cybersecurity",
    "energy": "Clean Energy",
    "climate": "Climate Tech",
    "blockchain": "Web3",
    "web3": "Web3",
}

WEIRD_KEYWORDS = {
    "prompt engineer": "Prompt Engineering",
    "futurist": "Futurist",
    "quantum": "Quantum",
    "bioinformatics": "Bioinformatics",
    "ethicist": "AI Ethics",
    "responsible ai": "AI Ethics",
    "cryptographer": "Cryptography",
    "threat hunter": "Threat Hunter",
    "astrophys": "Astrophysics",
    "geospatial": "Geospatial",
    "metaverse": "Metaverse",
    "behavioral": "Behavioral Science",
    "neuroscience": "Neuroscience",
    "policy": "Policy",
    "regulatory": "Regulatory",
}


def ensure_dirs() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(WEB_DATA_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)


def http_post(url: str, payload: Dict) -> bytes:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": "job-intel-bot/1.0",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TAVILY_API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read()


def parse_salary_range(raw: str) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    if not raw:
        return None, None, None
    cleaned = raw.replace(",", "")
    numbers = [int(n) for n in re.findall(r"\d+", cleaned)]
    if not numbers:
        return None, None, raw.strip()
    if len(numbers) == 1:
        return numbers[0], numbers[0], raw.strip()
    return min(numbers), max(numbers), raw.strip()


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            external_id TEXT NOT NULL,
            title TEXT NOT NULL,
            company TEXT,
            location TEXT,
            salary_min INTEGER,
            salary_max INTEGER,
            salary_text TEXT,
            category TEXT,
            tags TEXT,
            url TEXT,
            published_at TEXT,
            fetched_at TEXT NOT NULL,
            is_remote INTEGER NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_source_external
        ON jobs (source, external_id);
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at TEXT NOT NULL,
            total_jobs INTEGER NOT NULL
        );
        """
    )
    conn.commit()


def upsert_job(conn: sqlite3.Connection, job: Dict) -> None:
    conn.execute(
        """
        INSERT INTO jobs (
            source, external_id, title, company, location, salary_min, salary_max,
            salary_text, category, tags, url, published_at, fetched_at, is_remote
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source, external_id) DO UPDATE SET
            title=excluded.title,
            company=excluded.company,
            location=excluded.location,
            salary_min=excluded.salary_min,
            salary_max=excluded.salary_max,
            salary_text=excluded.salary_text,
            category=excluded.category,
            tags=excluded.tags,
            url=excluded.url,
            published_at=excluded.published_at,
            fetched_at=excluded.fetched_at,
            is_remote=excluded.is_remote
        ;
        """,
        (
            job["source"],
            job["external_id"],
            job["title"],
            job.get("company"),
            job.get("location"),
            job.get("salary_min"),
            job.get("salary_max"),
            job.get("salary_text"),
            job.get("category"),
            job.get("tags"),
            job.get("url"),
            job.get("published_at"),
            job["fetched_at"],
            1 if job.get("is_remote") else 0,
        ),
    )


def parse_title_company(text: str) -> Tuple[str, Optional[str]]:
    text = text.strip()
    separators = [" at ", " @ ", " | ", " - ", " — ", " – "]
    for sep in separators:
        if sep in text:
            parts = [p.strip() for p in text.split(sep) if p.strip()]
            if len(parts) >= 2:
                return parts[0], parts[1]
    return text, None


def infer_location(text: str, query: str) -> str:
    lowered = f"{text} {query}".lower()
    if "remote" in lowered:
        return "Remote"
    if "canada" in lowered:
        return "Canada"
    return "Canada"


def build_external_id(url: str, title: str) -> str:
    seed = f"{url}|{title}".encode("utf-8")
    return hashlib.sha1(seed).hexdigest()


def is_job_result(title: str, content: str) -> bool:
    text = f"{title} {content}".lower()
    keywords = ["job", "jobs", "hiring", "career", "careers", "position", "opening"]
    return any(keyword in text for keyword in keywords)


def tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9\+#\.]+", text)


def fetch_tavily_jobs(
    queries: List[str], max_results: int, search_depth: str
) -> List[Dict]:
    if not TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY missing")
    jobs: List[Dict] = []
    seen: set[str] = set()
    now = dt.datetime.utcnow().isoformat()

    for query in queries:
        payload = {
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": False,
            "include_raw_content": False,
        }
        response = json.loads(http_post(TAVILY_URL, payload))
        for result in response.get("results", []):
            title_text = (result.get("title") or "").strip()
            content = (result.get("content") or "").strip()
            url = (result.get("url") or "").strip()
            if not title_text and not content:
                continue
            if not is_job_result(title_text, content):
                continue
            title, company = parse_title_company(title_text)
            salary_min, salary_max, salary_text = parse_salary_range(
                f"{title_text} {content}"
            )
            tags = tokenize(f"{title_text} {content}")
            ext_id = build_external_id(url or title_text, title)
            if ext_id in seen:
                continue
            seen.add(ext_id)
            job = {
                "source": SOURCE_TAVILY,
                "external_id": ext_id,
                "title": title,
                "company": company or "Unknown",
                "location": infer_location(f"{title_text} {content}", query),
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_text": salary_text,
                "category": "Tavily Search",
                "tags": json.dumps(tags),
                "url": url,
                "published_at": result.get("published_date"),
                "fetched_at": now,
                "is_remote": "remote" in (title_text + " " + content).lower(),
            }
            jobs.append(job)
        time.sleep(0.5)
    return jobs


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


def salary_rank(
    salary_min: Optional[int], salary_max: Optional[int], salary_text: Optional[str]
) -> int:
    if salary_max:
        return salary_max
    if salary_min:
        return salary_min
    parsed_min, parsed_max, _ = parse_salary_range(salary_text or "")
    if parsed_max:
        return parsed_max
    if parsed_min:
        return parsed_min
    return 0


def generate_summary(conn: sqlite3.Connection) -> Tuple[Dict, List[Dict], Dict, Dict]:
    cursor = conn.execute(
        "SELECT source, title, company, location, salary_min, salary_max, salary_text, category, tags, url, published_at FROM jobs"
    )
    rows = cursor.fetchall()
    total = len(rows)
    locations: Dict[str, int] = {}
    skill_counts: Dict[str, int] = {}
    innovation_counts: Dict[str, int] = {}
    title_counts: Dict[str, int] = {}
    innovation_roles: List[Dict] = []
    weird_roles: List[Dict] = []
    rare_roles: List[Dict] = []
    roles: List[Dict] = []

    for row in rows:
        title_counts[row[1].strip().lower()] = (
            title_counts.get(row[1].strip().lower(), 0) + 1
        )

    for (
        source,
        title,
        company,
        location,
        salary_min,
        salary_max,
        salary_text,
        category,
        tags_raw,
        url,
        published_at,
    ) in rows:
        tags = json.loads(tags_raw) if tags_raw else []
        skills = compute_skills(title, tags)
        innovations = compute_innovations(title, tags)
        weird_tags = compute_weird_tags(title, tags)
        for skill in skills:
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
        for innovation in innovations:
            innovation_counts[innovation] = innovation_counts.get(innovation, 0) + 1
        if location:
            locations[location] = locations.get(location, 0) + 1
        salary_display = salary_text
        if salary_display is None and salary_min and salary_max:
            salary_display = f"{salary_min}-{salary_max}"
        rank = salary_rank(salary_min, salary_max, salary_text)
        role_entry = {
            "role": title,
            "company": company or source.title(),
            "location": location or "Remote",
            "salary": salary_display or "N/A",
            "trend": "up",
            "skills": skills[:5],
            "source": source,
            "url": url,
            "salary_rank": rank,
        }
        roles.append(role_entry)
        if innovations:
            innovation_roles.append({**role_entry, "innovations": innovations})
        if weird_tags:
            weird_roles.append({**role_entry, "weirdTags": weird_tags})
        title_key = title.strip().lower()
        if title_counts.get(title_key, 0) <= RARE_TITLE_MAX_FREQ:
            rare_roles.append(dict(role_entry))

    roles = sorted(roles, key=lambda r: r.get("salary_rank", 0), reverse=True)[:50]
    for role in roles:
        role.pop("salary_rank", None)

    top_regions = sorted(locations.keys(), key=lambda k: locations[k], reverse=True)[:5]
    top_skills = sorted(skill_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    top_innovations = sorted(
        innovation_counts.items(), key=lambda kv: kv[1], reverse=True
    )[:8]

    innovation_roles = sorted(
        innovation_roles, key=lambda r: r.get("salary_rank", 0), reverse=True
    )[:10]
    for role in innovation_roles:
        role.pop("salary_rank", None)

    weird_roles = sorted(
        weird_roles, key=lambda r: r.get("salary_rank", 0), reverse=True
    )[:20]
    for role in weird_roles:
        role.pop("salary_rank", None)

    rare_roles = sorted(
        rare_roles, key=lambda r: r.get("salary_rank", 0), reverse=True
    )[:20]
    for role in rare_roles:
        role.pop("salary_rank", None)

    prev_total = conn.execute(
        "SELECT total_jobs FROM metrics ORDER BY id DESC LIMIT 1"
    ).fetchone()
    growth = 0.0
    if prev_total and prev_total[0] > 0:
        growth = round(((total - prev_total[0]) / prev_total[0]) * 100, 2)

    summary = {
        "title": {
            "en": "Job Market Intelligence Dashboard",
            "zh": "就业市场情报仪表板",
        },
        "updatedAt": dt.date.today().isoformat(),
        "regions": top_regions,
        "totalPostings": total,
        "growthRate": growth,
        "topSkills": [
            {"name": name, "count": count, "change": 0.0} for name, count in top_skills
        ],
        "innovations": [
            {"name": name, "count": count} for name, count in top_innovations
        ],
        "insights": [
            {
                "title": {"en": "Current Canada focus", "zh": "聚焦加拿大当前岗位"},
                "description": {
                    "en": "Tavily search aggregates current Canada job listings.",
                    "zh": "Tavily 搜索聚合加拿大当前岗位。",
                },
                "icon": "🇨🇦",
            },
            {
                "title": {"en": "Remote demand", "zh": "远程需求"},
                "description": {
                    "en": "Remote postings are included in the search feed.",
                    "zh": "搜索结果包含远程岗位。",
                },
                "icon": "🌍",
            },
        ],
        "sources": [
            {
                "name": "Tavily",
                "url": "https://tavily.com",
                "note": "Current jobs via Tavily Search API",
            }
        ],
    }
    innovations = {
        "updatedAt": dt.date.today().isoformat(),
        "categories": [
            {"name": name, "count": count} for name, count in top_innovations
        ],
        "topRoles": innovation_roles,
    }

    rare_jobs = {
        "updatedAt": dt.date.today().isoformat(),
        "rareRoles": rare_roles,
        "weirdRoles": weird_roles,
    }

    return summary, roles, innovations, rare_jobs


def write_json(path: str, payload: object) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", default="", help="Override Tavily queries")
    parser.add_argument("--max-results", type=int, default=TAVILY_MAX_RESULTS)
    parser.add_argument("--search-depth", default=TAVILY_SEARCH_DEPTH)
    args = parser.parse_args()

    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    conn.execute("DELETE FROM jobs")
    conn.commit()

    queries = [q.strip() for q in (args.queries or TAVILY_QUERIES).split(";") if q]
    jobs = fetch_tavily_jobs(queries, args.max_results, args.search_depth)

    for job in jobs:
        upsert_job(conn, job)

    conn.execute(
        "INSERT INTO metrics (run_at, total_jobs) VALUES (?, ?)",
        (dt.datetime.utcnow().isoformat(), len(jobs)),
    )
    conn.commit()

    summary, roles, innovations, rare_jobs = generate_summary(conn)
    write_json(os.path.join(WEB_DATA_DIR, "summary.json"), summary)
    write_json(os.path.join(WEB_DATA_DIR, "roles.json"), roles)
    write_json(os.path.join(WEB_DATA_DIR, "innovations.json"), innovations)
    write_json(os.path.join(WEB_DATA_DIR, "rare_jobs.json"), rare_jobs)
    conn.close()

    print(f"Updated {len(jobs)} jobs and refreshed web data.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
