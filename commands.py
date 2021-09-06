import os

from discord import Client, ChannelType
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_permission, create_option
from discord_slash.model import SlashCommandPermissionType, SlashCommandOptionType


def load_perms(database):
    cursor = database.cursor()
    cursor.execute("SELECT guild_id, target_id, type FROM guild_admins")
    permissions = dict()
    for row in cursor.fetchall():
        if not row[0] in permissions.keys():
            permissions[row[0]] = []
        if row[2] == 'role':
            permissions[row[0]].append(create_permission(row[1], SlashCommandPermissionType.ROLE, True))
        elif row[2] == 'user':
            permissions[row[0]].append(create_permission(row[1], SlashCommandPermissionType.USER, True))

    cursor.execute("SELECT id FROM guilds")
    guilds = []
    for row in cursor.fetchall():
        guilds.append(row[0])
    cursor.close()

    return permissions, guilds


def init(client: Client, database):
    slash = SlashCommand(client, sync_commands=True)

    permissions, guilds = load_perms(database)

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
    async def ticker_enable(ctx: SlashContext, channel=None):
        if channel is None:
            channel = ctx.channel
        else:
            if channel.type != ChannelType.text:
                await ctx.send('*Erreur* : type de canal invalide.')
                return
        cur = database.cursor()
        cur.execute("SELECT count(*) FROM channels WHERE id = '%s' AND guild_id = %s", (channel.id, ctx.guild.id))
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO channels (id, guild_id, ticker) VALUES (%s, %s, TRUE)",
                        (channel.id, ctx.guild.id))
        else:
            cur.execute("SELECT ticker FROM channels WHERE id = %s AND guild_id = %s", (channel.id, ctx.guild.id))
            if cur.fetchone()[0]:
                await ctx.send('Information de tick déjà activé dans <#' + str(channel.id) + '>.')
                return
            cur.execute("UPDATE channels SET ticker = TRUE WHERE id = %s AND guild_id = %s",
                        (channel.id, ctx.guild.id))
        database.commit()
        cur.close()
        await ctx.send('Information de tick activé dans <#' + str(channel.id) + '>.')

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
    async def ticker_disable(ctx: SlashContext, channel=None):
        if channel is None:
            channel = ctx.channel
        else:
            if channel.type != ChannelType.text:
                await ctx.send('Erreur : type de canal invalide.')
                return
        cur = database.cursor()
        cur.execute("SELECT ticker FROM channels WHERE id = %s AND guild_id = %s", (channel.id, ctx.guild.id))
        if not cur.fetchone()[0]:
            await ctx.send('Information de tick déjà désactivé dans <#' + str(channel.id) + '>.')
            return
        cur.execute("UPDATE channels SET ticker = FALSE WHERE id = %s AND guild_id = %s", (channel.id, ctx.guild.id))
        database.commit()
        cur.close()
        await ctx.send('Information de tick désactivé dans <#' + str(channel.id) + '>.')

    client.loop.create_task(slash.sync_all_commands(True, True))

    @slash.slash(name='reload',
                 description='Recharger les permissions.',
                 default_permission=False,
                 permissions={
                     os.getenv('OWNER_GUILDID'): [
                         create_permission(int(os.getenv('OWNER_USERID')), SlashCommandPermissionType.USER, True)
                     ]
                 })
    async def reload(ctx: SlashContext):
        new_permissions, new_guilds = load_perms(database)
        slash.commands.get('ticker').permissions = new_permissions
        slash.commands.get('ticker').guilds = new_guilds
        await ctx.send('Permissions rechargées.')
