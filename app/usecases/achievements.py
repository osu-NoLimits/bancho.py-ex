from __future__ import annotations

import app.repositories.achievements
from app.repositories.achievements import Achievement
from app.repositories import user_achievements


async def create(
    file: str,
    name: str,
    desc: str,
    cond: str,
) -> Achievement:
    achievement = await app.repositories.achievements.create(
        file,
        name,
        desc,
        cond,
    )
    return achievement


async def fetch_many(
    page: int | None = None,
    page_size: int | None = None,
) -> list[Achievement]:
    achievements = await app.repositories.achievements.fetch_many(
        page,
        page_size,
    )
    return achievements


async def fetch_user_locked(
    user_id: int,
) -> list[Achievement]:
    achievements = await app.repositories.achievements.fetch_user_locked(
        user_id, UserAchievementsTable=user_achievements.UserAchievementsTable
    )
    return achievements
