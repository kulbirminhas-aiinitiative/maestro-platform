"""
Templates Router
Template listing, searching, and downloading endpoints
"""

from pathlib import Path
from typing import List, Optional
from uuid import UUID
import time

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse

from ..models.template import (
    TemplateResponse,
    TemplateListResponse,
    TemplateSearchQuery,
    TemplateDownloadRequest,
    TemplateCacheInfo
)
from ..security import rate_limit_dependency
from ..auth import get_current_active_user, User
from ..git_manager import GitManager
from ..cache_manager import CacheManager
from ..dependencies import get_db_pool, get_git_manager, get_cache_manager
from ..event_tracking import (
    track_template_search,
    track_template_retrieval,
    track_template_download
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])


def get_language_variants(language: str) -> List[str]:
    """
    Get compatible language variants for flexible matching.

    Handles language variants and supersets (e.g., TypeScript is compatible with JavaScript).
    This improves template discoverability by treating related languages as compatible.

    Args:
        language: The language to get variants for

    Returns:
        List of compatible language strings

    Examples:
        - "javascript" returns ["javascript", "typescript", "js", "ts"]
        - "python" returns ["python", "python3", "py"]
    """
    if not language:
        return []

    normalized = language.lower().strip()

    # TypeScript/JavaScript compatibility (TS is superset of JS)
    js_ts_variants = {'javascript', 'typescript', 'js', 'ts'}
    if normalized in js_ts_variants:
        return list(js_ts_variants)

    # Python variants
    python_variants = {'python', 'python3', 'py'}
    if normalized in python_variants:
        return list(python_variants)

    # Node.js / JavaScript
    node_variants = {'node', 'nodejs', 'node.js'}
    if normalized in node_variants:
        return list(js_ts_variants | node_variants)

    # Ruby variants
    ruby_variants = {'ruby', 'rb'}
    if normalized in ruby_variants:
        return list(ruby_variants)

    # Go variants
    go_variants = {'go', 'golang'}
    if normalized in go_variants:
        return list(go_variants)

    # If no variants, return original
    return [normalized]


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    language: Optional[str] = Query(None, description="Filter by language"),
    framework: Optional[str] = Query(None, description="Filter by framework"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    pinned: Optional[bool] = Query(None, description="Filter by pinned status"),
    quality_tier: Optional[str] = Query(None, pattern="^(gold|silver|bronze|standard)$", description="Filter by quality tier"),
    current_user: User = Depends(get_current_active_user),
    db_pool = Depends(get_db_pool)
):
    """
    List templates with pagination and filtering

    - **page**: Page number (starts at 1)
    - **page_size**: Number of items per page (1-100)
    - **language**: Filter by programming language
    - **framework**: Filter by framework
    - **category**: Filter by category
    - **tags**: Filter by tags (can specify multiple)

    Returns paginated list of templates
    """
    try:
        # Build query
        query = """
            SELECT id, name, description, category, language, framework, version,
                   tags, organization, persona, git_url, git_branch, templating_engine,
                   quality_score, security_score, performance_score, maintainability_score,
                   is_pinned, quality_tier, pin_reason, pinned_at, pinned_by,
                   status, manifest_validated, manifest_validation_date,
                   usage_count, success_rate, last_accessed_at, storage_tier,
                   cache_path, file_path, created_at, updated_at, created_by
            FROM templates
            WHERE 1=1
        """
        params = []
        param_count = 1

        # Apply filters
        if language:
            # Use language variants for flexible matching (e.g., JS/TS compatibility)
            language_variants = get_language_variants(language)
            query += f" AND language = ANY(${param_count})"
            params.append(language_variants)
            param_count += 1

        if framework:
            query += f" AND framework = ${param_count}"
            params.append(framework)
            param_count += 1

        if category:
            query += f" AND category = ${param_count}"
            params.append(category)
            param_count += 1

        if tags:
            query += f" AND tags && ${param_count}"
            params.append(tags)
            param_count += 1

        if pinned is not None:
            query += f" AND is_pinned = ${param_count}"
            params.append(pinned)
            param_count += 1

        if quality_tier:
            query += f" AND quality_tier = ${param_count}"
            params.append(quality_tier)
            param_count += 1

        # Get total count
        count_query = f"SELECT COUNT(*) FROM ({query}) AS filtered"

        # Add pagination
        query += f" ORDER BY created_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
        params.extend([page_size, (page - 1) * page_size])

        if db_pool:
            async with db_pool.acquire() as conn:
                total = await conn.fetchval(count_query, *params[:-2] if params else [])
                rows = await conn.fetch(query, *params)

                templates = [TemplateResponse(**dict(row)) for row in rows]

                return TemplateListResponse(
                    total=total,
                    page=page,
                    page_size=page_size,
                    templates=templates
                )
        else:
            # Fallback for testing
            return TemplateListResponse(
                total=0,
                page=page,
                page_size=page_size,
                templates=[]
            )

    except Exception as e:
        logger.error("list_templates_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list templates: {str(e)}"
        )


