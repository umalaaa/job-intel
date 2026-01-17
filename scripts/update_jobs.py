#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import sqlite3
import sys
import urllib.request
from typing import Dict, Iterable, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
WEB_DATA_DIR = os.path.join(BASE_DIR, "web", "data")
DB_PATH = os.path.join(DATA_DIR, "job-intel.db")
LOG_DIR = os.path.join(BASE_DIR, "logs")

REMOTIVE_URL = os.getenv("REMOTIVE_URL", "https://remotive.com/api/remote-jobs")
REMOTEOK_URL = os.getenv("REMOTEOK_URL", "https://remoteok.com/api")
JOBBANK_URL = os.getenv(
    "JOBBANK_URL",
    "https://open.canada.ca/data/dataset/ea639e28-c0fc-48bf-b5dd-b8899bd43072/resource/32d6617f-0a84-40bc-8d7b-6bfabd3c16f6/download/job-bank-open-data-all-job-postings-en-december2025.csv",
)
JOBBANK_CACHE_PATH = os.path.join(DATA_DIR, "jobbank.csv")
JOBBANK_MAX_AGE_DAYS = int(os.getenv("JOBBANK_MAX_AGE_DAYS", "30"))
JOBBANK_MIN_SALARY = int(os.getenv("JOBBANK_MIN_SALARY", "0"))
RARE_TITLE_MAX_FREQ = int(os.getenv("RARE_TITLE_MAX_FREQ", "1"))

SOURCE_REMOTIVE = "remotive"
SOURCE_REMOTEOK = "remoteok"
SOURCE_JOBBANK = "jobbank"

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


def http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "job-intel-bot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def load_jobbank_csv() -> Iterable[Dict[str, str]]:
    use_cache = False
    if os.path.exists(JOBBANK_CACHE_PATH):
        age = dt.datetime.utcnow() - dt.datetime.utcfromtimestamp(
            os.path.getmtime(JOBBANK_CACHE_PATH)
        )
        use_cache = age.days < JOBBANK_MAX_AGE_DAYS
    if not use_cache:
        raw = http_get(JOBBANK_URL)
        with open(JOBBANK_CACHE_PATH, "wb") as f:
            f.write(raw)
    with open(JOBBANK_CACHE_PATH, "rb") as f:
        decoded = f.read().decode("utf-8", errors="ignore")
    decoded = decoded.replace("\x00", "")
    return csv.DictReader(io.StringIO(decoded))


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


def fetch_remotive() -> List[Dict]:
    payload = json.loads(http_get(REMOTIVE_URL))
    jobs = []
    now = dt.datetime.utcnow().isoformat()
    for item in payload.get("jobs", []):
        salary_min, salary_max, salary_text = parse_salary_range(item.get("salary", ""))
        job = {
            "source": SOURCE_REMOTIVE,
            "external_id": str(item.get("id")),
            "title": item.get("title"),
            "company": item.get("company_name"),
            "location": item.get("candidate_required_location"),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_text": salary_text,
            "category": item.get("category"),
            "tags": json.dumps(item.get("tags", [])),
            "url": item.get("url"),
            "published_at": item.get("publication_date"),
            "fetched_at": now,
            "is_remote": True,
        }
        jobs.append(job)
    return jobs


def fetch_remoteok() -> List[Dict]:
    payload = json.loads(http_get(REMOTEOK_URL))
    now = dt.datetime.utcnow().isoformat()
    jobs = []
    for item in payload[1:]:
        salary_min = item.get("salary_min") or None
        salary_max = item.get("salary_max") or None
        salary_text = None
        if salary_min and salary_max:
            salary_text = f"{salary_min}-{salary_max}"
        job = {
            "source": SOURCE_REMOTEOK,
            "external_id": str(item.get("id")),
            "title": item.get("position"),
            "company": item.get("company"),
            "location": item.get("location"),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_text": salary_text,
            "category": None,
            "tags": json.dumps(item.get("tags", [])),
            "url": item.get("url"),
            "published_at": item.get("date"),
            "fetched_at": now,
            "is_remote": True,
        }
        jobs.append(job)
    return jobs


def find_value(row: Dict[str, str], keys: Iterable[str]) -> Optional[str]:
    for key in keys:
        if key in row and row[key]:
            return row[key]
    return None


