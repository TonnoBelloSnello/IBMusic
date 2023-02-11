import wavelink

from cogs.site.discord_utils import User


def get_cover(url: str) -> str:
    import re
    if len(url) > 0:
        exp = r"^.*((youtu.be\/)|(v\/)|(\/u\/\w\/)|(embed\/)|(watch\?))\??v?=?([^#&?]*).*"
        s = re.findall(exp, url)[0][-1]
        return f"https://img.youtube.com/vi/{s}/hqdefault.jpg"


def check_user(user_code: str, guild_id: str, session, srv: dict) -> bool:
    if session.get('token') is None:
        user = User(user_code)
        session['token'] = user.token
    else:
        user = User(None, session.get('token'))

    bot_player: wavelink.Player = srv.get(guild_id)
    if bot_player is None:
        return

    bot_player = bot_player.get('player')
    if bot_player is None:
        return

    bot_guild = bot_player.guild.id
    user_guilds = user.get_guilds()

    for guild in user_guilds:
        if int(guild['id']) == int(guild_id) == int(bot_guild):
            return True
    return False


def convert(seconds: int) -> str:
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60

    return "%d:%02d:%02d" % (hour, minutes, seconds)


def prepare_queue(queue: list) -> list:
    output = []
    for song in queue:
        try:
            output.append({
                "title": song.title,
                "duration": song.duration,
                "url": song.uri,
                "author": song.author,
                "cover": get_cover(url=song.uri),
            })
        except AttributeError:
            output.append({
                "title": song.title,
                "duration": 0,
                "url": None,
                "cover": None,
                "author": "Unknown"
            })
    return output
