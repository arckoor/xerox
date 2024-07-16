import pathlib

import disnake # noqa
from disnake import ApplicationCommandInteraction, Message
from disnake.ext import commands

from Cogs.BaseCog import BaseCog
from Database.DBConnector import db
from prisma.models import ImageMonitor as ImageMonitorModel
from Util import Logging, Utils
from Views import Embed


class ImageMonitor(BaseCog):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)

    async def cog_load(self):
        pathlib.Path("imgs").mkdir(parents=True, exist_ok=True)
        directory = pathlib.Path("imgs")
        for file in directory.iterdir():
            file.unlink(missing_ok=True)

    @commands.slash_command(name="img-mon-config", description="ImageMonitor management", dm_permission=False)
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True, view_channel=True, manage_messages=True, attach_files=True)
    @commands.default_member_permissions(ban_members=True)
    async def img_mon(self, inter: ApplicationCommandInteraction):
        pass

    @img_mon.sub_command(name="template-help", description="ImageMonitor template help.")
    async def help(self, inter: ApplicationCommandInteraction):
        embed = Embed.default_embed(
            title="ImageMonitor help",
            description="Explanation of the template syntax.",
            author=inter.author.name,
            icon_url=inter.author.avatar.url
        )
        embed.add_field(name="Line breaks", value="Line breaks are represented by `\\n`.", inline=False)
        embed.add_field(name="Variables", value="Variables are replaced with their corresponding value.", inline=False)
        embed.add_field(name="{{user}}", value="A user mention, e.g. @user", inline=False)
        await inter.response.send_message(embed=embed)

    @img_mon.sub_command(name="list", description="List the channels being monitored.")
    async def list(
        self,
        inter: ApplicationCommandInteraction
    ):
        monitors = await db.imagemonitor.find_many(
            where={
                "guild": inter.guild_id
            }
        )
        if not monitors:
            await inter.response.send_message("No channels are being monitored.", ephemeral=True)
            return
        embed = Embed.default_embed(
            title="ImageMonitor Watchlist",
            description="List of channels being monitored.",
            author=inter.author.name,
            icon_url=inter.author.avatar.url
        )
        for monitor in monitors:
            from_channel = Utils.coalesce(self.bot.get_channel(monitor.from_channel), Utils.get_alternate_channel(monitor.from_channel))
            to_channel: disnake.abc.GuildChannel = Utils.coalesce(self.bot.get_channel(monitor.to_channel), Utils.get_alternate_channel(monitor.to_channel))
            embed.add_field(
                name=f"From {from_channel.mention} | ID: {monitor.id}",
                value=f"To {to_channel.mention}"
            )
        await inter.response.send_message(embed=embed)

    @img_mon.sub_command(name="add", description="Add a channel to the watchlist.")
    async def add(
        inter: ApplicationCommandInteraction,
        from_channel: disnake.TextChannel = commands.Param(name="from-channel", description="The channel to watch."),
        to_channel: disnake.TextChannel = commands.Param(name="to-channel", description="The channel to send the alert."),
        success_msg: str = commands.Param(name="success-msg", description="The message to send in the from-channel when an image is redirected."),
        limit: int = commands.Param(name="limit", description="The maximum number of images that can be sent at once.", default=1, ge=1)
    ):
        if from_channel.guild.id != inter.guild_id or to_channel.guild.id != inter.guild_id:
            await inter.response.send_message("Both channels must be in this guild.", ephemeral=True)
            return
        if from_channel == to_channel:
            await inter.response.send_message("The channels must be different.", ephemeral=True)
            return

        success_msg = success_msg.replace("\\n", "\n")

        await db.imagemonitor.create(
            data={
                "guild": inter.guild_id,
                "from_channel": from_channel.id,
                "to_channel": to_channel.id,
                "success_msg": success_msg,
                "limit": limit
            }
        )

        await Logging.guild_log(inter.guild_id, f"A new ImageMonitor entry has been added by {inter.user.name} (`{inter.user.id}`) for {from_channel.mention} to {to_channel.mention}.")
        await inter.response.send_message(f"Added {from_channel.mention} to the watchlist. Images will be redirected to {to_channel.mention}.")

    @img_mon.sub_command(name="remove", description="Remove a channel from the watchlist.")
    async def remove(
        inter: ApplicationCommandInteraction,
        id: int = commands.Param(description="The ID of the watchlist entry to remove.")
    ):
        monitor = await db.imagemonitor.find_unique(
            where={
                "id": id
            }
        )
        if not monitor:
            await inter.response.send_message("No entry found with that ID.", ephemeral=True)
            return

        await db.imagemonitor.delete(
            where={
                "id": id
            }
        )
        await Logging.guild_log(inter.guild_id, f"An ImageMonitor entry from `{monitor.from_channel}` to `{monitor.to_channel}` has been removed by {inter.user.name} (`{inter.user.id}`).")
        await inter.response.send_message("Entry removed.")

    @img_mon.sub_command(name="parse-backlog", description="Parse messages sent that the bot didn't catch.")
    @commands.bot_has_permissions(read_message_history=True)
    async def parse_backlog(
        self,
        inter: ApplicationCommandInteraction,
        id: int = commands.Param(description="The ID of the watchlist entry to parse messages for.", default=None),
        limit: int = commands.Param(description="The maximum number of messages to parse.", default=100, ge=1, le=1000)
    ):
        if not id:
            monitor = await db.imagemonitor.find_unique(
                where={
                    "guild": inter.guild_id,
                    "from_channel": inter.channel.id
                }
            )
            if not monitor:
                await inter.response.send_message("You didn't specify a watchlist entry and there is no entry in this channel.", ephemeral=True)
                return
        else:
            monitor = await db.imagemonitor.find_unique(
                where={
                    "id": id
                }
            )
            if not monitor:
                await inter.response.send_message("No entry found with that ID.", ephemeral=True)
                return
        from_channel = self.bot.get_channel(monitor.from_channel)
        if not from_channel:
            await inter.response.send_message("Failed to find the input channel.", ephemeral=True)
            return
        to_channel = self.bot.get_channel(monitor.to_channel)
        if not to_channel:
            await inter.response.send_message("Failed to find the output channel.", ephemeral=True)
            return

        thinking_id = await inter.response.defer(with_message=True)
        total_parsed = 0
        async for message in from_channel.history(limit=limit):
            await self.parse_message(message, monitor, True)
            total_parsed += 1
        reply = f"Processed and redirected {total_parsed} images."
        if not inter.is_expired():
            await inter.followup.send(content=reply)
        else:
            try:
                await thinking_id.delete()
            except Exception:
                pass
            await inter.channel.send(content=reply)

    @commands.Cog.listener()
    @commands.guild_only()
    async def on_message(self, message: Message):
        if message.author.bot:
            return
        monitor = await db.imagemonitor.find_unique(
            where={
                "guild": message.guild.id,
                "from_channel": message.channel.id
            }
        )
        if not monitor:
            return
        await self.parse_message(message, monitor)

    async def parse_message(self, message: Message, monitor: ImageMonitorModel, is_backlog=False):
        if len(message.attachments) == 0:
            return
        if len(message.attachments) > monitor.limit and not is_backlog:
            await message.channel.send(f"{message.author.mention}, you may only send {monitor.limit} image(s) at a time, please try again.")
            await message.delete()
            return
        to_channel = message.guild.get_channel(monitor.to_channel)
        if not to_channel:
            await Logging.error(f"Failed to find channel {monitor.to_channel} in guild {message.guild.id}.")
            await Logging.guild_log(
                message.guild.id,
                f"Failed to find channel {monitor.to_channel} in guild {message.guild.id}."
            )
            return
        for attachment in message.attachments:
            if not attachment.content_type.startswith("image"):
                continue
            await attachment.save(f"imgs/{attachment.filename}")
            with open(f"imgs/{attachment.filename}", "rb") as f:
                msg = await to_channel.send(
                    file=disnake.File(f, attachment.filename),
                    content=f"Sent by {message.author.mention} in {message.channel.mention}. Original message:\n`{message.content if message.content else 'No message content'}`"
                )
                Logging.info(f"An image sent by {message.author.name} ({message.author.id}) in {message.channel.id} has been redirected to {monitor.to_channel}.")
                await Logging.guild_log(
                    message.guild.id,
                    f"An image sent by {message.author.mention} (`{message.author.id}`) in {message.channel.mention} has been redirected to {to_channel.mention} : {msg.jump_url}."
                )
            pathlib.Path(f"imgs/{attachment.filename}").unlink(missing_ok=True)
        await message.delete()
        if is_backlog:
            return
        success_msg = monitor.success_msg.replace("{{user}}", message.author.mention)
        await message.channel.send(success_msg)


def setup(bot: commands.Bot):
    bot.add_cog(ImageMonitor(bot))
