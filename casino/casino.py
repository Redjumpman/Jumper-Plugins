# Developed by Redjumpman for Redbot
# Inspired by Spriter's work on a modded economy
# Blackjack inspired by http://codereview.stackexchange.com/questions/57849/blackjack-game-with-classes-instead-of-functions
# Creates 1 json file and requires tabulate
import os
import discord
import random
import time
import asyncio
from operator import itemgetter
from .utils.dataIO import fileIO
from .utils import checks
from discord.ext import commands
from __main__ import send_cmd_help
try:   # Check if Tabulate is installed
    from tabulate import tabulate
    tabulateAvailable = True
except:
    tabulateAvailable = False


class Casino:
    """Casino"""

    def __init__(self, bot):
        self.bot = bot
        self.casinosys = fileIO("data/casino/casino.json", "load")
        self.games = ["Allin", "Blackjack", "Coin", "Cups", "Dice"]
        self.deck = ['Ace', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'Jack', 'Queen', 'King']
        self.card_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
                            '10': 10, 'Jack': 10, 'Queen': 10, 'King': 10}

    @commands.group(pass_context=True, no_pm=True)
    async def casino(self, ctx):
        """Casino Group Commands"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @casino.command(name="leaderboard", pass_context=True)
    async def _leaderboard_casino(self, ctx):
        """Displays Casino Leaderboard"""
        channel = ctx.message.channel
        pos = 0
        players = [subdict["Name"] for subdict in self.casinosys["Players"].values()]
        chips = [subdict["Chips"] for subdict in self.casinosys["Players"].values()]
        rank = []
        for item in players:
            pos += 1
            rank.append(pos)
        m = zip(players, chips)
        m = sorted(m, key=itemgetter(1), reverse=True)
        players = [x[0] for x in m]
        chips = [x[1] for x in m]
        li = list(zip(rank, players, chips))
        t = tabulate(li, headers=["Rank", "Names", "Chips"], numalign="left", tablefmt="orgtbl")
        msg = "```Python\n" + t + "```"
        await self.send_long_message(channel, msg)

    @casino.command(name="join", pass_context=True)
    async def _join_casino(self, ctx):
        """Grants you membership access to the casino"""
        user = ctx.message.author
        if user.id not in self.casinosys["Players"]:
            self.casinosys["Players"][user.id] = {"Chips": 100,
                                                  "Membership": None,
                                                  "Name": user.name,
                                                  "Played": {"Dice Played": 0,
                                                             "Cups Played": 0,
                                                             "BJ Played": 0,
                                                             "Coin Played": 0,
                                                             "Allin Played": 0},
                                                  "Won": {"Dice Won": 0,
                                                          "Cups Won": 0,
                                                          "BJ Won": 0,
                                                          "Coin Won": 0,
                                                          "Allin Won": 0},
                                                  "CD": {"Dice CD": 0,
                                                         "Cups CD": 0,
                                                         "Blackjack CD": 0,
                                                         "Coin CD": 0,
                                                         "Allin CD": 0}
                                                  }
            fileIO("data/casino/casino.json", "save", self.casinosys)
            name = self.casinosys["System Config"]["Casino Name"]
            await self.bot.say("Your membership has been approved! Welcome to {} Casino!\nAs a first time member we have credited your account with 100 free chips.\nHave fun!".format(name))
        else:
            await self.bot.say("You are already a member.")

    @casino.command(name="exchange", pass_context=True)
    async def _exchange_casino(self, ctx, currency: str, amount: int):
        """Exchange chips for credits and credits for chips"""
        bank = self.bot.get_cog('Economy').bank
        user = ctx.message.author
        currency = currency.title()
        chip_rate = self.casinosys["System Config"]["Chip Rate"]
        credit_rate = self.casinosys["System Config"]["Credit Rate"]
        chips = self.casinosys["System Config"]["Chip Name"]
        casino_name = self.casinosys["System Config"]["Casino Name"]
        if user.id in self.casinosys["Players"]:
            if currency == "Chips":
                if amount > 0:
                    if amount <= self.casinosys["Players"][user.id]["Chips"]:
                        await self.subtract_chips(user.id, amount)
                        credits = int(round(amount * credit_rate))
                        bank.deposit_credits(user, credits)
                        await self.bot.say("I have exchanged {} {} chips into {} credits.\nThank you for playing at {} Casino.".format(str(amount), chips, str(credits), casino_name))
                    else:
                        await self.bot.say("You don't have that many chips to exchange")
                else:
                    await self.bot.say("You need more than 0 chips wise guy.")
            elif currency == "Credits":
                if amount > 0:
                    if bank.can_spend(user, amount):
                        bank.withdraw_credits(user, amount)
                        chip_amount = int(round(amount * chip_rate))
                        self.casinosys["Players"][user.id]["Chips"] += chip_amount
                        fileIO("data/casino/casino.json", "save", self.casinosys)
                        await self.bot.say("I have exchanged {} credits for {} {} chips.\nEnjoy your time at {} Casino!".format(str(amount), str(chip_amount), chips, casino_name))
                    else:
                        await self.bot.say("You don't have that many credits to exchange.")
                else:
                    await self.bot.say("Very funny. I need more than 0 credits.")
            else:
                await self.bot.say("I can only exchange chips or credits, please specify one.")
        else:
            await self.bot.say("You need a {} Casino membership. To get one type !casino join".format(casino_name))

    @casino.command(name="stats", pass_context=True)
    async def _stats_casino(self, ctx):
        """Shows your casino play stats"""
        user = ctx.message.author
        casino_name = self.casinosys["System Config"]["Casino Name"]
        if user.id in self.casinosys["Players"]:
            column1 = ["Dice", "Cups", "All-In", "Coin", "Blackjack"]
            column2 = [x for x in self.casinosys["Players"][user.id]["Played"].values()]
            column3 = [x for x in self.casinosys["Players"][user.id]["Won"].values()]
            m = sorted(list(zip(column1, column2, column3)))
            t = tabulate(m, headers=["Game", "Played", "Won"])
            await self.bot.say("```Python\n" + t + "```")
        else:
            await self.bot.say("You need a {} Casino membership. To get one type !casino join".format(casino_name))

    @casino.command(name="info", pass_context=True)
    async def _info_casino(self, ctx):
        """Shows information about the server casino"""
        games = self.games
        min_bet = [subdict["Min"] for subdict in self.casinosys["Games"].values()]
        max_bet = [subdict["Max"] for subdict in self.casinosys["Games"].values()]
        cooldown = [subdict["Cooldown"] for subdict in self.casinosys["Games"].values()]
        time = []
        multiplier = [subdict["Multiplier"] for subdict in self.casinosys["Games"].values()]
        chip_exchange_rate = self.casinosys["System Config"]["Chip Rate"]
        credit_exchange_rate = self.casinosys["System Config"]["Credit Rate"]
        for x in cooldown:
            d = self.time_format(x)
            time.append(d)
        m = list(zip(games, multiplier, min_bet, max_bet, time))
        t = tabulate(m, headers=["Game", "Multiplier", "Min Bet", "Max Bet", "Cooldown"])
        msg = "```\n"
        msg += t + "\n" + "\n"
        msg += "Credit Exchange Rate: x" + str(credit_exchange_rate) + "\n"
        msg += "Chip Exchange Rate: x" + str(chip_exchange_rate) + "\n"
        msg += "Casino Members: " + str(len(self.casinosys["Players"].keys()))
        msg += "```"
        await self.bot.say(msg)

    @casino.command(name="toggle", pass_context=True)
    async def _toggle_casino(self, ctx):
        """Opens and closes the casino"""
        casino_name = self.casinosys["System Config"]["Casino Name"]
        if self.casinosys["System Config"]["Casino Open"]:
            self.casinosys["System Config"]["Casino Open"] = False
            fileIO("data/casino/casino.json", "save", self.casinosys)
            await self.bot.say("The {} Casino is now closed.".format(casino_name))
        else:
            self.casinosys["System Config"]["Casino Open"] = True
            fileIO("data/casino/casino.json", "save", self.casinosys)
            await self.bot.say("The {} Casino is now open!".format(casino_name))

    @casino.command(name="balance", pass_context=True)
    async def _balance_casino(self, ctx):
        """Shows your number of chips"""
        user = ctx.message.author
        casino_name = self.casinosys["System Config"]["Casino Name"]
        if user.id in self.casinosys["Players"]:
            amount = self.casinosys["Players"][user.id]["Chips"]
            chips = self.casinosys["System Config"]["Chip Name"]
            await self.bot.say("```Python\nYou have {} {} chips.```".format(str(amount), chips))
        else:
            await self.bot.say("You need a {} Casino membership. To get one type !casino join".format(casino_name))

    @commands.command(pass_context=True, no_pm=True)
    async def cups(self, ctx, cup: int, bet: int):
        """Pick the cup that is hiding the gold coin. Choose 1, 2, 3, or 4"""
        user = ctx.message.author
        game = "Cups"
        casino_name = self.casinosys["System Config"]["Casino Name"]
        if user.id in self.casinosys["Players"]:
            if self.casinosys["System Config"]["Casino Open"]:
                if await self.check_cooldowns(user.id, game):
                    if await self.minmax_check(bet, game):
                        if await self.subtract_chips(user.id, bet):
                            if cup < 5 and cup > 0:
                                outcome = random.randint(1, 4)
                                await self.bot.say("The cups start shuffling along the table...")
                                await asyncio.sleep(3)
                                self.casinosys["Players"][user.id]["Played"]["Cups Played"] += 1
                                fileIO("data/casino/casino.json", "save", self.casinosys)
                                if cup == outcome:
                                    amount = bet * self.casinosys["Games"]["Cups"]["Multiplier"]
                                    await self.bot.say("Congratulations! The coin was under cup {}!".format(str(outcome)))
                                    self.casinosys["Players"][user.id]["Won"]["Cups Won"] += 1
                                    fileIO("data/casino/casino.json", "save", self.casinosys)
                                    await self.add_chips(user.id, amount)
                                else:
                                    await self.bot.say("Sorry! The coin was under cup {}.".format(str(outcome)))
                            else:
                                await self.bot.say("You need to pick a cup 1-4.")
            else:
                await self.bot.say("The {} Casino is closed.".format(casino_name))
        else:
            await self.bot.say("You need a {} Casino membership. To get one type !casino join".format(casino_name))

    @commands.command(pass_context=True, no_pm=True)
    async def coin(self, ctx, choice: str, bet: int):
        """Bet on heads or tails"""
        user = ctx.message.author
        choice = choice.title()
        possible = ["Heads", "Tails"]
        game = "Coin"
        casino_name = self.casinosys["System Config"]["Casino Name"]
        if user.id in self.casinosys["Players"]:
            if self.casinosys["System Config"]["Casino Open"]:
                if await self.check_cooldowns(user.id, game):
                    if await self.minmax_check(bet, game):
                        if await self.subtract_chips(user.id, bet):
                            if choice == "Heads" or choice == "Tails":
                                outcome = random.choice(possible)
                                await self.bot.say("The coin flips into the air...")
                                await asyncio.sleep(2)
                                self.casinosys["Players"][user.id]["Played"]["Coin Played"] += 1
                                fileIO("data/casino/casino.json", "save", self.casinosys)
                                if choice == outcome:
                                    amount = bet * self.casinosys["Games"]["Coin"]["Multiplier"]
                                    await self.bot.say("Congratulations! The coin landed on {}!".format(outcome))
                                    await self.add_chips(user.id, amount)
                                    self.casinosys["Players"][user.id]["Won"]["Coin Won"] += 1
                                    fileIO("data/casino/casino.json", "save", self.casinosys)
                                else:
                                    await self.bot.say("Sorry! The coin landed on {}.".format(outcome))
                            else:
                                await self.bot.say("You need to pick heads or tails")
            else:
                await self.bot.say("The {} Casino is closed.".format(casino_name))
        else:
            await self.bot.say("You need a {} Casino membership. To get one type !casino join".format(casino_name))

    @commands.command(pass_context=True, no_pm=True)
    async def dice(self, ctx, bet: int):
        """Roll 2, 7, 11 or 12 to win."""
        user = ctx.message.author
        winning_numbers = [2, 7, 11, 12]
        game = "Dice"
        casino_name = self.casinosys["System Config"]["Casino Name"]
        if user.id in self.casinosys["Players"]:
            if self.casinosys["System Config"]["Casino Open"]:
                if await self.check_cooldowns(user.id, game):
                    if await self.minmax_check(bet, game):
                        if await self.subtract_chips(user.id, bet):
                            outcome = random.randint(1, 12)
                            await self.bot.say("The dice strike the back of the table and begin to tumble into place...")
                            await asyncio.sleep(3)
                            self.casinosys["Players"][user.id]["Played"]["Dice Played"] += 1
                            fileIO("data/casino/casino.json", "save", self.casinosys)
                            if outcome in winning_numbers:
                                amount = bet * self.casinosys["Games"]["Dice"]["Multiplier"]
                                await self.bot.say("Congratulations! The dice landed on {}.".format(str(outcome)))
                                await self.add_chips(user.id, amount)
                                self.casinosys["Players"][user.id]["Won"]["Dice Won"] += 1
                                fileIO("data/casino/casino.json", "save", self.casinosys)
                            else:
                                await self.bot.say("Sorry! The dice landed on {}.".format(str(outcome)))
            else:
                await self.bot.say("The {} Casino is closed.".format(casino_name))
        else:
            await self.bot.say("You need a {} Casino membership. To get one type !casino join".format(casino_name))

    @commands.command(pass_context=True, no_pm=True, aliases=["bj", "21"])
    async def blackjack(self, ctx, bet: int):
        """Modified Blackjack."""
        user = ctx.message.author
        game = "Blackjack"
        casino_name = self.casinosys["System Config"]["Casino Name"]
        if user.id in self.casinosys["Players"]:
            if self.casinosys["System Config"]["Casino Open"]:
                if await self.check_cooldowns(user.id, game):
                    if await self.minmax_check(bet, game):
                        if await self.subtract_chips(user.id, bet):
                            self.casinosys["Players"][user.id]["Played"]["BJ Played"] += 1
                            fileIO("data/casino/casino.json", "save", self.casinosys)
                            await self.blackjack_game(user, bet)
            else:
                await self.bot.say("The {} Casino is closed.".format(casino_name))
        else:
            await self.bot.say("You need a {} Casino membership. To get one type !casino join".format(casino_name))

    @commands.command(pass_context=True, no_pm=True)
    async def allin(self, ctx, multiplier: int):
        """It's all or nothing. Bets everything you have."""
        user = ctx.message.author
        game = "Allin"
        chips = self.casinosys["System Config"]["Chip Name"]
        bet = int(self.casinosys["Players"][user.id]["Chips"])
        casino_name = self.casinosys["System Config"]["Casino Name"]
        if self.casinosys["System Config"]["Casino Open"]:
            if await self.check_cooldowns(user.id, game):
                if await self.subtract_chips(user.id, bet):
                    outcome = random.randrange(0, multiplier + 1)
                    await self.bot.say("You put all your chips into the machine and pull the lever...")
                    self.casinosys["Players"][user.id]["Played"]["Allin Played"] += 1
                    fileIO("data/casino/casino.json", "save", self.casinosys)
                    await asyncio.sleep(3)
                    if outcome == 0:
                        amount = multiplier * self.casinosys["Players"][user.id]["Chips"]
                        self.casinosys["Players"][user.id]["Chips"] = 0
                        await self.bot.say("Jackpot!! You just won {} chips!!".format(str(amount)))
                        await self.add_chips(user.id, amount)
                        self.casinosys["Players"][user.id]["Won"]["Allin Won"] += 1
                        fileIO("data/casino/casino.json", "save", self.casinosys)
                    else:
                        await self.bot.say("Sorry! Your all or nothing gamble failed you lost {} {} chips.".format(str(bet), chips))
        else:
            await self.bot.say("The {} Casino is closed.".format(casino_name))

    @commands.group(pass_context=True, no_pm=True)
    async def setcasino(self, ctx):
        """Configures Casino Options"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @setcasino.command(name="multiplier", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _multiplier_setcasino(self, ctx, game: str, multiplier: float):
        """Sets the payout multiplier for casino games"""
        game = game.title()
        if game in self.games:
            if multiplier > 0:
                multiplier = float(abs(multiplier))
                self.casinosys["Games"][game]["Multiplier"] = multiplier
                fileIO("data/casino/casino.json", "save", self.casinosys)
                await self.bot.say("Now setting the payout multiplier for {} to {}".format(game, str(multiplier)))
            else:
                await self.bot.say("Multiplier needs to be higher than 0.")
        else:
            li = ", ".join(self.games)
            await self.bot.say("This game does not exist. Please pick from: " + li)

    @setcasino.command(name="balance", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _balance_setcasino(self, ctx, user: discord.Member, chips: int):
        """Sets a Casino member's chip balance"""
        chip_name = self.casinosys["System Config"]["Chip Name"]
        casino_name = self.casinosys["System Config"]["Casino Name"]
        if user.id in self.casinosys["Players"]:
            self.casinosys["Players"][user.id]["Chips"] = chips
            fileIO("data/casino/casino.json", "save", self.casinosys)
            await self.bot.say("```Python\nSetting the chip balance of {} to {} {} chips.```".format(user.name, str(chips), chip_name))
        else:
            await self.bot.say("{} needs a {} Casino membership.".format(user.name, casino_name))

    @setcasino.command(name="membership", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _membership_setcasino(self, ctx, level: int, *, name: str):
        """Sets the membership names. 0 is granted on joining, 3 is the highest."""
        if level < 4:
            m = "Membership Lvl " + str(level)
            self.casinosys["System Config"][m] = name
            fileIO("data/casino/casino.json", "save", self.casinosys)
            await self.bot.say("Changed {} name to {}".format(m, name))
        else:
            li = ", ".join(self.games)
            await self.bot.say("This game does not exist. Please pick from: " + li)

    @setcasino.command(name="name", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _name_setcasino(self, ctx, *, name: str):
        """Sets the name of the Casino."""
        self.casinosys["System Config"]["Casino Name"] = name
        fileIO("data/casino/casino.json", "save", self.casinosys)
        await self.bot.say("Changed the casino name to {}.".format(name))

    @setcasino.command(name="exchange", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _exchange_setcasino(self, ctx, rate: float, currency: str):
        """Sets the exchange rate for chips or credits"""
        if rate > 0:
            if currency.title() == "Chips":
                self.casinosys["System Config"]["Chip Rate"] = rate
                fileIO("data/casino/casino.json", "save", self.casinosys)
                await self.bot.say("Setting the exchange rate for credits to chips to {}".format(str(rate)))
            elif currency.title() == "Credits":
                self.casinosys["System Config"]["Credit Rate"] = rate
                fileIO("data/casino/casino.json", "save", self.casinosys)
                await self.bot.say("Setting the exchange rate for chips to credits to {}".format(str(rate)))
            else:
                await self.bot.say("Please specify chips or credits")
        else:
            await self.bot.say("Rate must be higher than 0. Default is 1.")

    @setcasino.command(name="chipname", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _chipname_setcasino(self, ctx, *, name: str):
        """Sets the name of your Casino chips."""
        self.casinosys["System Config"]["Chip Name"] = name
        fileIO("data/casino/casino.json", "save", self.casinosys)
        await self.bot.say("Changed the name of your chips to {}.".format(name))
        await self.bot.say("Test display:")
        await self.bot.say("```Python\nCongratulations, you just won 50 {} chips.```".format(name))

    @setcasino.command(name="cooldown", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _cooldown_setcasino(self, ctx, game, seconds: int):
        """Set the cooldown period for casino games"""
        game = game.title()
        if game in self.games:
            self.casinosys["Games"][game]["Cooldown"] = seconds
            fileIO("data/casino/casino.json", "save", self.casinosys)
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            await self.bot.say("Setting the cooldown period for {} to {} hours, {} minutes and {} seconds".format(game, h, m, s))

    @setcasino.command(name="max", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _max_setcasino(self, ctx, game, maxbet: int):
        """Set the maximum bet to play a game"""
        game = game.title()
        if game in self.games:
            if maxbet > 0:
                if maxbet > self.casinosys["Games"][game]["Min"]:
                    self.casinosys["Games"][game]["Max"] = maxbet
                    chips = self.casinosys["System Config"]["Chip Name"]
                    fileIO("data/casino/casino.json", "save", self.casinosys)
                    await self.bot.say("Setting the maximum bet for {} to {} {} chips.".format(game, str(maxbet), chips))
                else:
                    minbet = self.casinosys["Games"][game]["Min"]
                    await self.bot.say("The max bet needs be higher than the minimum bet of {}.".format(str(minbet)))
            else:
                await self.bot.say("You need to set a maximum bet higher than 0.")
        else:
            li = ", ".join(self.games)
            await self.bot.say("This game does not exist. Please pick from: " + li)

    @setcasino.command(name="min", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _min_setcasino(self, ctx, game, minbet: int):
        """Set the minimum bet to play a game"""
        game = game.title()
        if game in self.games:
            if minbet > 0:
                if minbet < self.casinosys["Games"][game]["Min"]:
                    self.casinosys["Games"][game]["Min"] = minbet
                    chips = self.casinosys["System Config"]["Chip Name"]
                    fileIO("data/casino/casino.json", "save", self.casinosys)
                    await self.bot.say("Setting the minimum bet for {} to {} {} chips.".format(game, str(minbet), chips))
                else:
                    maxbet = self.casinosys["Games"][game]["Max"]
                    await self.bot.say("The minimum bet can't bet set higher than the maximum bet of {} for {}.".format(str(maxbet), game))
            else:
                await self.bot.say("You need to set a minimum bet higher than 0.")
        else:
            li = ", ".join(self.games)
            await self.bot.say("This game does not exist. Please pick from: " + li)

    async def add_credits(self, user, amount):
        bank = self.bot.get_cog('Economy').bank
        bank.deposit_credits(user, amount)
        await self.bot.say("{} credits were deposited into your account.".format(str(amount)))

    async def add_chips(self, user, amount):
        amount = int(round(amount))
        self.casinosys["Players"][user]["Chips"] += amount
        fileIO("data/casino/casino.json", "save", self.casinosys)
        chips = self.casinosys["System Config"]["Chip Name"]
        await self.bot.say("```Python\n" + "Congratulations, you just won {} {} chips.```".format(str(amount), chips))

    async def subtract_chips(self, userid, number):
        chips = self.casinosys["System Config"]["Chip Name"]
        casino_name = self.casinosys["System Config"]["Casino Name"]
        if userid in self.casinosys["Players"]:
            if self.casinosys["Players"][userid]["Chips"] >= number:
                self.casinosys["Players"][userid]["Chips"] -= number
                fileIO("data/casino/casino.json", "save", self.casinosys)
                return True
            else:
                await self.bot.say("You do not have enough {} chips.".format(chips))
                return False
        else:
            await self.bot.say("You need a {} Casino membership. To get one type !casino join".format(casino_name))
            return False

    async def subtract_credits(self, user, number):
        bank = self.bot.get_cog("Economy").bank
        if bank.account_exists(user):
            if bank.can_spend(user, number):
                bank.withdraw_credits(user, number)
                return True
            else:
                await self.bot.say("You do not have enough credits in your account.")
                return False
        else:
            await self.bot.say("You do not have a bank account.")
            return False

    async def minmax_check(self, bet, game):
        mi = self.casinosys["Games"][game]["Min"]
        mx = self.casinosys["Games"][game]["Max"]
        if bet >= mi:
            if bet <= mx:
                return True
            else:
                await self.bot.say("Your bet exceeds the maximum of {} chips.".format(str(mx)))
                return False
        else:
            await self.bot.say("Your bet needs to be higher than {} chips.".format(str(mi)))
            return False

    async def check_cooldowns(self, userid, game):
        cd = game + " CD"
        if abs(self.casinosys["Players"][userid]["CD"][cd] - int(time.perf_counter())) >= self.casinosys["Games"][game]["Cooldown"]:
            self.casinosys["Players"][userid]["CD"][cd] = int(time.perf_counter())
            fileIO("data/casino/casino.json", "save", self.casinosys)
            return True
        elif self.casinosys["Players"][userid]["CD"][cd] == 0:
            self.casinosys["Players"][userid]["CD"][cd] = int(time.perf_counter())
            return True
        else:
            s = abs(self.casinosys["Players"][userid]["CD"][cd] - int(time.perf_counter()))
            seconds = abs(s - self.casinosys["Games"][game]["Cooldown"])
            await self.bot.say("This game has a cooldown. You still have: ")
            await self.time_formatting(seconds)
            return False

    async def time_formatting(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        await self.bot.say("```{} hours, {} minutes and {} seconds remaining```".format(h, m, s))

    def time_format(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            msg = "{} hours, {} minutes, {} seconds".format(h, m, s)
        elif h == 0 and m > 0:
            msg = "{} minutes, {} seconds".format(h, m, s)
        elif m == 0 and h == 0 and s > 0:
            msg = "{} seconds".format(h, m, s)
        elif m == 0 and h == 0 and s == 0:
            msg = "No cooldown"
        return msg

    def draw_two(self):
        card1 = random.choice(self.deck)
        card2 = random.choice(self.deck)
        hand = []
        hand.append(card1)
        hand.append(card2)
        return hand

    def draw_card(self, hand):
        card = random.choice(self.deck)
        hand.append(card)
        return hand

    def count_hand(self, hand):
        count = 0
        for i in hand:
            if i in self.card_values:
                count += self.card_values[i]
            else:
                pass
        for x in hand:
            if x == 'Ace':
                # Ace exceptions:
                if count + 11 > 21:
                    count += 1
                elif hand.count('Ace') == 1:
                    count += 11
                else:
                    count += 1
            else:
                pass
        return count

    def dealer(self):
        dh = self.draw_two()
        count = self.count_hand(dh)

        # forces hit if ace in first two cards
        if 'Ace' in dh:
            dh = self.draw_card(dh)
            count = self.count_hand(dh)

        # defines maximum hit score X
        while count < 16:
            self.draw_card(dh)
            count = self.count_hand(dh)
        return dh

    async def player(self, dh, user):
        ph = self.draw_two()
        count = self.count_hand(ph)
        msg = user.mention + "\n"
        msg += "Your cards: %s" % " ".join(ph) + "\n"
        msg += "Your score: %d" % count + "\n"
        msg += "The dealer shows: %s" % dh[0] + "\n"
        if count == 21:
            return ph
        msg += "hit or stay"
        await self.bot.say(msg)
        a = True
        while a:
            choice = await self.bot.wait_for_message(timeout=15, author=user)
            if choice.content == "Hit" or choice.content == "hit":
                ph = self.draw_card(ph)
                count = self.count_hand(ph)
                msg1 = user.mention + "\n"
                msg1 += "Your cards: %s" % " ".join(ph) + "\n"
                msg1 += "Your score: %d" % count + "\n"
                msg1 += "The dealer shows: %s" % dh[0] + "\n"
                await self.bot.say(msg1)
                if count >= 21:
                    a = False
                    break
                else:
                    await self.bot.say("hit or stay?")
            elif choice.content == "Stay" or choice.content == "stay":
                a = False
                break
            elif choice.content is None:
                a = False
                break
            else:
                await self.bot.say("You must choose hit or stay.")
                continue
        return ph

    async def blackjack_game(self, user, amount):
        chips = self.casinosys["System Config"]["Chip Name"]
        dh = self.dealer()
        ph = await self.player(dh, user)
        dc = self.count_hand(dh)
        pc = self.count_hand(ph)
        if dc > 21 and pc <= 21:
            msg = "----------------------" + "\n"
            msg += " The dealer's hand: %s" % " ".join(dh) + "\n"
            msg += "The dealer's score: %d" % dc + "\n"
            msg += "        Your score: %d" % pc + "\n"
            msg += "      Dealer Bust!" + "\n"
            msg += "*******" + user.name + " Wins!*******"
            await self.bot.say("```" + msg + "```")
            total = amount * self.casinosys["Games"]["Blackjack"]["Multiplier"]
            self.casinosys["Players"][user.id]["Chips"] += amount
            await self.add_chips(user.id, total)
            self.casinosys["Players"][user.id]["Won"]["BJ Won"] += 1
            fileIO("data/casino/casino.json", "save", self.casinosys)
            return True
        elif dc == pc:
            msg = "----------------------" + "\n"
            msg += " The dealer's hand: %s" % " ".join(dh) + "\n"
            msg += "The dealer's score: %d" % dc + "\n"
            msg += "        Your score: %d" % pc + "\n"
            msg += user.name + "  Pushed."
            await self.bot.say("```" + msg + "```")
            amount = int(round(amount))
            self.casinosys["Players"][user.id]["Chips"] += amount
            await self.bot.say("Returned {} {} chips to your account.".format(str(amount), chips))
            fileIO("data/casino/casino.json", "save", self.casinosys)
            return False
        elif pc > 21:
            msg = "----------------------" + "\n"
            msg += "        Bust!" + "\n"
            msg += "======" + user.name + "  Lost!======"
            await self.bot.say("```" + msg + "```")
            return False
        elif dc >= pc:
            msg = "----------------------" + "\n"
            msg += " The dealer's hand: %s" % " ".join(dh) + "\n"
            msg += "The dealer's score: %d" % dc + "\n"
            msg += "        Your score: %d" % pc + "\n"
            msg += "======" + user.name + "  Lost!======"
            await self.bot.say("```" + msg + "```")
            return False
        else:
            msg = "----------------------" + "\n"
            msg += " The dealer's hand: %s" % " ".join(dh) + "\n"
            msg += "The dealer's score: %d" % dc + "\n"
            msg += "        Your score: %d" % pc + "\n"
            msg += "*******" + user.name + " Wins!*******"
            await self.bot.say("```" + msg + "```")
            total = amount * self.casinosys["Games"]["Blackjack"]["Multiplier"]
            self.casinosys["Players"][user.id]["Chips"] += amount
            await self.add_chips(user.id, total)
            self.casinosys["Players"][user.id]["Won"]["BJ Won"] += 1
            fileIO("data/casino/casino.json", "save", self.casinosys)
            return True

    async def send_long_message(self, channel, message, truncate=False,
                                max_lines=15):
        for msg in long_message(message, truncate, max_lines):
            await self.bot.send_message(channel, msg)


def split_every(s, n):
    return [s[i:i + n] for i in range(0, len(s), n)]


def long_message(output, truncate=False, max_lines=15):
    output = output.strip()
    return ["\n".join(output.split("\n")[:max_lines]) +
            "\n... *Search results truncated. " +
            "Send me a command over PM to show more!*"] \
        if truncate and output.count("\n") > max_lines \
        else split_every(output, 2000)


def check_folders():
    if not os.path.exists("data/casino"):
        print("Creating data/casino folder...")
        os.makedirs("data/casino")


def check_files():
    system = {"System Config": {"Casino Name": "Redjumpman",
                                "Casino Open": True,
                                "Chip Name": "Jump",
                                "Chip Rate": 1,
                                "Credit Rate": 1,
                                "Membership Lvl 0": "Basic",
                                "Membership Lvl 1": "Silver",
                                "Membership Lvl 2": "Gold",
                                "Membership Lvl 3": "Platnium"},
              "Games": {"Dice": {"Multiplier": 2.2, "Cooldown": 0, "Open": True, "Min": 50, "Max": 500},
                        "Coin": {"Multiplier": 1.5, "Cooldown": 0, "Open": True, "Min": 10, "Max": 10},
                        "Cups": {"Multiplier": 2.2, "Cooldown": 0, "Open": True, "Min": 50, "Max": 500},
                        "Blackjack": {"Multiplier": 2.2, "Cooldown": 0, "Open": True, "Min": 50, "Max": 500},
                        "Allin": {"Multiplier": 2.2, "Cooldown": 86400, "Open": True, "Min": 50, "Max": 500}
                        },
              "Players": {},
              }

    f = "data/casino/casino.json"
    if not fileIO(f, "check"):
        print("Creating default casino.json...")
        fileIO(f, "save", system)
    else:  # consistency check
        current = fileIO(f, "load")
        if current["System Config"].keys() != system["System Config"].keys():
            for key in system["System Config"].keys():
                if key not in current["System Config"].keys():
                    current["System Config"][key] = system["System Config"][key]
                    print("Adding " + str(key) +
                          " field to casino's casinosys.json")
            fileIO(f, "save", current)


def setup(bot):
    check_folders()
    check_files()
    if tabulateAvailable:
        bot.add_cog(Casino(bot))
    else:
        raise RuntimeError("You need to run 'pip3 install tabulate'")
