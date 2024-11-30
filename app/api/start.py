import asyncio
import app.settings
import app.settings
import app.settings
import app.settings
import orjson

import app
from app.logging import log
from app.logging import Ansi
from .utils import *

async def start_pubsub_recievers():
    """Start pubsub recievers."""
    log("Starting pubsub recievers-ex...", Ansi.LGREEN)
    
    asyncio.create_task(channel_rank_receiver())
    asyncio.create_task(channel_restrict_reciever())
    asyncio.create_task(channel_unrestrict_reciever())
    asyncio.create_task(channel_alert_all_reciever())
    asyncio.create_task(channel_givedonator_reciever())
    asyncio.create_task(channel_addpriv_reciever())
    asyncio.create_task(channel_removepriv_reciever())
    asyncio.create_task(channel_wipe_reciever())
    asyncio.create_task(channel_country_change_reciever())
    asyncio.create_task(channel_name_change_reciever())

async def channel_name_change_reciever():
    pubsub = app.state.services.redis.pubsub()
    await pubsub.subscribe("name_change")

    log("Subscribed to 'name_change' channel.", Ansi.LGREEN)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = orjson.loads(message["data"]) 

                id = data["id"]
                name = data["name"]

                log(f"Received message on 'name_change'", Ansi.LBLUE)
                log(f"EX | Name Change | ID: {id}, Name: {name}", Ansi.LBLUE)
                response = await change_user_name(id, name)
                log(f"EX | " + response, Ansi.LBLUE)
    except asyncio.CancelledError:
        log("Channel name_change receiver task cancelled.", Ansi.LYELLOW)
    finally:
        await pubsub.unsubscribe("name_change")
        log("Unsubscribed from 'name_change'.", Ansi.LRED)

async def channel_country_change_reciever():
    pubsub = app.state.services.redis.pubsub()
    await pubsub.subscribe("country_change")

    log("Subscribed to 'country_change' channel.", Ansi.LGREEN)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = orjson.loads(message["data"]) 

                id = data["id"]
                country = data["country"]

                log(f"Received message on 'country_change'", Ansi.LBLUE)
                log(f"EX | Country Change | ID: {id}, Country: {country}", Ansi.LBLUE)
                response = await change_user_flag(id, country)
                log(f"EX | " + response, Ansi.LBLUE)
    except asyncio.CancelledError:
        log("Channel country_change receiver task cancelled.", Ansi.LYELLOW)
    finally:
        await pubsub.unsubscribe("country_change")
        log("Unsubscribed from 'country_change'.", Ansi.LRED)

async def channel_wipe_reciever():
    pubsub = app.state.services.redis.pubsub()
    await pubsub.subscribe("wipe")

    log("Subscribed to 'wipe' channel.", Ansi.LGREEN)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = orjson.loads(message["data"]) 

                id = data["id"]
                mode = data["mode"]

                log(f"Received message on 'wipe'", Ansi.LBLUE)
                log(f"EX | Wipe | ID: {id}, Mode: {mode}", Ansi.LBLUE)
                response = await wipe_user(id, mode)
                log(f"EX | " + response, Ansi.LBLUE)
    except asyncio.CancelledError:
        log("Channel wipe receiver task cancelled.", Ansi.LYELLOW)
    finally:
        await pubsub.unsubscribe("wipe")
        log("Unsubscribed from 'wipe'.", Ansi.LRED)


async def channel_rank_receiver():
    pubsub = app.state.services.redis.pubsub()
    await pubsub.subscribe("rank")

    log("Subscribed to 'rank' channel.", Ansi.LGREEN)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = orjson.loads(message["data"]) 

                beatmap_id = data["beatmap_id"]
                status = data["status"]
                frozen = data["frozen"]

                log(f"Received message on 'rank'", Ansi.LBLUE)
                log(f"EX | Rank | Beatmap ID: {beatmap_id}, Status: {status}, Frozen: {frozen}", Ansi.LBLUE)
                response = await change_bm_status(beatmap_id, status, frozen)
                log(f"EX | " + response, Ansi.LBLUE)
    except asyncio.CancelledError:
        log("Channel rank receiver task cancelled.", Ansi.LYELLOW)
    finally:
        await pubsub.unsubscribe("rank")
        log("Unsubscribed from 'rank'.", Ansi.LRED)