def fetch_jobbank() -> List[Dict]:
    reader = load_jobbank_csv()
    now = dt.datetime.utcnow().isoformat()
    jobs = []
    for row in reader:
        title = find_value(row, ["Job title", "JOB_TITLE", "Job_Title", "job_title"])
        if not title:
            continue
        salary_raw = find_value(
            row, ["Salary", "Wage", "SALARY", "WAGE", "hourly_wage", "annual_salary"]
        )
        salary_min, salary_max, salary_text = parse_salary_range(salary_raw or "")
        if JOBBANK_MIN_SALARY > 0:
            highest = salary_max or salary_min
            if highest is not None and highest < JOBBANK_MIN_SALARY:
                continue
        job = {
            "source": SOURCE_JOBBANK,
            "external_id": f"jobbank:{row.get('Job Bank number') or row.get('Job_Bank_number') or row.get('id') or title}",
            "title": title,
            "company": find_value(
                row, ["Employer name", "Employer", "EMPLOYER_NAME", "company"]
            ),
            "location": ", ".join(
                filter(
                    None,
                    [
                        find_value(row, ["City", "CITY", "city"]),
                        find_value(row, ["Province", "PROVINCE", "province"]),
                    ],
                )
            ),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_text": salary_text,
            "category": find_value(row, ["NOC group", "NOC", "noc", "occupation"]),
            "tags": json.dumps([]),
            "url": find_value(row, ["Job Bank URL", "URL", "url"]),
            "published_at": find_value(row, ["Date posted", "DATE_POSTED", "posted"]),
            "fetched_at": now,
            "is_remote": False,
        }
        jobs.append(job)
    return jobs


def compute_skills(title: str, tags: List[str]) -> List[str]:
    lower = f"{title} {', '.join(tags)}".lower()
    skills = []
    for key, label in SKILL_KEYWORDS.items():
        if re.search(rf"\b{re.escape(key)}\b", lower):
            skills.append(label)
    return sorted(set(skills))


def compute_innovations(title: str, tags: List[str]) -> List[str]:
    lower = f"{title} {', '.join(tags)}".lower()
    innovations = []
    for key, label in INNOVATION_KEYWORDS.items():
        if re.search(rf"\b{re.escape(key)}\b", lower):
            innovations.append(label)
    return sorted(set(innovations))


def compute_weird_tags(title: str, tags: List[str]) -> List[str]:
    lower = f"{title} {', '.join(tags)}".lower()
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
            innovation_roles.append(
                {
                    **role_entry,
                    "innovations": innovations,
                }
            )
        if weird_tags:
            weird_roles.append(
                {
                    **role_entry,
                    "weirdTags": weird_tags,
                }
            )
        title_key = title.strip().lower()
        if title_counts.get(title_key, 0) <= RARE_TITLE_MAX_FREQ:
            rare_roles.append(dict(role_entry))

    roles = sorted(
        roles,
        key=lambda r: r.get("salary_rank", 0),
        reverse=True,
    )[:50]
    for role in roles:
        role.pop("salary_rank", None)

    top_regions = sorted(locations.keys(), key=lambda k: locations[k], reverse=True)[:5]
    top_skills = sorted(skill_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    top_innovations = sorted(
        innovation_counts.items(), key=lambda kv: kv[1], reverse=True
    )[:8]

    innovation_roles = sorted(
        innovation_roles,
        key=lambda r: r.get("salary_rank", 0),
        reverse=True,
    )[:10]
    for role in innovation_roles:
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
                "title": {"en": "Remote roles lead", "zh": "远程职位领先"},
                "description": {
                    "en": "Remote-first sources dominate the high-paying list.",
                    "zh": "高薪职位主要来自远程来源。",
                },
                "icon": "🌍",
            },
            {
                "title": {"en": "Canada demand", "zh": "加拿大需求"},
                "description": {
                    "en": "Job Bank data captures Canadian postings above the salary threshold.",
                    "zh": "官方数据收录加拿大高薪岗位。",
                },
                "icon": "🇨🇦",
            },
        ],
        "sources": [
            {
                "name": "Remotive",
                "url": "https://remotive.com",
                "note": "Remote jobs via Remotive API",
            },
            {
                "name": "RemoteOK",
                "url": "https://remoteok.com",
                "note": "Remote jobs via RemoteOK JSON feed",
            },
            {
                "name": "Job Bank",
                "url": "https://open.canada.ca/data/en/dataset/ea639e28-c0fc-48bf-b5dd-b8899bd43072",
                "note": "Canada Job Bank open data",
            },
        ],
    }
    innovations = {
        "updatedAt": dt.date.today().isoformat(),
        "categories": [
            {"name": name, "count": count} for name, count in top_innovations
        ],
        "topRoles": innovation_roles,
    }

    weird_roles = sorted(
        weird_roles,
        key=lambda r: r.get("salary_rank", 0),
        reverse=True,
    )[:20]
    for role in weird_roles:
        role.pop("salary_rank", None)

    rare_roles = sorted(
        rare_roles,
        key=lambda r: r.get("salary_rank", 0),
        reverse=True,
    )[:20]
    for role in rare_roles:
        role.pop("salary_rank", None)

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
    parser.add_argument("--jobbank-only", action="store_true")
    parser.add_argument("--remote-only", action="store_true")
    args = parser.parse_args()

    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    jobs: List[Dict] = []
    if not args.jobbank_only:
        jobs.extend(fetch_remotive())
        jobs.extend(fetch_remoteok())
    if not args.remote_only:
        jobs.extend(fetch_jobbank())

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
