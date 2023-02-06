import asyncio
import secrets
import random
import wavelink
from flask import Flask, session
from flask_cors import CORS
from flask_socketio import SocketIO, Namespace, emit, join_room

from cogs.site.utils import check_user, get_cover
from flask_session import Session

srv = {}
logged_users = {}

app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(32)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
CORS(app, resources={r"/*": {"origins": "*"}})

socket = SocketIO(app, manage_session=False, cors_allowed_origins="*")


class SocketNamespace(Namespace):

    def on_connectBotQueue(self, data):

        if data.get('user_code') is None:
            emit('error', {'status': 'error', 'guild_id': data.get('guild_id')})
            return
        join_room(data.get('user_code'))
        guild_id = data.get('guild_id')
        if check_user(data.get('user_code'), guild_id, session, srv):
            if srv.get(guild_id) is None:
                emit('error', {'status': 'error', 'guild_id': guild_id}, room=data.get('user_code'))
                return
            elif srv.get(guild_id).get('queue') is None:
                emit('error', {'status': 'error', 'guild_id': guild_id}, room=data.get('user_code'))
                return

            join_room(int(guild_id))
            logged_users[data.get('user_code')] = guild_id

            queue = srv.get(guild_id).get('queue')
            queue = [{
                "title": song.title,
                "cover": get_cover(song.uri),
                "duration": song.duration,
                'author': song.author,
            } for song in queue]
            emit('connectBot', {
                'status': 'success',
                'guild_id': guild_id,
                'queue': queue
            }, room=data.get('user_code'))

    def on_getQueue(self, data):
        if data.get('user_code') is None:
            return
        guild_id = data.get('guild_id')
        if srv.get(guild_id) is None:
            return

        if logged_users.get(data.get('user_code')) == guild_id:
            queue = srv.get(guild_id).get('queue')
            queue = [{
                "title": song.title,
                "cover": get_cover(song.uri),
                "duration": song.duration,
                'author': song.author,
            } for song in queue]
            emit('getQueue', {'queue': queue}, room=int(guild_id))

    def on_skip(self, data):
        if data.get('user_code') is None:
            return
        guild_id = data.get('guild_id')
        if srv.get(guild_id) is None:
            return

        if logged_users.get(data.get('user_code')) == guild_id:
            player = srv.get(guild_id).get('player')
            asyncio.run(player.stop())

    def on_pause(self, data):
        if data.get('user_code') is None:
            return
        guild_id = data.get('guild_id')
        if srv.get(guild_id) is None:
            return

        if logged_users.get(data.get('user_code')) == guild_id:
            player = srv.get(guild_id).get('player')
            asyncio.run(player.pause())
            srv[str(guild_id)]['pause'] = True
            emit('pause', {'status': 'success', 'guild_id': guild_id}, room=int(guild_id))

    def on_resume(self, data):
        if data.get('user_code') is None:
            return
        guild_id = data.get('guild_id')
        if srv.get(guild_id) is None:
            return

        if logged_users.get(data.get('user_code')) == guild_id:
            player = srv.get(guild_id).get('player')
            try:
                asyncio.run(player.resume())
                srv[str(guild_id)]['pause'] = False
                emit('resume', {'status': 'success', 'guild_id': guild_id}, room=int(guild_id))
            except Exception:
                pass

    def on_play(self, data):
        if not data.get('user_code') or not data.get('index'):
            return
        guild_id = data.get('guild_id')
        if srv.get(guild_id) is None:
            return
        if logged_users.get(data.get('user_code')) == guild_id and not srv[guild_id]['skipping']:

            player: wavelink.Player = srv.get(guild_id).get('player')
            index: int = data.get('index')
            srv.get(guild_id)['time_loop'] = False
            if index > len(srv.get(guild_id).get('queue')) - 1:
                return

            srv[guild_id]['skipping'] = True
            for i in range(index - 1):
                srv.get(guild_id).get('queue').pop(0)

            asyncio.run(player.stop())
            srv.get(guild_id)['time'] = 0
            if srv.get(guild_id).get('pause'):
                srv[str(guild_id)]['pause'] = False

            queue = srv.get(guild_id).get('queue')
            output = [{
                "title": song.title,
                "cover": get_cover(song.uri),
                "duration": song.duration,
                'author': song.author,
            } for song in queue]
            srv[guild_id]['skipping'] = False
            socket.emit('getQueue', {'queue': output}, room=int(guild_id))

    def on_shuffle(self, data):
        if data.get('user_code') is None:
            return
        guild_id = data.get('guild_id')
        if srv.get(guild_id) is None:
            return

        if logged_users.get(data.get('user_code')) == guild_id:
            queue = srv.get(guild_id).get('queue')
            first_element = queue[0]
            queue.pop(0)
            random.shuffle(queue)

            queue.insert(0, first_element)
            srv.get(guild_id)['queue'] = queue
            output = [{
                "title": song.title,
                "cover": get_cover(song.uri),
                "duration": song.duration,
                'author': song.author,
            } for song in queue]
            emit('shuffle', {'status': 'success', 'guild_id': guild_id}, room=int(guild_id))
            emit('getQueue', {'queue': output}, room=int(guild_id))
socket.on_namespace(SocketNamespace(''))
