#!/usr/bin/env python3
"""
Seed script for Capability Registry taxonomy.

JIRA: MD-2063 (part of MD-2042)
Description: Populates the capabilities table from the capability_taxonomy.yaml file.

Usage:
    python seed_capability_taxonomy.py [--db-url DATABASE_URL] [--dry-run]

Environment:
    DATABASE_URL: PostgreSQL connection URL (default: from .env or config)
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import yaml

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    print("Warning: SQLAlchemy not installed. Install with: pip install sqlalchemy")

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_DB_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://maestro:maestro_password@localhost:5432/maestro_sandbox'
)

TAXONOMY_FILE = project_root / 'config' / 'capability_taxonomy.yaml'


# =============================================================================
# Taxonomy Parser
# =============================================================================

def load_taxonomy(taxonomy_path: Path) -> Dict[str, Any]:
    """Load taxonomy from YAML file."""
    with open(taxonomy_path, 'r') as f:
        return yaml.safe_load(f)


def flatten_taxonomy(taxonomy: Dict[str, Any], parent_skill_id: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Flatten hierarchical taxonomy into list of skills.

    Returns list of dicts with: skill_id, parent_skill_id, category
    """
    skills = []

    for key, value in taxonomy.items():
        if key in ('version', 'updated'):
            continue

        if isinstance(value, dict):
            # This is a category with subcategories/skills
            # Add the category itself
            skill_id = f"{parent_skill_id}:{key}" if parent_skill_id else key
            skills.append({
                'skill_id': skill_id,
                'parent_skill_id': parent_skill_id,
                'category': skill_id.split(':')[0] if ':' in skill_id else skill_id,
            })

            # Recursively process children
            children = flatten_taxonomy(value, skill_id)
            skills.extend(children)

        elif isinstance(value, list):
            # List of leaf skills
            parent_id = parent_skill_id or key
            for skill in value:
                skill_id = f"{parent_id}:{skill}"
                skills.append({
                    'skill_id': skill_id,
                    'parent_skill_id': parent_id,
                    'category': parent_id.split(':')[0],
                })
        else:
            # Single skill
            skill_id = f"{parent_skill_id}:{key}" if parent_skill_id else key
            skills.append({
                'skill_id': skill_id,
                'parent_skill_id': parent_skill_id,
                'category': skill_id.split(':')[0],
            })

    return skills


# =============================================================================
# Database Operations
# =============================================================================

def seed_capabilities(db_url: str, skills: List[Dict[str, str]], dry_run: bool = False) -> int:
    """
    Insert capabilities into database.

    Returns number of capabilities inserted/updated.
    """
    if not HAS_SQLALCHEMY:
        logger.error("SQLAlchemy required for database operations")
        return 0

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    inserted = 0
    updated = 0

    try:
        for skill in skills:
            if dry_run:
                logger.info(f"[DRY-RUN] Would insert: {skill['skill_id']}")
                inserted += 1
                continue

            # Use upsert pattern
            result = session.execute(text("""
                INSERT INTO capabilities (skill_id, parent_skill_id, category, version, created_at)
                VALUES (:skill_id, :parent_skill_id, :category, '1.0.0', NOW())
                ON CONFLICT (skill_id) DO UPDATE SET
                    parent_skill_id = EXCLUDED.parent_skill_id,
                    category = EXCLUDED.category
                RETURNING
                    (xmax = 0) AS inserted
            """), {
                'skill_id': skill['skill_id'],
                'parent_skill_id': skill['parent_skill_id'],
                'category': skill['category'],
            })

            row = result.fetchone()
            if row and row[0]:  # inserted
                inserted += 1
            else:
                updated += 1

        if not dry_run:
            session.commit()
            logger.info(f"Committed {inserted} new capabilities, {updated} updated")

    except Exception as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        session.close()

    return inserted + updated


def get_capability_count(db_url: str) -> int:
    """Get current capability count from database."""
    if not HAS_SQLALCHEMY:
        return 0

    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM capabilities"))
        return result.scalar() or 0


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Seed capability taxonomy into database'
    )
    parser.add_argument(
        '--db-url',
        default=DEFAULT_DB_URL,
        help='Database connection URL'
    )
    parser.add_argument(
        '--taxonomy',
        type=Path,
        default=TAXONOMY_FILE,
        help='Path to taxonomy YAML file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print what would be inserted without making changes'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load taxonomy
    logger.info(f"Loading taxonomy from: {args.taxonomy}")
    if not args.taxonomy.exists():
        logger.error(f"Taxonomy file not found: {args.taxonomy}")
        sys.exit(1)

    taxonomy = load_taxonomy(args.taxonomy)

    # Flatten to list of skills
    taxonomy_data = taxonomy.get('taxonomy', taxonomy)
    skills = flatten_taxonomy(taxonomy_data)

    logger.info(f"Found {len(skills)} capabilities in taxonomy")

    # Show sample
    if args.verbose:
        logger.debug("Sample capabilities:")
        for skill in skills[:10]:
            logger.debug(f"  {skill['skill_id']} (parent: {skill['parent_skill_id']})")

    # Get current count
    if not args.dry_run:
        try:
            current_count = get_capability_count(args.db_url)
            logger.info(f"Current capabilities in database: {current_count}")
        except Exception as e:
            logger.warning(f"Could not query database: {e}")

    # Seed database
    logger.info("Seeding capabilities...")
    count = seed_capabilities(args.db_url, skills, args.dry_run)

    if args.dry_run:
        logger.info(f"[DRY-RUN] Would process {count} capabilities")
    else:
        logger.info(f"Successfully seeded {count} capabilities")

    return 0


if __name__ == '__main__':
    sys.exit(main())
