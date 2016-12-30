# Developed by Redjumpman for Redbot.
# Inspired by Spriter's work on a modded economy.
# Creates 1 json file and requires tabulate.
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


server_default = {"System Config": {"Casino Name": "Redjumpman",
                                    "Casino Open": True,
                                    "Chip Name": "Jump",
                                    "Chip Rate": 1,
                                    "Credit Rate": 1,
                                    "Membership Lvl 0": "Basic",
                                    "Membership Lvl 1": "Silver",
                                    "Membership Lvl 2": "Gold",
                                    "Membership Lvl 3": "Platinum"},
                  "Games": {"Dice": {"Multiplier": 2.2, "Cooldown": 5, "Open": True, "Min": 50,
                                     "Max": 500},
                            "Coin": {"Multiplier": 1.5, "Cooldown": 5, "Open": True, "Min": 10,
                                     "Max": 10},
                            "Cups": {"Multiplier": 2.2, "Cooldown": 5, "Open": True, "Min": 50,
                                     "Max": 500},
                            "Blackjack": {"Multiplier": 2.2, "Cooldown": 5, "Open": True,
                                          "Min": 50, "Max": 500},
                            "Allin": {"Multiplier": 2.2, "Cooldown": 86400, "Open": True,
                                      "Min": 50, "Max": 500},
                            "Hi-Lo": {"Multiplier": 1.5, "Cooldown": 5, "Open": True,
                                      "Min": 20, "Max": 20},
                            },
                  "Players": {}}

main_deck = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'Jack', 'Queen', 'King', 'Ace'] * 4

card_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
               'Jack': 10, 'Queen': 10, 'King': 10}


class CasinoMembershipError(Exception):
    pass


class MembershipAlreadyExists(CasinoMembershipError):
    pass


class NoMembership(CasinoMembershipError):
    pass


class InsufficientChips(CasinoMembershipError):
    pass


class NegativeValue(CasinoMembershipError):
    pass


class SameSenderAndReceiver(CasinoMembershipError):
    pass


