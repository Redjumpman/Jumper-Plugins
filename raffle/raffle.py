# Standard Library
import asyncio
import calendar
import logging
import random
import time
import uuid
from datetime import datetime

# Discord.py
import discord

# Red
from redbot.core import Config, commands

log = logging.getLogger("red.raffle")

__author__ = 'Redjumpman'
__version__ = '4.0.02'


class Raffle:
    """Run simple Raffles for your server."""

    raffle_defaults = {
        "DOS": None,
        "Role": None,
        "Channel": None,
        "Raffle": {}
    }

    def __init__(self, bot):
        self.bot = bot
        self.db = Config.get_conf(self, 5074395005, force_registration=True)
        self.db.register_guild(**self.raffle_defaults)
        self.load_check = self.bot.loop.create_task(self.raffle_worker())

    @commands.group(autohelp=True)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def raffle(self, ctx):
        """Raffle group command"""
        pass

    @raffle.command()
    async def version(self, ctx):
        """Displays the currently installed version of raffle."""
        await ctx.send(f"You are running raffle version {__version__}")

    @raffle.command()
    async def start(self, ctx, timer, *, title: str):
        """Starts a raffle.

        Timer accepts a integer input that represents seconds or it will
        take the format of HH:MM:SS. For example:

        80       - 1 minute and 20 seconds or 80 seconds
        30:10    - 30 minutes and 10 seconds
        24:00:00 - 1 day or 24 hours

        Title should not be longer than 35 characters.
        Only one raffle can be active per server.
        """
        timer = await self.start_checks(ctx, timer, title)
        if timer is None:
            return
        try:
            info, winners = await self.start_questions(ctx)
        except asyncio.TimeoutError:
            return await ctx.send("Response timed out. A raffle failed to start.")
        dos = await self.db.guild(ctx.guild).DOS()
        role = await self.db.guild(ctx.guild).Role()
        description = (f'{info}\n\nReact to this '
                       f'message with \U0001F39F to enter.\n\n'
                       f'Role Required: **{role}**\n'
                       f'Days on Server Required: **{dos}**')

        channel_id = await self.db.guild(ctx.guild).Channel()
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            channel = ctx.channel
        end = calendar.timegm(ctx.message.created_at.utctimetuple()) + timer
        fmt_end = time.strftime("%a %d %b %Y %H:%M:%S", time.gmtime(end))
        embed = discord.Embed(description=description, title=title, color=0x50bdfe)
        embed.set_footer(text=f'Started by {ctx.author.name} | Winners: {winners} | Ends at {fmt_end} UTC')
        msg = await channel.send(embed=embed)
        await msg.add_reaction('\U0001F39F')
        async with self.db.guild(ctx.guild).Raffle() as raff:
            raff["ID"] = str(uuid.uuid4())[:12]
            raff["Channel"] = channel.id
            raff["Message"] = msg.id
            raff["Timestamp"] = end
        await self.raffle_timer(ctx.guild, raff, timer)

    @raffle.command()
    async def end(self, ctx):
        """Ends a raffle early. A winner will still be chosen."""
        if not await self.db.guild(ctx.guild).Raffle():
            return await ctx.send("There isn't an active raffle to end.")
        try:
            await self.raffle_teardown(ctx.guild)
        except discord.NotFound:
            pass

    @raffle.command()
    async def cancel(self, ctx):
        """Cancels an on-going raffle. No winner is chosen."""
        if not await self.db.guild(ctx.guild).Raffle():
            return await ctx.send("There isn't an active raffle to cancel.")

        try:
            await self.raffle_removal(ctx)
        except discord.NotFound:
            pass

        await self.db.guild(ctx.guild).Raffle.clear()
        await ctx.send("The ongoing Raffle has been canceled.")

    @raffle.command()
    async def reroll(self, ctx, channel: discord.TextChannel, messageid: int):
        """Reroll the winner for a raffle. Requires the channel and message id."""
        try:
            msg = await channel.get_message(messageid)
        except discord.HTTPException:
            return await ctx.send("Invalid message id.")
        try:
            await self.pick_winner(ctx.guild, channel, msg)
        except AttributeError:
            return await ctx.send("This is not a raffle message.")
        except IndexError:
            return await ctx.send("Nice try slim. You can't add a reaction to a random msg and think that I am "
                                  "stupid enough to say you won something.")

    @commands.group(autohelp=True)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def setraffle(self, ctx):
        """Set Raffle group command"""
        pass

    @setraffle.command()
    async def dos(self, ctx, days: int = None):
        """Set the days on server required to enter. Leave blank for none."""
        if not days:
            await self.db.guild(ctx.guild).DOS.clear()
            await ctx.send("DOS requirement for entering a raffle was disabled.")
        elif days < 0:
            await ctx.send("You can't do that.")
        else:
            await self.db.guild(ctx.guild).DOS.set(days)
            await ctx.send(f"Users must have {days} days on the server to enter a raffle.")
        

    @setraffle.command()
    async def channel(self, ctx, channel: discord.TextChannel = None):
        """Set the output channel for raffles."""
        if channel:
            await self.db.guild(ctx.guild).Channel.set(channel.id)
            return await ctx.send(f"Raffle output channel set to {channel.mention}.")
        await self.db.guild(ctx.guild).Channel.clear()
        await ctx.send("Raffles will now be started where they were created.")

    @setraffle.command()
    async def role(self, ctx, role: discord.Role = None):
        """Set the role required to join. Leave blank for none."""
        if role:
            await self.db.guild(ctx.guild).Role.set(role.name)
            return await ctx.send(f"{role.name} role is now required to enter a raffle.")
        await self.db.guild(ctx.guild).Role.clear()
        await ctx.send("Role requirement for entering a raffle was removed.")

    def __unload(self):
        self.load_check.cancel()

    async def start_checks(self, ctx, timer, title):
        timer = self.time_converter(timer)
        if len(title) > 35:
            await ctx.send("Title is too long. Must be 35 characters or less.")
            return None
        elif await self.db.guild(ctx.guild).Raffle():
            await ctx.send("A raffle is already in progress. End or cancel the "
                           "current one to start a new raffle.")
            return None
        elif timer is None:
            await ctx.send("Incorrect time format. Please use help on this command "
                           "for more information.")
            return None
        else:
            return timer

    async def start_questions(self, ctx):
        q1 = await ctx.send("Please set a brief description (200 chars max)")
        resp1 = await ctx.bot.wait_for('message', timeout=60,
                                       check=lambda m: m.author == ctx.author and len(m.content) < 200)
        info = resp1.content
        await resp1.delete()
        await q1.delete()
        q2 = await ctx.send("Please set how many winners are pulled. Must be in the range of 1-6.\nNote: If there are "
                            "more winners than entries, I will make everyone a winner.")
        resp2 = await ctx.bot.wait_for('message', timeout=30,
                                       check=lambda m: (m.author == ctx.author
                                                        and m.content.isdigit()
                                                        and 0 < int(m.content) <= 6))
        winners = int(resp2.content)
        await q2.delete()
        await  resp2.delete()
        return info, winners

    async def raffle_worker(self):
        """Restarts raffle timers
        This worker will attempt to restart raffle timers incase of a cog reload or
        if the bot has been restart or shutdown. The task is only created when the cog
        is loaded, and is destroyed when it has finished.
        """
        await self.bot.wait_until_ready()
        guilds = [self.bot.get_guild(guild) for guild in await self.db.all_guilds()]
        coros = []
        for guild in guilds:
            if await self.db.guild(guild).Raffle():
                now = calendar.timegm(datetime.utcnow().utctimetuple())
                raff = await self.db.guild(guild).Raffle.all()
                remaining = raff["Timestamp"] - now
                if remaining <= 0:
                    await self.raffle_teardown(guild)
                else:
                    coros.append(self.raffle_timer(guild, raff, remaining))
        await asyncio.gather(*coros)

    async def raffle_timer(self, guild, raff, remaining):
        """Helper function for starting the raffle countdown.

        This function will silently pass when the unique raffle id is not found or
        if a raffle is empty. It will call `raffle_teardown` if the ID is still
        current when the sleep call has completed.

        Parameters
        ----------
        guild : Guild
            The guild object
        raff : dict
            All of the raffle information gained from the db to include:
            ID, channel, message, timestamp, and entries.
        remaining : int
            Number of seconds remaining until the raffle should end
        """
        await asyncio.sleep(remaining)
        async with self.db.guild(guild).Raffle() as lot:
            cur_id = lot.get('ID', None)
        if cur_id == raff['ID']:
            await self.raffle_teardown(guild)

    async def raffle_teardown(self, guild):
        raff = await self.db.guild(guild).Raffle.all()
        channel = self.bot.get_channel(raff['Channel'])

        try:
            msg = await channel.get_message(raff['Message'])
        except AttributeError:
            return await self.db.guild(guild).Raffle.clear()
        await self.pick_winner(guild, channel, msg)

    async def pick_winner(self, guild, channel, msg):
        reaction = next(filter(lambda x: x.emoji == '\U0001F39F', msg.reactions), None)
        users = await reaction.users().flatten()
        amt = int(msg.embeds[0].footer.text.split('Winners: ')[1][0])
        valid_entries = await self.validate_entries(users, guild)
        winners = random.sample(valid_entries, min(len(valid_entries), amt))
        if not winners:
            await channel.send('It appears there were no valid entries, so a winner '
                               'for the raffle could not be picked.')
        else:
            display = ', '.join(winner.mention for winner in winners)
            await channel.send(f"Congratulations {display}! You have won the raffle!")
        await self.db.guild(guild).Raffle.clear()

    async def validate_entries(self, users, guild):
        dos = await self.db.guild(guild).DOS()
        role = await self.db.guild(guild).Role()
        users.remove(self.bot.user)
        try:
            if dos:
                users = [user for user in users if dos < (user.joined_at.now() - user.joined_at).days]

            if role:
                users = [user for user in users if role in [r.name for r in user.roles]]
        except AttributeError:
            return None
        return users

    async def raffle_removal(self, ctx):
        raff = await self.db.guild(ctx.guild).Raffle.all()
        channel = self.bot.get_channel(id=raff['Channel'])
        if channel is None:
            return
        message = await channel.get_message(raff['Message'])
        await message.delete()

    @staticmethod
    def time_converter(units):
        try:
            return sum(int(x) * 60 ** i for i, x in enumerate(reversed(units.split(":"))))
        except ValueError:
            return None
