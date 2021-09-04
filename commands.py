import discord
from discord import Client
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_permission, create_option
from discord_slash.model import SlashCommandPermissionType, SlashCommandOptionType


def init(client: Client, database):
    slash = SlashCommand(client, sync_commands=True)

    c = database.cursor()
    c.execute("SELECT guild_id, target_id, type FROM guild_admins")
    permissions = dict()
    for row in c.fetchall():
        if not row[0] in permissions.keys():
            permissions[row[0]] = []
        if row[2] == 'role':
            permissions[row[0]].append(create_permission(row[1], SlashCommandPermissionType.ROLE, True))
        elif row[2] == 'user':
            permissions[row[0]].append(create_permission(row[1], SlashCommandPermissionType.USER, True))

    c.execute("SELECT id FROM guilds")
    guilds = []
    for row in c.fetchall():
        guilds.append(row[0])

    @slash.subcommand(base='ticker',
                      guild_ids=guilds,
                      base_description='Gérer les informations du tick',
                      base_default_permission=False,
                      base_permissions=permissions,
                      name='enable',
                      description='Activer les informations du tick',
                      options=[
                          create_option(name='channel',
                                        description='Canal écrit sur lequel activer la fonctionnalité',
                                        option_type=SlashCommandOptionType.CHANNEL,
                                        required=False)
                      ])
    async def ticker(ctx: SlashContext, channel=None):
        if channel is None:
            channel = ctx.channel
        else:
            if channel.type != discord.ChannelType.text:
                await ctx.send('*Erreur* : type de canal invalide.')
                return
        c.execute("SELECT count(*) FROM channels WHERE id = '%s' AND guild_id = %s", (channel.id, ctx.guild.id))
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO channels (id, guild_id, ticker) VALUES (%s, %s, TRUE)",
                      (channel.id, ctx.guild.id))
        else:
            c.execute("SELECT ticker FROM channels WHERE id = %s AND guild_id = %s", (channel.id, ctx.guild.id))
            if c.fetchone()[0]:
                await ctx.send('Information de tick déjà activé.')
                return
            c.execute("UPDATE channels SET ticker = TRUE WHERE id = %s AND guild_id = %s",
                      (channel.id, ctx.guild.id))
        database.commit()
        await ctx.send('Information de tick activé.')

    @slash.subcommand(base='ticker',
                      guild_ids=guilds,
                      base_description='Gérer les informations de tick',
                      base_default_permission=False,
                      base_permissions=permissions,
                      name='disable',
                      description='Désactiver les informations de tick',
                      options=[
                          create_option(name='channel',
                                        description='Canal écrit sur lequel désactiver la fonctionnalité',
                                        option_type=SlashCommandOptionType.CHANNEL,
                                        required=False)
                      ])
    async def ticker(ctx: SlashContext, channel=None):
        if channel is None:
            channel = ctx.channel
        else:
            if channel.type != discord.ChannelType.text:
                await ctx.send('Erreur : type de canal invalide.')
                return
        c.execute("SELECT ticker FROM channels WHERE id = %s AND guild_id = %s", (channel.id, ctx.guild.id))
        if not c.fetchone()[0]:
            await ctx.send('Information de tick déjà désactivé.')
            return
        c.execute("UPDATE channels SET ticker = FALSE WHERE id = %s AND guild_id = %s", (channel.id, ctx.guild.id))
        database.commit()
        await ctx.send('Information de tick désactivé.')

    client.loop.create_task(slash.sync_all_commands(True, True))
