# Standard Library
import asyncio
import calendar
import logging
import random
import time
from datetime import datetime

# Discord.py
import discord

# Red
from redbot.core import Config, commands
from redbot.core.utils.predicates import MessagePredicate

log = logging.getLogger("red.jumper-plugins.raffle")

__author__ = "Redjumpman"
__version__ = "4.2.7"


class Raffle(commands.Cog):
    """Run simple Raffles for your server."""

    raffle_defaults = {"Channel": None, "Raffles": {}}

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 5074395005, force_registration=True)
        self.config.register_guild(**self.raffle_defaults)
        self.load_check = self.bot.loop.create_task(self.raffle_worker())

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete."""
        return

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

    @raffle.command(hidden=True)
    @commands.is_owner()
    async def clear(self, ctx):
        await self.config.guild(ctx.guild).Raffles.clear()
        await ctx.send("Raffle data cleared out.")

    @raffle.command()
    async def start(self, ctx, timer, *, title: str):
        """Starts a raffle.

        Timer accepts a integer input that represents seconds or it will
        take the format of HH:MM:SS.

        Example timer inputs:
        `80`       = 1 minute and 20 seconds or 80 seconds
        `30:10`    = 30 minutes and 10 seconds
        `24:00:00` = 1 day or 24 hours

        Title should not be longer than 35 characters.
        Only one raffle can be active per server.
        """
        timer = await self.start_checks(ctx, timer, title)
        if timer is None:
            return

        try:
            description, winners, dos, roles = await self.raffle_setup(ctx)
        except asyncio.TimeoutError:
            return await ctx.send("Response timed out. A raffle failed to start.")
        str_roles = [r[0] for r in roles]
        description = f"{description}\n\nReact to this message with \U0001F39F to enter.\n\n"

        channel = await self._get_channel(ctx)
        end = calendar.timegm(ctx.message.created_at.utctimetuple()) + timer
        fmt_end = time.strftime("%a %d %b %Y %H:%M:%S", time.gmtime(end))

        try:
            embed = discord.Embed(
                description=description, title=title, color=self.bot.color
            )  ### old compat, i think ?
        except:
            color = await self.bot.get_embed_color(ctx)
            embed = discord.Embed(description=description, title=title, color=color)  ### new code
        embed.add_field(name="Days on Server", value=f"{dos}")
        role_info = f'{", ".join(str_roles) if roles else "@everyone"}'
        embed.add_field(name="Allowed Roles", value=role_info)
        msg = await channel.send(embed=embed)
        embed.set_footer(
            text=(
                f"Started by: {ctx.author.name} | Winners: {winners} | Ends at {fmt_end} UTC | Raffle ID: {msg.id}"
            )
        )
        await msg.edit(embed=embed)
        await msg.add_reaction("\U0001F39F")

        async with self.config.guild(ctx.guild).Raffles() as r:
            new_raffle = {
                "Channel": channel.id,
                "Timestamp": end,
                "DOS": dos,
                "Roles": roles,
                "ID": msg.id,
                "Title": title,
            }
            r[msg.id] = new_raffle

        await self.raffle_timer(ctx.guild, new_raffle, timer)

    @raffle.command()
    async def end(self, ctx, message_id: int = None):
        """Ends a raffle early. A winner will still be chosen."""
        if message_id is None:
            try:
                message_id = await self._menu(ctx)
            except ValueError:
                return await ctx.send("There are no active raffles to end.")
            except asyncio.TimeoutError:
                return await ctx.send("Response timed out.")

        try:
            await self.raffle_teardown(ctx.guild, message_id)
        except discord.NotFound:
            await ctx.send("The message id provided could not be found.")
        else:
            await ctx.send("The raffle has been ended.")

    @raffle.command()
    async def cancel(self, ctx, message_id: int = None):
        """Cancels an on-going raffle. No winner is chosen."""
        if message_id is None:
            try:
                message_id = await self._menu(ctx, end="cancel")
            except ValueError:
                return await ctx.send("There are no active raffles to cancel.")
            except asyncio.TimeoutError:
                return await ctx.send("Response timed out.")

        try:
            await self.raffle_removal(ctx, message_id)
        except discord.NotFound:
            await ctx.send("The message id provided could not be found.")
        else:
            await ctx.send("The raffle has been canceled.")
        finally:
            # Attempt to cleanup if a message was deleted and it's still stored in config.
            async with self.config.guild(ctx.guild).Raffles() as r:
                try:
                    del r[str(message_id)]
                except KeyError:
                    pass

    async def _menu(self, ctx, end="end"):
        title = f"Which of the following **Active** Raffles would you like to {end}?"
        async with self.config.guild(ctx.guild).Raffles() as r:
            if not r:
                raise ValueError
            raffles = list(r.items())
        try:
            # pre-3.2 compatibility layer
            embed = self.embed_builder(raffles, ctx.bot.color, title)
        except AttributeError:
            color = await self.bot.get_embed_color(ctx)
            embed = self.embed_builder(raffles, color, title)
        msg = await ctx.send(embed=embed)

        def predicate(m):
            if m.channel == ctx.channel and m.author == ctx.author:
                return int(m.content) in range(1, 11)

        resp = await ctx.bot.wait_for("message", timeout=60, check=predicate)
        message_id = raffles[int(resp.content) - 1][0]
        await resp.delete()
        await msg.delete()
        return message_id

    def embed_builder(self, raffles, color, title):
        embeds = []
        # FIXME Come back and make this more dynamic
        truncate = raffles[:10]
        emojis = (
            ":one:",
            ":two:",
            ":three:",
            ":four:",
            ":five:",
            ":six:",
            ":seven:",
            ":eight:",
            ":nine:",
            ":ten:",
        )
        e = discord.Embed(colour=color, title=title)
        description = ""
        for raffle, number_emoji in zip(truncate, emojis):
            description += f"{number_emoji} - {raffle[1]['Title']}\n"
            e.description = description
            e.set_footer(text="Type the number of the raffle you wish to end.")
            embeds.append(e)
        return e

    @raffle.command()
    async def reroll(self, ctx, channel: discord.TextChannel, messageid: int):
        """Reroll the winner for a raffle. Requires the channel and message id."""
        try:
            msg = await channel.get_message(messageid)
        except AttributeError:
            try:
                msg = await channel.fetch_message(messageid)
            except discord.HTTPException:
                return await ctx.send("Invalid message id.")
        except discord.HTTPException:
            return await ctx.send("Invalid message id.")
        try:
            await self.pick_winner(ctx.guild, channel, msg)
        except AttributeError:
            return await ctx.send("This is not a raffle message.")
        except IndexError:
            return await ctx.send(
                "Nice try slim. You can't add a reaction to a random msg "
                "and think that I am stupid enough to say you won something."
            )

    @commands.group(autohelp=True)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def setraffle(self, ctx):
        """Set Raffle group command"""
        pass

    @setraffle.command()
    async def channel(self, ctx, channel: discord.TextChannel = None):
        """Set the output channel for raffles."""
        if channel:
            await self.config.guild(ctx.guild).Channel.set(channel.id)
            return await ctx.send(f"Raffle output channel set to {channel.mention}.")
        await self.config.guild(ctx.guild).Channel.clear()
        await ctx.send("Raffles will now be started where they were created.")

    def cog_unload(self):
        self.__unload()

    def __unload(self):
        self.load_check.cancel()

    async def start_checks(self, ctx, timer, title):
        timer = self.time_converter(timer)
        if len(title) > 35:
            await ctx.send("Title is too long. Must be 35 characters or less.")
            return None
        elif timer is None:
            await ctx.send("Incorrect time format. Please use help on this command for more information.")
            return None
        else:
            return timer

    async def _get_response(self, ctx, question, predicate):
        question = await ctx.send(question)
        resp = await ctx.bot.wait_for(
            "message",
            timeout=60,
            check=lambda m: (m.author == ctx.author and m.channel == ctx.channel and predicate(m)),
        )
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            await resp.delete()
        await question.delete()
        return resp.content

    async def _get_roles(self, ctx):
        q = await ctx.send(
            "What role or roles are allowed to enter? Use commas to separate "
            "multiple entries. For example: `Admin, Patrons, super mod, helper`"
        )

        def predicate(m):
            if m.author == ctx.author and m.channel == ctx.channel:
                given = set(m.content.split(", "))
                guild_roles = {r.name for r in ctx.guild.roles}
                return guild_roles.issuperset(given)
            else:
                return False

        resp = await ctx.bot.wait_for("message", timeout=60, check=predicate)
        roles = []
        for name in resp.content.split(", "):
            for role in ctx.guild.roles:
                if name == role.name:
                    roles.append((name, role.id))
        await q.delete()
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            await resp.delete()
        return roles

    async def _get_channel(self, ctx):
        channel_id = await self.config.guild(ctx.guild).Channel()
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            channel = ctx.channel
        return channel

    async def raffle_setup(self, ctx):
        predicate1 = lambda m: len(m.content) <= 200

        def predicate2(m):
            try:
                if int(m.content) > 9:
                    return False
                if int(m.content) >= 1:
                    return True
                return False
            except ValueError:
                return False

        predicate3 = MessagePredicate.yes_or_no(ctx, ctx.channel, ctx.author)

        def predicate4(m):
            try:
                if int(m.content) >= 0:
                    return True
                return False
            except ValueError:
                return False

        q1 = "Please set a brief description (200 chars max)"
        q2 = (
            "Please set how many winners are pulled, __*Maximum of up to and including 9*__.\n**Note**: If there are "
            "more winners than entries, I will make everyone a winner."
        )
        q3 = "Would you like to set a 'days on server' requirement?"
        q4 = "Do you want to limit this raffle to specific roles?"

        description = await self._get_response(ctx, q1, predicate1)
        winners = await self._get_response(ctx, q2, predicate2)
        dos = 0
        roles = []

        if await self._get_response(ctx, q3, predicate3) == "yes":
            dos = await self._get_response(ctx, "How many days on the server are required?", predicate4)

        if await self._get_response(ctx, q4, predicate3) == "yes":
            roles = await self._get_roles(ctx)

        return description, int(winners), int(dos), roles

    async def raffle_worker(self):
        """Restarts raffle timers
        This worker will attempt to restart raffle timers incase of a cog reload or
        if the bot has been restart or shutdown. The task is only created when the cog
        is loaded, and is destroyed when it has finished.
        """
        try:
            await self.bot.wait_until_red_ready()
            guilds = []
            guilds_in_config = await self.config.all_guilds()
            for guild in guilds_in_config:
                guild_obj = self.bot.get_guild(guild)
                if guild_obj is not None:
                    guilds.append(guild_obj)
                else:
                    continue
            coros = []
            for guild in guilds:
                raffles = await self.config.guild(guild).Raffles.all()
                if raffles:
                    now = calendar.timegm(datetime.utcnow().utctimetuple())
                    for key, value in raffles.items():
                        remaining = raffles[key]["Timestamp"] - now
                        if remaining <= 0:
                            await self.raffle_teardown(guild, raffles[key]["ID"])
                        else:
                            coros.append(self.raffle_timer(guild, raffles[key], remaining))
            await asyncio.gather(*coros)
        except Exception:
            log.error("Error in raffle_worker task.", exc_info=True)

    async def raffle_timer(self, guild, raffle: dict, remaining: int):
        """Helper function for starting the raffle countdown.

        This function will silently pass when the unique raffle id is not found or
        if a raffle is empty. It will call `raffle_teardown` if the ID is still
        current when the sleep call has completed.

        Parameters
        ----------
        guild : Guild
            The guild object
        raffle : dict
            All of the raffle information gained from the config to include:
            ID, channel, message, timestamp, and entries.
        remaining : int
            Number of seconds remaining until the raffle should end
        """
        await asyncio.sleep(remaining)
        async with self.config.guild(guild).Raffles() as r:
            data = r.get(str(raffle["ID"]))
        if data:
            await self.raffle_teardown(guild, raffle["ID"])

    async def raffle_teardown(self, guild, message_id):
        raffles = await self.config.guild(guild).Raffles.all()
        channel = self.bot.get_channel(raffles[str(message_id)]["Channel"])

        errored = False
        try:
            msg = await channel.get_message(raffles[str(message_id)]["ID"])
        except AttributeError:
            try:
                msg = await channel.fetch_message(raffles[str(message_id)]["ID"])
            except discord.NotFound:
                errored = True
        except discord.errors.NotFound:
            errored = True
        if not errored:
            await self.pick_winner(guild, channel, msg)

        async with self.config.guild(guild).Raffles() as r:
            try:
                del r[str(message_id)]
            except KeyError:
                pass

    async def pick_winner(self, guild, channel, msg):
        reaction = next(filter(lambda x: x.emoji == "\U0001F39F", msg.reactions), None)
        if reaction is None:
            return await channel.send(
                "It appears there were no valid entries, so a winner for the raffle could not be picked."
            )
        users = [user for user in await reaction.users().flatten() if guild.get_member(user.id)]
        users.remove(self.bot.user)
        try:
            amt = int(msg.embeds[0].footer.text.split("Winners: ")[1][0])
        except AttributeError:  # the footer was not set in time
            return await channel.send("An error occurred, so a winner for the raffle could not be picked.")
        valid_entries = await self.validate_entries(users, msg)
        winners = random.sample(valid_entries, min(len(valid_entries), amt))
        if not winners:
            await channel.send(
                "It appears there were no valid entries, so a winner for the raffle could not be picked."
            )
        else:
            display = ", ".join(winner.mention for winner in winners)
            await channel.send(f"Congratulations {display}! You have won the {msg.embeds[0].title} raffle!")

    async def validate_entries(self, users, msg):
        dos, roles = msg.embeds[0].fields
        dos = int(dos.value)
        roles = roles.value.split(", ")

        try:
            if dos:
                users = [user for user in users if dos < (user.joined_at.now() - user.joined_at).days]

            if roles:
                users = [user for user in users if any(role in [r.name for r in user.roles] for role in roles)]
        except AttributeError:
            return None
        return users

    async def raffle_removal(self, ctx, message_id):
        async with self.config.guild(ctx.guild).Raffles() as r:
            try:
                del r[str(message_id)]
            except KeyError:
                pass

    @staticmethod
    def time_converter(units):
        try:
            return sum(int(x) * 60 ** i for i, x in enumerate(reversed(units.split(":"))))
        except ValueError:
            return None
