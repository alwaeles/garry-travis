import os

from discord import Client, ChannelType, Embed, Colour, User, Message
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_permission, create_option
from discord_slash.model import SlashCommandPermissionType, SlashCommandOptionType


def load_perms(database):
    with database.cursor() as cursor:
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

    return permissions, guilds


class Commands:
    def __init__(self, database):
        self.database = database
        self.permissions, self.guilds = load_perms(database)
        self.slash = None

    def setup(self, client: Client):
        self.slash = SlashCommand(client, sync_commands=True)

        @self.slash.subcommand(base='ticker',
                               guild_ids=self.guilds,
                               base_description='Gérer les informations du tick.',
                               base_default_permission=False,
                               base_permissions=self.permissions,
                               name='enable',
                               description='Activer les informations du tick.',
                               options=[
                                   create_option(name='channel',
                                                 description='Canal écrit sur lequel activer la fonctionnalité.',
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
            with self.database.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM channels WHERE id = '%s' AND guild_id = %s",
                               (channel.id, ctx.guild.id))
                if cursor.fetchone()[0] == 0:
                    cursor.execute("INSERT INTO channels (id, guild_id, ticker) VALUES (%s, %s, TRUE)",
                                   (channel.id, ctx.guild.id))
                else:
                    cursor.execute("SELECT ticker FROM channels WHERE id = %s AND guild_id = %s",
                                   (channel.id, ctx.guild.id))
                    if cursor.fetchone()[0]:
                        await ctx.send('Information de tick déjà activé dans <#' + str(channel.id) + '>.')
                        return
                    cursor.execute("UPDATE channels SET ticker = TRUE WHERE id = %s AND guild_id = %s",
                                   (channel.id, ctx.guild.id))
                self.database.commit()
            await ctx.send('Information de tick activé dans <#' + str(channel.id) + '>.')

        @self.slash.subcommand(base='ticker',
                               guild_ids=self.guilds,
                               base_description='Gérer les informations de tick.',
                               base_default_permission=False,
                               base_permissions=self.permissions,
                               name='disable',
                               description='Désactiver les informations de tick.',
                               options=[
                                   create_option(name='channel',
                                                 description='Canal écrit sur lequel désactiver la fonctionnalité.',
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
            with self.database.cursor() as cursor:
                cursor.execute('SELECT ticker FROM channels WHERE id = %s AND guild_id = %s',
                               (channel.id, ctx.guild.id))
                if not cursor.fetchone()[0]:
                    await ctx.send('Information de tick déjà désactivé dans <#' + str(channel.id) + '>.')
                    return
                cursor.execute('UPDATE channels SET ticker = FALSE WHERE id = %s AND guild_id = %s',
                               (channel.id, ctx.guild.id))
                self.database.commit()
            await ctx.send('Information de tick désactivé dans <#' + str(channel.id) + '>.')

        @self.slash.subcommand(base='config',
                               guild_ids=self.guilds,
                               base_default_permission=True,
                               base_description='Afficher ou changer une configuration.',
                               name='view',
                               description='Afficher la configuration d\'un membre.',
                               options=[
                                   create_option(name='member',
                                                 description='Membre possédant la configuration.',
                                                 option_type=SlashCommandOptionType.USER,
                                                 required=True)
                               ])
        async def config_view(ctx: SlashContext, member: User):
            with self.database.cursor() as cursor:
                cursor.execute('SELECT config_text FROM configs WHERE guild_id = %s AND user_id = %s',
                               (ctx.guild.id, member.id))
                await ctx.send(content='Voici la configuration de <@' + str(member.id) + '>.',
                               embed=Embed(description=cursor.fetchone()[0], colour=Colour.dark_green()))

        @self.slash.subcommand(base='config',
                               guild_ids=self.guilds,
                               name='set',
                               description='Ajouter ou modifier une configuration.')
        async def config_set(ctx: SlashContext):
            with self.database.cursor() as cursor:
                cursor.execute('SELECT count(*) FROM configs WHERE guild_id = %s AND user_id = %s',
                               (ctx.guild.id, ctx.author.id))
                message = await ctx.send('Bonjour <@' + str(ctx.author.id) +
                                         '>, vous pouvez répondre à ce message avec votre configuratiuon pour' +
                                         ' l\'enregistrer.')
                if cursor.fetchone()[0] == 0:
                    cursor.execute('INSERT INTO configs (guild_id, user_id, reply_to) VALUES (%s, %s, %s)',
                                   (ctx.guild.id, ctx.author.id, message.id))
                else:
                    cursor.execute('UPDATE configs SET reply_to = %s WHERE guild_id = %s AND user_id = %s',
                                   (message.id, ctx.guild.id, ctx.author.id))
                self.database.commit()

        @client.event
        async def on_message(m: Message):
            if m.author.id != client.user.id and m.reference is not None:
                with self.database.cursor() as cursor:
                    cursor.execute('SELECT count(*)  FROM configs WHERE reply_to = %s AND user_id = %s',
                                   (m.reference.message_id, m.author.id))
                    if cursor.fetchone()[0] != 0:
                        cursor.execute('UPDATE configs SET reply_to = NULL, config_text = %s' +
                                       ' WHERE reply_to = %s AND user_id = %s',
                                       (m.content, m.reference.message_id, m.author.id))
                    self.database.commit()
                    await m.reply('Configuration prise en compte.')

    async def reload(self):
        if self.slash is None:
            return
        new_permissions, new_guilds = load_perms(self.database)
        self.slash.commands.get('ticker').permissions = new_permissions
        self.slash.commands.get('ticker').guilds = new_guilds
        await self.slash.sync_all_commands(True, True)
