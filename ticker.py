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
    database.commit()
    cursor = database.cursor()
    cursor.execute("SELECT count(*) FROM last_ticks WHERE id = %s", (tick['_id'],))
    dat = cursor.fetchone()[0]
    if dat == 0:
        cursor.execute("INSERT INTO last_ticks (id) VALUES (%s)", (tick['_id'],))
        database.commit()
        cursor.execute("SELECT id FROM channels WHERE ticker = TRUE")
        for row in cursor.fetchall():
            channel = client.get_channel(row[0])
            if channel.last_message_id is None or (await channel.fetch_message(channel.last_message_id)).author.id != client.user.id:
                await channel.send(embed=discord.Embed(description='Tick passé.', colour=discord.Colour.purple()))
    cursor.close()
