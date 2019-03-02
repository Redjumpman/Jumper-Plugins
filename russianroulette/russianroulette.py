# Standard Library
import asyncio
import itertools
import random
import discord

# Russian Roulette
from .kill import outputs

# Red
from redbot.core import Config, bank, checks, commands


__version__ = "3.1.01"
__author__ = "Redjumpman"


class RussianRoulette(commands.Cog):
    defaults = {
        "Cost": 50,
        "Chamber_Size": 6,
        "Wait_Time": 60,
        "Session": {"Pot": 0, "Players": [], "Active": False}
        }

    def __init__(self):
        self.db = Config.get_conf(self, 5074395004, force_registration=True)
        self.db.register_guild(**self.defaults)

    @commands.guild_only()
    @commands.command()
    async def russian(self, ctx):
        """Start or join a game of russian roulette.

        The game will not start if no players have joined. That's just
        suicide.

        The maximum number of players in a circle is determined by the
        size of the chamber. For example, a chamber size of 6 means the
        maximum number of players will be 6.
        """
        settings = await self.db.guild(ctx.guild).all()
        if await self.game_checks(ctx, settings):
            await self.add_player(ctx, settings["Cost"])

    @commands.command()
    async def russianversion(self, ctx):
        await ctx.send("You are using russian roulette version {}".format(__version__))

    @commands.group(autohelp=True)
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def setrussian(self, ctx):
        """Russian Roulette Settings group."""
        pass

    @setrussian.command()
    async def chamber(self, ctx, size: int):
        """Sets the chamber size of the gun used. MAX: 12."""
        if not 1 < size <= 12:
            return await ctx.send("Invalid chamber size. Must be in the range of 2 - 12.")
        await self.db.guild(ctx.guild).Chamber_Size.set(size)
        await ctx.send("Chamber size set to {}.".format(size))

    @setrussian.command()
    async def cost(self, ctx, amount: int):
        """Sets the required cost to play."""
        if amount < 0:
            return await ctx.send("You are an idiot.")
        await self.db.guild(ctx.guild).Cost.set(amount)
        currency = await bank.get_currency_name(ctx.guild)
        await ctx.send("Required cost to play set to {} {}.".format(amount, currency))

    @setrussian.command()
    async def wait(self, ctx, seconds: int):
        """Set the wait time (seconds) before starting the game."""
        if seconds <= 0:
            return await ctx.send("You are an idiot.")
        await self.db.guild(ctx.guild).Wait_Time.set(seconds)
        await ctx.send("The time before a roulette game starts is now {} seconds.".format(seconds))

    async def game_checks(self, ctx, settings):
        if settings["Session"]["Active"]:
            await ctx.author.send("You cannot join or start a game of russian roulette "
                                  "while one is active.")
            return False

        if ctx.author.id in settings["Session"]["Players"]:
            await ctx.send("You are already in the roulette circle.")
            return False

        if len(settings["Session"]["Players"]) == settings["Chamber_Size"]:
            await ctx.send("The roulette circle is full. Wait for this game to "
                           "finish to join.")
            return False

        try:
            await bank.withdraw_credits(ctx.author, settings["Cost"])
        except ValueError:
            currency = await bank.get_currency_name(ctx.guild)
            await ctx.send("Insufficient funds! This game requires "
                           "{} {}.".format(settings["Cost"], currency))
            return False
        else:
            return True

    async def add_player(self, ctx, cost):
        current_pot = await self.db.guild(ctx.guild).Session.Pot()
        await self.db.guild(ctx.guild).Session.Pot.set(value=(current_pot + cost))

        async with self.db.guild(ctx.guild).Session.Players() as players:
            players.append(ctx.author.id)
            num_players = len(players)

        if num_players == 1:
            wait = await self.db.guild(ctx.guild).Wait_Time()
            await ctx.send("{0.author.mention} is gathering players for a game of russian "
                           "roulette!\nType `{0.prefix}russian` to enter. "
                           "The round will start in {1} seconds.".format(ctx, wait))
            await asyncio.sleep(wait)
            await self.start_game(ctx)
        else:
            await ctx.send("{} was added to the roulette circle.".format(ctx.author.mention))

    async def start_game(self, ctx):
        await self.db.guild(ctx.guild).Session.Active.set(True)
        data = await self.db.guild(ctx.guild).Session.all()
        players = [ctx.bot.get_member(player) for player in data["Players"]]
        filtered_players = [player for player in players if isinstance(player, discord.Member)]
        if len(filtered_players) < 2:
            await bank.deposit_credits(ctx.author, data["Pot"])
            await self.reset_game(ctx)
            return await ctx.send("You can't play by youself. That's just suicide.\nGame reset "
                                  "and cost refunded.")
        chamber = await self.db.guild(ctx.guild).Chamber_Size()

        counter = 1
        while len(filtered_players) > 1:
            await ctx.send("**Round {}**\n*{} spins the cylinder of the gun "
                           "and with a flick of the wrist it locks into "
                           "place.*".format(counter, ctx.bot.user.name))
            await asyncio.sleep(3)
            await self.start_round(ctx, chamber, filtered_players)
            counter += 1
        await self.game_teardown(ctx, filtered_players)

    async def start_round(self, ctx, chamber, players):
        position = random.randint(1, chamber)
        while True:
            for turn, player in enumerate(itertools.cycle(players), 1):
                await ctx.send("{} presses the revolver to their head and slowly squeezes the "
                               "trigger...".format(player.name))
                await asyncio.sleep(5)
                if turn == position:
                    players.remove(player)
                    msg = "**BANG!** {0} is now dead.\n"
                    msg += random.choice(outputs)
                    await ctx.send(msg.format(player.mention, random.choice(players).name,
                                              ctx.guild.owner))
                    await asyncio.sleep(3)
                    break
                else:
                    await ctx.send("**CLICK!** {} passes the gun along.".format(player.name))
                    await asyncio.sleep(3)
            break

    async def game_teardown(self, ctx, players):
        winner = players[0]
        currency = await bank.get_currency_name(ctx.guild)
        total = await self.db.guild(ctx.guild).Session.Pot()
        await bank.deposit_credits(winner, total)
        await ctx.send("Congratulations {}! You are the last person standing and have "
                       "won a total of {} {}.".format(winner.mention, total, currency))
        await self.reset_game(ctx)

    async def reset_game(self, ctx):
        await self.db.guild(ctx.guild).Session.clear()
