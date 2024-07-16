import signal
import asyncio

import disnake  # noqa
from disnake import Intents

from Bot.Xerox import Xerox
from Database import DBConnector
from Util import Configuration, Logging


async def startup():
    Logging.setup_logging()
    await DBConnector.connect()


async def shutdown():
    await DBConnector.disconnect()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(startup())
    Logging.info("--------------")
    Logging.info("Starting up.")

    intents = Intents(
        guilds=True,
        members=True,
        emojis=True,
        messages=True,
        reactions=True,
        message_content=True,
        moderation=True
    )

    args = {
        "intents": intents,
    }

    xerox = Xerox(**args)
    xerox.run(Configuration.get_master_var("BOT_TOKEN", ""))

    try:
        for sig_name in ("SIGINT", "SIGTERM"):
            loop.add_signal_handler(getattr(signal, sig_name), lambda: asyncio.ensure_future(xerox.close()))
    except Exception:
        pass
    asyncio.run(shutdown())
    loop.close()