@router.get("/search", response_model=TemplateListResponse)
async def search_templates(
    query: Optional[str] = Query(None, description="Search query"),
    language: Optional[str] = Query(None, description="Filter by language"),
    framework: Optional[str] = Query(None, description="Filter by framework"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    min_quality_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum quality score"),
    pinned: Optional[bool] = Query(None, description="Filter by pinned status"),
    quality_tier: Optional[str] = Query(None, pattern="^(gold|silver|bronze|standard)$", description="Filter by quality tier"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: User = Depends(get_current_active_user),
    db_pool = Depends(get_db_pool)
):
    """
    Advanced search for templates

    - **query**: Full-text search across name and description
    - **language**, **framework**, **category**, **tags**: Filters
    - **min_quality_score**: Minimum quality score threshold
    - **sort_by**: Field to sort by (created_at, quality_score, usage_count)
    - **sort_order**: asc or desc

    Returns paginated search results
    """
    start_time = time.time()

    try:
        # Use full-text search with ranking if query provided
        if query:
            sql_query = """
                SELECT id, name, description, category, language, framework, version,
                       tags, organization, persona, git_url, git_branch, templating_engine,
                       quality_score, security_score, performance_score, maintainability_score,
                       is_pinned, quality_tier, pin_reason, pinned_at, pinned_by,
                       status, manifest_validated, manifest_validation_date,
                       usage_count, success_rate, last_accessed_at, storage_tier,
                       cache_path, file_path, created_at, updated_at, created_by,
                       ts_rank(search_vector, to_tsquery('english', $1)) as search_rank
                FROM templates
                WHERE search_vector @@ to_tsquery('english', $1)
            """
            # Convert query to tsquery format (replace spaces with & for AND)
            tsquery = ' & '.join(query.split())
            params = [tsquery]
            param_count = 2
        else:
            sql_query = """
                SELECT id, name, description, category, language, framework, version,
                       tags, organization, persona, git_url, git_branch, templating_engine,
                       quality_score, security_score, performance_score, maintainability_score,
                       is_pinned, quality_tier, pin_reason, pinned_at, pinned_by,
                       status, manifest_validated, manifest_validation_date,
                       usage_count, success_rate, last_accessed_at, storage_tier,
                       cache_path, file_path, created_at, updated_at, created_by,
                       0.0 as search_rank
                FROM templates
                WHERE 1=1
            """
            params = []
            param_count = 1

        # Apply filters (same as list_templates)
        if language:
            # Use language variants for flexible matching (e.g., JS/TS compatibility)
            language_variants = get_language_variants(language)
            sql_query += f" AND language = ANY(${param_count})"
            params.append(language_variants)
            param_count += 1

        if framework:
            sql_query += f" AND framework = ${param_count}"
            params.append(framework)
            param_count += 1

        if category:
            sql_query += f" AND category = ${param_count}"
            params.append(category)
            param_count += 1

        if tags:
            sql_query += f" AND tags && ${param_count}"
            params.append(tags)
            param_count += 1

        if min_quality_score is not None:
            sql_query += f" AND quality_score >= ${param_count}"
            params.append(min_quality_score)
            param_count += 1

        if pinned is not None:
            sql_query += f" AND is_pinned = ${param_count}"
            params.append(pinned)
            param_count += 1

        if quality_tier:
            sql_query += f" AND quality_tier = ${param_count}"
            params.append(quality_tier)
            param_count += 1

        # Get total count
        count_query = f"SELECT COUNT(*) FROM ({sql_query}) AS filtered"

        # Add sorting and pagination
        allowed_sort_fields = ['created_at', 'quality_score', 'usage_count', 'name', 'search_rank']

        # Default to search_rank DESC if query provided, otherwise created_at DESC
        if query and sort_by == 'created_at':
            sort_by = 'search_rank'
            sort_order = 'desc'
        elif sort_by not in allowed_sort_fields:
            sort_by = 'created_at'

        sql_query += f" ORDER BY {sort_by} {sort_order.upper()} LIMIT ${param_count} OFFSET ${param_count + 1}"
        params.extend([page_size, (page - 1) * page_size])

        if db_pool:
            async with db_pool.acquire() as conn:
                total = await conn.fetchval(count_query, *params[:-2] if params else [])
                rows = await conn.fetch(sql_query, *params)

                templates = [TemplateResponse(**dict(row)) for row in rows]

                # Track search event
                search_duration_ms = (time.time() - start_time) * 1000
                await track_template_search(
                    query=query,
                    results_count=len(templates),
                    category_filter=category,
                    language_filter=language,
                    framework_filter=framework,
                    tags_filter=tags,
                    min_quality_score=min_quality_score,
                    search_duration_ms=search_duration_ms
                )

                return TemplateListResponse(
                    total=total,
                    page=page,
                    page_size=page_size,
                    templates=templates
                )
        else:
            return TemplateListResponse(
                total=0,
                page=page,
                page_size=page_size,
                templates=[]
            )

    except Exception as e:
        logger.error("search_templates_error", error=str(e), query=query)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db_pool = Depends(get_db_pool)
):
    """
    Get single template by ID

    Returns detailed template information
    """
    start_time = time.time()

    try:
        query = """
            SELECT id, name, description, category, language, framework, version,
                   tags, organization, persona, git_url, git_branch, templating_engine,
                   quality_score, security_score, performance_score, maintainability_score,
                   is_pinned, quality_tier, pin_reason, pinned_at, pinned_by,
                   status, manifest_validated, manifest_validation_date,
                   usage_count, success_rate, last_accessed_at, storage_tier,
                   cache_path, file_path, created_at, updated_at, created_by
            FROM templates
            WHERE id = $1
        """

        if db_pool:
            async with db_pool.acquire() as conn:
                row = await conn.fetchrow(query, template_id)

                if not row:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Template {template_id} not found"
                    )

                template_data = dict(row)

                # Track retrieval event
                retrieval_duration_ms = (time.time() - start_time) * 1000
                await track_template_retrieval(
                    template_id=str(template_id),
                    template_name=template_data.get('name', 'unknown'),
                    template_version=template_data.get('version'),
                    template_category=template_data.get('category'),
                    retrieval_method="api",
                    retrieval_duration_ms=retrieval_duration_ms,
                    discovered_via="direct"
                )

                return TemplateResponse(**template_data)
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database not available"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_template_error", template_id=str(template_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get template: {str(e)}"
        )


