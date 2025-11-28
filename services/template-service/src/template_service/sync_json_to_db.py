#!/usr/bin/env python3
"""
Sync JSON Template Files to PostgreSQL Database
Imports template JSON files from storage/templates/ into the database
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import asyncpg
import asyncio
from uuid import UUID

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "maestro_registry",
    "user": "maestro_registry_user",
    "password": "changeme_registry_password"
}

STORAGE_PATH = Path("/home/ec2-user/projects/maestro-platform/maestro-templates/storage/templates")


async def sync_templates():
    """Sync all JSON templates to database"""

    # Connect to database
    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        # Find all JSON template files in persona subdirectories
        print(f"📂 Storage path: {STORAGE_PATH}")
        print(f"📂 Path exists: {STORAGE_PATH.exists()}")
        print(f"📂 Is directory: {STORAGE_PATH.is_dir()}")

        json_files = list(STORAGE_PATH.glob("*/*.json"))
        print(f"🔍 Found {len(json_files)} JSON template files in persona directories")

        if len(json_files) > 0:
            print(f"📄 Sample files:")
            for f in json_files[:3]:
                print(f"   - {f}")

        synced = 0
        skipped = 0
        errors = 0

        for json_file in json_files:
            try:
                # Load JSON
                with open(json_file, 'r') as f:
                    template_data = json.load(f)

                metadata = template_data.get("metadata", {})
                template_id = metadata.get("id")

                if not template_id:
                    print(f"⚠️  Skipping {json_file.name}: No template ID")
                    skipped += 1
                    continue

                # Convert to UUID - generate one if not valid UUID format
                try:
                    template_uuid = UUID(template_id)
                except (ValueError, AttributeError):
                    # Generate deterministic UUID from template_id string
                    import hashlib
                    hash_object = hashlib.md5(template_id.encode())
                    template_uuid = UUID(hash_object.hexdigest())
                    print(f"  Generated UUID {str(template_uuid)[:8]}... for ID '{template_id}'")

                # Check if already exists
                existing = await conn.fetchval(
                    "SELECT id FROM templates WHERE id = $1",
                    template_uuid
                )

                if existing:
                    print(f"⏭️  Skipping {metadata.get('name', 'unknown')}: Already in database")
                    skipped += 1
                    continue

                # Extract persona from directory
                persona = json_file.parent.name

                # Extract fields with defaults
                name = metadata.get("name", f"template_{template_id[:8]}")
                description = metadata.get("description", "")
                category = metadata.get("category", "utility")
                language = metadata.get("language", "unknown")
                framework = metadata.get("framework")
                version = metadata.get("version", "1.0.0")
                tags = metadata.get("tags", [])
                organization = metadata.get("organization", "maestro")
                quality_score = metadata.get("quality_score", 0.0)
                security_score = metadata.get("security_score", 0.0)
                performance_score = metadata.get("performance_score", 0.0)
                maintainability_score = metadata.get("maintainability_score", 0.0)
                status = metadata.get("status", "draft")
                created_by = metadata.get("created_by", "system")
                created_at = metadata.get("created_at", datetime.utcnow().isoformat())
                updated_at = metadata.get("updated_at", datetime.utcnow().isoformat())
                file_path = str(json_file)  # Store full path

                # Insert into database
                await conn.execute("""
                    INSERT INTO templates (
                        id, name, description, category, language, framework,
                        version, tags, organization, git_url, git_branch,
                        templating_engine, quality_score, security_score,
                        performance_score, maintainability_score, status,
                        manifest_validated, usage_count, success_rate,
                        storage_tier, file_path, created_at, updated_at, created_by
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
                        $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25
                    )
                """,
                    template_uuid,
                    name,
                    description,
                    category,
                    language,
                    framework,
                    version,
                    tags,
                    organization,
                    None,  # git_url
                    None,  # git_branch
                    "jinja2",  # templating_engine
                    float(quality_score),
                    float(security_score),
                    float(performance_score),
                    float(maintainability_score),
                    status,
                    True,  # manifest_validated
                    0,  # usage_count
                    0.0,  # success_rate
                    metadata.get("storage_tier", 2),
                    file_path,  # file_path
                    datetime.fromisoformat(created_at.replace('Z', '+00:00')) if 'T' in created_at else datetime.utcnow(),
                    datetime.fromisoformat(updated_at.replace('Z', '+00:00')) if 'T' in updated_at else datetime.utcnow(),
                    created_by
                )

                print(f"✅ Synced: {name} (ID: {template_id[:8]}...) [Persona: {persona}]")
                synced += 1

            except Exception as e:
                print(f"❌ Error processing {json_file.name}: {e}")
                errors += 1
                continue

        # Print summary
        print("\n" + "="*60)
        print(f"📊 Sync Summary:")
        print(f"   ✅ Synced: {synced}")
        print(f"   ⏭️  Skipped (already exist): {skipped}")
        print(f"   ❌ Errors: {errors}")
        print(f"   📁 Total files: {len(json_files)}")
        print("="*60)

        # Verify database count
        total = await conn.fetchval("SELECT COUNT(*) FROM templates")
        print(f"\n🗄️  Database now contains {total} templates")

    finally:
        await conn.close()


if __name__ == "__main__":
    print("🚀 MAESTRO Templates - JSON to Database Sync")
    print("="*60)
    asyncio.run(sync_templates())