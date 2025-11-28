"""
Admin Router
Administrative endpoints for template management
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

import structlog
import yaml
from fastapi import APIRouter, Depends, HTTPException, status

from ..models.template import (
    TemplateRegisterRequest,
    TemplateValidationResult,
    SeedingReport,
    CacheClearResult,
    TemplateCreate
)
from ..security import verify_admin_key
from ..git_manager import GitManager
from ..cache_manager import CacheManager
from ..json_storage_adapter import JSONStorageAdapter
from ..dependencies import get_db_pool, get_git_manager, get_cache_manager

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.post("/templates", status_code=status.HTTP_201_CREATED)
async def register_template(
    request: TemplateRegisterRequest,
    admin_key: str = Depends(verify_admin_key),
    git_manager: GitManager = Depends(get_git_manager),
    db_pool = Depends(get_db_pool)
):
    """
    Register a new template from Git repository

    - **git_url**: Repository URL
    - **git_branch**: Branch to use (default: main)
    - **organization**: Organization name
    - **auto_validate**: Auto-validate manifest (default: true)

    Returns created template information
    """
    try:
        logger.info("registering_template", git_url=request.git_url)

        if not git_manager:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Git manager not available"
            )

        # Clone repository
        clone_dir, commit_hash, _ = await git_manager.clone_repository(
            request.git_url,
            request.git_branch
        )

        try:
            # Extract and validate manifest
            manifest = await git_manager.extract_manifest(clone_dir)

            # Check if template already exists
            if db_pool:
                async with db_pool.acquire() as conn:
                    existing = await conn.fetchrow(
                        "SELECT id FROM templates WHERE name = $1 AND version = $2 AND organization = $3",
                        manifest.name,
                        manifest.version,
                        request.organization or manifest.metadata.category
                    )

                    if existing:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"Template {manifest.name} v{manifest.version} already exists"
                        )

                    # Insert template
                    template_id = uuid4()
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
                        request.organization,
                        request.git_url,
                        request.git_branch,
                        commit_hash,
                        manifest.engine,
                        request.auto_validate,
                        datetime.utcnow() if request.auto_validate else None,
                        manifest.get_validation_score() if request.auto_validate else None,
                        'approved' if request.auto_validate else 'draft',
                        'admin'
                    )

                    logger.info(
                        "template_registered",
                        template_id=str(template_id),
                        name=manifest.name,
                        version=manifest.version
                    )

                    return {
                        "id": str(template_id),
                        "name": manifest.name,
                        "version": manifest.version,
                        "git_url": request.git_url,
                        "commit_hash": commit_hash,
                        "manifest_validated": request.auto_validate,
                        "quality_score": manifest.get_validation_score() if request.auto_validate else None,
                        "message": "Template registered successfully"
                    }

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database not available"
            )

        finally:
            await git_manager.cleanup_clone(clone_dir)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("register_template_error", git_url=request.git_url, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/seed", response_model=SeedingReport)
async def seed_templates(
    config_path: Optional[str] = None,
    admin_key: str = Depends(verify_admin_key),
    db_pool = Depends(get_db_pool),
    git_manager: GitManager = Depends(get_git_manager)
):
    """
    Seed templates from configuration file

    - **config_path**: Path to templates.yaml (optional, uses default if not provided)

    Returns seeding report with statistics
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
        if not config_path:
            config_path = "/app/config/templates.yaml"

        config_file = Path(config_path)
        if not config_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration file not found: {config_path}"
            )

        with open(config_file) as f:
            config = yaml.safe_load(f)

        templates_config = config.get('templates', [])
        report.total_templates = len(templates_config)

        logger.info("seeding_templates", count=report.total_templates)

        # Process each template
        for template_config in templates_config:
            try:
                name = template_config.get('name')
                git_url = template_config.get('git_url')

                if not name or not git_url:
                    report.templates_failed += 1
                    report.errors.append(f"Missing name or git_url in config: {template_config}")
                    continue

                # Check if exists
                if db_pool:
                    async with db_pool.acquire() as conn:
                        existing = await conn.fetchrow(
                            "SELECT id FROM templates WHERE name = $1",
                            name
                        )

                        if existing:
                            report.templates_skipped += 1
                            logger.info("template_exists_skip", name=name)
                            continue

                # Clone and validate
                if git_manager:
                    clone_dir, commit_hash, _ = await git_manager.clone_repository(
                        git_url,
                        template_config.get('git_branch', 'main')
                    )

                    try:
                        manifest = await git_manager.extract_manifest(clone_dir)

                        # Insert
                        if db_pool:
                            async with db_pool.acquire() as conn:
                                template_id = uuid4()
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
                                    template_config.get('organization'),
                                    git_url,
                                    template_config.get('git_branch', 'main'),
                                    commit_hash,
                                    manifest.engine,
                                    True,
                                    datetime.utcnow(),
                                    manifest.get_validation_score(),
                                    'approved',
                                    'seeder'
                                )

                                report.templates_added += 1
                                logger.info("template_seeded", name=manifest.name, id=str(template_id))

                    finally:
                        await git_manager.cleanup_clone(clone_dir)

            except Exception as e:
                report.templates_failed += 1
                error_msg = f"Failed to seed {name}: {str(e)}"
                report.errors.append(error_msg)
                logger.error("seed_template_error", name=name, error=str(e))

        report.duration_seconds = time.time() - start_time

        logger.info(
            "seeding_complete",
            total=report.total_templates,
            added=report.templates_added,
            skipped=report.templates_skipped,
            failed=report.templates_failed
        )

        return report

    except HTTPException:
        raise
    except Exception as e:
        logger.error("seed_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Seeding failed: {str(e)}"
        )


