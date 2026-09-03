"""
Deterministic technology detection via keyword matching - no LLM. This is
what makes the resume pipeline NOT "rely entirely on an LLM": regardless of
which LLMClient is active (or whether the API key is even set), every
resume gets its languages/frameworks/databases/tools detected the same,
reproducible way.

Deliberately conservative: word-boundary, case-insensitive matching against
curated lists. This will miss technologies outside the lists (that's what
the LLM structuring pass is for for - it can add more), but it will not
produce false positives from partial-word matches (e.g. "Java" won't match
inside "JavaScript" because JavaScript is itself in the list and checked
as its own boundary-matched token).
"""

import re

PROGRAMMING_LANGUAGES = [
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Golang",
    "Rust", "Kotlin", "Swift", "Ruby", "PHP", "Scala", "R", "MATLAB", "Perl",
    "Dart", "Shell", "Bash", "SQL", "HTML", "CSS",
]

FRAMEWORKS = [
    "React", "Angular", "Vue", "Vue.js", "Next.js", "Nuxt.js", "Django",
    "Flask", "FastAPI", "Spring", "Spring Boot", "Express", "Express.js",
    "Node.js", ".NET", "ASP.NET", "Laravel", "Ruby on Rails", "jQuery",
    "Bootstrap", "Tailwind", "Tailwind CSS", "Redux", "GraphQL",
]

DATABASES = [
    "MongoDB", "MySQL", "PostgreSQL", "Postgres", "SQLite", "Redis",
    "Oracle", "Cassandra", "DynamoDB", "Firebase", "Firestore",
    "Elasticsearch", "MariaDB", "Microsoft SQL Server", "SQL Server",
]

TECHNOLOGIES = [
    "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Google Cloud", "Git",
    "GitHub", "GitLab", "Linux", "Jenkins", "CI/CD", "TensorFlow", "PyTorch",
    "Keras", "Pandas", "NumPy", "scikit-learn", "OpenCV", "Hadoop", "Spark",
    "Kafka", "RabbitMQ", "REST", "gRPC", "Terraform", "Ansible", "Nginx",
    "Postman", "Jira", "Figma",
]

_CATEGORIES: dict[str, list[str]] = {
    "programming_languages": PROGRAMMING_LANGUAGES,
    "frameworks": FRAMEWORKS,
    "databases": DATABASES,
    "technologies": TECHNOLOGIES,
}


def _compile_pattern(term: str) -> re.Pattern:
    # \b doesn't work cleanly around punctuation-heavy terms like "C++" or
    # "C#" or ".NET" - use lookaround on non-word-or-plus/hash/dot chars on
    # each side instead of a strict \b for those.
    escaped = re.escape(term)
    return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", re.IGNORECASE)


_COMPILED: dict[str, list[tuple[str, re.Pattern]]] = {
    category: [(term, _compile_pattern(term)) for term in terms]
    for category, terms in _CATEGORIES.items()
}


def extract_known_technologies(text: str) -> dict[str, list[str]]:
    """
    Returns {"programming_languages": [...], "frameworks": [...],
    "databases": [...], "technologies": [...]} - each a deduplicated list
    of canonical names (as written in the lists above, not as they
    appeared in the resume) found anywhere in `text`.
    """
    results: dict[str, list[str]] = {}
    for category, compiled_terms in _COMPILED.items():
        found = [term for term, pattern in compiled_terms if pattern.search(text)]
        results[category] = found
    return results
