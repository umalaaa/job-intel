import pytest
from src.services.parsers import (
    parse_salary_range,
    parse_title_company,
    infer_location,
    compute_skills,
    build_external_id,
)


def test_parse_salary_range():
    assert parse_salary_range("$100k - $120k per year") == (
        100,
        120,
        "$100k - $120k per year",
    )
    assert parse_salary_range("50/hr") == (50, 50, "50/hr")
    assert parse_salary_range("Competitive salary") == (
        None,
        None,
        "Competitive salary",
    )
    assert parse_salary_range("") == (None, None, None)


def test_parse_title_company():
    assert parse_title_company("Software Engineer at Google") == (
        "Software Engineer",
        "Google",
    )
    assert parse_title_company("Senior Dev - Amazon") == ("Senior Dev", "Amazon")
    assert parse_title_company("Frontend Developer") == ("Frontend Developer", None)


def test_infer_location():
    assert infer_location("Remote Software Engineer", "") == "Remote"
    assert infer_location("Software Engineer in Toronto", "") == "Canada"
    assert infer_location("Java Dev", "remote") == "Remote"


def test_compute_skills():
    assert "Python" in compute_skills("Python Developer", [])
    assert "React" in compute_skills("Frontend", ["react", "js"])
    assert "AWS" in compute_skills("Cloud Engineer", ["amazon web services", "aws"])


def test_build_external_id():
    id1 = build_external_id("http://a.com", "Job 1")
    id2 = build_external_id("http://a.com", "Job 1")
    id3 = build_external_id("http://b.com", "Job 1")
    assert id1 == id2
    assert id1 != id3
