# Standard Library
import asyncio
import itertools
import random

# Russian Roulette
from .kill import outputs

# Red
from redbot.core import Config, bank, commands


__version__ = "3.0.02"
__author__ = "Redjumpman"


def is_administrator():
    """

    Returns true if author has administrator perm or owner/co-owner.
    """
    async def pred(ctx: commands.Context):
        author = ctx.author
        if await ctx.bot.is_owner(author):
            return True
        else:
            return author == ctx.guild.owner or author.guild_permissions.administrator

    return commands.check(pred)


class RussianRoulette:
    defaults = {
        "Cost": 50,
        "Chamber_Size": 6,
        "Wait_Time": 60
        }

    def __init__(self):
        self.db = Config.get_conf(self, 5074395004, force_registration=True)
        self.db.register_guild(**self.defaults)
        self.pot = 0
        self.players = []
        self.active = False

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
        cost = await self.db.guild(ctx.guild).Cost()
        if await self.game_checks(ctx, cost):
            await self.add_player(ctx, cost)

    @commands.command()
    async def russianversion(self, ctx):
        await ctx.send("You are using russian roulette version {}".format(__version__))

    @commands.guild_only()
    @commands.group(autohelp=True)
    async def setrussian(self, ctx):
        """Russian Roulette Settings group."""
        pass

    @setrussian.command()
    @is_administrator()
    async def chamber(self, ctx, size: int):
        """Sets the chamber size of the gun used. MAX: 12."""
        if not 1 < size <= 12:
            return await ctx.send("Invalid chamber size. Must be in the range of 2 - 12.")
        await self.db.guild(ctx.guild).Chamber_Size.set(size)
        await ctx.send("Chamber size set to {}.".format(size))

    @setrussian.command()
    @is_administrator()
    async def cost(self, ctx, amount: int):
        """Sets the required cost to play."""
        if amount < 0:
            return await ctx.send("You are an idiot.")
        await self.db.guild(ctx.guild).Cost.set(amount)
        currency = await bank.get_currency_name(ctx.guild)
        await ctx.send("Required cost to play set to {} {}.".format(amount, currency))

    @setrussian.command()
    @is_administrator()
    async def wait(self, ctx, seconds: int):
        """Set the wait time (seconds) before starting the game."""
        if seconds <= 0:
            return await ctx.send("You are an idiot.")
        await self.db.guild(ctx.guild).Wait_Time.set(seconds)
        await ctx.send("The time before a roulette game starts is now {} seconds.".format(seconds))

    async def game_checks(self, ctx, cost):
        if self.active:
            await ctx.author.send("You cannot join or start a game of russian roulette "
                                  "while one is active.")
            return False

        if ctx.author in self.players:
            await ctx.send("You are already in the roulette circle.")
            return False

        chamber = await self.db.guild(ctx.guild).Chamber_Size()
        if len(self.players) == chamber:
            await ctx.send("The roulette circle is full. Wait for this game to "
                           "finish to join.")
            return False

        try:
            await bank.withdraw_credits(ctx.author, cost)
        except ValueError:
            currency = await bank.get_currency_name(ctx.guild)
            await ctx.send("Insufficient funds! This game requires "
                           "{} {}.".format(cost, currency))
            return False
        else:
            return True

    async def add_player(self, ctx, cost):
        self.pot += cost
        self.players.append(ctx.author)
        chamber = await self.db.guild(ctx.guild).Chamber_Size()

        if len(self.players) == 1:
            await ctx.send("{0.author.mention} is gathering players for a game of russian "
                           "roulette!\nType `{0.prefix}russian` to enter.".format(ctx))
            wait = await self.db.guild(ctx.guild).Wait_Time()
            await asyncio.sleep(wait)
            await self.start_game(ctx)
        else:
            await ctx.send("{} was added to the roulette circle.".format(ctx.author.mention))

    async def start_game(self, ctx):
        self.active = True
        if len(self.players) < 2:
            await bank.deposit_credits(ctx.author, self.pot)
            self.reset_game()
            return await ctx.send("You can't play by youself. That's just suicide.\nGame reset "
                                  "and cost refunded.")
        chamber = await self.db.guild(ctx.guild).Chamber_Size()

        counter = 1
        while len(self.players) > 1:
            await ctx.send("**Round {}**\n*{} spins the cylinder of the gun "
                           "and with a flick of the wrist it locks into "
                           "place.*".format(counter, ctx.bot.user.name))
            await asyncio.sleep(3)
            await self.start_round(ctx, chamber)
            counter += 1
        await self.game_teardown(ctx)

    async def start_round(self, ctx, chamber):
        position = random.randint(1, chamber)
        while True:
            for turn, player in enumerate(itertools.cycle(self.players), 1):
                await ctx.send("{} presses the revolver to their head and slowly squeezes the "
                               "trigger...".format(player.name))
                await asyncio.sleep(5)
                if turn == position:
                    self.players.remove(player)
                    msg = "**BANG!** {0} is now dead.\n"
                    msg += random.choice(outputs)
                    await ctx.send(msg.format(player.mention, random.choice(self.players).name,
                                              ctx.guild.owner))
                    await asyncio.sleep(3)
                    break
                else:
                    await ctx.send("**CLICK!** {} passes the gun along.".format(player.name))
                    await asyncio.sleep(3)
            break

    async def game_teardown(self, ctx):
        winner = self.players.pop()
        currency = await bank.get_currency_name(ctx.guild)
        await bank.deposit_credits(winner, self.pot)
        await ctx.send("Congratulations {}! You are the last person standing and have "
                       "won a total of {} {}.".format(winner.mention, self.pot, currency))
        self.reset_game()

    def reset_game(self):
        self.players = []
        self.pot = 0
        self.active = False
