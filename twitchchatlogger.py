#!/usr/bin/env python3

import asyncio
import signal

from pytwitchauthlistener import AuthListener
from twitchAPI.type import AuthScope

from appsecrets import TWITCH_CLIENTID, TWITCH_CLIENTSECRET
from Config import Config
from ChatLoggerSession import ChatLoggerSession


class TwitchChatLogger:
    def __init__(self):
        self.auth = AuthListener(
            TWITCH_CLIENTID,
            TWITCH_CLIENTSECRET,
            [AuthScope.CHAT_READ],
            "https://twitch-chat-logger.gently.org.uk",
            8003,
            self.authReauthCallback,
        )

        signal.signal(signal.SIGINT, self.signalHandler)

        self.finished = False
        self.chats = []

    def signalHandler(self, sig, frame):
        self.finished = True

    async def waitFinish(self):
        while not self.finished:
            await asyncio.sleep(0.1)

    async def authReauthCallback(self, userID, login, accessToken, refreshToken):
        print(
            f"user: '{userID}', login: '{login}', access: '{accessToken}', refresh: '{refreshToken}'"
        )

        config = Config()
        config.addUser(userID, login, accessToken, refreshToken)

    def userAuthRefreshed(self, userID, accessToken, refreshToken):
        print(
            f"Main: User auth refreshed, user: {userID}, acccess: '{accessToken}', refresh: '{refreshToken}'"
        )

        config = Config()
        config.updateUserTokens(userID, accessToken, refreshToken)

    async def asyncMain(self):
        await self.auth.initialise()

        config = Config()

        for user in config.config["users"]:
            newChat = ChatLoggerSession(
                TWITCH_CLIENTID,
                TWITCH_CLIENTSECRET,
                user["userID"],
                user["login"],
                user["accessToken"],
                user["refreshToken"],
                user["channels"],
                config.config["logdir"],
                self.userAuthRefreshed,
            )

            await newChat.initialise()

            self.chats.append(newChat)
        await self.waitFinish()

        await self.auth.shutdown()

        for chat in self.chats:
            await chat.shutdown()


try:
    twitchChatLogger = TwitchChatLogger()
    asyncio.run(twitchChatLogger.asyncMain())
except asyncio.CancelledError:
    pass
