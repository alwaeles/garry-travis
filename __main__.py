import os
import platform
import signal

from discord.ext import tasks
from dotenv import load_dotenv
import discord
import sys
import logging.handlers
import mysql.connector

import utils
import commands
import ticker

logger = logging.getLogger('garry-travis')


def init_loggers():
    logger.setLevel(logging.INFO)

    handler = logging.handlers.SysLogHandler(address='/dev/log')
    logger.addHandler(handler)

    sys.stdout = utils.StreamLogger(logger, logging.DEBUG)
    sys.stderr = utils.StreamLogger(logger, logging.WARNING)


client = discord.Client(intents=discord.Intents.default())
global db
global cmd_inst


@tasks.loop(minutes=15)
async def repeat():
    await ticker.check_tick(client, db)


async def stop_bot():
    await client.change_presence(status=discord.Status.offline)
    await client.close()
    db.close()
    print('Goodbye.')


@client.event
async def on_ready():
    if not repeat.is_running():
        repeat.start()
    cmd_inst.setup(client)
    await client.change_presence(status=discord.Status.online, activity=discord.Game(name='Version 0.3.1'))
    print('Ready!')


if __name__ == '__main__':
    if platform.system() == 'Linux':
        init_loggers()
        load_dotenv('/etc/garry-travis/.env')
    load_dotenv()
    db = mysql.connector.connect(host=os.getenv('DATABASE_HOST'),
                                 port=os.getenv('DATABASE_PORT'),
                                 user=os.getenv('DATABASE_USER'),
                                 password=os.getenv('DATABASE_PASSWORD'),
                                 database=os.getenv('DATABASE_NAME'))
    cmd_inst = commands.Commands(db)
    if platform.system() == 'Linux':
        client.loop.add_signal_handler(signal.SIGINT, lambda: client.loop.create_task(stop_bot()))
        client.loop.add_signal_handler(signal.SIGTERM, lambda: client.loop.create_task(stop_bot()))
        client.loop.add_signal_handler(signal.SIGHUP, lambda: client.loop.create_task(cmd_inst.reload()))
    client.run(os.getenv('DISCORD_KEY'))
