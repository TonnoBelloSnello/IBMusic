import os

import nextcord
from nextcord.ext import commands
from nextcord.ext.commands import Context


def setup(bot):
    bot.add_cog(FlaskInteraction(bot))


class FlaskInteraction(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.host = os.getenv("ADDRESS")

    @commands.command(name="player", aliases=['manage'])
    async def player_command(self, ctx: Context):
        embed = nextcord.Embed(
            title="Player Management",
            description="Click the link below to manage your player",
            color=0x00ff00
        )
        embed.add_field(name="Link", value=f"{self.host}/{ctx.guild.id}")
        return await ctx.send(embed=embed)