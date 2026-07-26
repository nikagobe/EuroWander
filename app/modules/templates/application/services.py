"""Template application service — orchestrates domain logic."""

from datetime import datetime, timedelta

from app.modules.templates.domain.entities import (
    TemplateLeg,
    TemplateStatus,
    TripTemplate,
)
from app.modules.templates.domain.interfaces import TemplateRepository


class TemplateService:
    def __init__(self, repo: TemplateRepository) -> None:
        self.repo = repo

    async def create_template(
        self,
        author_id: str,
        title: str,
        description: str,
        legs: list[TemplateLeg],
        tags: list[str] | None = None,
        cover_photo_url: str = "",
        estimated_budget_min: float | None = None,
        estimated_budget_max: float | None = None,
        currency: str = "EUR",
    ) -> TripTemplate:
        total_days = sum(leg.days for leg in legs)
        template = TripTemplate(
            author_id=author_id,
            title=title,
            description=description,
            legs=legs,
            tags=tags or [],
            cover_photo_url=cover_photo_url,
            estimated_budget_min=estimated_budget_min,
            estimated_budget_max=estimated_budget_max,
            currency=currency,
            total_days=total_days,
        )
        return await self.repo.create(template)

    async def get_template(self, template_id: str) -> TripTemplate | None:
        return await self.repo.get_by_id(template_id)

    async def update_template(
        self,
        template_id: str,
        user_id: str,
        **fields: object,
    ) -> TripTemplate | None:
        template = await self.repo.get_by_id(template_id)
        if template is None or not template.is_author(user_id):
            return None

        for key, value in fields.items():
            if hasattr(template, key) and value is not None:
                setattr(template, key, value)

        # Recalculate total_days if legs changed
        if "legs" in fields and fields["legs"] is not None:
            template.total_days = sum(leg.days for leg in template.legs)

        template.updated_at = datetime.utcnow()
        return await self.repo.update(template)

    async def publish(self, template_id: str, user_id: str) -> TripTemplate | None:
        template = await self.repo.get_by_id(template_id)
        if template is None or not template.is_author(user_id):
            return None
        if not template.can_be_published():
            return None
        template.status = TemplateStatus.PUBLISHED
        template.updated_at = datetime.utcnow()
        return await self.repo.update(template)

    async def unpublish(self, template_id: str, user_id: str) -> TripTemplate | None:
        """Move a published template back to draft so it can be edited."""
        template = await self.repo.get_by_id(template_id)
        if template is None or not template.is_author(user_id):
            return None
        template.status = TemplateStatus.DRAFT
        template.updated_at = datetime.utcnow()
        return await self.repo.update(template)

    async def delete_template(self, template_id: str, user_id: str) -> bool:
        template = await self.repo.get_by_id(template_id)
        if template is None or not template.is_author(user_id):
            return False
        return await self.repo.delete(template_id)

    async def toggle_like(self, template_id: str, user_id: str) -> TripTemplate | None:
        template = await self.repo.get_by_id(template_id)
        if template is None or not template.is_published():
            return None
        if user_id in template.liked_by:
            template.liked_by.remove(user_id)
            template.like_count = max(0, template.like_count - 1)
        else:
            template.liked_by.append(user_id)
            template.like_count += 1
        return await self.repo.update(template)

    async def list_published(
        self,
        skip: int = 0,
        limit: int = 20,
        tags: list[str] | None = None,
        destination: str | None = None,
        sort_by: str = "newest",
    ) -> list[TripTemplate]:
        return await self.repo.list_published(skip, limit, tags, destination, sort_by)

    async def list_my_templates(self, author_id: str, skip: int = 0, limit: int = 20) -> list[TripTemplate]:
        return await self.repo.list_by_author(author_id, skip, limit)

    async def generate_fork_guide(
        self,
        template_id: str,
        start_date: str,
    ) -> dict | None:
        """Generate a fork guide with concrete dates. Transportation is left
        entirely to the user — the guide only provides cities, dates, and hotels."""
        template = await self.repo.get_by_id(template_id)
        if template is None or not template.is_published():
            return None

        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        legs_guide: list[dict] = []

        for leg in template.legs:
            leg_start = current_date
            leg_end = current_date + timedelta(days=leg.days)

            guide: dict = {
                "order": leg.order,
                "city": leg.city,
                "country": leg.country,
                "days": leg.days,
                "date_range": {
                    "start": leg_start.strftime("%Y-%m-%d"),
                    "end": leg_end.strftime("%Y-%m-%d"),
                },
                "author_notes": leg.author_notes,
                "playlist_id": leg.playlist_id,
                "restaurant_ids": leg.restaurant_ids,
            }

            if leg.hotel_recommendations:
                hr = leg.hotel_recommendations
                guide["hotel_search"] = {
                    "city": hr.city,
                    "checkin": leg_start.strftime("%Y-%m-%d"),
                    "checkout": leg_end.strftime("%Y-%m-%d"),
                    "primary_picks": [
                        {
                            "booking_hotel_id": p.booking_hotel_id,
                            "name": p.name,
                            "neighborhood": p.neighborhood,
                            "stars": p.stars,
                            "photo_url": p.photo_url,
                            "author_review": p.author_review,
                            "priority": p.priority,
                            "price_paid": p.price_paid,
                            "currency": p.currency,
                        }
                        for p in hr.primary_picks
                    ],
                    "fallback_params": {
                        "neighborhood": hr.fallback_neighborhood,
                        "star_min": hr.fallback_star_min,
                        "star_max": hr.fallback_star_max,
                        "budget_min_per_night": hr.fallback_budget_per_night_min,
                        "budget_max_per_night": hr.fallback_budget_per_night_max,
                    },
                }

            current_date = leg_end
            legs_guide.append(guide)

        return {
            "template_id": template.id,
            "title": template.title,
            "total_days": template.total_days,
            "estimated_budget_min": template.estimated_budget_min,
            "estimated_budget_max": template.estimated_budget_max,
            "currency": template.currency,
            "legs": legs_guide,
        }

    async def fork_template(self, template_id: str, user_id: str) -> str | None:
        """Increment fork count. Returns template_id if successful.
        Actual Trip creation happens in the trips module."""
        template = await self.repo.get_by_id(template_id)
        if template is None or not template.is_published():
            return None
        await self.repo.increment_fork_count(template_id)
        return template_id


