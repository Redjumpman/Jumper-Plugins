# Developed by Redjumpman for Redbot.
# Inspired by the snail race mini game.
import asyncio
import discord
import random
from redbot.core import Config, bank, commands, checks

from .animals import Animal, racers

__author__ = "Redjumpman"
__version__ = "2.0.01"

guild_defaults = {"Wait": 60,
                  "Mode": "normal",
                  "Prize": 100,
                  "Pooling": False,
                  "Payout_Min": 0,
                  "Bet_Multiplier": 2,
                  "Bet_Min": 10,
                  "Bet_Max": 50,
                  "Bet_Allowed": True}

# First, Second, and Third place wins
member_defaults = {"Wins": {"1": 0, "2": 0, "3": 0}, "Losses": 0}


class Race(commands.Cog):
    """Cog for racing animals"""

    def __init__(self):
        self.db = Config.get_conf(self, 5074395009, force_registration=True)
        self.db.register_guild(**guild_defaults)
        self.db.register_member(**member_defaults)
        self.active = False
        self.started = False
        self.winners = []
        self.players = []
        self.bets = {}

    @commands.group()
    @commands.guild_only()
    async def race(self, ctx):
        """Race related commands"""
        pass

    @race.command()
    async def start(self, ctx):
        """Begins a new race.

        You cannot start a new race until the active on has ended.

        If you are the only player in the race, you will race against
        your bot.

        The user who started the race is automatically entered into the race.
        """
        if self.active:
            return
        self.active = True
        self.players.append(ctx.author)
        wait = await self.db.guild(ctx.guild).Wait()

        await ctx.send(f"🚩 A race has begun! Type {ctx.prefix}race enter "
                       f"to join the race! 🚩\nThe race will begin in "
                       f"{wait} seconds!\n\n**{ctx.author.mention}** entered the race!")
        await asyncio.sleep(wait)
        self.started = True
        await ctx.send("🏁 The race is now in progress. 🏁")
        await self.run_game(ctx)

        settings = await self.db.guild(ctx.guild).all()
        currency = await bank.get_currency_name(ctx.guild)
        msg, embed = self._build_end_screen(settings, currency)
        await ctx.send(content=msg, embed=embed)
        await self._race_teardown(settings)

    @race.command()
    async def bet(self, ctx, bet: int, user: discord.Member):
        """Bet on a user in the race."""
        if not await self.bet_conditions(ctx, bet, user):
            return
        self.bets[user.id] = {"Bets": [(ctx.author, bet)]}
        currency = await bank.get_currency_name(ctx.guild)
        await bank.withdraw_credits(ctx.author, bet)
        await ctx.send(f"{ctx.author.mention} placed a {bet} {currency} bet on {str(user)}.")

    @race.command()
    async def enter(self, ctx):
        """Allows you to enter the race.

        This command will return silently if a race has already started.
        By not repeatedly telling the user that they can't enter the race, this
        prevents spam.

        """
        if self.started:
            return
        elif not self.active:
            return await ctx.send("A race must be started before you can enter.")
        elif ctx.author in self.players:
            return await ctx.send("You have already entered the race.")
        else:
            self.players.append(ctx.author)
            await ctx.send(f"{ctx.author.mention} has joined the race.")

    @race.command(hidden=True)
    async def clear(self, ctx):
        """ONLY USE THIS COMMAND FOR DEBUG PURPOSES

        You shouldn't use this command unless the race is stuck
        or you are debugging."""
        self.clear_local()
        await ctx.send("Race cleared")

    @race.command()
    async def wipe(self, ctx):
        """This command will wipe ALL race data.

        You are given a confirmation dialog when using this command.
        If you decide to wipe your data, all stats and settings will be deleted.
        """
        await ctx.send(f"You are about to clear all race data including stats and settings."
                       "If you are sure you wish to proceed, type `{ctx.prefix}yes`.")
        choices = (f"{ctx.prefix}yes", f"{ctx.prefix}no")
        check = lambda m: (m.author == ctx.author and m.channel == ctx.channel
                           and m.content in choices)
        try:
            choice = await ctx.bot.wait_for("message", timeout=20.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("No response. Race wipe cancelled.")

        if choice.content.lower() == f"{ctx.prefix}yes":
            await self.db.guild(ctx.guild).clear()
            await self.db.clear_all_members(ctx.guild)
            return await ctx.send("Race data has been wiped.")
        else:
            return await ctx.send("Race wipe cancelled.")

    @race.command()
    async def version(self, ctx):
        """Displays the version of race"""
        await ctx.send(f"You are running race version {__version__}.")

    @commands.group()
    @checks.admin_or_permissions(administrator=True)
    async def setrace(self, ctx):
        """Race settings commands"""
        pass

    @setrace.command()
    async def wait(self, ctx, wait: int):
        """Changes the wait time before a race starts.

        This only affects the period where race is still waiting
        for more participants to join the race."""
        if wait < 0:
            return await ctx.send("Really? You're an idiot.")
        await self.db.guild(ctx.guild).Wait.set(wait)
        await ctx.send(f"Wait time before a race begins is now {wait} seconds.")

    @setrace.group(name='bet')
    async def _bet(self, ctx):
        """Bet settings for race"""
        pass

    @_bet.command(name='min')
    async def _min(self, ctx, amount: int):
        """Sets the betting minimum."""
        if amount < 0:
            return await ctx.send("Come on now. Let's be reasonable.")
        maximum = await self.db.guild(ctx.guild).Bet_Max()
        if amount > maximum:
            return await ctx.send(f"Minimum must be lower than the set max of {maximum}.")

        await self.db.guild(ctx.guild).Bet_Min.set(amount)
        await ctx.send(f"Minimum bet amount set to {amount}.")

    @_bet.command(name='max')
    async def _max(self, ctx, amount: int):
        """Sets the betting minimum."""
        if amount < 0:
            return await ctx.send("Come on now. Let's be reasonable.")
        minimum = await self.db.guild(ctx.guild).Bet_Min()
        if amount < minimum:
            return await ctx.send(f"Maximum must be higher than the set min of {minimum}.")

        await self.db.guild(ctx.guild).Bet_Max.set(amount)
        await ctx.send(f"Maximum bet amount set to {amount}.")

    @_bet.command()
    async def multiplier(self, ctx, multiplier: float):
        """Sets the betting minimum."""
        if multiplier < 0:
            return await ctx.send("So... you want them to lose money...when they win."
                                  "I'm not doing that.")
        if multiplier == 0:
            return await ctx.send("That means they win nothing. Just turn off betting.")

        await self.db.guild(ctx.guild).Bet_Multiplier.set(multiplier)
        await ctx.send(f"Betting multiplier set to {multiplier}.")

    @_bet.command()
    async def toggle(self, ctx):
        """Toggles betting on and off."""
        current = await self.db.guild(ctx.guild).Bet_Min()
        await self.db.guild(ctx.guild).Bet_Allowed.set(not current)
        await ctx.send(f"Betting is now {'OFF' if current else 'ON'}.")

    @setrace.command()
    async def mode(self, ctx, mode):
        """Changes the race mode

        Race can either be in normal mode or zoo mode.

        Normal Mode:
            All racers are turtles.

        Zoo Mode:
            Racers are randomly selected from a list of animals with
            different attributes.
        """
        if mode.lower() not in ('zoo', 'normal'):
            return await ctx.send("Must select either `zoo` or `normal` as a mode.")

        await self.db.guild(ctx.guild).Mode.set(mode.lower())
        await ctx.send(f"Mode changed to {mode.lower()}")

    @setrace.command()
    async def prize(self, ctx, prize: int):
        """Sets the prize pool for winners.

        Set the prize to 0 if you do not wish any credits to be distributed.

        When prize pooling is enabled (see `setrace pool`) the prize will be
        distributed as follows:
            1st place 60%
            2nd place 30%
            3rd place 10%.

        Example:
            100 results in 60, 30, 10
            130 results in 78, 39, 13

        When prize pooling is disabled, only first place will win, and they take
        100% of the winnings.
        """
        if prize < 0:
            return await ctx.send("... that's not how prizes work buddy.")

        if prize == 0:
            return await ctx.send("No prizes will be awarded to the winners.")
        else:
            currency = await bank.get_currency_name(ctx.guild)
            await self.db.guild(ctx.guild).Prize.set(prize)
            await ctx.send(f"Prize set for {prize} {currency}.")

    @setrace.command(name='togglepool')
    async def _tooglepool(self, ctx):
        """Toggles on/off prize pooling.

        Makes it so that prizes are pooled between 1st, 2nd, and 3rd.
        It's a 60/30/10 split rounded to the nearest whole number.

        There must be at least four human players, otherwise, only first
        place wins.
        """
        pool = await self.db.guild(ctx.guild).Pooling()
        await self.db.guild(ctx.guild).Pooling.set(not pool)
        await ctx.send(f"Prize pooling is now {'OFF' if pool else 'ON'}.")

    @setrace.command()
    async def payoutmin(self, ctx, players: int):
        """Sets the number of players needed to payout prizes and bets.

        This sets the required number of players needed to payout prizes.
        If the number of racers aren't met, then nothing is paid out.

        If you want race to always pay out, then set players to 0.
        """
        if players < 0:
            return await ctx.send("I don't have time for this shit.")
        await self.db.guild(ctx.guild).Payout_Min.set(players)
        if players == 0:
            await ctx.send("Races will now always payout.")
        else:
            await ctx.send(f"Races will only payout if there are {players} human players.")

    async def stats_update(self):
        for player in self.players:
            if player in self.winners:
                position = self.winners.index(player) + 1
                current = await self.db.member(player).Wins.get_raw(str(position))
                await self.db.member(player).Wins.set_raw(str(position), value=current+1)
            else:
                current = await self.db.member(player).Losses()
                await self.db.member(player).Losses.set(current+1)

    async def _race_teardown(self, settings):
        await self.stats_update()
        await self.distribute_prizes(settings)
        await self.bet_payouts(settings)
        self.clear_local()

    def clear_local(self):
        self.players.clear()
        self.winners.clear()
        self.bets.clear()
        self.active = False
        self.started = False

    async def distribute_prizes(self, settings):
        if settings["Prize"] == 0 or (settings["Payout_Min"] >= len(self.players)):
            return

        if settings["Pooling"] and len(self.players) > 3:
            for winner, _ in self.winners:
                if winner.bot:
                    continue
                await bank.deposit_credits(winner, settings["Prize"])
        else:
            await bank.deposit_credits(self.winners[0][0], settings["Prize"])

    async def bet_payouts(self, settings):
        if not self.bets or not settings["Bet_Allowed"]:
            return
        multiplier = settings["Bet_Multiplier"]
        first = self.winners[0]
        for user, wagers in self.bets.items():
            for jockey, bet in wagers["Bets"]:
                if jockey == first:
                    await bank.deposit_credits(user, (bet * multiplier))

    async def bet_conditions(self, ctx, bet, user):
        if not self.active:
            await ctx.send("There isn't a race right now.")
            return False
        elif self.started:
            await ctx.author.send("You can't place a bet after the race has started.")
            return False
        elif user not in self.players:
            await ctx.send("You can't bet on someone who isn't in the race.")
            return False
        elif ctx.author.id in self.bets:
            await ctx.send("You have already entered a bet for the race.")
            return False

        # Separated the logic such that calls to config only happen if the statements
        # above pass.
        data = await self.db.guild(ctx.guild).all()
        allowed = data["Bet_Allowed"]
        minimum = data["Bet_Min"]
        maximum = data["Bet_Max"]

        if not allowed:
            await ctx.send("Betting has been turned off.")
            return False
        elif minimum <= bet <= maximum:
            return True
        else:
            await ctx.send(f"Bet must not be lower than {minimum} or higher than {maximum}.")
            return False

    def _build_end_screen(self, settings, currency):
        if len(self.winners) == 3:
            first, second, third = self.winners
        else:
            first, second, = self.winners
            third = None
        payout_msg = self._payout_msg(settings, currency)
        race_config = (f"Prize: {settings['Prize']} {currency}\n"
                       f"Prize Pooling: {'ON' if settings['Pooling'] else 'OFF'}\n"
                       f"Players needed for payout: {settings['Payout_Min']}\n"
                       f"Betting Allowed: {'YES' if settings['Bet_Allowed'] else 'NO'}")
        embed = discord.Embed(colour=0x00CC33, title="Race Results")
        embed.add_field(name=f'{first[0].name} 🥇', value=first[1].emoji)
        embed.add_field(name=f'{second[0].name} 🥈', value=second[1].emoji)
        if third:
            embed.add_field(name=f'{third[0].name} 🥉', value=third[1].emoji)
        embed.add_field(name='-' * 90, value="\u200b")
        embed.add_field(name="Payouts", value=payout_msg)
        embed.add_field(name="Settings", value=race_config)
        mentions = '' if first[0].bot else f'{first[0].mention}'
        mentions += '' if second[0].bot else f', {second[0].mention}'
        mentions += '' if third is None or third[0].bot else f', {third[0].mention}'
        return mentions, embed

    def _payout_msg(self, settings, currency):
        if settings["Prize"] == 0:
            return "No prize money was distributed."
        elif settings["Payout_Min"] >= len(self.players):
            return "Not enough racers to give prizes."
        elif not settings["Pooling"] or len(self.players) < 4:
            if self.winners[0][0].bot:
                return f"{self.winners[0][0]} is the winner!"
            return f"{self.winners[0][0]} recieved {settings['Prize']} {currency}."
        if settings["Pooling"]:
            msg = ''
            first, second, third = self.winners
            for player, percentage in zip((first[0], second[0], third[0]), (0.6, 0.3, 0.1)):
                print(player)
                if player.bot:
                    continue
                msg += f'{player.name} recieved {settings["Prize"] * percentage} {currency}'
            return msg

    async def _game_setup(self, ctx):
        mode = await self.db.guild(ctx.guild).Mode()
        users = self.players
        if mode == 'zoo':
            players = [(Animal(*random.choice(racers)), user) for user in users]
            if len(players) == 1:
                players.append((Animal(*random.choice(racers)), ctx.bot.user))
        else:
            players = [(Animal(":turtle:", "slow"), user) for user in users]
            if len(players) == 1:
                players.append((Animal(":turtle:", "slow"), ctx.bot.user))
        return players

    async def run_game(self, ctx):
        players = await self._game_setup(ctx)
        setup = "\u200b\n" + '\n'.join(f":carrot: **{animal.current}** 🏁"  
                                       f"[{jockey.name}]" for animal, jockey in players)
        track = await ctx.send(setup)
        counter = 0
        while not all(animal.position == 0 for animal, jockey in players):

            await asyncio.sleep(2.0)
            fields = []
            for animal, jockey in players:
                if animal.position == 0:
                    fields.append(f":carrot: **{animal.current}** 🏁  [{jockey.name}]")
                    continue
                animal.move()
                fields.append(f":carrot: **{animal.current}** 🏁  [{jockey.name}]")
                if animal.position == 0 and len(self.winners) < 3:
                    self.winners.append((jockey, animal))
            t = "\u200b\n" + "\n".join(fields)
            # There is a display bug in discord that requires this if.
            if counter == 0:
                await track.edit(content='')
            await track.edit(content=t)
            counter += 1
