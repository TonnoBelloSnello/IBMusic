import os

import nextcord
import wavelink
from nextcord.ext import commands
from wavelink import Node
from wavelink.ext import spotify

from cogs.music import send_message
from server import socket, srv


def setup(bot):
    bot.add_cog(NodeListener(bot))


class NodeListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.loop.create_task(self.load_nodes())

    async def load_nodes(self):
        await self.bot.wait_until_ready()

        await wavelink.NodePool.create_node(
            spotify_client=spotify.SpotifyClient(
                client_id=os.getenv("SPOTIFY_CLIENT_ID"),
                client_secret=os.getenv("SPOTIFY_TOKEN")
            ),
            bot=self.bot,
            host='localhost',
            port=7000,
            password='SeiUnPazzo123',
            identifier="Music-main"
        )

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, node: Node):
        print(node.identifier + " is ready")

    @commands.Cog.listener("on_wavelink_track_end")
    async def on_track_end(self, player: wavelink.Player, track: wavelink.Track, reason):
        print(f"{player.guild.id} has finished the track: {track.title} for the reason: {reason}")
        srv[str(player.guild.id)]['time_loop'] = False
        srv[str(player.guild.id)]['time'] = 0
        socket.emit("songStop", {"guild_id": player.guild.id}, room=player.guild.id)

        if reason == "LOAD_FAILED":
            await srv[str(player.guild.id)]["ctx"].send(embed=nextcord.Embed(
                title="Failed to load",
                description=f"**{track.title}** \n**Has failed to load 😥**",
                color=nextcord.Color.green()
            ))
        queue: list = srv[str(player.guild.id)]['queue']
        if queue and not srv[str(player.guild.id)]["loop"]:
            queue.pop(0)
        if queue:
            await send_message(srv[str(player.guild.id)]["ctx"])
            await player.play(queue[0])
            srv[str(player.guild.id)]['time_loop'] = True

        elif player.is_playing():
            await player.stop()
