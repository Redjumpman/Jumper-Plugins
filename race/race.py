# Developed by Redjumpman for Redbot.
# Inspired by the snail race mini game.

# Standard Library
import asyncio
import random
from typing import Literal

# Red
from redbot.core import Config, bank, commands, checks
from redbot.core.utils import AsyncIter
from redbot.core.errors import BalanceTooHigh

# Discord
import discord

# Race
from .animals import Animal, racers

__author__ = "Redjumpman"
__version__ = "2.1.5"


class FancyDict(dict):
    def __missing__(self, key):
        value = self[key] = type(self)()
        return value


class FancyDictList(dict):
    def __missing__(self, key):
        value = self[key] = []
        return value


class Race(commands.Cog):
    """Cog for racing animals"""

    def __init__(self):
        self.config = Config.get_conf(self, 5074395009, force_registration=True)

        self.active = FancyDict()
        self.started = FancyDict()
        self.winners = FancyDictList()
        self.players = FancyDictList()
        self.bets = FancyDict()

        guild_defaults = {
            "Wait": 60,
            "Mode": "normal",
            "Prize": 100,
            "Pooling": False,
            "Payout_Min": 0,
            "Bet_Multiplier": 2,
            "Bet_Min": 10,
            "Bet_Max": 50,
            "Bet_Allowed": True,
            "Games_Played": 0,
        }

        # First, Second, and Third place wins
        member_defaults = {"Wins": {"1": 0, "2": 0, "3": 0}, "Losses": 0}
        
        self.config.register_guild(**guild_defaults)
        self.config.register_member(**member_defaults)

    async def red_delete_data_for_user(
        self, *, requester: Literal["discord", "owner", "user", "user_strict"], user_id: int
    ):
        all_members = await self.config.all_members()
        async for guild_id, guild_data in AsyncIter(all_members.items(), steps=100):
            if user_id in guild_data:
                await self.config.member_from_ids(guild_id, user_id).clear()

    @commands.group()
    @commands.guild_only()
    async def race(self, ctx):
        """Race related commands."""
        pass

    @race.command()
    async def start(self, ctx):
        """Begins a new race.

        You cannot start a new race until the active on has ended.

        If you are the only player in the race, you will race against
        your bot.

        The user who started the race is automatically entered into the race.
        """
        if self.active[ctx.guild.id]:
            return await ctx.send(f"A race is already in progress!  Type `{ctx.prefix}race enter` to enter!")
        self.active[ctx.guild.id] = True
        self.players[ctx.guild.id].append(ctx.author)
        wait = await self.config.guild(ctx.guild).Wait()
        current = await self.config.guild(ctx.guild).Games_Played()
        await self.config.guild(ctx.guild).Games_Played.set(current + 1)
        await ctx.send(
            f"🚩 A race has begun! Type {ctx.prefix}race enter "
            f"to join the race! 🚩\nThe race will begin in "
            f"{wait} seconds!\n\n**{ctx.author.mention}** entered the race!"
        )
        await asyncio.sleep(wait)
        self.started[ctx.guild.id] = True
        await ctx.send("🏁 The race is now in progress. 🏁")
        await self.run_game(ctx)

        settings = await self.config.guild(ctx.guild).all()
        currency = await bank.get_currency_name(ctx.guild)
        color = await ctx.embed_colour()
        msg, embed = await self._build_end_screen(ctx, settings, currency, color)
        await ctx.send(content=msg, embed=embed)
        await self._race_teardown(ctx, settings)

    @race.command()
    async def stats(self, ctx, user: discord.Member = None):
        """Display your race stats."""
        if not user:
            user = ctx.author
        color = await ctx.embed_colour()
        user_data = await self.config.member(user).all()
        player_total = sum(user_data["Wins"].values()) + user_data["Losses"]
        server_total = await self.config.guild(ctx.guild).Games_Played()
        try:
            percent = round((player_total / server_total) * 100, 1)
        except ZeroDivisionError:
            percent = 0
        embed = discord.Embed(color=color, description="Race Stats")
        embed.set_author(name=f"{user}", icon_url=user.avatar_url)
        embed.add_field(
            name="Wins",
            value=(
                f"1st: {user_data['Wins']['1']}\n2nd: {user_data['Wins']['2']}\n3rd: {user_data['Wins']['3']}"
            ),
        )
        embed.add_field(name="Losses", value=f'{user_data["Losses"]}')
        embed.set_footer(
            text=(
                f"You have played in {player_total} ({percent}%) races out "
                f"of {server_total} total races on the server."
            )
        )
        await ctx.send(embed=embed)

    @race.command()
    async def bet(self, ctx, bet: int, user: discord.Member):
        """Bet on a user in the race."""
        if await self.bet_conditions(ctx, bet, user):
            self.bets[ctx.guild.id][ctx.author.id] = {user.id: bet}
            currency = await bank.get_currency_name(ctx.guild)
            await bank.withdraw_credits(ctx.author, bet)
            await ctx.send(f"{ctx.author.mention} placed a {bet} {currency} bet on {user.display_name}.")

    @race.command()
    async def enter(self, ctx):
        """Allows you to enter the race.

        This command will return silently if a race has already started.
        By not repeatedly telling the user that they can't enter the race, this
        prevents spam.

        """
        if self.started[ctx.guild.id]:
            return await ctx.send(
                "A race has already started.  Please wait for the first one to finish before entering or starting a race."
            )
        elif not self.active.get(ctx.guild.id):
            return await ctx.send("A race must be started before you can enter.")
        elif ctx.author in self.players[ctx.guild.id]:
            return await ctx.send("You have already entered the race.")
        elif len(self.players[ctx.guild.id]) >= 14:
            return await ctx.send("The maximum number of players has been reached.")
        else:
            self.players[ctx.guild.id].append(ctx.author)
            await ctx.send(f"{ctx.author.mention} has joined the race.")

    @race.command(hidden=True)
    @checks.admin_or_permissions(administrator=True)
    async def clear(self, ctx):
        """ONLY USE THIS COMMAND FOR DEBUG PURPOSES

        You shouldn't use this command unless the race is stuck
        or you are debugging."""
        self.clear_local(ctx)
        await ctx.send("Race cleared.")

    @race.command()
    @checks.admin_or_permissions(administrator=True)
    async def wipe(self, ctx):
        """This command will wipe ALL race data.

        You are given a confirmation dialog when using this command.
        If you decide to wipe your data, all stats and settings will be deleted.
        """
        await ctx.send(
            f"You are about to clear all race data including stats and settings. "
            f"If you are sure you wish to proceed, type `{ctx.prefix}yes`."
        )
        choices = (f"{ctx.prefix}yes", f"{ctx.prefix}no")
        check = lambda m: (m.author == ctx.author and m.channel == ctx.channel and m.content in choices)
        try:
            choice = await ctx.bot.wait_for("message", timeout=20.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("No response. Race wipe cancelled.")

        if choice.content.lower() == f"{ctx.prefix}yes":
            await self.config.guild(ctx.guild).clear()
            await self.config.clear_all_members(ctx.guild)
            return await ctx.send("Race data has been wiped.")
        else:
            return await ctx.send("Race wipe cancelled.")

    @race.command()
    async def version(self, ctx):
        """Displays the version of race."""
        await ctx.send(f"You are running race version {__version__}.")

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def setrace(self, ctx):
        """Race settings commands."""
        pass

    @setrace.command()
    async def wait(self, ctx, wait: int):
        """Changes the wait time before a race starts.

        This only affects the period where race is still waiting
        for more participants to join the race."""
        if wait < 0:
            return await ctx.send("Really? You're an idiot.")
        await self.config.guild(ctx.guild).Wait.set(wait)
        await ctx.send(f"Wait time before a race begins is now {wait} seconds.")

    @setrace.group(name="bet")
    async def _bet(self, ctx):
        """Bet settings for race."""
        pass

    @_bet.command(name="min")
    async def _min(self, ctx, amount: int):
        """Sets the betting minimum."""
        if amount < 0:
            return await ctx.send("Come on now. Let's be reasonable.")
        maximum = await self.config.guild(ctx.guild).Bet_Max()
        if amount > maximum:
            return await ctx.send(f"Minimum must be lower than the set max of {maximum}.")

        await self.config.guild(ctx.guild).Bet_Min.set(amount)
        await ctx.send(f"Minimum bet amount set to {amount}.")

    @_bet.command(name="max")
    async def _max(self, ctx, amount: int):
        """Sets the betting maximum."""
        if amount < 0:
            return await ctx.send("Come on now. Let's be reasonable.")
        if amount > 2 ** 63 - 1:
            return await ctx.send("Come on now. Let's be reasonable.")
        minimum = await self.config.guild(ctx.guild).Bet_Min()
        if amount < minimum:
            return await ctx.send(f"Maximum must be higher than the set min of {minimum}.")

        await self.config.guild(ctx.guild).Bet_Max.set(amount)
        await ctx.send(f"Maximum bet amount set to {amount}.")

    @_bet.command()
    async def multiplier(self, ctx, multiplier: float):
        """Sets the betting multiplier.
        
        If the bot's economy mode is set to global instead of server-based, this setting is not available.
        """
        global_bank = await bank.is_global()
        if global_bank:
            return await ctx.send("This setting is not available for non-server-based bot economies.")
        if multiplier < 0:
            return await ctx.send("So... you want them to lose money... when they win. I'm not doing that.")
        if multiplier == 0:
            return await ctx.send("That means they win nothing. Just turn off betting.")
        if multiplier > 2 ** 63 - 1:
            return await ctx.send("Try a smaller number.")

        await self.config.guild(ctx.guild).Bet_Multiplier.set(multiplier)
        await ctx.send(f"Betting multiplier set to {multiplier}.")

    @_bet.command()
    async def toggle(self, ctx):
        """Toggles betting on and off."""
        current = await self.config.guild(ctx.guild).Bet_Allowed()
        await self.config.guild(ctx.guild).Bet_Allowed.set(not current)
        await ctx.send(f"Betting is now {'OFF' if current else 'ON'}.")

    @setrace.command()
    async def mode(self, ctx, mode: str):
        """Changes the race mode.

        Race can either be in normal mode or zoo mode.

        Normal Mode:
            All racers are turtles.

        Zoo Mode:
            Racers are randomly selected from a list of animals with
            different attributes.
        """
        if mode.lower() not in ("zoo", "normal"):
            return await ctx.send("Must select either `zoo` or `normal` as a mode.")

        await self.config.guild(ctx.guild).Mode.set(mode.lower())
        await ctx.send(f"Mode changed to {mode.lower()}")

    @setrace.command()
    async def prize(self, ctx, prize: int):
        """Sets the prize pool for winners.

        Set the prize to 0 if you do not wish any credits to be distributed.

        When prize pooling is enabled (see `[p]setrace togglepool`) the prize 
        will be distributed as follows:
            1st place 60%
            2nd place 30%
            3rd place 10%

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
        if prize > 2 ** 63 - 1:
            return await ctx.send("Try a smaller number.")
        else:
            currency = await bank.get_currency_name(ctx.guild)
            await self.config.guild(ctx.guild).Prize.set(prize)
            await ctx.send(f"Prize set for {prize} {currency}.")

    @setrace.command(name="togglepool")
    async def _tooglepool(self, ctx):
        """Toggles on/off prize pooling.

        Makes it so that prizes are pooled between 1st, 2nd, and 3rd.
        It's a 60/30/10 split rounded to the nearest whole number.

        There must be at least four human players, otherwise, only first
        place wins.
        """
        pool = await self.config.guild(ctx.guild).Pooling()
        await self.config.guild(ctx.guild).Pooling.set(not pool)
        await ctx.send(f"Prize pooling is now {'OFF' if pool else 'ON'}.")

    @setrace.command()
    async def payoutmin(self, ctx, players: int):
        """Sets the number of players needed to payout prizes and bets.

        This sets the required number of players needed to payout prizes.
        If the number of racers aren't met, then nothing is paid out.

        The person starting the race is not counted in this minimum number.
        For example, if you are playing alone vs. the bot and the payout min
        is set to 1, you need 1 human player besides the race starter for a
        payout to occur.

        If you want race to always pay out, then set players to 0.
        """
        if players < 0:
            return await ctx.send("I don't have time for this shit.")
        await self.config.guild(ctx.guild).Payout_Min.set(players)
        if players == 0:
            await ctx.send("Races will now always payout.")
        else:
            plural = "s" if players != 1 else ""
            await ctx.send(f"Races will only payout if there are {players} human player{plural} besides the person that starts the game.")

    async def stats_update(self, ctx):
        names = [player for player, emoji in self.winners[ctx.guild.id]]
        for player in self.players[ctx.guild.id]:
            if player in names:
                position = names.index(player) + 1
                current = await self.config.member(player).Wins.get_raw(str(position))
                await self.config.member(player).Wins.set_raw(str(position), value=current + 1)
            else:
                current = await self.config.member(player).Losses()
                await self.config.member(player).Losses.set(current + 1)

    async def _race_teardown(self, ctx, settings):
        await self.stats_update(ctx)
        await self.distribute_prizes(ctx, settings)
        await self.bet_payouts(ctx, settings)
        self.clear_local(ctx)

    def clear_local(self, ctx):
        self.players[ctx.guild.id].clear()
        self.winners[ctx.guild.id].clear()
        self.bets[ctx.guild.id].clear()
        self.active[ctx.guild.id] = False
        self.started[ctx.guild.id] = False

    async def distribute_prizes(self, ctx, settings):
        if settings["Prize"] == 0 or (settings["Payout_Min"] > len(self.players[ctx.guild.id])):
            return

        if settings["Pooling"] and len(self.players[ctx.guild.id]) > 3:
            first, second, third = self.winners[ctx.guild.id]
            for player, percentage in zip((first[0], second[0], third[0]), (0.6, 0.3, 0.1)):
                if player.bot:
                    continue
                try:
                    await bank.deposit_credits(player, int(settings["Prize"] * percentage))
                except BalanceTooHigh as e:
                    await bank.set_balance(player, e.max_balance)
        else:
            if self.winners[ctx.guild.id][0][0].bot:
                return
            try:
                await bank.deposit_credits(self.winners[ctx.guild.id][0][0], settings["Prize"])
            except BalanceTooHigh as e:
                await bank.set_balance(self.winners[ctx.guild.id][0][0], e.max_balance)

    async def bet_payouts(self, ctx, settings):
        if not self.bets[ctx.guild.id] or not settings["Bet_Allowed"]:
            return
        multiplier = settings["Bet_Multiplier"]
        first = self.winners[ctx.guild.id][0]
        for user_id, wagers in self.bets[ctx.guild.id].items():
            for jockey, bet in wagers.items():
                if jockey == first[0].id:
                    user = ctx.guild.get_member(user_id)
                    try:
                        await bank.deposit_credits(user, (int(bet * multiplier)))
                    except BalanceTooHigh as e:
                        await bank.set_balance(user, e.max_balance)

    async def bet_conditions(self, ctx, bet, user):
        if not self.active[ctx.guild.id]:
            await ctx.send("There isn't a race right now.")
            return False
        elif self.started[ctx.guild.id]:
            await ctx.send("You can't place a bet after the race has started.")
            return False
        elif user not in self.players[ctx.guild.id]:
            await ctx.send("You can't bet on someone who isn't in the race.")
            return False
        elif self.bets[ctx.guild.id][ctx.author.id]:
            await ctx.send("You have already entered a bet for the race.")
            return False

        # Separated the logic such that calls to config only happen if the statements
        # above pass.
        data = await self.config.guild(ctx.guild).all()
        allowed = data["Bet_Allowed"]
        minimum = data["Bet_Min"]
        maximum = data["Bet_Max"]

        if not allowed:
            await ctx.send("Betting has been turned off.")
            return False
        elif not await bank.can_spend(ctx.author, bet):
            await ctx.send("You do not have enough money to cover the bet.")
        elif minimum <= bet <= maximum:
            return True
        else:
            await ctx.send(f"Bet must not be lower than {minimum} or higher than {maximum}.")
            return False

    async def _build_end_screen(self, ctx, settings, currency, color):
        if len(self.winners[ctx.guild.id]) == 3:
            first, second, third = self.winners[ctx.guild.id]
        else:
            first, second, = self.winners[ctx.guild.id]
            third = None
        payout_msg = self._payout_msg(ctx, settings, currency)
        footer = await self._get_bet_winners(ctx, first[0])
        race_config = (
            f"Prize: {settings['Prize']} {currency}\n"
            f"Prize Pooling: {'ON' if settings['Pooling'] else 'OFF'}\n"
            f"Min. human players for payout: {settings['Payout_Min'] + 1}\n"
            f"Betting Allowed: {'YES' if settings['Bet_Allowed'] else 'NO'}\n"
            f"Bet Multiplier: {settings['Bet_Multiplier']}x"
        )
        embed = discord.Embed(colour=color, title="Race Results")
        embed.add_field(name=f"{first[0].display_name} 🥇", value=first[1].emoji)
        embed.add_field(name=f"{second[0].display_name} 🥈", value=second[1].emoji)
        if third:
            embed.add_field(name=f"{third[0].display_name} 🥉", value=third[1].emoji)
        embed.add_field(name="-" * 90, value="\u200b", inline=False)
        embed.add_field(name="Payouts", value=payout_msg)
        embed.add_field(name="Settings", value=race_config)
        embed.set_footer(text=f"Bet winners: {footer[0:2000]}")
        mentions = "" if first[0].bot else f"{first[0].mention}"
        mentions += "" if second[0].bot else f", {second[0].mention}" if not first[0].bot else f"{second[0].mention}"
        mentions += "" if third is None or third[0].bot else f", {third[0].mention}"
        return mentions, embed

    def _payout_msg(self, ctx, settings, currency):
        if settings["Prize"] == 0:
            return "No prize money was distributed."
        elif settings["Payout_Min"] > len(self.players[ctx.guild.id]):
            return "Not enough racers to give prizes."
        elif not settings["Pooling"] or len(self.players[ctx.guild.id]) < 4:
            if self.winners[ctx.guild.id][0][0].bot:
                return f"{self.winners[ctx.guild.id][0][0]} is the winner!"
            return f"{self.winners[ctx.guild.id][0][0]} received {settings['Prize']} {currency}."
        if settings["Pooling"]:
            msg = ""
            first, second, third = self.winners[ctx.guild.id]
            for player, percentage in zip((first[0], second[0], third[0]), (0.6, 0.3, 0.1)):
                if player.bot:
                    continue
                msg += f'{player.display_name} received {int(settings["Prize"] * percentage)} {currency}. '
            return msg

    async def _get_bet_winners(self, ctx, winner):
        bet_winners = []
        multiplier = await self.config.guild(ctx.guild).Bet_Multiplier()
        for better, bets in self.bets[ctx.guild.id].items():
            for jockey, bet in bets.items():
                if jockey == winner.id:
                    better_obj = ctx.guild.get_member(better)
                    bet_winners.append(f"{better_obj.display_name}: {bet * multiplier}")
        return ", ".join(bet_winners) if bet_winners else "None."

    async def _game_setup(self, ctx):
        mode = await self.config.guild(ctx.guild).Mode()
        users = self.players[ctx.guild.id]
        if mode == "zoo":
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
        setup = "\u200b\n" + "\n".join(
            f":carrot: **{animal.current}** 🏁[{jockey.display_name}]" for animal, jockey in players
        )
        track = await ctx.send(setup)
        while not all(animal.position == 0 for animal, jockey in players):

            await asyncio.sleep(2.0)
            fields = []
            for animal, jockey in players:
                if animal.position == 0:
                    fields.append(f":carrot: **{animal.current}** 🏁  [{jockey.display_name}]")
                    continue
                animal.move()
                fields.append(f":carrot: **{animal.current}** 🏁  [{jockey.display_name}]")
                if animal.position == 0 and len(self.winners[ctx.guild.id]) < 3:
                    self.winners[ctx.guild.id].append((jockey, animal))
            t = "\u200b\n" + "\n".join(fields)
            try:
                await track.edit(content=t)
            except discord.errors.NotFound:
            	pass
