from __future__ import annotations
 
import asyncio
import re
import time
import traceback
import ipaddress
from ipaddress import IPv4Address, IPv6Address, ip_network
from typing import Optional
 
import app.packets
import app.settings
import app.state
import app.settings
from app import commands
from app.logging import Ansi
from app.logging import log
from app.objects.channel import Channel
from app.objects.player import Player
from app.utils import make_safe_name

NAME = "banchobot"
WHITE_SPACE = re.compile(r"\r?\n")

class BanchoIRCException(Exception):
    """IRC exception."""
 
    def __init__(self, code_error: int, error: str):
        self.code: int = code_error
        self.error: str = error
 
    def __str__(self) -> str:
        return repr(self.error)
 
class IRCClient:
    def __init__(
        self,
        server: IRCServer,
        writer: asyncio.StreamWriter,
    ):
        self.player = None
        self.ping_time = int(time.time())
        self.queue = bytearray()
        self.socket = writer
        self.server = server
        self.player: Player
        self._ip = None 
        self.ip_obj = None
 
    def __repr__(self) -> str:
        if self.player is not None:
            return f"{self.player.name}@{NAME}"
        else:
            return f"UNAUTHORIZED@{NAME}"
 
    def __str__(self) -> str:
        if self.player is not None:
            return f"{self.player.name}@{NAME}"
        else:
            return f"UNAUTHORIZED@{NAME}"
 
    def __or__(self):
        if not self.player:
            return None
        else:
            return self.player
 
    def dequeue(self) -> bytearray:
        buffer = self.queue
        self.queue = bytearray()
        return buffer
 
    async def add_queue(self, message: str) -> None:
            self.socket.write((message + "\r\n").encode())
            await self.socket.drain()
 
    async def send_welcome_msg(self) -> None:
        if self.player is None:
            raise RuntimeError(
                "Attempted to send welcome message to an unauthenticated IRC client.",
            )
        await self.add_queue(
            f":{NAME} 001 {self.player.name} :Welcome to the Internet Relay Network, {self!r}")
        await self.add_queue(
            f":{NAME} 002 :- Your host is {self.socket.get_extra_info('peername')[0]}")
        await self.add_queue(
            f":{NAME} 251 :- There are {len(app.state.sessions.players)} users")
        await self.add_queue(f":{NAME} 375 :- {NAME} Message of the day - ")
        await self.add_queue(
            f":{NAME} 372 {self.player.name} :- Visit {app.settings.DOMAIN}")
        await self.add_queue(f":{NAME} 376 : End of MOTD command")
 
    async def login(self, irc_key: Optional[str] = "") -> Player | None:
        
        player = await Player.from_irc(irc_key)

        log(f"IRC login: {player.name}", Ansi.LCYAN)
 
        if not irc_key:
            raise BanchoIRCException(464, f"PASS :Incorrect password")
 
        if not player:
            raise BanchoIRCException(404, f"PLAYER :Incorrect username")
 
        if player.restricted:
            raise BanchoIRCException(404, f"PLAYER :You can't login in restricted mode")

        player.irc_client = True
 
        
        await player.stats_from_sql_full()
 
        player.geoloc = await app.state.services.fetch_geoloc(self.ip_obj)

        user_data = app.packets.user_presence(player) 

        app.state.sessions.players.append(player)
        app.state.sessions.players.enqueue(user_data)
 
        log(f"{player} logged in from IRC with {self.ip}", Ansi.LCYAN)
 
        return player
 
    async def data_received(self, data: bytes) -> None:
        global cmd
        message = data.decode("utf-8")
        parts, command, args = None, None, None
        try:
            client_data = WHITE_SPACE.split(message.strip())
            for cmd in client_data:
                if not cmd.strip(): 
                    continue
                parts = cmd.split(" ", 1)
                command = parts[0]
                args = parts[1] if len(parts) > 1 else ""
 
                if command == "CAP":
                    continue
 
                if command == "GET":
                    log(f"[WARN]: IRC SERVER GOT GET METHODE FROM ANONYMOUS", Ansi.LYELLOW)
                    continue
 
                if command == "LIST":
                    await self.handler_list(args)
                    continue
 
                if command == "NAMES":
                    await self.handler_names(args)
                    continue
 
                if command == "PASS":
                    player = await self.login(args)
 
                    if player:
                        self.player = player
                        await self.send_welcome_msg()
                        continue
 
                    raise BanchoIRCException(464, f"{command} :Incorrect password")
 
                handler = getattr(self, f"handler_{command.lower()}", None)
                if not handler:
                    raise BanchoIRCException(421, f"{command} :Unknown Command!")
 
                await handler(args)
 
        except ValueError:
            log(f"[ERROR] Malformed command: {cmd!r}", Ansi.LRED)
            traceback.print_exc()
        except TypeError:
            await self.socket.drain()
            return
        except AttributeError as e:
            if "player" in str(e):
                error_msg = f":{NAME} 451 :You must finish logging in first"
                self.socket.write(error_msg.encode())
                log(f"Unauthenticated client tried to send data: {e}", Ansi.LRED)
            else:
                raise
        except BanchoIRCException as e:
            self.socket.write(f":{NAME} {e.code} {e.error}\r\n".encode())
        except Exception as e:
            self.socket.write(f":{NAME} ERROR {repr(e)}".encode())
            traceback.print_exc()

    async def handler_nick(self, args: str) -> None:
        pass
 
    async def handler_topic(self, args: str) -> None:
        if self.player is None:
            raise BanchoIRCException(451, "You have not registered")
        channel_name, *topic_parts = args.split(" :")
        channel = app.state.sessions.channels.get_by_name(channel_name)
 
        if not channel:
            raise BanchoIRCException(403, f"{channel_name} :No such channel")
 
        # GET TOPIC
        if not topic_parts:
            await self.add_queue(f":{NAME} 332 {self.player.name} {channel.name} :{channel.topic}")
        # SET TOPIC
        else:
            if not self.player in channel.moderators:
                raise BanchoIRCException(482, f"{channel.name} :You're not a channel operator")
            channel.topic = " :".join(topic_parts)
            await self.add_queue(f":{self.player.name} TOPIC {channel.name} :{channel.topic}")
 
    async def handler_names(self, args: str) -> None:
        if self.player is None:
            raise BanchoIRCException(451, "You have not registered") 
 
        channel_name = args.strip()
        channel = app.state.sessions.channels.get_by_name(channel_name)
 
        if not channel:
            raise BanchoIRCException(403, f"{channel_name} :No such channel")
 
        if channel not in self.player.channels:
            raise BanchoIRCException(442, f"{channel_name} :You're not in this channel")
 
        members = " ".join([p.name for p in channel.players])
        await self.add_queue(f":{NAME} 353 {self.player.name} = {channel.name} :{members}")
        await self.add_queue(f":{NAME} 366 {self.player.name} {channel.name} :End of NAMES list")
 
    async def handler_ping(self, args: str) -> None:
        if self.player is None:
            raise BanchoIRCException(451, "You have not registered")
        if self.player is not None:
            self.ping_time = int(time.time())
            await self.add_queue(f":{NAME} PONG :{NAME}")
            if self.player.irc_client:
                self.player.last_recv_time = time.time()
 
    async def handler_privmsg(self, args: str) -> None:
        if self.player is None:
            raise BanchoIRCException(451, "PRIVMSG :You must log in first")
 
        recipient, msg = args.split(" ", 1)
        if " " in msg and msg.startswith(":"):
            msg = msg[1:]
        elif msg.startswith(":"):
            msg = msg[1:]

        if msg.startswith("!mp close"):
            log(f"Trying to part channel {recipient}", Ansi.LYELLOW)
            await self.handle_mp_close()

        if recipient.startswith("#") or recipient.startswith("$"):
            channel = app.state.sessions.channels.get_by_name(recipient)
            if not channel:
                raise BanchoIRCException(
                    403,
                    f"{recipient} :Cannot send a message to a non-existing channel",
                )
 
            if channel not in self.player.channels:
                raise BanchoIRCException(
                    404,
                    f"{recipient} :Cannot send message to the channel",
                )
 
            await self.send_message(self.player, recipient, msg)
 
            for client in await self.server.authorized_clients:
                assert client.player is not None
 
                if channel in client.player.channels and client != self:
                    await client.add_queue(
                        f":{self.player.safe_name} PRIVMSG {recipient} :{msg}",
                    )
        else:
            log(f"[IRC] Private message from {self.player.name} to {recipient}: {msg}", Ansi.LMAGENTA)
            await self.send_message(self.player, recipient, msg)
 
            for client in await self.server.authorized_clients:
                assert client.player is not None
 
                if msg.startswith("!mp_make"):
                    await self.handle_mp_make()
 
                if client.player.name == recipient:
                    await client.add_queue(f":{self.player.name} PRIVMSG {recipient} :{msg}")
 
    async def handler_list(self, args: str) -> None:
        if self.player is None:
            raise BanchoIRCException(451, "You have not registered")
        """Send a message with all channels."""
        if self.player is None:
            raise RuntimeError("Unauthenticated client tried to list channels.")
 
        for channel in app.state.sessions.channels:
            if channel.can_read(self.player.priv): 
                await self.add_queue(
                    f":{NAME} 322 {self.player.name} {channel.real_name} "
                    f"{len(channel.players)} :{channel.topic or 'No topic'}"
                )
 
        await self.add_queue(f":{NAME} 323 {self.player.name} :End of LIST")
 
    async def handler_part(self, channel: str) -> None:
        if self.player is None:
            raise BanchoIRCException(451, "You have not registered") 
 
        channel = channel.split(" ")[0]
        chan = app.state.sessions.channels.get_by_name(channel)
 
        if len(chan.players) == 0:
            if chan.name.startswith("#multi_"):
                app.state.sessions.channels.remove(chan)
                log(f"Auto-removed empty channel: {chan.name}", Ansi.LYELLOW)
 
        if not chan:
            raise BanchoIRCException(
                403,
                f"{channel} :No channel named {channel} has been found",
            )
 
        if chan in self.player.channels:
            for client in await self.server.authorized_clients:
                assert client.player is not None
 
                if chan in client.player.channels:
                    await client.add_queue(f":{self.player.name} PART :{chan.name}")
 
            await self.player.leave_channel(chan)
        else:
            raise BanchoIRCException(
                442,
                f"{channel} :You're not on that channel",
            )
 
    async def handle_mp_make(self) -> None:
        """Handle !mp make to create a new match."""
        if not hasattr(self.player, 'match') or not self.player.match:
            raise BanchoIRCException(404, "NOTICE :You're not in a match")
 
        match_id = self.player.match.id
        channel_name = f"#multi_{match_id}"
 
        try:
            await self.handler_join(channel_name)
 
        except BanchoIRCException as e:
            if e.code == 403:
                await self.add_queue(f":{NAME} NOTICE {self.player.name} :❌ Lobby {channel_name} doesn't exist")
                await self.socket.drain()
            else:
                raise
 
    async def handle_mp_close(self) -> None:
        """Handle !mp close to leave and part the match."""
        try:
            if not self.player.match:
                return
 
            match_id = self.player.match.id
            channel_name = f"#multi_{match_id}"

            await self.add_queue(f":{self.player.name} PART {channel_name} :Match closed")

            log(f"[IRC] Sent PART for {channel_name}", Ansi.LYELLOW)
            await self.handler_part(channel_name)
 
            await self.player.leave_match()
 
        except Exception as e:
            log(f"[WARN] MP close failed: {e}", Ansi.LYELLOW)
            await self.socket.drain()
 
    async def handler_join(self, channel: str) -> None:
        if self.player is None:
            raise BanchoIRCException(451, "You have not registered") 
 
        chan = app.state.sessions.channels.get_by_name(channel)
 
        if not chan:
            raise BanchoIRCException(
                403,
                f"{channel} :No channel named {channel} has been found",
            )
        try:
            log(f"Joining channel {channel}", Ansi.LYELLOW)
            if self.player.join_channel(chan):
                for client in await self.server.authorized_clients:
                    assert client.player is not None
    
                    if chan in client.player.channels:
                        await client.add_queue(f":{self.player.name} JOIN :{chan.real_name}")
    
                if chan.topic:
                    await self.add_queue(f"332 {chan.real_name} :{chan.topic}")
                else:
                    await self.add_queue(f"331 {chan.real_name} :No topic is set")
    
                nicks = " ".join([x.name for x in chan.players])
                await self.add_queue(f":{NAME} 353 {self.player.name} = {chan.real_name} :{nicks}")
                await self.add_queue(
                    f":{NAME} 366 {self.player.name} {chan.real_name} :End of NAMES list",
                )
            else:
                raise BanchoIRCException(
                    403,
                    f"{channel} :No channel named {channel} has been found",
                )
        except Exception as e:
            log(f"Error {e}", Ansi.LRED)
        


 
 
    async def handler_user(self, args: str) -> None:
        pass
 
    async def handler_away(self, args: str) -> None:
        pass
 
    async def handler_quit(self, args: str) -> None:
        if self.player is None:
            raise BanchoIRCException(451, "You have not registered")
 
        for chan in self.player.channels:
            for client in await self.server.authorized_clients:
                assert client.player is not None
 
                if chan in client.player.channels:
                    await client.add_queue(f":{self.player.name} QUIT :{args.lstrip(':')}")
 
            if self.player.irc_client:
                await self.player.logout()
                log(f"{self.player} disconnected from IRC", Ansi.YELLOW)
 
        self.socket.close()
        await self.socket.wait_closed()
 
    async def handler_mp(self, channel: str) -> None:
        if self.player is None:
            raise BanchoIRCException(451, "You have not registered") 

        chan = app.state.sessions.channels.get_by_name(channel)
 
        if not chan:
            raise BanchoIRCException(
                403,
                f"{channel} :No channel named {channel} has been found",
            )
 
        if self.player.join_channel(chan):
            for client in await self.server.authorized_clients:
                assert client.player is not None
 
                if chan in client.player.channels:
                    await client.add_queue(f":{self.player.name} JOIN :{chan.get_realname()}")
 
            if chan.topic:
                await self.add_queue(f"332 {chan.get_realname()} :{chan.topic}")
            else:
                await self.add_queue(f"331 {chan.get_realname()} :No topic is set")
 
            nicks = " ".join([x.name for x in chan.players])
            await self.add_queue(f":{NAME} 353 {self.player.name} = {chan.get_realname()} :{nicks}")
            await self.add_queue(
                f":{NAME} 366 {self.player.name} {chan.get_realname()} :End of NAMES list",
            )
        else:
            raise BanchoIRCException(
                403,
                f"{channel} :No channel named {channel} has been found",
            )
 
    async def send_message(self, fro: Player, to: str, message: str) -> int:
        if not self.player: 
            return 451
        if to.startswith("#"):
            channel = app.state.sessions.channels.get_by_name(to)
 
            if not channel:
                return 403
 
            if message.startswith(app.settings.COMMAND_PREFIX):
                cmd = await commands.process_commands(fro, channel, message)
            else:
                cmd = None
 
            if cmd:
                # a command was triggered.
                if not cmd["hidden"]:
                    await channel.send(message, sender=fro)
                    if cmd["resp"] is not None:
                        await channel.send_bot(cmd["resp"])
                else:
                    staff = app.state.sessions.players.staff
                    await channel.send_selective(
                        msg=message,
                        sender=fro,
                        recipients=staff - {fro},
                    )
                    if cmd["resp"] is not None:
                        await channel.send_selective(
                            msg=cmd["resp"],
                            sender=app.state.sessions.bot,
                            recipients=staff | {fro},
                        )
            else:
                await channel.send(message, fro)
                log(
                    f"{fro} @ {channel}: {message}",
                    Ansi.LCYAN,
                    file=".data/logs/chat.log",
                )
        else:
            recipient = await app.state.sessions.players.from_cache_or_sql(
                name=make_safe_name(to),
            )
 
            if not recipient:
                return 401
 
            if recipient.is_bot_client:
                if message.startswith(app.settings.COMMAND_PREFIX):
                    cmd = await commands.process_commands(fro, recipient, message)
                else:
                    cmd = None
 
                if cmd:
                    await recipient.send(message, sender=fro)
 
                    if cmd["resp"] is not None:
                        await fro.send_bot(cmd["resp"])
            else:
                await recipient.send(message, fro)
                log(
                    f"{fro} @ {recipient}: {message}",
                    Ansi.LCYAN,
                    file=".data/logs/chat.log",
                )
 
        return 1
 
    @property
    def ip(self):
        return self._ip
 
    @ip.setter
    def ip(self, value):
        self._ip = value
        try:
            self.ip_obj = ipaddress.IPv4Address(value)
        except ipaddress.AddressValueError:
            try:
                self.ip_obj = ipaddress.IPv6Address(value)
            except ipaddress.AddressValueError:
                self.ip_obj = None
                if app.settings.DEBUG:
                    log(f"Invalid IP format: {value}", Ansi.LRED)
 
 