@router.get("/{template_id}/download")
async def download_template(
    template_id: UUID,
    version: str = Query("main", description="Git branch/tag version"),
    format: str = Query("tar.gz", pattern="^(tar\\.gz|zip)$", description="Archive format"),
    current_user: User = Depends(get_current_active_user),
    git_manager: GitManager = Depends(get_git_manager),
    cache_manager: CacheManager = Depends(get_cache_manager),
    db_pool = Depends(get_db_pool)
):
    """
    Download template archive

    - **version**: Git branch, tag, or commit hash
    - **format**: Archive format (tar.gz or zip)

    Returns streaming archive file
    """
    start_time = time.time()

    try:
        # Get template info
        if db_pool:
            async with db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT git_url, git_branch, name FROM templates WHERE id = $1",
                    template_id
                )

                if not row:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Template {template_id} not found"
                    )

                git_url = row['git_url']
                name = row['name']

                if not git_url:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Template does not have Git URL configured"
                    )

        # Check cache
        if cache_manager:
            cached_path = await cache_manager.check_cache(template_id, version)
            if cached_path:
                logger.info("serving_from_cache", template_id=str(template_id), version=version)
                return FileResponse(
                    cached_path,
                    media_type="application/x-gzip" if format == "tar.gz" else "application/zip",
                    filename=f"{name}-{version}.{format}"
                )

        # Clone and archive
        if git_manager:
            clone_dir, commit_hash, clone_ms = await git_manager.clone_repository(
                git_url,
                version
            )

            try:
                # Create archive
                archive_path = Path(f"/storage/temp/{template_id}_{version}.{format}")
                size, checksum, archive_ms = await git_manager.create_archive(
                    clone_dir,
                    archive_path,
                    format
                )

                # Store in cache
                if cache_manager:
                    await cache_manager.store_cache(
                        template_id,
                        version,
                        archive_path,
                        commit_hash,
                        clone_ms,
                        archive_ms,
                        checksum
                    )

                # Update usage statistics
                if db_pool:
                    async with db_pool.acquire() as conn:
                        await conn.execute(
                            """
                            UPDATE templates
                            SET usage_count = usage_count + 1,
                                last_accessed_at = NOW()
                            WHERE id = $1
                            """,
                            template_id
                        )

                logger.info(
                    "template_downloaded",
                    template_id=str(template_id),
                    version=version,
                    size_mb=round(size / 1024 / 1024, 2)
                )

                # Track download event
                download_duration_ms = (time.time() - start_time) * 1000
                download_size_mb = size / 1024 / 1024
                await track_template_download(
                    template_id=str(template_id),
                    template_name=name,
                    template_version=version,
                    download_format=format,
                    download_size_mb=download_size_mb,
                    download_duration_ms=download_duration_ms
                )

                return FileResponse(
                    archive_path,
                    media_type="application/x-gzip" if format == "tar.gz" else "application/zip",
                    filename=f"{name}-{version}.{format}"
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
        logger.error("download_template_error", template_id=str(template_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Download failed: {str(e)}"
        )


@router.get("/{template_id}/manifest")
async def get_template_manifest(
    template_id: UUID,
    version: str = Query("main", description="Git branch/tag version"),
    current_user: User = Depends(get_current_active_user),
    git_manager: GitManager = Depends(get_git_manager),
    db_pool = Depends(get_db_pool)
):
    """
    Get template manifest

    Returns parsed and validated manifest.yaml
    """
    try:
        # Get Git URL
        if db_pool:
            async with db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT git_url FROM templates WHERE id = $1",
                    template_id
                )

                if not row or not row['git_url']:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Template not found or no Git URL"
                    )

                git_url = row['git_url']

        # Clone and extract manifest
        if git_manager:
            clone_dir, _, _ = await git_manager.clone_repository(git_url, version)

            try:
                manifest = await git_manager.extract_manifest(clone_dir)
                return {
                    "manifest": manifest.dict(),
                    "validation_score": manifest.get_validation_score(),
                    "version": version
                }
            finally:
                await git_manager.cleanup_clone(clone_dir)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Git manager not available"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_manifest_error", template_id=str(template_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get manifest: {str(e)}"
        )


