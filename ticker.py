from discord import Client
import discord
import requests
import datetime


async def check_tick(client: Client, database):
    try:
        r = requests.get(url='https://elitebgs.app/api/ebgs/v5/ticks', timeout=10)
        if r.status_code != 200:
            return
        tick = r.json()[0]
    except requests.Timeout:
        return
    c = database.cursor()
    c.execute("SELECT count(*) FROM last_ticks WHERE id = %s", (tick['_id'],))
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO last_ticks (id) VALUES (%s)", (tick['_id'],))
        database.commit()
        c.execute("SELECT id FROM channels WHERE ticker = TRUE")
        for row in c.fetchall():
            channel = client.get_channel(row[0])
            last_message = await channel.fetch_message(channel.last_message_id)
            if last_message.author.id != client.user.id:
                await channel.send(embed=discord.Embed(description='Tick passé.', colour=discord.Colour.purple()))