class IRCServer:
    def __init__(self, port: int, host: str, loop: asyncio.AbstractEventLoop) -> None:
        self.socket_server = None
        self.loop = loop
        self.host = host
        self.port = port
        self.socket_server: asyncio.Server
        self.clients: set[IRCClient] = set()
 
    @property
    async def authorized_clients(self) -> set[IRCClient]:
        return {client for client in self.clients if hasattr(client, "player") and client.player is not None}  # 👈 Sicherer Check
 
    async def bancho_join(self, player: Player, channel: Channel) -> None:
        try:
            for client in await self.authorized_clients:
                assert client.player is not None
 
                if channel in client.player.channels:
                    await client.add_queue(f":{player.name} JOIN {channel.name}")
        except TypeError:
            return
 
    async def bancho_part(self, player: Player, channel: Channel) -> None:
        try:
            for client in await self.authorized_clients:
                assert client.player is not None
 
                if channel in client.player.channels:
                    await client.add_queue(f":{player.name} PART {channel.name}")
        except TypeError:
            return
 
    async def bancho_message(self, fro: str, to: str, message: str) -> None:
        if to.startswith("#"):
            channel = app.state.sessions.channels.get_by_name(to)
            if channel:
                for client in await self.authorized_clients:
                    #  Nur Clients im Channel benachrichtigen
                    if channel in client.player.channels:
                        if client is None:
                            continue
                        await client.add_queue(f":{fro} PRIVMSG {to} :{message}")
                        """ try:
                               for client in self.authorized_clients:
                                   if client is None:
                                       return
                                    assert client.player is not None
                                    fix sometime i guess
                                    if client.player.name != fro and to in [
                                       x.name for x in client.player.channels
                                   ]:
                                   client.add_queue(f":{fro} PRIVMSG {to} :{message}")
                           except TypeError:
                               return"""
        else:
            for client in await self.authorized_clients:
                # assert client.player is not None
                if client is None:
                    continue
                # private message
                if client.player.name == to:
                    await client.add_queue(f":{fro} PRIVMSG {to} :{message}")

    async def callback_handler(
            self,
            reader: asyncio.StreamReader,
            writer: asyncio.StreamWriter,
    ) -> None:
        try:
            peername = writer.get_extra_info("peername")
            client_ip = peername[0] if peername else "0.0.0.0"
 
            client = IRCClient(self, writer)
            client.ip = client_ip
 
            log(f"[IRC] New connection from {client_ip}", Ansi.LGREEN)
 
            self.clients.add(client)
 
            while True:
                if data_to_send := client.dequeue():
                    writer.write(data_to_send)

                data = await reader.read(4096)
                if not data:
                    break
 
                try:
                    await client.data_received(data)
                except BanchoIRCException as e:
                    writer.write(e.error.encode())
                    await writer.drain()
                except Exception as e:
                    log(f"[IRC] Error handling data: {e}", Ansi.LRED)
                    break
 
                if app.settings.DEBUG:
                    sanitized_msg = data.decode("utf-8").replace("\r\n", "; ")
                    log(f"[IRC] Received: {sanitized_msg}", Ansi.LGREEN)
 
                await writer.drain()
 
        except ConnectionResetError:
            log(f"[IRC] Connection reset by {client_ip}", Ansi.LYELLOW)
        except Exception as e:
            log(f"[IRC] Unexpected error: {e}", Ansi.LRED)
        finally:
            try:
                if client in self.clients:
                    self.clients.remove(client)
 
                if not writer.is_closing():
                    writer.close()
                    await writer.wait_closed()
 
                if client.player:
                    await client.player.logout()
                    log_msg = f"{client.player.name} ({client_ip})"
                else:
                    log_msg = f"Anonymous ({client_ip})"
 
                log(f"[IRC] Client disconnected: {log_msg}", Ansi.LYELLOW)
 
            except Exception as e:
                log(f"[IRC] Cleanup error: {e}", Ansi.LRED)
 
    async def start(self) -> IRCServer:
        server = await asyncio.start_server(
                    self.callback_handler,
                    self.host,
                    self.port,
        )
 
        sockname = server.sockets[0].getsockname()
        log(
                    f"Serving IRC on {sockname[0]}:{sockname[1]}",
                    Ansi.LCYAN,
        )
 
        self.socket_server = server
        return self
    
