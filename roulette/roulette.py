#  Roulette.py was created by Redjumpman for Redbot
#  This will create a bets.JSON file and a data folder
#  This will modify values your bank.json from economy.py
import os
import random
import asyncio
import aiohttp
from .utils.dataIO import fileIO
from discord.ext import commands
from .utils import checks
from __main__ import send_cmd_help
try:   # Check if Tabulate is installed
    from tabulate import tabulate
    tabulateAvailable = True
except:
    tabulateAvailable = False


class Roulette:
    """Casino roulette game"""

    def __init__(self, bot):
        self.bot = bot
        self.url = "http://www.lasvegasdirect.com/roulette-table-layout.gif"
        self.layout_load = os.path.exists('data/casino/layout.png')
        self.roulette = fileIO("data/casino/roulette.json", "load")
        self.image = "data/casino/layout.png"
        self.rednum = [1, 3, 5, 7, 9, 12, 14, 16, 18, 21, 23, 25, 27, 30, 32, 34, 36]
        self.blacknum = [2, 4, 6, 8, 10, 11, 13, 15, 17, 19, 20, 22, 24, 26, 28, 29, 31, 33, 35]
        self.greennum = [0, 00]
        self.evennum = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36]
        self.oddnum = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35]
        self.half1num = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
        self.half2num = [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36]
        self.dozen1num = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        self.dozen2num = [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
        self.dozen3num = [25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36]
        self.numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
                        15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26,
                        27, 28, 29, 30, 31, 32, 33, 34, 35, 36]
        self.highnum = [19, 20, 21, 22, 23, 24, 25, 26,
                        27, 28, 29, 30, 31, 32, 33, 34, 35, 36]
        self.lownum = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
                       15, 16, 17, 18]

    @commands.group(name="roulette", pass_context=True)
    async def _roulette(self, ctx):
        """Group Command for Roulette Commands"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_roulette.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def reset(self, ctx):
        """Resets the game. For debugging use ONLY"""
        del self.roulette["Players"]
        self.roulette["Players"] = {}
        self.roulette["Config"]["Active"] = False
        self.roulette["Config"]["Betting Closed"] = True
        fileIO("data/casino/roulette.json", "save", self.roulette)
        await self.bot.say("Data cleared.")

    @_roulette.command(pass_context=True, no_pm=True)
    async def play(self, ctx):
        """Start a game of roulette"""
        server = ctx.message.server
        if not self.roulette["Config"]["Active"]:
            self.roulette["Config"]["Active"] = True
            self.roulette["Config"]["Betting Closed"] = False
            fileIO("data/casino/roulette.json", "save", self.roulette)
            await self.bot.say("A game of roulette is about to start. You have 30 seconds to place your bets.")
            await asyncio.sleep(15)
            await self.bot.say("15 seconds before betting is closed")
            await asyncio.sleep(10)
            await self.bot.say("Finish your bets, 5 seconds remaining")
            await asyncio.sleep(5)
            self.roulette["Config"]["Betting Closed"] = True
            fileIO("data/casino/roulette.json", "save", self.roulette)
            await self.bot.say("Betting is now closed")
            await asyncio.sleep(1)
            await self.bot.say("The ball landed on...")
            await asyncio.sleep(1)
            outcome = random.randint(0, 36)
            if outcome in self.numbers:
                if outcome in self.rednum:
                    await self.bot.say("Red " + str(outcome))
                    await asyncio.sleep(2)
                    await self.bot.say("Alotting payouts to winners...")
                    self.game_payouts(outcome, server)
                    del self.roulette["Players"]
                    self.roulette["Players"] = {}
                    fileIO("data/casino/roulette.json", "save", self.roulette)
                    await asyncio.sleep(2)
                    await self.bot.say("Done. Type roulette play to play again.")
                    self.roulette["Config"]["Active"] = False
                    fileIO("data/casino/roulette.json", "save", self.roulette)
                else:
                    await self.bot.say("Black " + str(outcome))
                    await asyncio.sleep(2)
                    await self.bot.say("Allotting payouts to winners and clearing chips from the board...")
                    self.game_payouts(outcome, server)
                    del self.roulette["Players"]
                    self.roulette["Players"] = {}
                    fileIO("data/casino/roulette.json", "save", self.roulette)
                    await asyncio.sleep(2)
                    await self.bot.say("Done. Type roulette play to play again.")
                    self.roulette["Config"]["Active"] = False
                    fileIO("data/casino/roulette.json", "save", self.roulette)
            else:
                zeros = ["0", "00"]
                zero_outcome = random.choice(zeros)
                await self.bot.say("```" + "Green " + zero_outcome + "```")
                await asyncio.sleep(2)
                await self.bot.say("Allotting payouts to winners and clearing chips from the board...")
                self.game_payouts(outcome, server)
                del self.roulette["Players"]
                self.roulette["Players"] = {}
                fileIO("data/casino/roulette.json", "save", self.roulette)
                await asyncio.sleep(2)
                await self.bot.say("Done. Type roulette play to play again.")
                self.roulette["Config"]["Active"] = False
                fileIO("data/casino/roulette.json", "save", self.roulette)
        else:
            await self.bot.say("I can't start a new game of roulette while one is active.")

    @_roulette.command(pass_context=True, no_pm=True)
    async def layout(self, ctx):
        """Shows a basic layout picture of the roulette betting table"""
        channel = ctx.message.channel
        if not self.layout_load:
            try:
                url = "http://www.lasvegasdirect.com/roulette-table-layout.gif"
                async with aiohttp.get(url) as response:
                    image = await response.content.read()
                with open('data/casino/layout.png', 'wb') as f:
                    f.write(image)
                self.layout_load = os.path.exists('data/casino/layout.png')
                await self.bot.send_file(channel, self.image)
            except Exception as e:
                print(e)
                print("Could not find the image, using the url instead")
                await self.bot.send_message(channel, self.url)
        else:
            await self.bot.send_file(channel, self.image)

    @_roulette.command(pass_context=True, no_pm=True)
    async def payouts(self, ctx):
        """Shows the payouts for each bet"""
        inside_bets = ["straight", "split", "zero", "double zero", "corner"]
        inside_description = ["bet on a single number (1-36)",
                              "betting on 0",
                              "betting double 0",
                              "bet on two numbers adjacent numbers",
                              "bet on four numbers within a square"]
        inside_odds = ["2.63%", "2.63%", "2.63%", "5.26%", "10.53%"]
        inside_payout = ["35-1", "35-1", "35-1", "17-1", "8-1"]
        inside = list(zip(inside_bets, inside_description, inside_odds, inside_payout))
        inside_table = tabulate(inside, headers=["Bet Names", "Description", "Odds", "Payout"])
        outside_bets = ["red", "black", "high", "low", "odd", "even", "first half",
                        "second half", "first dozen", "second dozen", "third dozen"]
        outside_description = ["bet on red number showing",
                               "bet on black number showing",
                               "bet on all high numbers (19-36)",
                               "bet on all low numbers (1-18)",
                               "bet on any odd number showing",
                               "bet on any even number showing",
                               "bet on first half of numbers",
                               "bet on second half of numbers",
                               "bet on first dozen numbers (1-12)",
                               "bet on second doezen numbers (13-24)",
                               "bet on third dozen numbers (25-36)"]
        outside_odds = ["47.37%", "47.37%", "47.37%", "47.37%", "47.37%", "47.37%",
                        "47.37%", "47.37%", "31.58%", "31.58%", "31.58%"]
        outside_payout = ["1-1", "1-1", "1-1", "1-1", "1-1",
                          "1-1", "1-1", "1-1", "2-1", "2-1", "2-1"]
        outside = list(zip(outside_bets, outside_description, outside_odds, outside_payout))
        outside_table = tabulate(outside, headers=["Bet Names", "Description", "Odds", "Payout"])
        await self.bot.say("**Inside Bets**")
        await self.bot.say("```Ruby" + "\n" + str(inside_table) + "```")
        await self.bot.say("**Outside Bets**")
        await self.bot.say("```Ruby" + "\n" + str(outside_table) + "```")

    @_roulette.command(pass_context=True, no_pm=True)
    async def info(self, ctx):
        """Rules of the game roulette"""
        msg = "```Ruby" + "\n"
        msg += "Rules & Helpful Info" + "\n"
        msg += "=" * 80 + "\n"
        msg += "\n" + "once a roulette game starts you may place any number of bets you wish." + "\n"
        msg += "\n" + "you can no longer place a bet once the timer expires." + "\n"
        msg += "\n" + "review the roulette payout table to better understand bets." + "\n"
        msg += "\n" + "use <p>roulette layout to see a picture of the roulette betting board." + "\n"
        msg += "\n" + "house wins on a 0 OR a double 00 unless you have points on them." + "\n"
        msg += "\n" + "use !help insidebet & !help outsidebet to see a list of bets." + "\n"
        msg += "\n" + "```"
        await self.bot.say(msg)

    @commands.group(name="insidebet", pass_context=True, aliases=["inside", "ib"])
    async def _insidebet(self, ctx):
        """Group Command for outside betting.
        Can use 'inside' or 'ib' as aliases"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_insidebet.command(pass_context=True, no_pm=True)
    async def straight(self, ctx, number: int, bet: int):
        """Bet on a single number 1-36"""
        user = ctx.message.author
        if self.roulette["Config"]["Active"]:
            if not self.roulette["Config"]["Betting Closed"]:
                if await self.subtract_bet(user, bet):
                    if user.id in self.roulette["Players"]:
                        if "Straight" not in self.roulette["Players"][user.id]:
                            self.roulette["Players"][user.id]["Straight"] = {}
                            self.roulette["Players"][user.id]["Straight"] = {"Straight":  True,
                                                                             "Number": number,
                                                                             "Bet": bet}
                            fileIO("data/casino/roulette.json", "save", self.roulette)
                            await self.bot.say("Thank you, " + user.name + ". Your bet of " + str(bet) +
                                               " points, has been recorded.")
                        else:
                            await self.bot.say("You already have a Straight bet.")
                    else:
                        self.roulette["Players"][user.id] = {}
                        self.roulette["Players"][user.id]["Straight"] = {}
                        self.roulette["Players"][user.id]["Straight"] = {"Straight":  True,
                                                                         "Number": number,
                                                                         "Bet": bet}
                        fileIO("data/casino/roulette.json", "save", self.roulette)
                        await self.bot.say("Thank you, " + user.name + ". Your bet of " + str(bet) +
                                           " has been recorded.")
            else:
                await self.bot.say("Betting is currently closed.")
        else:
            await self.bot.say("I can't accept a bet until a game is started.")

    @_insidebet.command(pass_context=True, no_pm=True)
    async def split(self, ctx, *, itemname):
        """Bet on two numbers"""
        user = ctx.message.author
        await self.bot.say("Sorry this command is currently disabled, and will become active once complete")

    @_insidebet.command(pass_context=True, no_pm=True)
    async def corner(self, ctx, *, itemname):
        """Bet on a four numbers"""
        user = ctx.message.author
        await self.bot.say("Sorry this command is currently disabled, and will become active once complete")

    @commands.group(name="outsidebet", pass_context=True, aliases=["outside", "ob"])
    async def _outsidebet(self, ctx):
        """Group Command for outside betting.
        Can use 'outside' or 'ob' as aliases"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_outsidebet.command(pass_context=True, no_pm=True)
    async def high(self, ctx, bet: int):
        """Bet on the high numbers 19-36"""
        user = ctx.message.author
        if self.roulette["Config"]["Active"]:
            if not self.roulette["Config"]["Betting Closed"]:
                if await self.subtract_bet(user, bet):
                    if user.id in self.roulette["Players"]:
                        if "High" not in self.roulette["Players"][user.id]:
                            self.roulette["Players"][user.id]["High"] = {}
                            self.roulette["Players"][user.id]["High"] = {"High":  True,
                                                                         "Bet": bet}
                            fileIO("data/casino/roulette.json", "save", self.roulette)
                            await self.bot.say("Thank you, " + user.name + ". Your bet of " + str(bet) +
                                               " points, has been recorded.")
                        else:
                            await self.bot.say("You already have a High bet.")
                    else:
                        self.roulette["Players"][user.id] = {}
                        self.roulette["Players"][user.id]["High"] = {}
                        self.roulette["Players"][user.id]["High"] = {"High":  True,
                                                                     "Bet": bet}
                        fileIO("data/casino/roulette.json", "save", self.roulette)
                        await self.bot.say("Thank you, " + user.name + ". Your bet of " + str(bet) +
                                           " has been recorded.")
            else:
                await self.bot.say("Betting is currently closed.")
        else:
            await self.bot.say("I can't accept a bet until a game is started.")

    @_outsidebet.command(pass_context=True, no_pm=True)
    async def low(self, ctx, bet: int):
        """Bet on the low numbers 1-18"""
        user = ctx.message.author
        if self.roulette["Config"]["Active"]:
            if not self.roulette["Config"]["Betting Closed"]:
                if await self.subtract_bet(user, bet):
                    if user.id in self.roulette["Players"]:
                        if "Low" not in self.roulette["Players"][user.id]:
                            self.roulette["Players"][user.id]["Low"] = {"Low":  True,
                                                                        "Bet": bet}
                            fileIO("data/casino/roulette.json", "save", self.roulette)
                            await self.bot.say("Thank you, " + user.name + ". Your bet of " + str(bet) +
                                               " points, has been recorded.")
                        else:
                            await self.bot.say("You already have a Low bet.")
                    else:
                        self.roulette["Players"][user.id] = {}
                        self.roulette["Players"][user.id]["Low"] = {"Low":  True,
                                                                    "Bet": bet}
                        fileIO("data/casino/roulette.json", "save", self.roulette)
                        await self.bot.say("Thank you, " + user.name + ". Your bet of " + str(bet) +
                                           " has been recorded.")
            else:
                await self.bot.say("Betting is currently closed.")
        else:
            await self.bot.say("I can't accept a bet until a game is started.")

    @_outsidebet.command(pass_context=True, no_pm=True)
    async def red(self, ctx, bet: int):
        """Bet on the color red"""
        user = ctx.message.author
        if self.roulette["Config"]["Active"]:
            if not self.roulette["Config"]["Betting Closed"]:
                if await self.subtract_bet(user, bet):
                    if user.id in self.roulette["Players"]:
                        if "Red" not in self.roulette["Players"][user.id]:
                            self.roulette["Players"][user.id]["Red"] = {"Red":  True,
                                                                        "Bet": bet}
                            fileIO("data/casino/roulette.json", "save", self.roulette)
                            await self.bot.say("Thank you, " + user.name + ". Your bet of " + str(bet) +
                                               " points, has been recorded.")
                        else:
                            await self.bot.say("You already have a Red bet.")
                    else:
                        self.roulette["Players"][user.id] = {}
                        self.roulette["Players"][user.id]["Red"] = {"Red":  True,
                                                                    "Bet": bet}
                        fileIO("data/casino/roulette.json", "save", self.roulette)
                        await self.bot.say("Thank you, " + user.name + ". Your bet of " + str(bet) +
                                           " has been recorded.")
            else:
                await self.bot.say("Betting is currently closed.")
        else:
            await self.bot.say("I can't accept a bet until a game is started.")

    @_outsidebet.command(pass_context=True, no_pm=True)
    async def black(self, ctx, bet: int):
        """Bet on the color black"""
        user = ctx.message.author
        if self.roulette["Config"]["Active"]:
            if not self.roulette["Config"]["Betting Closed"]:
                if await self.subtract_bet(user, bet):
                    if user.id in self.roulette["Players"]:
                        if "Black" not in self.roulette["Players"][user.id]:
                            self.roulette["Players"][user.id]["Black"] = {"Black":  True,
                                                                          "Bet": bet}
                            fileIO("data/casino/roulette.json", "save", self.roulette)
                            await self.bot.say("Thank you, " + user.name + ". Your bet of " + str(bet) +
                                               " points, has been recorded.")
                        else:
                            await self.bot.say("You already have a Black bet.")
                    else:
                        self.roulette["Players"][user.id] = {}
                        self.roulette["Players"][user.id]["Black"] = {"Black":  True,
                                                                      "Bet": bet}
                        fileIO("data/casino/roulette.json", "save", self.roulette)
                        await self.bot.say("Thank you, " + user.name + ". Your bet of " + str(bet) +
                                           " has been recorded.")
            else:
                await self.bot.say("Betting is currently closed.")
        else:
            await self.bot.say("I can't accept a bet until a game is started.")

    @_outsidebet.command(pass_context=True, no_pm=True)
    async def odd(self, ctx, bet: int):
        """Bet on odd number coming up"""
        user = ctx.message.author
        if self.roulette["Config"]["Active"]:
            if not self.roulette["Config"]["Betting Closed"]:
                if await self.subtract_bet(user, bet):
                    if user.id in self.roulette["Players"]:
                        if "Odd" not in self.roulette["Players"][user.id]:
                            self.roulette["Players"][user.id]["Odd"] = {"Odd":  True,
                                                                        "Bet": bet}
                            fileIO("data/casino/roulette.json", "save", self.roulette)
                            await self.bot.say("Thank you, " + user.name + ". Your bet of " + str(bet) +
                                               " points, has been recorded.")
                        else:
                            await self.bot.say("You already have a Odd bet.")
                    else:
                        self.roulette["Players"][user.id] = {}
                        self.roulette["Players"][user.id]["Odd"] = {"Odd":  True,
                                                                    "Bet": bet}
                        fileIO("data/casino/roulette.json", "save", self.roulette)
                        await self.bot.say("Thank you, " + user.name + ". Your bet of " + str(bet) +
                                           " has been recorded.")
            else:
                await self.bot.say("Betting is currently closed.")
        else:
            await self.bot.say("I can't accept a bet until a game is started.")

    @_outsidebet.command(pass_context=True, no_pm=True)
    async def even(self, ctx, bet: int):
        """Bet on even number coming up"""
        user = ctx.message.author
        if self.roulette["Config"]["Active"]:
            if not self.roulette["Config"]["Betting Closed"]:
                if await self.subtract_bet(user, bet):
                    if user.id in self.roulette["Players"]:
                        if "Even" not in self.roulette["Players"][user.id]:
                            self.roulette["Players"][user.id]["Even"] = {"Even":  True,
                                                                         "Bet": bet}
                            fileIO("data/casino/roulette.json", "save", self.roulette)
                            await self.bot.say("Thank you, " + user.name + ". Your bet of " + str(bet) +
                                               " points, has been recorded.")
                        else:
                            await self.bot.say("You already have a Even bet.")
                    else:
                        self.roulette["Players"][user.id] = {}
                        self.roulette["Players"][user.id]["Even"] = {"Even":  True,
                                                                     "Bet": bet}
                        fileIO("data/casino/roulette.json", "save", self.roulette)
                        await self.bot.say("Thank you, " + user.name + ". Your bet of " + str(bet) +
                                           " has been recorded.")
            else:
                await self.bot.say("Betting is currently closed.")
        else:
            await self.bot.say("I can't accept a bet until a game is started.")

    @_outsidebet.command(pass_context=True, no_pm=True)
    async def dozen(self, ctx, bet: int):
        """Bet on first, second, or third dozen"""
        user = ctx.message.author

    @_outsidebet.command(pass_context=True, no_pm=True)
    async def half(self, ctx, bet: int):
        """Bet on first or second half"""
        user = ctx.message.author
        await self.bot.say("Sorry this command is currently disabled, and will become active once complete")

    async def subtract_bet(self, user, number):
        bank = self.bot.get_cog("Economy").bank
        if bank.account_exists(user):
            if bank.can_spend(user, number):
                bank.withdraw_credits(user, number)
                return True
            else:
                await self.bot.say("You do not have enough credits in your account to place that bet.")
                return False
        else:
            await self.bot.say("You do not have a bank account.")
            return False

    def game_payouts(self, number, server):
        bank = self.bot.get_cog("Economy").bank
        if number in self.rednum:
            for subdict in self.roulette["Players"]:
                if "Red" in self.roulette["Players"][subdict]:
                    bet = self.roulette["Players"][subdict]["Red"]["Bet"]
                    amount = bet * 2
                    mobj = server.get_member(subdict)
                    bank.deposit_credits(mobj, amount)
        if number in self.blacknum:
            for subdict in self.roulette["Players"]:
                if "Black" in self.roulette["Players"][subdict]:
                    bet = self.roulette["Players"][subdict]["Black"]["Bet"]
                    amount = bet * 2
                    mobj = server.get_member(subdict)
                    bank.deposit_credits(mobj, amount)
        if number in self.oddnum:
            for subdict in self.roulette["Players"]:
                if "Odd" in self.roulette["Players"][subdict]:
                    bet = self.roulette["Players"][subdict]["Odd"]["Bet"]
                    amount = bet * 2
                    mobj = server.get_member(subdict)
                    bank.deposit_credits(mobj, amount)
        if number in self.evennum:
            for subdict in self.roulette["Players"]:
                if "Even" in self.roulette["Players"][subdict]:
                    bet = self.roulette["Players"][subdict]["Even"]["Bet"]
                    amount = bet * 2
                    mobj = server.get_member(subdict)
                    bank.deposit_credits(mobj, amount)
        if number in self.half1num:
            for subdict in self.roulette["Players"]:
                if "Half1" in self.roulette["Players"][subdict]:
                    bet = self.roulette["Players"][subdict]["Half1"]["Bet"]
                    amount = bet * 2
                    mobj = server.get_member(subdict)
                    bank.deposit_credits(mobj, amount)
        if number in self.half2num:
            for subdict in self.roulette["Players"]:
                if "Half2" in self.roulette["Players"][subdict]:
                    bet = self.roulette["Players"][subdict]["Half2"]["Bet"]
                    amount = bet * 2
                    mobj = server.get_member(subdict)
                    bank.deposit_credits(mobj, amount)
        if number in self.dozen1num:
            for subdict in self.roulette["Players"]:
                if "Dozen1" in self.roulette["Players"][subdict]:
                    bet = self.roulette["Players"][subdict]["Dozen1"]["Bet"]
                    amount = bet * 2 + bet
                    mobj = server.get_member(subdict)
                    bank.deposit_credits(mobj, amount)
        if number in self.dozen2num:
            for subdict in self.roulette["Players"]:
                if "Dozen2" in self.roulette["Players"][subdict]:
                    bet = self.roulette["Players"][subdict]["Dozen2"]["Bet"]
                    amount = bet * 2 + bet
                    mobj = server.get_member(subdict)
                    bank.deposit_credits(mobj, amount)
        if number in self.dozen3num:
            for subdict in self.roulette["Players"]:
                if "Dozen3" in self.roulette["Players"][subdict]:
                    bet = self.roulette["Players"][subdict]["Dozen3"]["Bet"]
                    amount = bet * 2 + bet
                    mobj = server.get_member(subdict)
                    bank.deposit_credits(mobj, amount)
        if number in self.highnum:
            for subdict in self.roulette["Players"]:
                if "High" in self.roulette["Players"][subdict]:
                    bet = self.roulette["Players"][subdict]["High"]["Bet"]
                    amount = bet * 2
                    mobj = server.get_member(subdict)
                    bank.deposit_credits(mobj, amount)
        if number in self.lownum:
            for subdict in self.roulette["Players"]:
                if "Low" in self.roulette["Players"][subdict]:
                    bet = self.roulette["Players"][subdict]["Low"]["Bet"]
                    amount = bet * 2
                    mobj = server.get_member(subdict)
                    bank.deposit_credits(mobj, amount)
        if number in self.numbers:
            for subdict in self.roulette["Players"]:
                if "Straight" in self.roulette["Players"][subdict]:
                    if number == self.roulette["Players"][subdict]["Straight"]["Number"]:
                        bet = self.roulette["Players"][subdict]["Straight"]["Bet"]
                        amount = bet * 35 + bet
                        mobj = server.get_member(subdict)
                        bank.deposit_credits(mobj, amount)


def check_folders():
    if not os.path.exists("data/casino"):
        print("Creating data/casino folder...")
        os.makedirs("data/casino")


def check_files():
    system = {"Players": {},
              "Config": {"Timer": 30,
                         "Min Bet": 0,
                         "Active": False,
                         "Betting Closed": True}}

    f = "data/casino/roulette.json"
    if not fileIO(f, "check"):
        print("Creating default roulette.json...")
        fileIO(f, "save", system)
    else:  # consistency check
        current = fileIO(f, "load")
        if current.keys() != system.keys():
            for key in system.keys():
                if key not in current.keys():
                    current[key] = system[key]
                    print("Adding " + str(key) +
                          " field to casino's roulette.json")
            fileIO(f, "save", current)


def setup(bot):
    check_folders()
    check_files()
    n = Roulette(bot)
    bot.add_cog(n)
