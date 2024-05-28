from pathlib import Path
from datetime import datetime

from twitchAPI.twitch import Twitch
from twitchAPI.helper import first
from twitchAPI.type import AuthScope
from twitchAPI.chat import Chat, ChatEvent

from pprint import pprint


class ChatLoggerSession:
    SCOPE = [AuthScope.CHAT_READ]

    def __init__(
        self,
        appID,
        appSecret,
        userID,
        userName,
        accessToken,
        refreshToken,
        channels,
        logDir,
        refreshCallback,
    ):
        self.appID = appID
        self.appSecret = appSecret
        self.userID = userID
        self.userName = userName
        self.accessToken = accessToken
        self.refreshToken = refreshToken
        self.channels = channels
        self.logDir = logDir
        self.refreshCallback = refreshCallback

    async def initialise(self):
        print(f"Initialising logger user: '{self.userName}'")

        self.twitch = await Twitch(self.appID, self.appSecret)
        await self.twitch.set_user_authentication(
            self.accessToken, ChatLoggerSession.SCOPE, self.refreshToken
        )

        self.twitch.user_auth_refresh_callback = self.userAuthRefreshed

        self.chat = await Chat(self.twitch)

        self.chat.register_event(ChatEvent.READY, self.onReady)
        self.chat.register_event(ChatEvent.MESSAGE, self.onMessage)
        self.chat.register_event(ChatEvent.JOIN, self.onJoin)
        self.chat.register_event(ChatEvent.USER_LEFT, self.onLeave)

        self.chat.start()

    async def shutdown(self):
        self.chat.stop()
        await self.twitch.close()

    async def onReady(self, readyEvent):
        print(f"'{self.userName}' joining {self.channels}")

        await self.chat.join_room(self.channels)

    async def onMessage(self, messageEvent):
        # print(
        #     f"Message from '{messageEvent.user.name}' in '{messageEvent.room.name}': '{messageEvent.text}'"
        # )

        self.logEvent(messageEvent.room.name,
                      f"{messageEvent.user.name}: {messageEvent.text}")

    def logEvent(self, channel, event):
        now = datetime.now()

        directory = Path(self.logDir) / \
            f"{channel}" / \
            f"{now.year:04}" / f"{now.month:02}"

        directory.mkdir(parents=True, exist_ok=True)

        fileName = directory / \
            f"{channel}-{now.year:04}-{now.month:02}-{now.day:02}.txt"

        with open(fileName, "a") as log:
            log.write(
                f"{now.hour:02}:{now.minute:02}:{now.second:02} - {event}\n")

    async def onJoin(self, joinEvent):
        print(f"User: '{joinEvent.user_name}' joined '{joinEvent.room.name}")
        self.logEvent(joinEvent.room.name,
                      f"User: '{joinEvent.user_name}' joined")

    async def onLeave(self, leaveEvent):
        print(f"User: '{leaveEvent.user_name}' left '{leaveEvent.room_name}")
        self.logEvent(leaveEvent.room.name,
                      f"User: '{leaveEvent.user_name}' left")

    async def userAuthRefreshed(self, accessToken, refreshToken):
        print(
            f"Chat: User auth refreshed, access: '{accessToken}', refresh: '{refreshToken}'"
        )

        if self.refreshCallback:
            self.refreshCallback(self.userID, accessToken, refreshToken)