@router.delete("/cache", response_model=CacheClearResult)
async def clear_cache(
    template_id: Optional[UUID] = None,
    admin_key: str = Depends(verify_admin_key),
    cache_manager: CacheManager = Depends(get_cache_manager)
):
    """
    Clear template cache

    - **template_id**: Specific template ID (optional, clears all if not provided)

    Returns cache clearing statistics
    """
    try:
        if not cache_manager:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Cache manager not available"
            )

        if template_id:
            # Clear specific template
            count = await cache_manager.invalidate_cache(template_id)
            logger.info("cache_cleared_template", template_id=str(template_id), count=count)

            return CacheClearResult(
                cache_entries_deleted=count,
                files_deleted=count,
                space_freed_bytes=0,  # Would need to track before deletion
                errors=[]
            )
        else:
            # Clear all cache
            files_deleted, redis_keys = await cache_manager.clear_all_cache()
            logger.info("cache_cleared_all", files=files_deleted, redis_keys=redis_keys)

            return CacheClearResult(
                cache_entries_deleted=redis_keys,
                files_deleted=files_deleted,
                space_freed_bytes=0,  # Would need to track before deletion
                errors=[]
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("clear_cache_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache clear failed: {str(e)}"
        )


@router.post("/{template_id}/validate", response_model=TemplateValidationResult)
async def validate_template_manifest(
    template_id: UUID,
    admin_key: str = Depends(verify_admin_key),
    git_manager: GitManager = Depends(get_git_manager),
    db_pool = Depends(get_db_pool)
):
    """
    Re-validate template manifest

    Updates validation status in database

    Returns validation result
    """
    try:
        # Get template
        if db_pool:
            async with db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT git_url, git_branch FROM templates WHERE id = $1",
                    template_id
                )

                if not row or not row['git_url']:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Template not found or no Git URL"
                    )

                git_url = row['git_url']
                git_branch = row['git_branch']

        # Clone and validate
        if git_manager:
            clone_dir, commit_hash, _ = await git_manager.clone_repository(git_url, git_branch)

            try:
                manifest = await git_manager.extract_manifest(clone_dir)
                validation_score = manifest.get_validation_score()

                # Update database
                if db_pool:
                    async with db_pool.acquire() as conn:
                        await conn.execute(
                            """
                            UPDATE templates
                            SET manifest_validated = TRUE,
                                manifest_validation_date = NOW(),
                                quality_score = $1,
                                git_commit_hash = $2,
                                updated_at = NOW()
                            WHERE id = $3
                            """,
                            validation_score,
                            commit_hash,
                            template_id
                        )

                logger.info(
                    "template_validated",
                    template_id=str(template_id),
                    score=validation_score
                )

                return TemplateValidationResult(
                    valid=True,
                    manifest_score=validation_score,
                    errors=[],
                    warnings=[],
                    manifest_data=manifest.dict()
                )

            finally:
                await git_manager.cleanup_clone(clone_dir)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Git manager not available"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("validate_template_error", template_id=str(template_id), error=str(e))

        # Return failed validation
        return TemplateValidationResult(
            valid=False,
            manifest_score=None,
            errors=[str(e)],
            warnings=[],
            manifest_data=None
        )


