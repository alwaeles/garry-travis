from discord import Client
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_permission
from discord_slash.model import SlashCommandPermissionType


def init(client: Client, database):
    slash = SlashCommand(client, sync_commands=True)
    c = database.cursor()
    c.execute("SELECT guild_id, role_id FROM guild_admin_roles")
    permissions = dict()
    for row in c.fetchall():
        if not row[0] in permissions.keys():
            permissions[row[0]] = []
        permissions[row[0]].append(create_permission(row[1], SlashCommandPermissionType.ROLE, True))

    print(permissions)

    @slash.subcommand(base='ticker',
                      base_description='Gérer les informations du tick',
                      base_default_permission=False,
                      base_permissions=permissions,
                      name='enable',
                      description='Activer les informations du tick')
    async def ticker(ctx: SlashContext):
        c.execute("SELECT count(*) FROM channels WHERE id = '%s' AND guild_id = %s", (ctx.channel.id, ctx.guild.id))
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO channels (id, guild_id, ticker) VALUES (%s, %s, TRUE)",
                      (ctx.channel.id, ctx.guild.id))
        else:
            c.execute("UPDATE channels SET ticker = TRUE WHERE id = %s AND guild_id = %s",
                      (ctx.channel.id, ctx.guild.id))
        database.commit()
        await ctx.send('Informations du tick activé.')

    @slash.subcommand(base='ticker',
                      base_description='Gérer les informations du tick',
                      base_default_permission=False,
                      base_permissions=permissions,
                      name='disable',
                      description='Désactiver les informations du tick')
    async def ticker(ctx: SlashContext):
        c.execute("UPDATE channels SET ticker = FALSE WHERE id = %s AND guild_id = %s",
                  (ctx.channel.id, ctx.guild.id))
        database.commit()
        await ctx.send('Informations du tick désactivé.')
