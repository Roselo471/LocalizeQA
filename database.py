"""
database.py — SQLite storage module for LocalizeQA

Stores translation records, evaluation scores, and fix history.
Enables quality trend tracking and benchmark analysis.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

# Default database path
DB_PATH = Path(__file__).parent / "localizeqa.db"


def get_connection(db_path: str = None) -> sqlite3.Connection:
    """Get a database connection, creating tables if needed."""
    path = db_path or str(DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row  # Access columns by name
    _create_tables(conn)
    return conn


def _create_tables(conn: sqlite3.Connection):
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS translations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_text TEXT NOT NULL,
            translated_text TEXT NOT NULL,
            content_type TEXT NOT NULL,
            accuracy_score REAL,
            fluency_score REAL,
            cultural_score REAL,
            terminology_score REAL,
            overall_score REAL,
            issues TEXT,
            summary TEXT,
            fixed_text TEXT,
            had_issues INTEGER DEFAULT 0,
            issues_fixed TEXT,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()


def save_record(
    conn: sqlite3.Connection,
    source_text: str,
    translated_text: str,
    content_type: str,
    eval_result: dict,
    fix_result: dict = None,
) -> int:
    """
    Save a complete translation record.

    Args:
        conn: Database connection
        source_text: Original English text
        translated_text: Chinese translation
        content_type: Content category
        eval_result: Evaluation result dictionary
        fix_result: Fix result dictionary (optional)

    Returns:
        Row ID of the inserted record
    """
    # Collect all issues into one list
    all_issues = []
    for dim in ["accuracy", "fluency", "cultural_adaptation", "terminology"]:
        dim_data = eval_result.get(dim, {})
        all_issues.extend(dim_data.get("issues", []))

    cursor = conn.execute(
        """
        INSERT INTO translations (
            source_text, translated_text, content_type,
            accuracy_score, fluency_score, cultural_score, terminology_score,
            overall_score, issues, summary,
            fixed_text, had_issues, issues_fixed,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_text,
            translated_text,
            content_type,
            eval_result.get("accuracy", {}).get("score", 0),
            eval_result.get("fluency", {}).get("score", 0),
            eval_result.get("cultural_adaptation", {}).get("score", 0),
            eval_result.get("terminology", {}).get("score", 0),
            eval_result.get("overall_score", 0),
            json.dumps(all_issues, ensure_ascii=False),
            eval_result.get("summary", ""),
            fix_result.get("fixed_text", "") if fix_result else "",
            1 if (fix_result and fix_result.get("had_issues")) else 0,
            json.dumps(fix_result.get("issues_fixed", []), ensure_ascii=False) if fix_result else "[]",
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_all_records(conn: sqlite3.Connection) -> list:
    """Get all translation records."""
    cursor = conn.execute(
        "SELECT * FROM translations ORDER BY created_at DESC"
    )
    return [dict(row) for row in cursor.fetchall()]


def get_stats(conn: sqlite3.Connection) -> dict:
    """
    Get aggregate statistics from all records.

    Returns:
        Dictionary with counts, averages, and distributions.
    """
    cursor = conn.execute("""
        SELECT
            COUNT(*) as total,
            ROUND(AVG(accuracy_score), 2) as avg_accuracy,
            ROUND(AVG(fluency_score), 2) as avg_fluency,
            ROUND(AVG(cultural_score), 2) as avg_cultural,
            ROUND(AVG(terminology_score), 2) as avg_terminology,
            ROUND(AVG(overall_score), 2) as avg_overall,
            SUM(had_issues) as total_with_issues,
            ROUND(MIN(overall_score), 2) as min_score,
            ROUND(MAX(overall_score), 2) as max_score
        FROM translations
        WHERE overall_score > 0
    """)
    row = cursor.fetchone()
    return dict(row) if row else {}


def get_stats_by_type(conn: sqlite3.Connection) -> list:
    """Get statistics grouped by content type."""
    cursor = conn.execute("""
        SELECT
            content_type,
            COUNT(*) as count,
            ROUND(AVG(overall_score), 2) as avg_score,
            SUM(had_issues) as with_issues
        FROM translations
        WHERE overall_score > 0
        GROUP BY content_type
    """)
    return [dict(row) for row in cursor.fetchall()]


def get_common_issues(conn: sqlite3.Connection, limit: int = 10) -> list:
    """Get most common issues across all translations."""
    cursor = conn.execute("SELECT issues FROM translations WHERE issues != '[]'")

    issue_count = {}
    for row in cursor.fetchall():
        issues = json.loads(row["issues"])
        for issue in issues:
            issue_count[issue] = issue_count.get(issue, 0) + 1

    sorted_issues = sorted(issue_count.items(), key=lambda x: x[1], reverse=True)
    return sorted_issues[:limit]


def format_stats_report(stats: dict, by_type: list, common_issues: list) -> str:
    """Format statistics into a readable report."""
    lines = []

    lines.append("=" * 60)
    lines.append("  LocalizeQA — Quality Statistics Report")
    lines.append("=" * 60)

    if not stats or stats.get("total", 0) == 0:
        lines.append("\n  No records found.")
        return "\n".join(lines)

    # Overall stats
    lines.append(f"\n  Total translations: {stats['total']}")
    lines.append(f"  Translations with issues: {stats['total_with_issues']}")
    lines.append(f"  Issue rate: {stats['total_with_issues'] / stats['total'] * 100:.1f}%")

    lines.append(f"\n  {'Dimension':<30} {'Average Score':>15}")
    lines.append(f"  {'─' * 45}")
    lines.append(f"  {'Accuracy (准确性)':<30} {stats['avg_accuracy']:>12}/5.0")
    lines.append(f"  {'Fluency (流畅度)':<30} {stats['avg_fluency']:>12}/5.0")
    lines.append(f"  {'Cultural Adaptation (文化适配)':<30} {stats['avg_cultural']:>12}/5.0")
    lines.append(f"  {'Terminology (术语一致性)':<30} {stats['avg_terminology']:>12}/5.0")
    lines.append(f"  {'─' * 45}")
    lines.append(f"  {'Overall':<30} {stats['avg_overall']:>12}/5.0")
    lines.append(f"  {'Score range':<30} {stats['min_score']}-{stats['max_score']}")

    # By content type
    if by_type:
        lines.append(f"\n  {'Content Type':<20} {'Count':>8} {'Avg Score':>12} {'Issues':>8}")
        lines.append(f"  {'─' * 50}")
        for row in by_type:
            lines.append(
                f"  {row['content_type']:<20} {row['count']:>8} "
                f"{row['avg_score']:>9}/5.0 {row['with_issues']:>8}"
            )

    # Common issues
    if common_issues:
        lines.append(f"\n  Top Issues:")
        for issue, count in common_issues:
            lines.append(f"    [{count}x] {issue}")

    lines.append(f"\n{'=' * 60}")
    return "\n".join(lines)
