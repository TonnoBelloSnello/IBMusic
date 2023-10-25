import asyncio
import random
import threading
import typing

import nextcord
import validators
import wavelink
from nextcord import ClientException
from nextcord.ext import commands
from nextcord.ext.commands import Context
from wavelink import Node, Track
from wavelink.ext import spotify

from cogs.site.utils import get_cover, convert, prepare_queue
from server import socket
from server import srv


def setup(bot):
    bot.add_cog(music(bot))


async def send_message(ctx: Context):
    em = nextcord.Embed(
        title="New song 🎶",
        description=f"**You are listening** \n{srv[str(ctx.guild.id)]['queue'][0].title}",
        color=nextcord.Color.green()
    )
    try:
        em.set_thumbnail(url=get_cover(url=srv[str(ctx.guild.id)]['queue'][0].uri))
    except AttributeError:
        pass
    srv[str(ctx.guild.id)]["last_message"] = await ctx.send(embed=em)


class music(commands.Cog):
    def __init__(self, bot: nextcord.Client):
        self.bot = bot

    @commands.command(name="connect", aliases=["join", "j"])
    async def connect_command(self, ctx: Context):
        try:
            channel = ctx.author.voice.channel
        except AttributeError:
            await ctx.send("** You are not connected **")
            return None

        try:
            player: wavelink.Player = await channel.connect(cls=wavelink.Player)
        except ClientException:
            player: wavelink.Player = ctx.voice_client

        srv[str(ctx.guild.id)]["player"] = player
        return player

    @commands.command(name="disconnect", aliases=["leave", "d"])
    async def disconnect_command(self, ctx: Context):
        try:
            player: wavelink.Player = ctx.voice_client
            await player.disconnect(force=True)
            srv[str(ctx.guild.id)]['queue'].clear()
            srv[str(ctx.guild.id)]['time_loop'] = False
        except AttributeError:
            return await ctx.send("** The client is not connected **")

    @commands.command(name="play", aliases=["p"])
    async def play_command(self, ctx: Context, *args):
        player = await self.connect_command(ctx)
        if player is None:
            return

        srv[str(ctx.guild.id)]["ctx"] = ctx
        node: Node = wavelink.NodePool.get_node()
        queue: list = srv[str(ctx.guild.id)]["queue"]
        try:
            await player.set_volume(50)
            if validators.url(args[0]):
                query = args[0]
                if args[0].startswith(("https://www.youtube.com/", "https://www.youtu.be/", "https://youtu.be/")):
                    try:
                        tracks: list[Track] = await node.get_tracks(cls=Track, query=query)
                        queue.append(tracks[0])
                    except Exception:
                        tracks: wavelink.YouTubePlaylist = await node.get_playlist(
                            cls=wavelink.YouTubePlaylist, identifier=query
                        )
                        queue.extend(tracks.tracks)
                elif args[0].startswith("https://music.youtube.com/"):
                    try:
                        tracks: list[wavelink.YouTubeMusicTrack] = await node.get_tracks(
                            cls=wavelink.YouTubeMusicTrack, query=query
                        )
                        queue.append(tracks[0])
                    except Exception:
                        tracks: wavelink.YouTubePlaylist = await node.get_playlist(
                            cls=wavelink.YouTubePlaylist, identifier=query
                        )
                        queue.append(tracks.tracks)

                elif args[0].startswith("https://open.spotify.com/"):
                    decoded = spotify.decode_url(args[0])
                    if decoded:
                        if decoded['type'] is spotify.SpotifySearchType.track:
                            tracks = await spotify.SpotifyTrack.search(query=decoded["id"], type=decoded['type'])
                            queue.append(tracks[0])

                        elif decoded["type"] is spotify.SpotifySearchType.playlist:
                            async for partial in spotify.SpotifyTrack.iterator(query=args[0], partial_tracks=True):
                                queue.append(partial)

                        elif decoded["type"] is spotify.SpotifySearchType.album:
                            tracks = await spotify.SpotifyTrack.search(query=args[0])
                            queue.extend(tracks)

                        elif decoded["type"] is spotify.SpotifySearchType.unusable:
                            return await ctx.send("**Not implemented yet**")
                    else:
                        return await ctx.send("**Not implemented yet**")
            else:
                query = "ytsearch:"
                query += "+".join(args)
                tracks = await node.get_tracks(query=query, cls=wavelink.YouTubeTrack)
                queue.append(tracks[0])

            output = prepare_queue(queue)
            if not ctx.voice_client.is_playing():
                await send_message(ctx)
                await player.play(queue[0])

                srv[str(ctx.guild.id)]['time_loop'] = True
                if srv[str(ctx.guild.id)]['thread'] is None:
                    srv[str(ctx.guild.id)]['thread'] = threading.Thread(target=wrapper, args=(ctx.guild.id,))
                    srv[str(ctx.guild.id)]['thread'].start()
                socket.emit("getQueue", {"guild_id": ctx.guild.id, "queue": output}, room=ctx.guild.id)
            else:
                socket.emit("getQueue", {"guild_id": ctx.guild.id, "queue": output}, room=ctx.guild.id)
                return await ctx.send("** Added to queue **")
        except IndexError:
            return await ctx.send("**No song found**")

    @commands.command(name="stop")
    async def stop_command(self, ctx: Context):
        try:
            player: wavelink.Player = ctx.voice_client
            await player.stop()
            socket.emit("songStop", {"guild_id": ctx.guild.id}, room=ctx.guild.id)
            srv[str(ctx.guild.id)]['queue'].clear()
            await ctx.message.add_reaction("🛑")
        except AttributeError:
            return await ctx.send("** The client is not connected **")

    @commands.command(name="queue", aliases=["q"])
    async def queue_command(self, ctx: Context, *, args: typing.Optional[int]):
        description = str()
        queue = srv[str(ctx.guild.id)]['queue']
        if args is None or args < 0:
            args = 0
        if len(queue) == 0:
            return await ctx.send("** Queue is empty **")
        for i in range(args * 10, args * 10 + 10):
            if i < len(queue):
                try:
                    description += f"**{i + 1}.** [{queue[i].title} - {queue[i].author}]({queue[i].uri})\n"
                except AttributeError:
                    description += f"**{i + 1}.** {queue[i].title}\n"

        next_button = nextcord.ui.Button(style=nextcord.ButtonStyle.green, label="Next page", custom_id="next")
        prev_button = nextcord.ui.Button(style=nextcord.ButtonStyle.red, label="Previous page",
                                         custom_id="previous")

        async def previous_callback(interaction: nextcord.Interaction):
            await interaction.response.defer()
            previous_page = args - 1
            if previous_page < 0:
                previous_page = 0
            await self.queue_command(ctx, args=previous_page)

        async def next_callback(interaction: nextcord.Interaction):
            await interaction.response.defer()
            await self.queue_command(ctx, args=args + 1)

        prev_button.callback = previous_callback
        next_button.callback = next_callback

        buttons = [prev_button, next_button]

        em = nextcord.Embed(
            title="Reproductions list 🎸",
            description=description,
            color=nextcord.Color.green()
        )

        view = nextcord.ui.View()
        for button in buttons:
            view.add_item(button)

        return await ctx.send(embed=em, view=view)

    @commands.command(name="skip", aliases=["s", "n", "next"])
    async def skip_command(self, ctx: Context, *, args: typing.Optional[int]):
        try:
            player: wavelink.Player = ctx.voice_client
        except AttributeError:
            return await ctx.send("** The client is not connected **")

        if args is None or args == 0:
            max_skip = 1
        elif args > len(srv[str(ctx.guild.id)]['queue']):
            max_skip = len(srv[str(ctx.guild.id)]['queue'])
        else:
            max_skip = args
        for index in range(max_skip - 1):
            srv[str(ctx.guild.id)]['queue'].pop(0)

        try:
            await player.stop()
        except AttributeError:
            return await ctx.send("** The client is not connected **")

        return await ctx.send(f"**Skipped {max_skip} songs!**")

    @commands.command(name="shuffle")
    async def shuffle(self, ctx: Context):
        try:
            queue: list = srv[str(ctx.guild.id)]['queue']
            first_element = queue[0]
            queue.pop(0)
            random.shuffle(queue)
            queue.insert(0, first_element)

            em = nextcord.Embed(
                title="🔀 Shuffled",
                color=nextcord.Color.green()
            )
            await ctx.message.add_reaction("🔀")
            await ctx.send(embed=em)

        except Exception:
            await ctx.send("📵 The queue is empty")

    @commands.command(name="loop", aliases=["l"])
    async def loop_command(self, ctx: Context):
        srv[str(ctx.guild.id)]["loop"] = not srv[str(ctx.guild.id)]["loop"]
        if srv[str(ctx.guild.id)]["loop"]:
            await ctx.message.add_reaction("🔂")
            return await ctx.send("Loop mode __enabled__ 🔂")
        else:
            await ctx.message.add_reaction("⏭")
            return await ctx.send("Loop mode __disabled__ ⏭")

    @commands.command(name="song", aliases=["np"])
    async def song_command(self, ctx: Context, *url):
        node: Node = wavelink.NodePool.get_node()
        if len(url) > 0:
            em = nextcord.Embed(
                title="Song stats 📈",
                color=nextcord.Color.green()
            )
            if validators.url(url[0]):
                query = url[0]
                result = None
                if url[0].startswith(("https://www.youtube.com/", "https://www.youtu.be/", "https://youtu.be/")):
                    try:
                        tracks: list[Track] = await node.get_tracks(cls=Track, query=query)
                        result = tracks[0]
                    except Exception:
                        return await ctx.send("** Please put a valid song**")
                elif url[0].startswith("https://music.youtube.com/"):
                    try:
                        tracks: list[wavelink.YouTubeMusicTrack] = await node.get_tracks(
                            cls=wavelink.YouTubeMusicTrack,
                            query=query
                        )
                        result = tracks[0]
                    except Exception:
                        return await ctx.send("** Please put a valid song**")
                elif url[0].startswith("https://open.spotify.com/"):
                    decoded = spotify.decode_url(url[0])
                    if decoded and decoded['type'] is spotify.SpotifySearchType.track:
                        tracks = await spotify.SpotifyTrack.search(query=decoded["id"], type=decoded["type"])
                        result = tracks[0]
                    else:
                        return await ctx.send("** Please put a valid song**")
            else:
                query = "ytsearch:"
                query += "+".join(url)
                tracks: list[wavelink.YouTubeMusicTrack] = await node.get_tracks(
                    cls=wavelink.YouTubeMusicTrack,
                    query=query
                )
                result = tracks[0]
            if result is not None:
                thumbnail = get_cover(result.uri)
                em.description = f"**{result.title}** \n" \
                                 f"Duration: **{convert(result.duration)}**\n" \
                                 f"Published by: **{result.author}**\n" \
                                 f"Url: {result.uri}"
                em.set_image(url=thumbnail)
            else:
                em.description = "Did you put a valid song?"
            return await ctx.send(embed=em)
        else:
            player: wavelink.Player = ctx.voice_client
            em = nextcord.Embed(
                title="Song stats 📈",
                color=nextcord.Color.green()
            )
            em.description = f"**{player.track.title}** \n " \
                             f"Duration: **{convert(player.track.duration)}**\n" \
                             f"Published by: **{player.track.author}**\n" \
                             f"Url: {player.track.uri}"
            em.set_image(url=get_cover(player.track.uri))
            return await ctx.send(embed=em)


def wrapper(*args):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_count(args[0]))
    loop.close()


async def start_count(guild_id):
    while True:
        queue = srv.get(str(guild_id)).get('queue')
        output = prepare_queue(queue)
        socket.emit("songStart", {"guild_id": guild_id, "queue": output}, room=guild_id)

        srv[str(guild_id)]['time'] = 0
        socket.emit('getTime', {'time': srv.get(str(guild_id)).get('time')}, room=guild_id)
        while srv[str(guild_id)]['time_loop']:
            while srv[str(guild_id)]['pause']:
                ...

            srv[str(guild_id)]['time'] += 1
            socket.emit('getTime', {'time': srv.get(str(guild_id)).get('time')}, room=guild_id)
            await asyncio.sleep(1)

        srv[str(guild_id)]['time'] = 0
        socket.emit('getTime', {'time': srv.get(str(guild_id)).get('time')}, room=guild_id)
        while not srv[str(guild_id)]['time_loop']:
            ...