@router.get("/stats")
async def get_registry_stats(
    admin_key: str = Depends(verify_admin_key),
    db_pool = Depends(get_db_pool),
    cache_manager: CacheManager = Depends(get_cache_manager)
):
    """
    Get registry statistics

    Returns comprehensive statistics about templates and cache
    """
    try:
        stats = {
            "templates": {},
            "cache": {},
            "json_storage": {},
            "timestamp": datetime.utcnow().isoformat()
        }

        # Template statistics
        if db_pool:
            async with db_pool.acquire() as conn:
                total = await conn.fetchval("SELECT COUNT(*) FROM templates")
                by_status = await conn.fetch(
                    "SELECT status, COUNT(*) as count FROM templates GROUP BY status"
                )
                by_language = await conn.fetch(
                    "SELECT language, COUNT(*) as count FROM templates GROUP BY language ORDER BY count DESC LIMIT 10"
                )

                stats["templates"] = {
                    "total": total,
                    "by_status": {row['status']: row['count'] for row in by_status},
                    "top_languages": {row['language']: row['count'] for row in by_language}
                }

        # Cache statistics
        if cache_manager:
            cache_stats = await cache_manager.get_cache_stats()
            stats["cache"] = cache_stats

        # JSON storage statistics (maestro-engine integration)
        try:
            json_adapter = JSONStorageAdapter()
            json_stats = await json_adapter.get_json_template_stats()
            stats["json_storage"] = json_stats
        except Exception as e:
            logger.warning("json_storage_stats_unavailable", error=str(e))
            stats["json_storage"] = {"error": "unavailable"}

        return stats

    except Exception as e:
        logger.error("get_stats_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


@router.post("/sync-json-templates")
async def sync_json_templates(
    admin_key: str = Depends(verify_admin_key),
    db_pool = Depends(get_db_pool)
):
    """
    Sync JSON templates from maestro-engine storage to registry database

    This endpoint synchronizes templates generated by maestro-engine workflows
    (stored as JSON files) into the central registry database.

    Returns:
        Sync statistics with counts
    """
    try:
        if not db_pool:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database not available"
            )

        logger.info("starting_json_template_sync")

        # Create adapter and sync
        json_adapter = JSONStorageAdapter()
        sync_stats = await json_adapter.sync_all_json_templates_to_db(db_pool)

        logger.info(
            "json_template_sync_complete",
            total=sync_stats["total"],
            registered=sync_stats["registered"],
            skipped=sync_stats["skipped"],
            failed=sync_stats["failed"]
        )

        return {
            "status": "success",
            "message": f"Synced {sync_stats['registered']} templates",
            "statistics": sync_stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("sync_json_templates_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}"
        )


@router.get("/json-templates")
async def list_json_templates(
    admin_key: str = Depends(verify_admin_key),
    language: Optional[str] = None,
    category: Optional[str] = None,
    min_quality_score: Optional[float] = None
):
    """
    List JSON templates from maestro-engine storage

    Query Parameters:
    - language: Filter by programming language
    - category: Filter by category
    - min_quality_score: Minimum quality score threshold

    Returns:
        List of JSON template metadata
    """
    try:
        json_adapter = JSONStorageAdapter()
        templates = await json_adapter.list_json_templates(
            language=language,
            category=category,
            min_quality_score=min_quality_score
        )

        return {
            "total": len(templates),
            "templates": templates,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error("list_json_templates_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list JSON templates: {str(e)}"
        )


@router.get("/json-templates/{template_id}")
async def get_json_template(
    template_id: str,
    admin_key: str = Depends(verify_admin_key)
):
    """
    Get specific JSON template by ID

    Returns full template data including metadata, workflow context,
    quality validation, and code content.

    Path Parameters:
    - template_id: UUID of the template

    Returns:
        Complete template data
    """
    try:
        json_adapter = JSONStorageAdapter()
        template = await json_adapter.get_json_template(template_id)

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"JSON template {template_id} not found"
            )

        return template

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_json_template_error", template_id=template_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get JSON template: {str(e)}"
        )