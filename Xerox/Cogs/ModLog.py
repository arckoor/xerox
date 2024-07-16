import io
import zoneinfo

import disnake # noqa
from disnake import ApplicationCommandInteraction
from disnake.ext import commands

from Cogs.BaseCog import BaseCog
from Database.DBConnector import db, get_guild_config


class ModLog(BaseCog):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)

    @commands.slash_command(name="mod-log-config", description="Mod-Log management", dm_permission=False)
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, send_messages=True, view_channel=True)
    @commands.default_member_permissions(ban_members=True)
    async def ml_config(self, inter: ApplicationCommandInteraction):
        pass

    @ml_config.sub_command(name="channel", description="Set the mod-log channel.")
    async def ml_configure_channel(self, inter: ApplicationCommandInteraction, channel: disnake.TextChannel = commands.Param(description="The channel to set as the Mod-Log channel.")):
        perms = channel.permissions_for(inter.guild.me)
        if not perms.view_channel:
            await inter.response.send_message("I don't have permission to view that channel.", ephemeral=True)
            return
        elif not perms.send_messages:
            await inter.response.send_message("I don't have permission to send messages in that channel.", ephemeral=True)
            return
        elif not perms.embed_links:
            await inter.response.send_message("I don't have permission to embed links in that channel.", ephemeral=True)
            return
        _ = await get_guild_config(inter.guild_id)
        await db.guildconfig.update(
            where={
                "guild": inter.guild_id
            },
            data={
                "guild_log": channel.id
            }
        )
        await inter.response.send_message(f"Mod-Log channel set to {channel.mention}.")

    @ml_config.sub_command(name="time-zone", description="Set the time zone for logs")
    async def ml_configure_time_zone(self, inter: ApplicationCommandInteraction, time_zone: str = commands.param(description="The time zone to use for logs.")):
        available_zones = zoneinfo.available_timezones()
        if time_zone not in available_zones:
            out = "\n".join(x for x in (sorted(x for x in available_zones)))
            buffer = io.BytesIO()
            buffer.write(out.encode("utf-8"))
            buffer.seek(0)
            await inter.response.send_message("I don't know this time zone. See the attached file for all valid values.", file=disnake.File(buffer, filename="time-zones.txt"), ephemeral=True)
            return

        _ = await get_guild_config(inter.guild_id)
        await db.guildconfig.update(
            where={
                "guild": inter.guild_id
            },
            data={
                "time_zone": time_zone
            }
        )
        await inter.response.send_message(f"Time zone set to {time_zone}.")


def setup(bot: commands.Bot):
    bot.add_cog(ModLog(bot))
