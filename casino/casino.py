# Developed by Redjumpman for Redbot
# Inspired by Spriter's work on a modded economy.
# Creates 1 json file and requires tabulate
import os
import discord
import random
import time
import asyncio
from fractions import Fraction
from operator import itemgetter
from .utils.dataIO import dataIO
from .utils import checks
from discord.ext import commands
from __main__ import send_cmd_help
try:   # Check if Tabulate is installed
    from tabulate import tabulate
    tabulateAvailable = True
except ImportError:
    tabulateAvailable = False


class Casino:
    """Casino"""

    def __init__(self, bot):
        self.bot = bot
        try:
            self.legacy_path = "data/casino/casino.json"
            self.legacy_system = dataIO.load_json(self.legacy_path)
            self.legacy_available = True
        except:
            self.legacy_available = False
        self.file_path = "data/JumperCogs/casino/casino.json"
        self.system = dataIO.load_json(self.file_path)
        self.games = ["Blackjack", "Coin", "Allin", "Cups", "Dice", "Hi-Lo"]
        self.deck = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'Jack', 'Queen', 'King', 'Ace']
        self.card_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
                            '10': 10, 'Jack': 10, 'Queen': 10, 'King': 10}
        self.version = "1.3"

    @commands.group(pass_context=True, no_pm=True)
    async def casino(self, ctx):
        """Casino Group Commands"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @casino.command(name="leaderboard", pass_context=True)
    async def _leaderboard_casino(self, ctx):
        """Displays Casino Leaderboard"""
        channel = ctx.message.channel
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if settings["Players"] is not None:
            players = [subdict["Name"] for subdict in settings["Players"].values()]
            chips = [subdict["Chips"] for subdict in settings["Players"].values()]
            rank = [position[0] + 1 for position in enumerate(players)]
            m = zip(players, chips)
            m = sorted(m, key=itemgetter(1), reverse=True)
            players = [x[0] for x in m]
            chips = [x[1] for x in m]
            li = list(zip(rank, players, chips))
            headers = ["Rank", "Names", "Chips"]
            t = tabulate(li, headers=headers, numalign="left",  tablefmt="simple")
            msg = "```Python\n" + t + "```"
            await self.send_long_message(channel, msg)
        else:
            await self.bot.say("There are no casino players to show on the leaderboard.")

    @casino.command(name="transfer", pass_context=True)
    async def _transfer_casino(self, ctx):
        """Transfers account info from old casino. Limit 1 transfer per user"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if user.id in settings["Players"]:
            msg = "I can't transfer data if you already have an account with the new casino."
        elif not self.legacy_available:
            msg = "No legacy file was found. Unable to perform membership transfers."
        elif user.id in self.legacy_system["Players"]:
            await self.bot.say("Account for {} found. Your casino data will be transfered to the "
                               "{} server. After your data is transfered your old data will be "
                               "deleted. I can only transfer data **one time**.\nDo you wish to "
                               "transfer?".format(user.name, server.name))
            response = await self.bot.wait_for_message(timeout=15, author=user)
            if response is None:
                msg = "No response, transfer cancelled."
            elif response.content.title() == "No":
                msg = "Transfer cancelled."
            elif response.content.title() == "Yes":
                old_data = self.legacy_system["Players"][user.id]
                transfer = {user.id: old_data}
                settings["Players"].update(transfer)
                self.legacy_system["Players"].pop(user.id)
                dataIO.save_json(self.legacy_path, self.legacy_system)
                dataIO.save_json(self.file_path, self.system)
                msg = "Data transfer successful. You can now access your old casino data."
            else:
                msg = "Improper response. Please state yes or no. Cancelling transfer."
        else:
            msg = "Unable to locate your previous data."
        await self.bot.say(msg)

    @casino.command(name="join", pass_context=True)
    async def _join_casino(self, ctx):
        """Grants you membership access to the casino"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if user.id not in settings["Players"]:
            settings["Players"][user.id] = {"Chips": 100,
                                            "Membership": None,
                                            "Name": user.name,
                                            "Played": {"Dice Played": 0,
                                                       "Cups Played": 0,
                                                       "BJ Played": 0,
                                                       "Coin Played": 0,
                                                       "Allin Played": 0,
                                                       "Hi-Lo Played": 0},
                                            "Won": {"Dice Won": 0,
                                                    "Cups Won": 0,
                                                    "BJ Won": 0,
                                                    "Coin Won": 0,
                                                    "Allin Won": 0,
                                                    "Hi-Lo Won": 0},
                                            "CD": {"Dice CD": 0,
                                                   "Cups CD": 0,
                                                   "Blackjack CD": 0,
                                                   "Coin CD": 0,
                                                   "Allin CD": 0,
                                                   "Hi-Lo CD": 0}
                                            }
            dataIO.save_json(self.file_path, self.system)
            name = settings["System Config"]["Casino Name"]
            msg = ("Your membership has been approved! Welcome to {} Casino!\nAs a first time "
                   "member we have credited your account with 100 free chips. "
                   "\nHave fun!".format(name))
        else:
            msg = "You are already a member."
        await self.bot.say(msg)

    @casino.command(name="exchange", pass_context=True)
    async def _exchange_casino(self, ctx, currency: str, amount: int):
        """Exchange chips for credits and credits for chips"""
        bank = self.bot.get_cog('Economy').bank
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        currency = currency.title()
        chip_rate = settings["System Config"]["Chip Rate"]
        credit_rate = settings["System Config"]["Credit Rate"]
        chip_multiple = Fraction(chip_rate).limit_denominator().denominator
        credit_multiple = Fraction(credit_rate).limit_denominator().denominator
        chip_name = settings["System Config"]["Chip Name"]
        casino_name = settings["System Config"]["Casino Name"]
        if user.id not in settings["Players"]:
            msg = ("You need a {} Casino membership. To get one type "
                   "!casino join.".format(casino_name))
        elif currency not in ["Chips", "Credits"]:
            msg = "I can only exchange chips or credits, please specify one."
        elif currency == "Chips":
            if amount <= 0 and amount % credit_multiple != 0:
                msg = ("The amount must be higher than 0 and "
                       "a multiple of {}.".format(credit_multiple))
            elif amount <= settings["Players"][user.id]["Chips"]:
                await self.subtract_chips(user.id, amount, ctx, settings)
                credits = int(amount * credit_rate)
                bank.deposit_credits(user, credits)
                msg = ("I have exchanged {} {} chips into {} credits.\nThank you for playing at "
                       "{} Casino.".format(amount, chip_name, str(int(credits)), casino_name))
            else:
                msg = "You don't have that many chips to exchange."
        elif currency == "Credits":
            if amount <= 0 and amount % chip_multiple != 0:
                msg = "The amount must be higher than 0 and a multiple of {}.".format(chip_multiple)
            elif bank.can_spend(user, amount):
                bank.withdraw_credits(user, amount)
                chip_amount = int(amount * chip_rate)
                settings["Players"][user.id]["Chips"] += chip_amount
                dataIO.save_json(self.file_path, self.system)
                msg = ("I have exchanged {} credits for {} {} chips.\nEnjoy your time at "
                       "{} Casino!".format(amount, chip_amount, chip_name, casino_name))
            else:
                msg = "You don't have that many credits to exchange."
        await self.bot.say(msg)

    @casino.command(name="stats", pass_context=True)
    async def _stats_casino(self, ctx):
        """Shows your casino play stats"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        casino_name = settings["System Config"]["Casino Name"]
        if user.id in settings["Players"]:
            column1 = list(sorted(settings["Games"].keys()))
            column2 = [x[1] for x in sorted(settings["Players"][user.id]["Played"].items(),
                       key=lambda tup: tup[0])
                       ]
            column3 = [x[1] for x in sorted(settings["Players"][user.id]["Won"].items(),
                       key=lambda tup: tup[0])
                       ]
            m = list(zip(column1, column2, column3))
            t = tabulate(m, headers=["Game", "Played", "Won"])
            msg = "```Python\n{}```".format(t)
        else:
            msg = ("You need a {} Casino membership. To get one type {}casino "
                   "join .".format(casino_name, ctx.prefix))
        await self.bot.say(msg)

    @casino.command(name="info", pass_context=True)
    async def _info_casino(self, ctx):
        """Shows information about the server casino"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        games = settings["Games"].keys()
        multiplier = [subdict["Multiplier"] for subdict in settings["Games"].values()]
        min_bet = [subdict["Min"] for subdict in settings["Games"].values()]
        max_bet = [subdict["Max"] for subdict in settings["Games"].values()]
        cooldown = [subdict["Cooldown"] for subdict in settings["Games"].values()]
        time = []
        chip_exchange_rate = settings["System Config"]["Chip Rate"]
        chip_ratio = str(Fraction(chip_exchange_rate).limit_denominator()).replace("/", ":")
        if chip_ratio == "1":
            chip_ratio = "1:1"
        credit_exchange_rate = settings["System Config"]["Credit Rate"]
        credit_ratio = str(Fraction(credit_exchange_rate).limit_denominator()).replace("/", ":")
        if credit_ratio == "1":
            credit_ratio = "1:1"
        for x in cooldown:
            d = self.time_format(x)
            time.append(d)
        m = list(zip(games, multiplier, min_bet, max_bet, time))
        m = sorted(m, key=itemgetter(0))
        t = tabulate(m, headers=["Game", "Multiplier", "Min Bet", "Max Bet", "Cooldown"])
        msg = "```\n"
        msg += t + "\n" + "\n"
        msg += "Credit Exchange Rate:    " + credit_ratio + "\n"
        msg += "Chip Exchange Rate:      " + chip_ratio + "\n"
        msg += "Casino Members: " + str(len(settings["Players"].keys()))
        msg += "```"
        await self.bot.say(msg)

    @casino.command(name="balance", pass_context=True)
    async def _balance_casino(self, ctx):
        """Shows your number of chips"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        casino_name = settings["System Config"]["Casino Name"]
        if user.id in settings["Players"]:
            amount = settings["Players"][user.id]["Chips"]
            chips = settings["System Config"]["Chip Name"]
            msg = "```Python\nYou have {} {} chips.```".format(amount, chips)
        else:
            msg = ("You need a {} Casino membership. To get one type "
                   "{}casino join .".format(casino_name, ctx.prefix))
        await self.bot.say(msg)

    @casino.command(name="remove", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _remove_casino(self, ctx, user: discord.Member):
        """Remove a user from casino"""
        author = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if user.id not in settings["Players"]:
            msg = "This user is not a member of the casino."
        else:
            await self.bot.say("Are you sure you want to remove player data for {}? Type {} to "
                               "confirm.".format(user.name, user.name))
            response = await self.bot.wait_for_message(timeout=15, author=author)
            if response is None:
                msg = "No response. Player removal cancelled."
            elif response.content.title() == user.name:
                settings["Players"].pop(user.id)
                dataIO.save_json(self.file_path, self.system)
                msg = "{}\'s casino data has been removed by {}.".format(user.name, author.name)
            else:
                msg = "Incorrect name. Cancelling player removal."
        await self.bot.say(msg)

    @casino.command(name="wipe", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _wipe_casino(self, ctx):
        """Wipe casino server data"""
        user = ctx.message.author
        server = ctx.message.server
        if server.id not in self.system["Servers"]:
            msg = "This server hasn't used casino yet!"
        else:
            await self.bot.say("This will wipe casino server data.**WARNING** ALL PLAYER DATA WILL "
                               "BE DESTROYED.\nDo you wish to wipe casino data for this server?")
            response = await self.bot.wait_for_message(timeout=15, author=user)
            if response is None:
                msg = "No response, casino wipe cancelled."
            elif response.content.title() == "No":
                msg = "Cancelling casino wipe."
            elif response.content.title() == "Yes":
                await self.bot.say("To confirm type the server name: {}".format(server.name))
                response = await self.bot.wait_for_message(timeout=15, author=user)
                if response is None:
                    msg = "No response, casino wipe cancelled."
                elif response.content == server.name:
                    self.system["Servers"].pop(server.id)
                    dataIO.save_json(self.file_path, self.system)
                    msg = "Casino wiped."
                else:
                    msg = "Incorrect server name. Cancelling casino wipe."
            else:
                msg = "Improper response. Cancelling casino wipe."
        await self.bot.say(msg)

    @casino.command(name="reset", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _reset_casino(self, ctx):
        """Resets casino to default settings. Keeps user data"""
        user = ctx.message.author
        server = ctx.message.server
        default = {"System Config": {"Casino Name": "Redjumpman",
                                     "Casino Open": True,
                                     "Chip Name": "Jump",
                                     "Chip Rate": 1,
                                     "Credit Rate": 1,
                                     "Membership Lvl 0": "Basic",
                                     "Membership Lvl 1": "Silver",
                                     "Membership Lvl 2": "Gold",
                                     "Membership Lvl 3": "Platnium"},
                   "Games": {"Dice": {"Multiplier": 2.2, "Cooldown": 0, "Open": True, "Min": 50,
                                      "Max": 500},
                             "Coin": {"Multiplier": 1.5, "Cooldown": 0, "Open": True, "Min": 10,
                                      "Max": 10},
                             "Cups": {"Multiplier": 2.2, "Cooldown": 0, "Open": True, "Min": 50,
                                      "Max": 500},
                             "Blackjack": {"Multiplier": 2.2, "Cooldown": 0, "Open": True,
                                           "Min": 50, "Max": 500},
                             "Allin": {"Multiplier": 2.2, "Cooldown": 86400, "Open": True,
                                       "Min": 50, "Max": 500}
                             }
                   }
        settings = self.check_server_settings(server)
        await self.bot.say("This will reset casino to it's default settings and keep player data.\n"
                           "Do you wish to reset casino settings?")
        response = await self.bot.wait_for_message(timeout=15, author=user)
        if response is None:
            msg = "No response, reset cancelled."
        elif response.content.title() == "No":
            msg = "Cancelling reset."
        elif response.content.title() == "Yes":
            settings["System Config"] = default["System Config"]
            settings["Games"] = default["Games"]
            dataIO.save_json(self.file_path, self.system)
            msg = "Casino settings reset to default."
        else:
            msg = "Improper response. Cancelling reset."
        await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True, aliases=["hl", "hi-lo"])
    async def hilo(self, ctx, choice: str, bet: int):
        """Pick High, Low, Seven. Lo is < 7 Hi is > 7. 12x payout on 7"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        hilo_data = {"Played": {"Hi-Lo Played": 0}, "Won": {"Hi-Lo Won": 0}, "CD": {"Hi-Lo CD": 0}}
        game = "Hi-Lo"
        choice = str(choice).title()
        choices = ["Hi", "High", "Low", "Lo", "Seven", "7"]
        casino_name = settings["System Config"]["Casino Name"]
        if user.id not in settings["Players"]:
            await self.bot.say("You need a {} Casino membership. To get one type "
                               "{}casino join .".format(casino_name, ctx.prefix))
        elif not settings["System Config"]["Casino Open"]:
            await self.bot.say("The {} Casino is closed.".format(casino_name))
        elif choice not in choices:
            await self.bot.say("Incorrect response. "
                               "Accepted response are:\n{}".format(", ".join(choices)))
        elif await self.minmax_check(bet, game, settings):
            if "Hi-Lo Played" not in settings["Players"][user.id]["Played"].keys():
                self.game_add(settings["Players"][user.id], hilo_data)
            if await self.check_cooldowns(user.id, game, settings):
                if await self.subtract_chips(user.id, bet, ctx, settings):
                    await self.bot.say("The dice hit the table and slowly fall into place...")
                    await asyncio.sleep(2)
                    settings["Players"][user.id]["Played"]["Hi-Lo Played"] += 1
                    outcome, result = self.hl_outcome()
                    if choice in result:
                        msg = "Congratulations the outcome was {} ({})".format(outcome, result[0])
                        if result[0] == "Seven":
                            amount = bet * 12
                            msg += "\n**BONUS!** 12x multiplier for Seven!"
                        else:
                            amount = bet * settings["Games"]["Hi-Lo"]["Multiplier"]
                        await self.add_chips(user.id, amount, settings)
                        settings["Players"][user.id]["Won"]["Hi-Lo Won"] += 1
                    else:
                        msg = "Sorry. The outcome was {} ({})".format(outcome, result[0])
                    dataIO.save_json(self.file_path, self.system)
                    await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True)
    async def cups(self, ctx, cup: int, bet: int):
        """Pick the cup that is hiding the gold coin. Choose 1, 2, 3, or 4"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        game = "Cups"
        casino_name = settings["System Config"]["Casino Name"]
        if user.id not in settings["Players"]:
            await self.bot.say("You need a {} Casino membership. To get one type "
                               "{}casino join .".format(casino_name, ctx.prefix))
        elif not settings["System Config"]["Casino Open"]:
            await self.bot.say("The {} Casino is closed.".format(casino_name))
        elif cup >= 5 or cup <= 0:
            await self.bot.say("You need to pick a cup 1-4.")
        elif await self.minmax_check(bet, game, settings):
            if await self.check_cooldowns(user.id, game, settings):
                if await self.subtract_chips(user.id, bet, ctx, settings):
                    outcome = random.randint(1, 4)
                    await self.bot.say("The cups start shuffling along the table...")
                    await asyncio.sleep(2)
                    settings["Players"][user.id]["Played"]["Cups Played"] += 1
                    if cup == outcome:
                        amount = bet * settings["Games"]["Cups"]["Multiplier"]
                        settings["Players"][user.id]["Won"]["Cups Won"] += 1
                        await self.add_chips(user.id, amount, settings)
                        msg = "Congratulations! The coin was under cup {}!".format(outcome)
                    else:
                        msg = "Sorry! The coin was under cup {}.".format(outcome)
                    dataIO.save_json(self.file_path, self.system)
                    await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True)
    async def coin(self, ctx, choice: str, bet: int):
        """Bet on heads or tails"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        choice = choice.title()
        possible = ["Heads", "Tails"]
        game = "Coin"
        casino_name = settings["System Config"]["Casino Name"]
        if user.id not in settings["Players"]:
            await self.bot.say("You need a {} Casino membership. To get a membership, "
                               "type {}casino join .".format(casino_name, ctx.prefix))
        elif not settings["System Config"]["Casino Open"]:
            await self.bot.say("The {} Casino is closed.".format(casino_name))
        elif choice not in ["Heads", "Tails"]:
            await self.bot.say("You need to pick heads or tails")
        elif await self.minmax_check(bet, game, settings):
            if await self.check_cooldowns(user.id, game, settings):
                if await self.subtract_chips(user.id, bet, ctx, settings):
                    outcome = random.choice(possible)
                    await self.bot.say("The coin flips into the air...")
                    await asyncio.sleep(2)
                    settings["Players"][user.id]["Played"]["Coin Played"] += 1
                    if choice == outcome:
                        amount = bet * settings["Games"]["Coin"]["Multiplier"]
                        await self.add_chips(user.id, amount, settings)
                        settings["Players"][user.id]["Won"]["Coin Won"] += 1
                        msg = "Congratulations! The coin landed on {}!".format(outcome)
                    else:
                        msg = "Sorry! The coin landed on {}.".format(outcome)
                    dataIO.save_json(self.file_path, self.system)
                    await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True)
    async def dice(self, ctx, bet: int):
        """Roll 2, 7, 11 or 12 to win."""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        winning_numbers = [2, 7, 11, 12]
        game = "Dice"
        casino_name = settings["System Config"]["Casino Name"]
        if user.id not in settings["Players"]:
            await self.bot.say("You need a {} Casino membership. To get one type "
                               "{}casino join .".format(casino_name, ctx.prefix))
        elif not settings["System Config"]["Casino Open"]:
            await self.bot.say("The {} Casino is closed.".format(casino_name))
        elif await self.minmax_check(bet, game, settings):
            if await self.check_cooldowns(user.id, game, settings):
                if await self.subtract_chips(user.id, bet, ctx, settings):
                    outcome = random.randint(1, 12)
                    await self.bot.say("The dice strike the back of the table and begin to tumble "
                                       "into place...")
                    await asyncio.sleep(2)
                    settings["Players"][user.id]["Played"]["Dice Played"] += 1
                    if outcome in winning_numbers:
                        amount = bet * settings["Games"]["Dice"]["Multiplier"]
                        msg = "Congratulations! The dice landed on {}.".format(outcome)
                        await self.add_chips(user.id, amount, settings)
                        settings["Players"][user.id]["Won"]["Dice Won"] += 1
                    else:
                        msg = "Sorry! The dice landed on {}.".format(outcome)
                    dataIO.save_json(self.file_path, self.system)
                    await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True, aliases=["bj", "21"])
    async def blackjack(self, ctx, bet: int):
        """Modified Blackjack."""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        game = "Blackjack"
        casino_name = settings["System Config"]["Casino Name"]
        if user.id not in settings["Players"]:
            await self.bot.say("You need a {} Casino membership. To get one type "
                               "{}casino join .".format(casino_name, ctx.prefix))
        elif not settings["System Config"]["Casino Open"]:
            await self.bot.say("The {} Casino is closed.".format(casino_name))
        elif await self.minmax_check(bet, game, settings):
            if await self.check_cooldowns(user.id, game, settings):
                if await self.subtract_chips(user.id, bet, ctx, settings):
                    settings["Players"][user.id]["Played"]["BJ Played"] += 1
                    await self.blackjack_game(user, bet, ctx, settings)
                    dataIO.save_json(self.file_path, self.system)

    @commands.command(pass_context=True, no_pm=True)
    async def allin(self, ctx, multiplier: int):
        """It's all or nothing. Bets everything you have."""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        game = "Allin"
        chips = settings["System Config"]["Chip Name"]
        bet = int(settings["Players"][user.id]["Chips"])
        casino_name = settings["System Config"]["Casino Name"]
        if not settings["System Config"]["Casino Open"]:
            await self.bot.say("The {} Casino is closed.".format(casino_name))
        elif await self.check_cooldowns(user.id, game, settings):
            amount = multiplier * settings["Players"][user.id]["Chips"]
            if await self.subtract_chips(user.id, bet, ctx, settings):
                outcome = random.randrange(0, multiplier + 1)
                await self.bot.say("You put all your chips into the machine and pull the lever...")
                settings["Players"][user.id]["Played"]["Allin Played"] += 1
                await asyncio.sleep(3)
                if outcome == 0:
                    msg = "Jackpot!! You just won {} chips!!".format(amount)
                    await self.add_chips(user.id, amount, settings)
                    settings["Players"][user.id]["Won"]["Allin Won"] += 1
                else:
                    msg = ("Sorry! Your all or nothing gamble failed and you lost "
                           "{} {} chips.".format(bet, chips))
                dataIO.save_json(self.file_path, self.system)
                await self.bot.say(msg)

    @casino.command(name="toggle", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _toggle_casino(self, ctx):
        """Opens and closes the casino"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        casino_name = settings["System Config"]["Casino Name"]
        if settings["System Config"]["Casino Open"]:
            settings["System Config"]["Casino Open"] = False
            msg = "The {} Casino is now closed.".format(casino_name)
        else:
            settings["System Config"]["Casino Open"] = True
            msg = "The {} Casino is now open!".format(casino_name)
        dataIO.save_json(self.file_path, self.system)
        await self.bot.say(msg)

    @commands.group(pass_context=True, no_pm=True)
    async def setcasino(self, ctx):
        """Configures Casino Options"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @setcasino.command(name="multiplier", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _multiplier_setcasino(self, ctx, game: str, multiplier: float):
        """Sets the payout multiplier for casino games"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        game = game.title()
        if game not in self.games:
            msg = "This game does not exist. Please pick from: {}".format(", ".join(self.games))
        elif multiplier > 0:
            multiplier = float(abs(multiplier))
            settings["Games"][game]["Multiplier"] = multiplier
            dataIO.save_json(self.file_path, self.system)
            msg = "Now setting the payout multiplier for {} to {}".format(game, multiplier)
        else:
            msg = "Multiplier needs to be higher than 0."
        await self.bot.say(msg)

    @setcasino.command(name="balance", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _balance_setcasino(self, ctx, user: discord.Member, chips: int):
        """Sets a Casino member's chip balance"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        chip_name = settings["System Config"]["Chip Name"]
        casino_name = settings["System Config"]["Casino Name"]
        if user.id in settings["Players"]:
            settings["Players"][user.id]["Chips"] = chips
            dataIO.save_json(self.file_path, self.system)
            msg = ("```Python\nSetting the chip balance of {} to "
                   "{} {} chips.```".format(user.name, chips, chip_name))
        else:
            msg = "{} needs a {} Casino membership.".format(user.name, casino_name)
        await self.bot.say(msg)

    @setcasino.command(name="membership", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _membership_setcasino(self, ctx, level: int, *, name: str):
        """Sets the membership names. 0 is granted on joining, 3 is the highest."""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if level < 4:
            m = "Membership Lvl " + str(level)
            settings["System Config"][m] = name
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("Changed {} name to {}".format(m, name))
        else:
            li = ", ".join(self.games)
            await self.bot.say("This game does not exist. Please pick from: " + li)

    @setcasino.command(name="name", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _name_setcasino(self, ctx, *, name: str):
        """Sets the name of the Casino."""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        settings["System Config"]["Casino Name"] = name
        dataIO.save_json(self.file_path, self.system)
        await self.bot.say("Changed the casino name to {}.".format(name))

    @setcasino.command(name="exchange", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _exchange_setcasino(self, ctx, rate: float, currency: str):
        """Sets the exchange rate for chips or credits"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if rate <= 0:
            msg = "Rate must be higher than 0. Default is 1."
        elif currency.title() == "Chips":
            settings["System Config"]["Chip Rate"] = rate
            dataIO.save_json(self.file_path, self.system)
            msg = "Setting the exchange rate for credits to chips to {}".format(rate)
        elif currency.title() == "Credits":
            settings["System Config"]["Credit Rate"] = rate
            dataIO.save_json(self.file_path, self.system)
            msg = "Setting the exchange rate for chips to credits to {}".format(rate)
        else:
            msg = "Please specify chips or credits"
        await self.bot.say(msg)

    @setcasino.command(name="chipname", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _chipname_setcasino(self, ctx, *, name: str):
        """Sets the name of your Casino chips."""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        settings["System Config"]["Chip Name"] = name
        dataIO.save_json(self.file_path, self.system)
        msg = ("Changed the name of your chips to {0}.\nTest Display:\n"
               "```Python\nCongratulations, you just won 50 {0} chips.```".format(name))
        await self.bot.say(msg)

    @setcasino.command(name="cooldown", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _cooldown_setcasino(self, ctx, game, seconds: int):
        """Set the cooldown period for casino games"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        game = game.title()
        if game not in self.games:
            msg = "This game does not exist. Please pick from: {}".format(", ".join(self.games))
        else:
            settings["Games"][game]["Cooldown"] = seconds
            dataIO.save_json(self.file_path, self.system)
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            msg = ("Setting the cooldown period for {} to {} hours, {} minutes and "
                   "{} seconds".format(game, h, m, s))
        await self.bot.say(msg)

    @setcasino.command(name="max", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _max_setcasino(self, ctx, game, maxbet: int):
        """Set the maximum bet to play a game"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        game = game.title()
        if game not in self.games:
            msg = "This game does not exist. Please pick from: {}".format(", ".join(self.games))
        elif maxbet <= 0:
            msg = "You need to set a maximum bet higher than 0."
        elif maxbet > settings["Games"][game]["Min"]:
            settings["Games"][game]["Max"] = maxbet
            chips = settings["System Config"]["Chip Name"]
            dataIO.save_json(self.file_path, self.system)
            msg = "Setting the maximum bet for {} to {} {} chips.".format(game, maxbet, chips)
        else:
            minbet = settings["Games"][game]["Min"]
            msg = "The max bet needs be higher than the minimum bet of {}.".format(minbet)
        await self.bot.say(msg)

    @setcasino.command(name="min", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _min_setcasino(self, ctx, game, minbet: int):
        """Set the minimum bet to play a game"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        game = game.title()
        if game not in self.games:
            msg = "This game does not exist. Please pick from: {}".format(", ".join(self.games))
        elif minbet < 0:
            msg = "You need to set a minimum bet higher than 0."
        elif minbet < settings["Games"][game]["Max"]:
            settings["Games"][game]["Min"] = minbet
            chips = settings["System Config"]["Chip Name"]
            dataIO.save_json(self.file_path, self.system)
            msg = "Setting the minimum bet for {} to {} {} chips.".format(game, minbet, chips)
        else:
            maxbet = settings["Games"][game]["Max"]
            msg = ("The minimum bet can't bet set higher than the maximum bet of "
                   "{} for {}.".format(maxbet, game))
        await self.bot.say(msg)

    async def add_credits(self, user, amount):
        bank = self.bot.get_cog('Economy').bank
        bank.deposit_credits(user, amount)
        await self.bot.say("{} credits were deposited into your account.".format(amount))

    async def add_chips(self, user, amount, settings):
        amount = int(round(amount))
        settings["Players"][user]["Chips"] += amount
        dataIO.save_json(self.file_path, self.system)
        chips = settings["System Config"]["Chip Name"]
        await self.bot.say("```Python\n" + "Congratulations, you just won {} {} chips."
                           "```".format(amount, chips))

    async def subtract_chips(self, userid, number, ctx, settings):
        chips = settings["System Config"]["Chip Name"]
        casino_name = settings["System Config"]["Casino Name"]
        if userid in settings["Players"]:
            if settings["Players"][userid]["Chips"] >= number:
                settings["Players"][userid]["Chips"] -= number
                dataIO.save_json(self.file_path, self.system)
                return True
            else:
                await self.bot.say("You do not have enough {} chips.".format(chips))
                return False
        else:
            await self.bot.say("You need a {} Casino membership. To get one type "
                               "{}casino join .".format(casino_name, ctx.prefix))
            return False

    async def minmax_check(self, bet, game, settings):
        mi = settings["Games"][game]["Min"]
        mx = settings["Games"][game]["Max"]
        if bet >= mi:
            if bet <= mx:
                return True
            else:
                await self.bot.say("Your bet exceeds the maximum of {} chips.".format(mx))
                return False
        else:
            await self.bot.say("Your bet needs to be higher than {} chips.".format(mi))
            return False

    async def check_cooldowns(self, userid, game, settings):
        cd = game + " CD"
        path = settings["Games"][game]["Cooldown"]
        if abs(settings["Players"][userid]["CD"][cd] - int(time.perf_counter())) >= path:
            settings["Players"][userid]["CD"][cd] = int(time.perf_counter())
            dataIO.save_json(self.file_path, self.system)
            return True
        elif settings["Players"][userid]["CD"][cd] == 0:
            settings["Players"][userid]["CD"][cd] = int(time.perf_counter())
            dataIO.save_json(self.file_path, self.system)
            return True
        else:
            s = abs(settings["Players"][userid]["CD"][cd] - int(time.perf_counter()))
            seconds = abs(s - settings["Games"][game]["Cooldown"])
            await self.bot.say("This game has a cooldown. You still have: ")
            await self.time_formatting(seconds)
            return False

    async def time_formatting(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        await self.bot.say("```{} hours, {} minutes and {} seconds remaining```".format(h, m, s))

    async def send_long_message(self, channel, message, truncate=False,
                                max_lines=15):
        for msg in long_message(message, truncate, max_lines):
            await self.bot.send_message(channel, msg)

    async def player(self, dh, user, amount, ctx, settings):
        ph = self.draw_two()
        count = self.count_hand(ph)
        msg = user.mention + "\n"
        msg += "Your cards: %s" % " ".join(ph) + "\n"
        msg += "Your score: %d" % count + "\n"
        msg += "The dealer shows: %s" % dh[0] + "\n"
        if count == 21:
            return ph, dh, amount
        else:
            msg += "hit, stay, or double"
            await self.bot.say(msg)
            i = 0
            while count < 21:
                i = i + 1
                choice = await self.bot.wait_for_message(timeout=15, author=user)
                if choice is None:
                    break
                elif choice.content.title() == "Hit":
                    ph = self.draw_card(ph)
                    count = self.count_hand(ph)
                    msg1 = user.mention + "\n"
                    msg1 += "Your cards: %s" % " ".join(ph) + "\n"
                    msg1 += "Your score: %d" % count + "\n"
                    msg1 += "The dealer shows: %s" % dh[0] + "\n"
                    await self.bot.say(msg1)
                    if count >= 21:
                        break
                    else:
                        await self.bot.say("Hit or stay?")
                elif choice.content.title() == "Double":
                    if i <= 1:
                        if await self.subtract_chips(user.id, amount, ctx, settings):
                            amount = amount * 2
                            ph = self.draw_card(ph)
                            count = self.count_hand(ph)
                            break
                        else:
                            ret = "Because you can't cover this bet, please choose hit or stay."
                            await self.bot.say(ret)
                            continue
                    else:
                        await self.bot.say("You may only double down on the first deal.")
                        continue
                elif choice.content.title() == "Stay":
                    break
                else:
                    await self.bot.say("You must choose hit or stay.")
                    continue
            return ph, dh, amount

    async def blackjack_game(self, user, amount, ctx, settings):
        chips = settings["System Config"]["Chip Name"]
        dhand = self.dealer()
        ph, dh, amount = await self.player(dhand, user, amount, ctx, settings)
        dc = self.count_hand(dh)
        pc = self.count_hand(ph)
        if dc > 21 and pc <= 21:
            msg = "The dealer's hand: %s" % " ".join(dh) + "\n"
            msg += "The dealer's score: %d" % dc + "\n"
            msg += "        Your score: %d" % pc + "\n"
            msg += "      Dealer Bust!" + "\n"
            msg += "*******" + user.name + " Wins!*******"
            await self.bot.say("```" + msg + "```")
            total = amount * settings["Games"]["Blackjack"]["Multiplier"]
            settings["Players"][user.id]["Chips"] += amount
            await self.add_chips(user.id, total, settings)
            settings["Players"][user.id]["Won"]["BJ Won"] += 1
            return True
        elif pc > 21:
            msg = "      Your score: %d" % pc + "\n"
            msg += "          BUST!" + "\n"
            msg += "======" + user.name + "  Lost!======"
            await self.bot.say("```" + msg + "```")
            return False
        elif dc == pc and dc <= 21 and pc <= 21:
            msg = "The dealer's hand: %s" % " ".join(dh) + "\n"
            msg += "The dealer's score: %d" % dc + "\n"
            msg += "        Your score: %d" % pc + "\n"
            msg += user.name + "  Pushed."
            await self.bot.say("```" + msg + "```")
            amount = int(round(amount))
            settings["Players"][user.id]["Chips"] += amount
            await self.bot.say("Returned {} {} chips to your account.".format(amount, chips))
            return False
        elif dc > pc and dc <= 21:
            msg = "The dealer's hand: %s" % " ".join(dh) + "\n"
            msg += "The dealer's score: %d" % dc + "\n"
            msg += "        Your score: %d" % pc + "\n"
            msg += "======" + user.name + "  Lost!======"
            await self.bot.say("```" + msg + "```")
            return False
        else:
            msg = "The dealer's hand: %s" % " ".join(dh) + "\n"
            msg += "The dealer's score: %d" % dc + "\n"
            msg += "        Your score: %d" % pc + "\n"
            msg += "*******" + user.name + " Wins!*******"
            await self.bot.say("```" + msg + "```")
            total = amount * settings["Games"]["Blackjack"]["Multiplier"]
            settings["Players"][user.id]["Chips"] += amount
            await self.add_chips(user.id, total, settings)
            settings["Players"][user.id]["Won"]["BJ Won"] += 1
            return True

    # Casino Hooks TODO Turn this into a proper class
    # =======================================

    def chip_balance(self, user):
        server = user.server
        settings = self.check_server_settings(server)
        if user.id in settings["Players"]:
            balance = settings["Players"][user.id]["Chips"]
            return balance
        else:
            return 0

    def deposit_chips(self, user, amount):
        server = user.server
        settings = self.check_server_settings(server)
        if user.id in settings["Players"]:
            settings["Players"][user.id]["Chips"] += amount
        else:
            pass

    def withdraw_chips(self, user, amount):
        server = user.server
        settings = self.check_server_settings(server)
        if user.id in settings["Players"]:
            settings["Players"][user.id]["Chips"] -= amount
            dataIO.save_json(self.file_path, self.system)
        else:
            pass

    # =======================================================

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
        for x in hand:
            if x == 'Ace':
                # Ace exceptions:
                if count + 11 > 21:
                    count += 1
                elif hand.count('Ace') == 1:
                    count += 11
                else:
                    count += 1
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

    def hl_outcome(self):
        hi = [8, 9, 10, 11, 12]
        lo = [1, 2, 3, 4, 5, 6]
        outcome = random.randint(1, 12)
        if outcome in hi:
            result = ["High", "Hi"]
        elif outcome in lo:
            result = ["Low", "Lo"]
        else:
            result = ["Seven", "7"]
        return outcome, result

    def game_add(self, player_data, new_game, path=None):
        if path is None:
            path = []
        for key in new_game:
            if key in player_data:
                if isinstance(player_data[key], dict) and isinstance(new_game[key], dict):
                    self.game_add(player_data[key], new_game[key], path + [str(key)])
                elif player_data[key] == new_game[key]:
                    pass
                else:
                    raise Exception("Conflict at {}".format("".join(path + [str(key)])))
            else:
                player_data[key] = new_game[key]
        dataIO.save_json(self.file_path, self.system)

    def time_format(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            msg = "{} hours, {} minutes, {} seconds".format(h, m, s)
        elif h == 0 and m > 0:
            msg = "{} minutes, {} seconds".format(m, s)
        elif m == 0 and h == 0 and s > 0:
            msg = "{} seconds".format(s)
        elif m == 0 and h == 0 and s == 0:
            msg = "No cooldown"
        return msg

    def check_server_settings(self, server):
        if server.id not in self.system["Servers"]:
            default = {"System Config": {"Casino Name": "Redjumpman",
                                         "Casino Open": True,
                                         "Chip Name": "Jump",
                                         "Chip Rate": 1,
                                         "Credit Rate": 1,
                                         "Membership Lvl 0": "Basic",
                                         "Membership Lvl 1": "Silver",
                                         "Membership Lvl 2": "Gold",
                                         "Membership Lvl 3": "Platnium"},
                       "Games": {"Dice": {"Multiplier": 2.2, "Cooldown": 0, "Open": True, "Min": 50,
                                          "Max": 500},
                                 "Coin": {"Multiplier": 1.5, "Cooldown": 0, "Open": True, "Min": 10,
                                          "Max": 10},
                                 "Cups": {"Multiplier": 2.2, "Cooldown": 0, "Open": True, "Min": 50,
                                          "Max": 500},
                                 "Blackjack": {"Multiplier": 2.2, "Cooldown": 0, "Open": True,
                                               "Min": 50, "Max": 500},
                                 "Allin": {"Multiplier": 2.2, "Cooldown": 86400, "Open": True,
                                           "Min": 50, "Max": 500},
                                 "Hi-Lo": {"Multiplier": 1.5, "Cooldown": 0, "Open": True,
                                           "Min": 20, "Max": 20},
                                 },
                       "Players": {}}
            self.system["Servers"][server.id] = default
            dataIO.save_json(self.file_path, self.system)
            print("Creating default casino settings for Server: {}".format(server.name))
            path = self.system["Servers"][server.id]
            return path
        else:
            if "Hi-Lo" not in self.system["Servers"][server.id]["Games"]:
                hl = {"Hi-Lo": {"Multiplier": 1.5, "Cooldown": 0, "Open": True, "Min": 20,
                                "Max": 20}}
                self.system["Servers"][server.id]["Games"].update(hl)
                dataIO.save_json(self.file_path, self.system)
            path = self.system["Servers"][server.id]
            return path


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
    if not os.path.exists("data/JumperCogs/casino"):
        print("Creating data/JumperCogs/casino folder...")
        os.makedirs("data/JumperCogs/casino")


def check_files():
    system = {"Servers": {}}

    f = "data/JumperCogs/casino/casino.json"
    if not dataIO.is_valid_json(f):
        print("Creating default casino.json...")
        dataIO.save_json(f, system)


def setup(bot):
    check_folders()
    check_files()
    if tabulateAvailable:
        bot.add_cog(Casino(bot))
    else:
        raise RuntimeError("You need to run 'pip3 install tabulate'")