async def channel_restrict_reciever():
    pubsub = app.state.services.redis.pubsub()
    await pubsub.subscribe("restrict")

    log("Subscribed to 'restrict' channel.", Ansi.LGREEN)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = orjson.loads(message["data"]) 

                id = data["id"]
                userId = data["userId"]
                reason = data["reason"]

                log(f"Received message on 'restrict'", Ansi.LBLUE)
                log(f"EX | Restrict | ID: {id}, User ID: {userId}, Reason: {reason}", Ansi.LBLUE)
                response = await restrict(id, userId, reason)
                log(f"EX | " + response, Ansi.LBLUE)
    except asyncio.CancelledError:
        log("Channel restrict receiver task cancelled.", Ansi.LYELLOW)
    finally:
        await pubsub.unsubscribe("restrict")
        log("Unsubscribed from 'restrict'.", Ansi.LRED)

async def channel_unrestrict_reciever():
    pubsub = app.state.services.redis.pubsub()
    await pubsub.subscribe("unrestrict")

    log("Subscribed to 'unrestrict' channel.", Ansi.LGREEN)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = orjson.loads(message["data"]) 

                id = data["id"]
                userId = data["userId"]
                reason = data["reason"]

                log(f"Received message on 'unrestrict'", Ansi.LBLUE)
                log(f"EX | Unrestrict | ID: {id}, User ID: {userId}", Ansi.LBLUE)
                response = await unrestrict(id, userId, reason)
                log(f"EX | " + response, Ansi.LBLUE)
    except asyncio.CancelledError:
        log("Channel unrestrict receiver task cancelled.", Ansi.LYELLOW)
    finally:
        await pubsub.unsubscribe("unrestrict")
        log("Unsubscribed from 'unrestrict'.", Ansi.LRED)

async def channel_alert_all_reciever() -> str:
    pubsub = app.state.services.redis.pubsub()
    await pubsub.subscribe("alert_all")

    log("Subscribed to 'alert_all' channel.", Ansi.LGREEN)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = orjson.loads(message["data"]) 

                message = data["message"]

                log(f"Received message on 'alert_all'", Ansi.LBLUE)
                log(f"EX | Alert All | Message: {message}", Ansi.LBLUE)
                response = await alert_all(message)
                log(f"EX | " + response, Ansi.LBLUE)
    except asyncio.CancelledError:
        log("Channel alert_all receiver task cancelled.", Ansi.LYELLOW)
    finally:
        await pubsub.unsubscribe("alert_all")
        log("Unsubscribed from 'alert_all'.", Ansi.LRED)

async def channel_givedonator_reciever() -> str:
    pubsub = app.state.services.redis.pubsub()
    await pubsub.subscribe("givedonator")

    log("Subscribed to 'givedonator' channel.", Ansi.LGREEN)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = orjson.loads(message["data"]) 

                id = data["id"]
                duration = data["duration"]

                log(f"Received message on 'givedonator'", Ansi.LBLUE)
                log(f"EX | Give Donator | ID: {id}, Duration: {duration}", Ansi.LBLUE)
                response = await givedonator(id, duration)
                log(f"EX | " + response, Ansi.LBLUE)
    except asyncio.CancelledError:
        log("Channel givedonator receiver task cancelled.", Ansi.LYELLOW)
    finally:
        await pubsub.unsubscribe("givedonator")
        log("Unsubscribed from 'givedonator'.", Ansi.LRED)

async def channel_addpriv_reciever():
    pubsub = app.state.services.redis.pubsub()
    await pubsub.subscribe("addpriv")

    log("Subscribed to 'addpriv' channel.", Ansi.LGREEN)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = orjson.loads(message["data"]) 

                id = data["id"]
                privs = data["privs"]

                log(f"Received message on 'addpriv'", Ansi.LBLUE)
                log(f"EX | Add Priv | ID: {id}, Privs: {privs}", Ansi.LBLUE)
                response = await addpriv(id, privs)
                log(f"EX | " + response, Ansi.LBLUE)
    except asyncio.CancelledError:
        log("Channel addpriv receiver task cancelled.", Ansi.LYELLOW)
    finally:
        await pubsub.unsubscribe("addpriv")
        log("Unsubscribed from 'addpriv'.", Ansi.LRED)

async def channel_removepriv_reciever():
    pubsub = app.state.services.redis.pubsub()
    await pubsub.subscribe("removepriv")

    log("Subscribed to 'removepriv' channel.", Ansi.LGREEN)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = orjson.loads(message["data"]) 

                id = data["id"]
                privs = data["privs"]

                log(f"Received message on 'removepriv'", Ansi.LBLUE)
                log(f"EX | Remove Priv | ID: {id}, Privs: {privs}", Ansi.LBLUE)
                response = await removepriv(id, privs)
                log(f"EX | " + response, Ansi.LBLUE)
    except asyncio.CancelledError:
        log("Channel removepriv receiver task cancelled.", Ansi.LYELLOW)
    finally:
        await pubsub.unsubscribe("removepriv")
        log("Unsubscribed from 'removepriv'.", Ansi.LRED)

