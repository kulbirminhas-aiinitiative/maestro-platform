"""
Template Seeder
Automatically seed templates from configuration file into the database
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from uuid import uuid4

import structlog
import yaml

from .git_manager import GitManager
from .models.template import SeedingReport

logger = structlog.get_logger(__name__)


class TemplateSeeder:
    """Seeds templates from YAML configuration into database."""

    def __init__(self, git_manager: GitManager, db_pool):
        """
        Initialize seeder.

        Args:
            git_manager: GitManager instance for cloning repositories
            db_pool: AsyncPG database pool
        """
        self.git_manager = git_manager
        self.db_pool = db_pool

    async def seed_from_config(
        self,
        config_path: str = "/app/config/templates.yaml",
        force_update: bool = False
    ) -> SeedingReport:
        """
        Seed templates from configuration file.

        Args:
            config_path: Path to templates.yaml configuration file
            force_update: If True, update existing templates

        Returns:
            SeedingReport with statistics
        """
        start_time = time.time()

        report = SeedingReport(
            total_templates=0,
            templates_added=0,
            templates_updated=0,
            templates_skipped=0,
            templates_failed=0,
            errors=[],
            duration_seconds=0.0
        )

        try:
            # Load configuration
            config_file = Path(config_path)
            if not config_file.exists():
                error_msg = f"Configuration file not found: {config_path}"
                logger.error("config_not_found", path=config_path)
                report.errors.append(error_msg)
                report.duration_seconds = time.time() - start_time
                return report

            with open(config_file) as f:
                config = yaml.safe_load(f)

            templates_config = config.get('templates', [])
            report.total_templates = len(templates_config)

            logger.info("starting_seed", total_templates=report.total_templates, config_path=config_path)

            # Process each template
            for template_config in templates_config:
                try:
                    await self._seed_template(template_config, force_update, report)
                except Exception as e:
                    name = template_config.get('name', 'unknown')
                    error_msg = f"Failed to seed {name}: {str(e)}"
                    report.templates_failed += 1
                    report.errors.append(error_msg)
                    logger.error("seed_template_error", name=name, error=str(e))

            report.duration_seconds = time.time() - start_time

            logger.info(
                "seeding_complete",
                total=report.total_templates,
                added=report.templates_added,
                updated=report.templates_updated,
                skipped=report.templates_skipped,
                failed=report.templates_failed,
                duration=f"{report.duration_seconds:.2f}s"
            )

            return report

        except Exception as e:
            logger.error("seed_error", error=str(e))
            report.errors.append(f"Seeding failed: {str(e)}")
            report.duration_seconds = time.time() - start_time
            return report

    async def _seed_template(
        self,
        template_config: Dict[str, Any],
        force_update: bool,
        report: SeedingReport
    ):
        """
        Seed a single template.

        Args:
            template_config: Template configuration dictionary
            force_update: Whether to update existing templates
            report: Report to update with results
        """
        name = template_config.get('name')
        git_url = template_config.get('git_url')
        git_branch = template_config.get('git_branch', 'main')
        organization = template_config.get('organization', 'maestro')

        if not name or not git_url:
            raise ValueError("Template must have 'name' and 'git_url' fields")

        logger.info("processing_template", name=name, git_url=git_url)

        # Check if template already exists
        async with self.db_pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT id, version FROM templates WHERE name = $1 AND organization = $2",
                name,
                organization
            )

            if existing and not force_update:
                report.templates_skipped += 1
                logger.info("template_exists_skip", name=name, version=existing['version'])
                return

        # Clone repository
        clone_dir = None
        try:
            clone_dir, commit_hash, clone_ms = await self.git_manager.clone_repository(
                git_url,
                git_branch
            )

            # Extract and validate manifest
            manifest = await self.git_manager.extract_manifest(clone_dir)

            # Validate manifest matches config name
            if manifest.name != name:
                logger.warning(
                    "name_mismatch",
                    config_name=name,
                    manifest_name=manifest.name
                )

            # Calculate quality score
            quality_score = manifest.get_validation_score()

            # Insert or update template
            async with self.db_pool.acquire() as conn:
                template_id = existing['id'] if existing else uuid4()

                if existing:
                    # Update existing template
                    await conn.execute(
                        """
                        UPDATE templates SET
                            version = $1,
                            description = $2,
                            category = $3,
                            language = $4,
                            framework = $5,
                            tags = $6,
                            git_url = $7,
                            git_branch = $8,
                            git_commit_hash = $9,
                            templating_engine = $10,
                            manifest_validated = TRUE,
                            manifest_validation_date = NOW(),
                            quality_score = $11,
                            status = 'approved',
                            updated_at = NOW()
                        WHERE id = $12
                        """,
                        manifest.version,
                        manifest.description,
                        manifest.metadata.category,
                        manifest.metadata.language,
                        manifest.metadata.framework,
                        manifest.metadata.tags,
                        git_url,
                        git_branch,
                        commit_hash,
                        manifest.engine,
                        quality_score,
                        template_id
                    )
                    report.templates_updated += 1
                    logger.info("template_updated", name=name, version=manifest.version)
                else:
                    # Insert new template
                    await conn.execute(
                        """
                        INSERT INTO templates (
                            id, name, description, category, language, framework, version,
                            tags, organization, git_url, git_branch, git_commit_hash,
                            templating_engine, manifest_validated, manifest_validation_date,
                            quality_score, status, created_by, created_at, updated_at
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, NOW(), NOW()
                        )
                        """,
                        template_id,
                        manifest.name,
                        manifest.description,
                        manifest.metadata.category,
                        manifest.metadata.language,
                        manifest.metadata.framework,
                        manifest.version,
                        manifest.metadata.tags,
                        organization,
                        git_url,
                        git_branch,
                        commit_hash,
                        manifest.engine,
                        True,
                        datetime.utcnow(),
                        quality_score,
                        'approved',
                        'seeder'
                    )
                    report.templates_added += 1
                    logger.info("template_added", name=name, version=manifest.version, id=str(template_id))

        finally:
            # Always cleanup clone directory
            if clone_dir:
                await self.git_manager.cleanup_clone(clone_dir)


async def run_seeder(db_pool, git_manager: GitManager, config_path: str = None):
    """
    Convenience function to run seeder.

    Args:
        db_pool: Database pool
        git_manager: Git manager instance
        config_path: Optional path to configuration file

    Returns:
        SeedingReport
    """
    seeder = TemplateSeeder(git_manager, db_pool)

    if config_path is None:
        config_path = "/app/config/templates.yaml"

    return await seeder.seed_from_config(config_path)


if __name__ == "__main__":
    # For testing/standalone execution
    import asyncpg

    async def main():
        # Initialize services
        db_pool = await asyncpg.create_pool(
            "postgresql://maestro_template_user:maestro_template_pass@localhost:5432/maestro_templates"
        )
        git_manager = GitManager(temp_dir="/storage/temp")

        # Run seeder
        report = await run_seeder(db_pool, git_manager)

        print(f"\n{'='*60}")
        print("SEEDING REPORT")
        print(f"{'='*60}")
        print(f"Total templates: {report.total_templates}")
        print(f"Added: {report.templates_added}")
        print(f"Updated: {report.templates_updated}")
        print(f"Skipped: {report.templates_skipped}")
        print(f"Failed: {report.templates_failed}")
        print(f"Duration: {report.duration_seconds:.2f}s")

        if report.errors:
            print(f"\nErrors:")
            for error in report.errors:
                print(f"  - {error}")

        # Cleanup
        await db_pool.close()

    asyncio.run(main())