class CasinoBank:
    def __init__(self, bot, file_path):
        self.memberships = dataIO.load_json(file_path)
        self.bot = bot

    def create_account(self, user):
        server = user.server
        path = self.check_server_settings(server)
        if user.id not in path["Players"]:
            path["Players"][user.id] = {"Chips": 100,
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
            self.save_system()
            membership = path["Players"][user.id]
            return membership
        else:
            raise MembershipAlreadyExists("{} already has a casino membership".format(user.name))

    def membership_exists(self, user):
        try:
            self.get_membership(user)
        except NoMembership():
            return False
        return True

    def chip_balance(self, user):
        account = self.get_membership(user)
        return account["Chips"]

    def can_bet(self, user, amount):
        account = self.get_membership(user)
        if account["Chips"] >= amount:
            return True
        else:
            raise InsufficientChips("{} does not have enough chips.".format(user.name))

    def set_chips(self, user, amount):
        if amount < 0:
            raise NegativeValue()
        account = self.get_membership(user)
        account["Chips"] = amount
        self.save_system()

    def deposit_chips(self, user, amount):
        amount = int(round(amount))
        if amount < 0:
            raise NegativeValue()
        account = self.get_membership(user)
        account["Chips"] += amount
        self.save_system()

    def withdraw_chips(self, user, amount):
        if amount < 0:
            raise NegativeValue()
        account = self.get_membership(user)
        if account["Chips"] >= amount:
            account["Chips"] -= amount
            self.save_system()
        else:
            raise InsufficientChips("{} does not have enough chips.".format(user.name))

    def transfer_chips(self, sender, receiver, amount):
        if amount < 0:
            raise NegativeValue()
        if sender is receiver:
            raise SameSenderAndReceiver()
        if self.membership_exists(sender) and self.membership_exists(receiver):
            sender_acc = self.get_membership(sender)
            if sender_acc["Chips"] < amount:
                raise InsufficientChips()
            self.withdraw_credits(sender, amount)
            self.deposit_credits(receiver, amount)
        else:
            raise NoMembership()

    def wipe_caisno_server(self, server):
        self.memberships["Servers"].pop(server.id)
        self.save_system

    def wipe_casino_members(self, server):
        self.memberships["Servers"][server.id]["Players"] = {}
        self.save_system()

    def remove_membership(self, user):
        server = user.server
        self.memberships["Servers"][server.id]["Players"].pop(user.id)
        self.save_system()

    def get_membership(self, user):
        server = user.server
        path = self.check_server_settings(server)
        try:
            return path["Players"][user.id]
        except KeyError:
            raise NoMembership()

    def get_server_memberships(self, server):
        if server.id in self.memberships["Servers"]:
            members = self.memberships["Servers"][server.id]["Players"]
            return members
        else:
            return []

    def save_system(self):
        dataIO.save_json("data/JumperCogs/casino/casino.json", self.memberships)

    def check_server_settings(self, server):
        if server.id not in self.memberships["Servers"]:
            self.memberships["Servers"][server.id] = server_default
            self.save_system()
            print("Creating default casino settings for Server: {}".format(server.name))
            path = self.memberships["Servers"][server.id]
            return path
        else:
            if "Hi-Lo" not in self.memberships["Servers"][server.id]["Games"]:
                hl = {"Hi-Lo": {"Multiplier": 1.5, "Cooldown": 0, "Open": True, "Min": 20,
                                "Max": 20}}
                self.memberships["Servers"][server.id]["Games"].update(hl)
                self.save_system()
            path = self.memberships["Servers"][server.id]
            return path


class PluralDict(dict):
    def __missing__(self, key):
        if '(' in key and key.endswith(')'):
            key, rest = key.split('(', 1)
            value = super().__getitem__(key)
            suffix = rest.rstrip(')').split(',')
            if len(suffix) == 1:
                suffix.insert(0, '')
            return suffix[0] if value <= 1 else suffix[1]
        raise KeyError(key)


class Casino:
    """Casino"""

    def __init__(self, bot):
        self.bot = bot
        try:  # This allows you to port accounts from older versions of casino
            self.legacy_path = "data/casino/casino.json"
            self.legacy_system = dataIO.load_json(self.legacy_path)
            self.legacy_available = True
        except FileNotFoundError:
            self.legacy_available = False
        self.file_path = "data/JumperCogs/casino/casino.json"
        self.casino_bank = CasinoBank(bot, self.file_path)
        self.system = dataIO.load_json(self.file_path)
        self.games = ["Blackjack", "Coin", "Allin", "Cups", "Dice", "Hi-Lo"]
        self.version = "1.4"

    @commands.group(pass_context=True, no_pm=True)
    async def casino(self, ctx):
        """Casino Group Commands"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @casino.command(name="version", pass_context=True)
    async def _version_casino(self, ctx):
        """Shows current Casino version"""
        await self.bot.say("You are currently running Casino version {}.".format(self.version))

    @casino.command(name="leaderboard", pass_context=True)
    async def _leaderboard_casino(self, ctx, sort="top"):
        """Displays Casino Leaderboard"""
        user = ctx.message.author
        server = ctx.message.server
        self.check_server_settings(server)
        members = self.casino_bank.get_server_memberships(server)
        if sort not in ["top", "bottom", "place"]:
            sort = "top"
        if members:
            players = [(x["Name"], x["Chips"]) for x in members.values()]
            pos = [x + 1 for x, y in enumerate(players)]
            if sort == "top":
                style = sorted(players, key=itemgetter(1), reverse=True)
                players, chips = zip(*style)
                data = list(zip(pos, players, chips))
            elif sort == "bottom":
                style = sorted(players, key=itemgetter(1))
                rev_pos = list(reversed(pos))
                players, chips = zip(*style)
                data = list(zip(rev_pos, players, chips))
            elif sort == "place":
                style = sorted([[x["Name"], x["Chips"]] if x["Name"] != user.name
                               else ["[" + x["Name"] + "]", x["Chips"]]
                               for x in members.values()], key=itemgetter(1), reverse=True)
                players, chips = zip(*style)
                data = list(zip(pos, players, chips))
            headers = ["Rank", "Names", "Chips"]
            msg = await self.table_split(user, headers, data, sort)
        else:
            msg = "There are no casino players to show on the leaderboard."
        await self.bot.say(msg)

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
        self.casino_bank.create_account(user)
        name = settings["System Config"]["Casino Name"]
        msg = ("Your membership has been approved! Welcome to {} Casino!\nAs a first time "
               "member we have credited your account with 100 free chips. "
               "\nHave fun!".format(name))
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
            elif self.casino_bank.can_bet(user, amount):
                self.casino_bank.withdraw_chips(user, amount)
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
                self.casino_bank.deposit_chips(user, chip_amount)
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
        remaining = [self.time_format(x) for x in cooldown]
        chip_exchange_rate = settings["System Config"]["Chip Rate"]
        chip_ratio = str(Fraction(chip_exchange_rate).limit_denominator()).replace("/", ":")
        if chip_ratio == "1":
            chip_ratio = "1:1"
        credit_exchange_rate = settings["System Config"]["Credit Rate"]
        credit_ratio = str(Fraction(credit_exchange_rate).limit_denominator()).replace("/", ":")
        if credit_ratio == "1":
            credit_ratio = "1:1"
        m = list(zip(games, multiplier, min_bet, max_bet, remaining))
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
        chip_name = settings["System Config"]["Chip Name"]
        balance = self.casino_bank.chip_balance(user)
        await self.bot.say("```Python\nYou have {} {} chips.```".format(balance, chip_name))

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
                self.casino_bank.remove_membership(user)
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
                    self.casino_bank.wipe_caisno_server(server)
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
        settings = self.check_server_settings(server)
        await self.bot.say("This will reset casino to it's default settings and keep player data.\n"
                           "Do you wish to reset casino settings?")
        response = await self.bot.wait_for_message(timeout=15, author=user)
        if response is None:
            msg = "No response, reset cancelled."
        elif response.content.title() == "No":
            msg = "Cancelling reset."
        elif response.content.title() == "Yes":
            settings["System Config"] = server_default["System Config"]
            settings["Games"] = server_default["Games"]
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
        chip_name = settings["System Config"]["Chip Name"]
        hilo_data = {"Played": {"Hi-Lo Played": 0}, "Won": {"Hi-Lo Won": 0}, "CD": {"Hi-Lo CD": 0}}
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
        elif await self.minmax_check(bet, "Hi-Lo", settings):
            if "Hi-Lo Played" not in settings["Players"][user.id]["Played"].keys():
                self.game_add(settings["Players"][user.id], hilo_data)
            if await self.check_cooldowns(user.id, "Hi-Lo", settings):
                if self.casino_bank.can_bet(user, bet):
                    self.casino_bank.withdraw_chips(user, bet)
                    await self.bot.say("The dice hit the table and slowly fall into place...")
                    await asyncio.sleep(2)
                    settings["Players"][user.id]["Played"]["Hi-Lo Played"] += 1
                    outcome = self.hl_outcome()
                    if choice in outcome:
                        msg = ("Congratulations the outcome was "
                               "{} ({})".format(outcome[0], outcome[2]))
                        if outcome[1] == "Seven":
                            amount = bet * 12
                            msg += "\n**BONUS!** 12x multiplier for Seven!"
                        else:
                            amount = int(round(bet * settings["Games"]["Hi-Lo"]["Multiplier"]))
                            self.casino_bank.deposit_chips(user, amount)
                        msg += "```Python\nYou just won {} {} chips.```".format(amount, chip_name)
                        settings["Players"][user.id]["Won"]["Hi-Lo Won"] += 1
                    else:
                        msg = "Sorry. The outcome was {} ({})".format(outcome[0], outcome[2])
                    dataIO.save_json(self.file_path, self.system)
                    await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True)
    async def cups(self, ctx, cup: int, bet: int):
        """Pick the cup that is hiding the gold coin. Choose 1, 2, 3, or 4"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        chip_name = settings["System Config"]["Chip Name"]
        casino_name = settings["System Config"]["Casino Name"]
        if user.id not in settings["Players"]:
            await self.bot.say("You need a {} Casino membership. To get one type "
                               "{}casino join .".format(casino_name, ctx.prefix))
        elif not settings["System Config"]["Casino Open"]:
            await self.bot.say("The {} Casino is closed.".format(casino_name))
        elif cup >= 5 or cup <= 0:
            await self.bot.say("You need to pick a cup 1-4.")
        elif await self.minmax_check(bet, "Cups", settings):
            if await self.check_cooldowns(user.id, "Cups", settings):
                if self.casino_bank.can_bet(user, bet):
                    self.casino_bank.withdraw_chips(user, bet)
                    outcome = random.randint(1, 4)
                    await self.bot.say("The cups start shuffling along the table...")
                    await asyncio.sleep(3)
                    settings["Players"][user.id]["Played"]["Cups Played"] += 1
                    if cup == outcome:
                        amount = int(round(bet * settings["Games"]["Cups"]["Multiplier"]))
                        settings["Players"][user.id]["Won"]["Cups Won"] += 1
                        self.casino_bank.deposit_chips(user, amount)
                        msg = "Congratulations! The coin was under cup {}!".format(outcome)
                        msg += "```Python\nYou just won {} {} chips.```".format(amount, chip_name)
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
        chip_name = settings["System Config"]["Chip Name"]
        casino_name = settings["System Config"]["Casino Name"]
        if user.id not in settings["Players"]:
            await self.bot.say("You need a {} Casino membership. To get a membership, "
                               "type {}casino join .".format(casino_name, ctx.prefix))
        elif not settings["System Config"]["Casino Open"]:
            await self.bot.say("The {} Casino is closed.".format(casino_name))
        elif choice not in ["Heads", "Tails"]:
            await self.bot.say("You need to pick heads or tails")
        elif await self.minmax_check(bet, "Coin", settings):
            if await self.check_cooldowns(user.id, "Coin", settings):
                if self.casino_bank.can_bet(user, bet):
                    self.casino_bank.withdraw_chips(user, bet)
                    outcome = random.choice(["Heads", "Tails"])
                    await self.bot.say("The coin flips into the air...")
                    await asyncio.sleep(2)
                    settings["Players"][user.id]["Played"]["Coin Played"] += 1
                    if choice == outcome:
                        amount = int(round(bet * settings["Games"]["Coin"]["Multiplier"]))
                        self.casino_bank.deposit_chips(user, amount)
                        settings["Players"][user.id]["Won"]["Coin Won"] += 1
                        msg = "Congratulations! The coin landed on {}!".format(outcome)
                        msg += "```Python\nYou just won {} {} chips.```".format(amount, chip_name)
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
        chip_name = settings["System Config"]["Chip Name"]
        casino_name = settings["System Config"]["Casino Name"]
        if user.id not in settings["Players"]:
            await self.bot.say("You need a {} Casino membership. To get one type "
                               "{}casino join .".format(casino_name, ctx.prefix))
        elif not settings["System Config"]["Casino Open"]:
            await self.bot.say("The {} Casino is closed.".format(casino_name))
        elif await self.minmax_check(bet, "Dice", settings):
            if await self.check_cooldowns(user.id, "Dice", settings):
                if self.casino_bank.can_bet(user, bet):
                    self.casino_bank.withdraw_chips(user, bet)
                    outcome = random.randint(1, 12)
                    await self.bot.say("The dice strike the back of the table and begin to tumble "
                                       "into place...")
                    await asyncio.sleep(2)
                    settings["Players"][user.id]["Played"]["Dice Played"] += 1
                    if outcome in [2, 7, 11, 12]:
                        amount = int(round(bet * settings["Games"]["Dice"]["Multiplier"]))
                        msg = "Congratulations! The dice landed on {}.".format(outcome)
                        msg += "```Python\nYou just won {} {} chips.```".format(amount, chip_name)
                        self.casino_bank.deposit_chips(user, amount)
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
        casino_name = settings["System Config"]["Casino Name"]
        chip_name = settings["System Config"]["Chip Name"]
        if user.id not in settings["Players"]:
            await self.bot.say("You need a {} Casino membership. To get one type "
                               "{}casino join .".format(casino_name, ctx.prefix))
        elif not settings["System Config"]["Casino Open"]:
            await self.bot.say("The {} Casino is closed.".format(casino_name))
        elif await self.minmax_check(bet, "Blackjack", settings):
            if await self.check_cooldowns(user.id, "Blackjack", settings):
                if self.casino_bank.can_bet(user, bet):
                    self.casino_bank.withdraw_chips(user, bet)
                    settings["Players"][user.id]["Played"]["BJ Played"] += 1
                    deck = main_deck[:]
                    dhand = self.dealer(deck)
                    ph, dh, amt = await self.blackjack_game(dhand, user, bet, ctx, settings, deck)
                    results = self.blackjack_results(settings, user, amt, chip_name, ph, dh)
                    await self.bot.say(results)

    @commands.command(pass_context=True, no_pm=True)
    async def allin(self, ctx, multiplier: int):
        """It's all or nothing. Bets everything you have."""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        chip_name = settings["System Config"]["Chip Name"]
        bet = int(settings["Players"][user.id]["Chips"])
        casino_name = settings["System Config"]["Casino Name"]
        if not settings["System Config"]["Casino Open"]:
            await self.bot.say("The {} Casino is closed.".format(casino_name))
        elif await self.check_cooldowns(user.id, "Allin", settings):
            amount = int(round(multiplier * settings["Players"][user.id]["Chips"]))
            balance = self.casino_bank.chip_balance(user)
            self.casino_bank.withdraw_chips(user, balance)
            outcome = random.randint(0, multiplier + 1)
            await self.bot.say("You put all your chips into the machine and pull the lever...")
            settings["Players"][user.id]["Played"]["Allin Played"] += 1
            await asyncio.sleep(3)
            if outcome == 0:
                msg = "Jackpot!! You just won {} chips!!".format(amount)
                msg += "```Python\nYou just won {} {} chips.```".format(amount, chip_name)
                self.casino_bank.deposit_chips(user, amount)
                settings["Players"][user.id]["Won"]["Allin Won"] += 1
            else:
                msg = ("Sorry! Your all or nothing gamble failed and you lost "
                       "{} {} chips.".format(bet, chip_name))
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
        if game.title() not in self.games:
            msg = "This game does not exist. Please pick from: {}".format(", ".join(self.games))
        elif multiplier > 0:
            multiplier = float(abs(multiplier))
            settings["Games"][game.title()]["Multiplier"] = multiplier
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
        self.casino_bank.set_chips(user, chips)
        await self.bot.say("```Python\nSetting the chip balance of {} to "
                           "{} {} chips.```".format(user.name, chips, chip_name))

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
        if game.title() not in self.games:
            msg = "This game does not exist. Please pick from: {}".format(", ".join(self.games))
        else:
            settings["Games"][game.title()]["Cooldown"] = seconds
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
        if game.title() not in self.games:
            msg = "This game does not exist. Please pick from: {}".format(", ".join(self.games))
        elif maxbet <= 0:
            msg = "You need to set a maximum bet higher than 0."
        elif maxbet > settings["Games"][game.title()]["Min"]:
            settings["Games"][game.title()]["Max"] = maxbet
            chips = settings["System Config"]["Chip Name"]
            dataIO.save_json(self.file_path, self.system)
            msg = ("Setting the maximum bet for {} to {} {}"
                   "chips.".format(game.title(), maxbet, chips))
        else:
            minbet = settings["Games"][game.title()]["Min"]
            msg = "The max bet needs be higher than the minimum bet of {}.".format(minbet)
        await self.bot.say(msg)

    @setcasino.command(name="min", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _min_setcasino(self, ctx, game, minbet: int):
        """Set the minimum bet to play a game"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if game.title() not in self.games:
            msg = "This game does not exist. Please pick from: {}".format(", ".join(self.games))
        elif minbet < 0:
            msg = "You need to set a minimum bet higher than 0."
        elif minbet < settings["Games"][game.title()]["Max"]:
            settings["Games"][game.title()]["Min"] = minbet
            chips = settings["System Config"]["Chip Name"]
            dataIO.save_json(self.file_path, self.system)
            msg = ("Setting the minimum bet for {} to {} {} "
                   "chips.".format(game.title(), minbet, chips))
        else:
            maxbet = settings["Games"][game.title()]["Max"]
            msg = ("The minimum bet can't bet set higher than the maximum bet of "
                   "{} for {}.".format(maxbet, game.title()))
        await self.bot.say(msg)

    async def table_split(self, user, headers, data, sort):
        groups = [data[i:i+20] for i in range(0, len(data), 20)]
        pages = len(groups)

        if sort == "place":
            name = "[{}]".format(user.name)
            page = next((idx for idx, sub in enumerate(groups) for tup in sub if name in tup), None)
            if not page:
                page = 0
            table = tabulate(groups[page], headers=headers, numalign="left",  tablefmt="simple")
            msg = ("```ini\n{}``````Python\nYou are viewing page {} of {}. "
                   "{} casino members.```".format(table, page + 1, pages, len(data)))
            return msg
        elif pages == 1:
            page = 0
            table = tabulate(groups[page], headers=headers, numalign="left",  tablefmt="simple")
            msg = ("```ini\n{}``````Python\nYou are viewing page 1 of {}. "
                   "{} casino members```".format(table, pages, len(data)))
            return msg

        await self.bot.say("There are {} pages of highscores. "
                           "Which page would you like to display?".format(pages))
        response = await self.bot.wait_for_message(timeout=15, author=user)
        if response is None:
            page = 0
        else:
            try:
                page = int(response.content) - 1
                table = tabulate(groups[page], headers=headers, numalign="left",  tablefmt="simple")
                msg = ("```ini\n{}``````Python\nYou are viewing page {} of {}. "
                       "{} casino members.```".format(table, page + 1, pages, len(data)))
                return msg
            except ValueError:
                await self.bot.say("Sorry your response was not a number. Defaulting to page 1")
                page = 0
                table = tabulate(groups[page], headers=headers, numalign="left",  tablefmt="simple")
                msg = ("```ini\n{}``````Python\nYou are viewing page 1 of {}. "
                       "{} casino members```".format(table, pages, len(data)))
                return msg

    async def add_credits(self, user, amount):
        bank = self.bot.get_cog('Economy').bank
        bank.deposit_credits(user, amount)
        await self.bot.say("{} credits were deposited into your account.".format(amount))

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
            remaining = self.time_format(seconds)
            await self.bot.say("This game has a cooldown. You still have: {}".format(remaining))
            return False

    async def blackjack_game(self, dh, user, amount, ctx, settings, deck):
        ph = self.draw_two(deck)
        count = self.count_hand(ph)
        if count == 21:
            return ph, dh, amount
        msg = ("{}\nYour cards: {}\nYour score: {}\nThe dealer shows: "
               "{}\nHit, stay, or double".format(user.mention, ", ".join(ph), count, dh[0]))
        await self.bot.say(msg)
        choice = await self.bot.wait_for_message(timeout=15, author=user)
        if choice is None or choice.content.title() == "Stay":
            return ph, dh, amount
        elif choice.content.title() == "Double":
            if self.casino_bank.can_bet(user, amount):
                self.casino_bank.withdraw_chips(user, amount)
                amount = amount * 2
                ph = self.draw_card(ph, deck)
                count = self.count_hand(ph)
                return ph, dh, amount
            else:
                await self.bot.say("Not enough chips. Please choose hit or stay.")
        elif choice.content.title() == "Hit":
            while count < 21:
                ph = self.draw_card(ph, deck)
                count = self.count_hand(ph)
                if count >= 21:
                    break
                msg = ("{}\nYour cards: {}\nYour score: {}\nThe dealer shows: "
                       "{}\nHit or stay?".format(user.mention, ", ".join(ph), count, dh[0]))
                await self.bot.say(msg)
                response = await self.bot.wait_for_message(timeout=15, author=user)
                if response is None or response.content.title() != "Hit":
                    break
                else:
                    continue
            return ph, dh, amount

    def blackjack_results(self, settings, user, amount, chip_name, ph, dh):
        dc = self.count_hand(dh)
        pc = self.count_hand(ph)
        msg = ("Your hand: {}\nThe dealer's hand: {}\nThe dealer's score: {}\nYour "
               "score: {}\n".format(", ".join(ph), ", ".join(dh), dc, pc, user.name))
        if dc > 21 and pc <= 21 or dc < pc <= 21:
            total = int(round(amount * settings["Games"]["Blackjack"]["Multiplier"]))
            msg += ("**\*\*\*\*\*\*{} Wins!\*\*\*\*\*\***\n```Python\nYou just "
                    "won {} {} chips.```".format(user.name, total, chip_name))
            self.casino_bank.deposit_chips(user, total)
            settings["Players"][user.id]["Won"]["BJ Won"] += 1
        elif pc > 21:
            msg += "          BUST!\n======{}  Lost!======".format(user.name)
        elif dc == pc and dc <= 21 and pc <= 21:
            msg += ("{}  Pushed.\nReturned {} {} chips to your "
                    "account.".format(user.name, amount, chip_name))
            amount = int(round(amount))
            self.casino_bank.deposit_chips(user, amount)
        elif dc > pc and dc <= 21:
            msg += "======{}  Lost!======".format(user.name)
        dataIO.save_json(self.file_path, self.system)
        return msg

    def draw_two(self, deck):
        hand = random.sample(deck, 2)
        deck.remove(hand[0])
        deck.remove(hand[1])
        return hand

    def draw_card(self, hand, deck):
        card = random.choice(deck)
        deck.remove(card)
        hand.append(card)
        return hand

    def count_hand(self, hand):
        count = sum([card_values[x] for x in hand if x in card_values])
        count += sum([1 if x == 'Ace' and count + 11 > 21 else 11
                      if x == 'Ace' and hand.count('Ace') == 1 else 1
                      if x == 'Ace' and hand.count('Ace') > 1 else 0 for x in hand])
        return count

    def dealer(self, deck):
        dh = self.draw_two(deck)
        count = self.count_hand(dh)

        # forces hit if ace in first two cards
        if 'Ace' in dh:
            dh = self.draw_card(dh, deck)
            count = self.count_hand(dh)

        # defines maximum hit score X
        while count < 16:
            self.draw_card(dh, deck)
            count = self.count_hand(dh)
        return dh

    def hl_outcome(self):
        choices = [(1, "Lo", "Low"), (2, "Lo", "Low"), (3, "Lo", "Low"), (4, "Lo", "Low"),
                   (5, "Lo", "Low"), (6, "Lo", "Low"), (7, "7", "Seven"), (8, "Hi", "High"),
                   (9, "Hi", "High"), (10, "Hi", "High"), (11, "Hi", "High"), (12, "Hi", "High")]
        outcome = random.choice(choices)
        return outcome

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
        data = PluralDict({'hour': h, 'minute': m, 'second': s})
        if h > 0:
            fmt = "{hour} hour{hour(s)}"
            if data["minute"] > 0 and data["second"] > 0:
                fmt += ", {minute} minute{minute(s)}, and {second} second{second(s)}"
            if data["second"] > 0 == data["minute"]:
                fmt += ", and {second} second{second(s)}"
            msg = fmt.format_map(data)
        elif h == 0 and m > 0:
            if data["second"] == 0:
                fmt = "{minute} minute{minute(s)}"
            else:
                fmt = "{minute} minute{minute(s)}, and {second} second{second(s)}"
            msg = fmt.format_map(data)
        elif m == 0 and h == 0 and s > 0:
            fmt = "{second} second{second(s)}"
            msg = fmt.format_map(data)
        elif m == 0 and h == 0 and s == 0:
            msg = "No cooldown"
        return msg

    def check_server_settings(self, server):
        if server.id not in self.system["Servers"]:
            self.system["Servers"][server.id] = server_default
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
