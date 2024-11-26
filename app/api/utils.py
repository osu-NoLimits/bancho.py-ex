import time
import app
from app.constants.privileges import Privileges
from app.objects.beatmap import Beatmap, ensure_osu_file_is_available
from app.repositories import maps as maps_repo
from pytimeparse.timeparse import timeparse

str_priv_dict = {
    "normal": Privileges.UNRESTRICTED,
    "verified": Privileges.VERIFIED,
    "whitelisted": Privileges.WHITELISTED,
    "supporter": Privileges.SUPPORTER,
    "premium": Privileges.PREMIUM,
    "alumni": Privileges.ALUMNI,
    "tournament": Privileges.TOURNEY_MANAGER,
    "nominator": Privileges.NOMINATOR,
    "mod": Privileges.MODERATOR,
    "admin": Privileges.ADMINISTRATOR,
    "developer": Privileges.DEVELOPER,
}

async def change_bm_status(beatmap_id: int, status: int, frozen: bool) -> str:
    beatmap = await Beatmap.from_bid(beatmap_id)

    if not beatmap:
        return "beatmap not found"

    osu_file_available = await ensure_osu_file_is_available(
        beatmap.id,
        expected_md5=beatmap.md5,
    )
    if not osu_file_available:
        return "osu file not found"
    

    await maps_repo.partial_update(beatmap.id, status=status, frozen=frozen)
    beatmap.status = status
    beatmap.frozen = frozen

    return "success"

async def restrict(id: int, userId: int, reason: str) -> str:

    target = await app.state.sessions.players.from_cache_or_sql(id=id)
    user = await app.state.sessions.players.from_cache_or_sql(id=userId)
    if not target:
        return "user not found"
    
    if target.priv & Privileges.STAFF and not user.priv & Privileges.DEVELOPER:
        return "Only developers can manage staff members."
    
    if target.restricted:
        return "User is already restricted!"
    
    await target.restrict(admin=user, reason=reason)

    if target.is_online:
        target.logout()

    return "success"

async def unrestrict(id: int, userId: int, reason: str) -> str:
    target = await app.state.sessions.players.from_cache_or_sql(id=id)
    user = await app.state.sessions.players.from_cache_or_sql(id=userId)
    if not target:
        return "user not found"
    
    if target.priv & Privileges.STAFF and not user.priv & Privileges.DEVELOPER:
        return "Only developers can manage staff members."
    
    if not target.restricted:
        return "User is not restricted!"
    
    await target.unrestrict(admin=user, reason=reason)

    if target.is_online:
        target.logout()
    
    return "success"

async def alert_all(message: str) -> str:
    app.state.sessions.players.enqueue(app.packets.notification(message))
    return "success"

async def givedonator(id: int, duration: any) -> str:
    target = app.state.sessions.players.from_cache_or_sql(id=id)
    if not target:
        return "user not found"
    
    timespan = timeparse(duration)
    if not timespan:
        return "Invalid timespan."
    
    if target.donor_end < time.time():
        timespan += time.time()
    else:
        timespan += target.donor_end

    target.donor_end = int(timespan)
    
    await app.state.services.database.execute(
        "UPDATE users SET donor_end = :end WHERE id = :user_id",
        {"end": timespan, "user_id": target.id},
    )

    await target.add_privs(Privileges.SUPPORTER)
    return "success"

from typing import List

async def addpriv(id: int, privs: List[str]) -> str:
    bits = Privileges(0)

    for priv in privs:
        if priv not in str_priv_dict:
            return f"Invalid privilege: {priv}"
        bits |= str_priv_dict[priv]

    target = app.state.sessions.players.from_cache_or_sql(id=id)
    if not target:
        return "user not found"
    
    if bits & Privileges.DONATOR != 0:
        return "use givedonor."

    await target.add_privs(bits)
    return "success"

async def removepriv(id: int, privs: List[str]) -> str:
    bits = Privileges(0)

    for priv in privs:
        if priv not in str_priv_dict:
            return f"Invalid privilege: {priv}"
        bits |= str_priv_dict[priv]

    target = app.state.sessions.players.from_cache_or_sql(id=id)
    if not target:
        return "user not found"
    
    if bits & Privileges.DONATOR != 0:
        return "use givedonor."

    await target.remove_privs(bits)
    return "success"