@router.get("/{template_id}/versions")
async def list_template_versions(
    template_id: UUID,
    current_user: User = Depends(get_current_active_user),
    git_manager: GitManager = Depends(get_git_manager),
    db_pool = Depends(get_db_pool)
):
    """
    List available versions for template

    Returns list of branches and tags from Git repository
    """
    try:
        # Get Git URL
        if db_pool:
            async with db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT git_url FROM templates WHERE id = $1",
                    template_id
                )

                if not row or not row['git_url']:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Template not found or no Git URL"
                    )

                git_url = row['git_url']

        # List versions
        if git_manager:
            versions = await git_manager.list_versions(git_url)
            return {
                "template_id": str(template_id),
                "versions": versions,
                "count": len(versions)
            }

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Git manager not available"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("list_versions_error", template_id=str(template_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list versions: {str(e)}"
        )


@router.post("/{template_id}/pin", status_code=status.HTTP_200_OK)
async def pin_template(
    template_id: UUID,
    reason: str = Query(..., description="Reason for pinning this template"),
    quality_tier: str = Query("gold", pattern="^(gold|silver|bronze)$", description="Quality tier"),
    pinned_by: str = Query(..., description="Username of person pinning"),
    current_user: User = Depends(get_current_active_user),
    db_pool = Depends(get_db_pool)
):
    """
    Pin a template as recommended ("golden" template)

    - **reason**: Business justification for pinning
    - **quality_tier**: gold (best), silver, or bronze
    - **pinned_by**: Username for audit trail

    Returns success confirmation
    """
    try:
        if not db_pool:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database not available"
            )

        async with db_pool.acquire() as conn:
            # Check template exists
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM templates WHERE id = $1)",
                template_id
            )

            if not exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Template {template_id} not found"
                )

            # Pin the template
            await conn.execute(
                """
                UPDATE templates
                SET is_pinned = true,
                    quality_tier = $2,
                    pin_reason = $3,
                    pinned_at = NOW(),
                    pinned_by = $4
                WHERE id = $1
                """,
                template_id, quality_tier, reason, pinned_by
            )

            logger.info(
                "template_pinned",
                template_id=str(template_id),
                quality_tier=quality_tier,
                pinned_by=pinned_by
            )

            return {
                "status": "success",
                "message": f"Template pinned as {quality_tier}",
                "template_id": str(template_id),
                "quality_tier": quality_tier,
                "pinned_by": pinned_by
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("pin_template_error", template_id=str(template_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pin template: {str(e)}"
        )


@router.delete("/{template_id}/pin", status_code=status.HTTP_200_OK)
async def unpin_template(
    template_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db_pool = Depends(get_db_pool)
):
    """
    Remove pin from template

    Returns success confirmation
    """
    try:
        if not db_pool:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database not available"
            )

        async with db_pool.acquire() as conn:
            # Check template exists and is pinned
            row = await conn.fetchrow(
                "SELECT is_pinned FROM templates WHERE id = $1",
                template_id
            )

            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Template {template_id} not found"
                )

            if not row['is_pinned']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Template is not currently pinned"
                )

            # Unpin the template
            await conn.execute(
                """
                UPDATE templates
                SET is_pinned = false,
                    quality_tier = 'standard',
                    pin_reason = NULL,
                    pinned_at = NULL,
                    pinned_by = NULL
                WHERE id = $1
                """,
                template_id
            )

            logger.info("template_unpinned", template_id=str(template_id))

            return {
                "status": "success",
                "message": "Template unpinned",
                "template_id": str(template_id)
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("unpin_template_error", template_id=str(template_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unpin template: {str(e)}"
        )