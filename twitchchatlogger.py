#!/usr/bin/env python3

import asyncio
import signal

from pytwitchauthlistener import AuthListener
from twitchAPI.type import AuthScope
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

from appsecrets import TWITCH_CLIENTID, TWITCH_CLIENTSECRET
from Config import Config
from ChatLoggerSession import ChatLoggerSession


class TwitchChatLogger(PatternMatchingEventHandler):
    def __init__(self):
        super().__init__(
            patterns=['config.json'],
            ignore_directories=True)

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

        observer = Observer()

        observer.schedule(self, ".", recursive=True)
        observer.start()

        await self.loadConfig()

        await self.waitFinish()

        await self.auth.shutdown()

        for chat in self.chats:
            await chat.shutdown()

        observer.stop()
        observer.join()

    def on_created(self, event):
        print(f"File '{event.src_path}' created")

        if event.src_path == "./config.json":
            asyncio.run(asyncio.sleep(2))

            asyncio.run(self.loadConfig())

    def on_deleted(self, event):
        print(f"File '{event.src_path}' deleted")

        if event.src_path == "./config.json":
            asyncio.run(asyncio.sleep(2))

            asyncio.run(self.loadConfig())

    def on_modified(self, event):
        print(f"File '{event.src_path}' modified")

        if event.src_path == "./config.json":
            asyncio.run(asyncio.sleep(2))

            asyncio.run(self.loadConfig())

    def findSession(self, userID):
        return next(
            (i for i, item in enumerate(self.chats) if item.userID == userID), None
        )

    async def loadConfig(self):
        config = Config()

        for user in config.config["users"]:
            existingChat = self.findSession(user["userID"])

            if existingChat is not None:
                await self.chats[existingChat].initialise(user["userID"],
                                                          user["login"],
                                                          user["accessToken"],
                                                          user["refreshToken"],
                                                          user["channels"],
                                                          config.config["logdir"],
                                                          )
            else:
                newChat = ChatLoggerSession(
                    TWITCH_CLIENTID,
                    TWITCH_CLIENTSECRET,
                    self.userAuthRefreshed,
                )

                await newChat.initialise(user["userID"],
                                         user["login"],
                                         user["accessToken"],
                                         user["refreshToken"],
                                         user["channels"],
                                         config.config["logdir"],
                                         )

                self.chats.append(newChat)

        removeChats = []

        for chat in self.chats:
            if config.findUser(chat.userID) == None:
                await chat.shutdown()

                removeChats.append(chat.userID)

        self.chats = [
            chat for chat in self.chats if chat.userID not in removeChats
        ]


try:
    twitchChatLogger = TwitchChatLogger()
    asyncio.run(twitchChatLogger.asyncMain())
except asyncio.CancelledError:
    pass
