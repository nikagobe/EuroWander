"""Playlist API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.client import get_db
from app.modules.playlists.application.services import PlaylistService
from app.modules.playlists.infrastructure.repositories import (
    MongoPlaylistRepository,
    MongoPlaylistReviewRepository,
)
from app.modules.playlists.presentation.schemas import (
    CreatePlaylistRequest,
    CreateReviewRequest,
    ImportPlaylistRequest,
    LikeResponse,
    PlaylistItemSchema,
    PlaylistResponse,
    PlaylistSummaryResponse,
    ReviewResponse,
    UpdatePlaylistRequest,
)
from app.modules.cities.application.services import CityService
from app.modules.cities.infrastructure.repositories import MongoCityRepository
from app.modules.schedule.infrastructure.repositories import MongoScheduleRepository
from app.modules.trips.infrastructure.repositories import MongoTripRepository
from app.modules.users.domain.entities import User
from app.modules.users.presentation.router import get_current_user

router = APIRouter(prefix="/playlists", tags=["playlists"])


# ── Dependency factory ──────────────────────────────────────────────────────────


def get_playlist_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> PlaylistService:
    return PlaylistService(
        playlist_repo=MongoPlaylistRepository(db["playlists"]),
        review_repo=MongoPlaylistReviewRepository(db["playlist_reviews"]),
        schedule_repo=MongoScheduleRepository(db["schedule_items"]),
        trip_repo=MongoTripRepository(db["trips"]),
    )


# ── CRUD ────────────────────────────────────────────────────────────────────────


@router.post("", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
async def create_playlist(
    body: CreatePlaylistRequest,
    current_user: User = Depends(get_current_user),
    service: PlaylistService = Depends(get_playlist_service),
) -> PlaylistResponse:
    """
    Create a new playlist.

    **Flutter flow:** Playlist Builder screen → fill city, vibe, budget,
    add items with drag-and-drop → submit.
    """
    playlist = await service.create_playlist(
        creator_id=current_user.id,
        city=body.city,
        country=body.country,
        title=body.title,
        description=body.description,
        cover_photo_url=body.cover_photo_url,
        vibe=body.vibe,
        budget_tier=body.budget_tier,
        tags=body.tags,
        total_days=body.total_days,
        is_public=body.is_public,
        items=[i.model_dump() for i in body.items],
    )
    return _to_response(playlist)


@router.get("/search", response_model=list[PlaylistSummaryResponse])
async def search_playlists(
    city: str | None = None,
    country: str | None = None,
    vibe: str | None = None,
    budget_tier: str | None = None,
    keyword: str | None = None,
    sort_by: str = Query("popular", pattern="^(popular|newest|top_rated)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: PlaylistService = Depends(get_playlist_service),
) -> list[PlaylistSummaryResponse]:
    """
    Search public playlists with filters.

    **Flutter flow:** Discovery screen → search bar + filter chips → infinite scroll.
    """
    playlists = await service.search_playlists(
        city=city, country=country, vibe=vibe,
        budget_tier=budget_tier, keyword=keyword,
        sort_by=sort_by, skip=skip, limit=limit,
    )
    return [_to_summary(p) for p in playlists]


@router.get("/cities")
async def search_playlist_cities(
    q: str = Query("", description="City name prefix to search"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncIOMotorDatabase = Depends(get_db),
    service: PlaylistService = Depends(get_playlist_service),
) -> list[str]:
    """
    Search cities for playlist filtering.

    If `q` is provided, searches all known cities (not just those with playlists).
    If `q` is empty, returns cities that have existing public playlists.

    **Flutter flow:** Autocomplete in playlist discovery search bar.
    """
    if q:
        city_service = CityService(MongoCityRepository(db["cities"]))
        cities = await city_service.search(q, limit)
        return [c.name for c in cities]
    return await service.list_cities()


@router.get("/mine", response_model=list[PlaylistSummaryResponse])
async def get_my_playlists(
    current_user: User = Depends(get_current_user),
    service: PlaylistService = Depends(get_playlist_service),
) -> list[PlaylistSummaryResponse]:
    """Get all playlists created by the current user."""
    playlists = await service.get_user_playlists(current_user.id)
    return [_to_summary(p) for p in playlists]


@router.get("/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(
    playlist_id: str,
    service: PlaylistService = Depends(get_playlist_service),
) -> PlaylistResponse:
    """Get a playlist by ID with all items."""
    try:
        playlist = await service.get_playlist(playlist_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return _to_response(playlist)


@router.put("/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist(
    playlist_id: str,
    body: UpdatePlaylistRequest,
    current_user: User = Depends(get_current_user),
    service: PlaylistService = Depends(get_playlist_service),
) -> PlaylistResponse:
    """Update a playlist — owner only."""
    updates = body.model_dump(exclude_none=True)
    if "items" in updates:
        updates["items"] = [i.model_dump() for i in body.items]  # type: ignore[union-attr]
    try:
        playlist = await service.update_playlist(playlist_id, current_user.id, **updates)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return _to_response(playlist)


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist(
    playlist_id: str,
    current_user: User = Depends(get_current_user),
    service: PlaylistService = Depends(get_playlist_service),
) -> None:
    """Delete a playlist — owner only."""
    try:
        await service.delete_playlist(playlist_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# ── Like / Fork / Import ────────────────────────────────────────────────────────


@router.post("/{playlist_id}/like", response_model=LikeResponse)
async def toggle_like(
    playlist_id: str,
    current_user: User = Depends(get_current_user),
    service: PlaylistService = Depends(get_playlist_service),
) -> LikeResponse:
    """Toggle like on a playlist."""
    try:
        liked = await service.toggle_like(playlist_id, current_user.id)
        playlist = await service.get_playlist(playlist_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return LikeResponse(liked=liked, like_count=playlist.like_count)


@router.post("/{playlist_id}/fork", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
async def fork_playlist(
    playlist_id: str,
    current_user: User = Depends(get_current_user),
    service: PlaylistService = Depends(get_playlist_service),
) -> PlaylistResponse:
    """Fork (copy) a playlist to your own collection."""
    try:
        forked = await service.fork_playlist(playlist_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return _to_response(forked)


@router.post("/{playlist_id}/import/{trip_id}")
async def import_playlist_to_schedule(
    playlist_id: str,
    trip_id: str,
    body: ImportPlaylistRequest,
    current_user: User = Depends(get_current_user),
    service: PlaylistService = Depends(get_playlist_service),
) -> dict[str, int]:
    """
    Import playlist items into a trip schedule.

    Maps each playlist item's `day_number` onto real dates starting from `start_date`.
    Items with `day_number=1` → start_date, `day_number=2` → start_date + 1, etc.

    **Flutter flow:** Tap "Import to Trip" → pick trip → pick start date → confirm.
    """
    try:
        count = await service.import_to_schedule(
            playlist_id=playlist_id,
            trip_id=trip_id,
            user_id=current_user.id,
            start_date=body.start_date,
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"imported_items": count}


# ── Reviews ──────────────────────────────────────────────────────────────────────


@router.post(
    "/{playlist_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_review(
    playlist_id: str,
    body: CreateReviewRequest,
    current_user: User = Depends(get_current_user),
    service: PlaylistService = Depends(get_playlist_service),
) -> ReviewResponse:
    """Add a review to a playlist (1–5 stars + optional comment)."""
    try:
        review = await service.add_review(
            playlist_id=playlist_id,
            user_id=current_user.id,
            user_first_name=current_user.first_name,
            user_last_name=current_user.last_name,
            rating=body.rating,
            comment=body.comment,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _review_to_response(review)


@router.get("/{playlist_id}/reviews", response_model=list[ReviewResponse])
async def get_reviews(
    playlist_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: PlaylistService = Depends(get_playlist_service),
) -> list[ReviewResponse]:
    """Get paginated reviews for a playlist."""
    reviews = await service.get_reviews(playlist_id, skip=skip, limit=limit)
    return [_review_to_response(r) for r in reviews]


@router.delete(
    "/{playlist_id}/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_review(
    playlist_id: str,
    review_id: str,
    current_user: User = Depends(get_current_user),
    service: PlaylistService = Depends(get_playlist_service),
) -> None:
    """Delete a review — only the review author can delete."""
    try:
        await service.delete_review(playlist_id, review_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Response mappers ─────────────────────────────────────────────────────────────


def _to_response(p) -> PlaylistResponse:
    return PlaylistResponse(
        id=p.id,
        creator_id=p.creator_id,
        city=p.city,
        country=p.country,
        title=p.title,
        description=p.description,
        cover_photo_url=p.cover_photo_url,
        vibe=[v.value if hasattr(v, "value") else v for v in p.vibe] if isinstance(p.vibe, list) else [p.vibe.value if hasattr(p.vibe, "value") else p.vibe],
        budget_tier=p.budget_tier.value if hasattr(p.budget_tier, "value") else p.budget_tier,
        items=[
            PlaylistItemSchema(
                item_type=i.item_type.value if hasattr(i.item_type, "value") else i.item_type,
                name=i.name,
                day_number=i.day_number,
                time_slot=i.time_slot.value if hasattr(i.time_slot, "value") else i.time_slot,
                order=i.order,
                location_id=i.location_id,
                category=i.category,
                photo_url=i.photo_url,
                latitude=i.latitude,
                longitude=i.longitude,
                address=i.address,
                rating=i.rating,
                num_reviews=i.num_reviews,
                price_indicator=i.price_indicator,
                note=i.note,
                suggested_duration_minutes=i.suggested_duration_minutes,
            )
            for i in p.items
        ],
        tags=p.tags,
        total_days=p.total_days,
        is_public=p.is_public,
        like_count=p.like_count,
        import_count=p.import_count,
        review_count=p.review_count,
        average_rating=p.average_rating,
        created_at=p.created_at.isoformat() if hasattr(p.created_at, "isoformat") else str(p.created_at),
        updated_at=p.updated_at.isoformat() if hasattr(p.updated_at, "isoformat") else str(p.updated_at),
    )


def _to_summary(p) -> PlaylistSummaryResponse:
    return PlaylistSummaryResponse(
        id=p.id,
        creator_id=p.creator_id,
        city=p.city,
        country=p.country,
        title=p.title,
        description=p.description,
        cover_photo_url=p.cover_photo_url,
        vibe=[v.value if hasattr(v, "value") else v for v in p.vibe] if isinstance(p.vibe, list) else [p.vibe.value if hasattr(p.vibe, "value") else p.vibe],
        budget_tier=p.budget_tier.value if hasattr(p.budget_tier, "value") else p.budget_tier,
        total_days=p.total_days,
        item_count=len(p.items),
        like_count=p.like_count,
        import_count=p.import_count,
        review_count=p.review_count,
        average_rating=p.average_rating,
        tags=p.tags,
    )


def _review_to_response(r) -> ReviewResponse:
    return ReviewResponse(
        id=r.id,
        playlist_id=r.playlist_id,
        user_id=r.user_id,
        user_first_name=r.user_first_name,
        user_last_name=r.user_last_name,
        rating=r.rating,
        comment=r.comment,
        created_at=r.created_at.isoformat() if hasattr(r.created_at, "isoformat") else str(r.created_at),
    )

