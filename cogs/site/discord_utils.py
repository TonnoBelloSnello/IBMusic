import json
import requests
import os

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')


class User:
    _discord_api = "https://discord.com/api"

    def __init__(self, code: str, token=None):
        self.token = token
        if token is None:
            self.set_token(code)

    def set_token(self, code: str):
        data = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        response = requests.post("%s/oauth2/token" % self._discord_api, data=data, headers=headers)
        response.raise_for_status()
        self.token = response.json()

    def _request(self, link: str):
        if self.token is None:
            return

        response = requests.get(f"{link}", headers={
            "Authorization": f"Bearer {self.token['access_token']}"
        })
        response.raise_for_status()
        return response.json()

    def get_guilds(self) -> json:
        return self._request("%s/users/@me/guilds" % self._discord_api)

    def get_guild_channel(self, guild_id: int) -> json:
        return self._request(f"%s/guilds/{guild_id}/channels" % self._discord_api)

    def get_user(self) -> json:
        return self._request("%s/users/@me" % self._discord_api)

    def get_connection(self) -> json:
        return self._request("%s/users/@me/connections" % self._discord_api)

    def get_oauth_info(self) -> json:
        return self._request("%s/oauth2/@me" % self._discord_api)
