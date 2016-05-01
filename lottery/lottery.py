import os
import logging
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
from random import choice as randchoice
try:   # Check if Tabulate is installed
    from tabulate import tabulate
    tabulateAvailable = True
except:
    tabulateAvailable = False


class Lottery:
    """Starts a lottery on the server"""

    def __init__(self, bot):
        self.bot = bot
        self.players = fileIO("data/lottery/players.json", "load")
        self.system = fileIO("data/lottery/system.json", "load")

    @commands.group(name="lottery", pass_context=True)
    async def _lottery(self, ctx):
        """Lottery Commands."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_lottery.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def start(self, ctx):
        """Begins the lottery until you enter a stop command"""
        user = ctx.message.author
        if self.system["lottery_start"] == "Inactive":
            self.system["lottery_start"] = "Active"
            self.system["lotteries_played"] = self.system[
                                                             "lotteries_played"
                                                             ] + 1
            fileIO("data/lottery/system.json", "save", self.system)
            await self.bot.say("A lottery has been started by " +
                               user.mention +
                               "\n" + "To enter type, !lottery play." +
                               " Make sure to sign up or you can't play!!")
        else:
            await self.bot.say("You cannot start another lottery while one" +
                               " is active." + "\n" + "End the current" +
                               " lottery to start another.")

    @_lottery.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def end(self, ctx):
        """This will stop the lottery and pick a winner"""
        if self.system["lottery_start"] == "Active":
            self.system["lottery_start"] = "Inactive"
            fileIO("data/lottery/system.json", "save", self.system)
            results = []
            for subdict in self.players.values():
                results.append(subdict['current_ticket'])
            for subdict in self.players.values():
                subdict['ticket_played'] = "No"
            fileIO("data/lottery/players.json", "save", self.players)
            f = list(filter(None, results))
            winner = randchoice(f)
            await self.bot.say("The lottery has ended. The winner is:  " +
                               str(winner) + "!!!")
            await self.bot.say("Congratulations " + str(winner))
            for subdict in self.players.values():
                subdict['current_ticket'] = ""
            fileIO("data/lottery/players.json", "save", self.players)

        else:
            await self.bot.say("You can't end a lottery that I have"
                               " not started.")

    @_lottery.command(pass_context=True, no_pm=True)
    async def signup(self, ctx):
        """This allows a user to sign-up to play lotteries"""
        user = ctx.message.author
        if user.id not in self.players:
            self.players[user.id] = {"name": user.name,
                                     "lotteries_played": 0,
                                     "lotteries_won": 0,
                                     "current_ticket": "",
                                     "ticket_played": "No"}
            fileIO("data/lottery/players.json", "save", self.players)
            await self.bot.say("You have joined the lottery system " +
                               user.mention + ". You can now participate in" +
                               " all future lotteries")
        else:
            await self.bot.say("You are already a lottery member")

    @_lottery.command(pass_context=True, no_pm=True)
    async def play(self, ctx):
        """This let's a user play in an on-going lottery"""
        user = ctx.message.author
        id = user.id
        if self.system["lottery_start"] == "Active":
            if user.id in self.players:
                if self.players[id]["ticket_played"] == "No":
                    self.players[id]["ticket_played"] = "Yes"
                    self.players[id]["current_ticket"] = user.name
                    self.players[id]["lotteries_played"] = self.players[id][
                        "lotteries_played"
                        ] + 1
                    fileIO("data/lottery/players.json", "save", self.players)
                    await self.bot.say("You have been entered into the" +
                                       " lottery")
                else:
                    await self.bot.say("You have already been entered into " +
                                       "this lottery.")
            else:
                await self.bot.say("You need to sign-up to play in an " +
                                   "ongoing lottery")
        else:
            await self.bot.say("There is currently no on-going lottery")

    @_lottery.command(pass_context=True, no_pm=True)
    async def stats(self, ctx):
        """Retrieves a user's lottery stats"""
        user = ctx.message.author
        id = user.id
        if user.id in self.players:
            results = self.players[id].values()
            result_list = list(results)
            keys = ["Lotteries Played:", "Lottery Player:", "Ticket Name:",
                    "Lotteries Won:", "Playing in a lottery:"]
            stats = list(zip(keys, result_list))
            t = tabulate(stats)
            await self.bot.say("\n" + "```" + str(t) + "```")
        else:
            await self.bot.say("You need to sign-up for lotteries first.")


def check_folders():
    if not os.path.exists("data/lottery"):
        print("Creating data/lottery folder...")
        os.makedirs("data/lottery")


def check_files():
    system = {"lotteries_played": 0, "lottery_start": "Inactive"}

    f = "data/lottery/system.json"
    if not fileIO(f, "check"):
        print("Creating default lottery system.json...")
        fileIO(f, "save", system)

    f = "data/lottery/players.json"
    if not fileIO(f, "check"):
        print("Adding lottery player.json...")
        fileIO(f, "save", {})


def setup(bot):
    global logger
    check_folders()
    check_files()
    logger = logging.getLogger("lottery")
# Prevents the logger from being loaded again in case of module reload
    if logger.level == 0:
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(filename='data/lottery/lottery.log',
                                      encoding='utf-8', mode='a')
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s',
                                               datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
        if tabulateAvailable:
            bot.add_cog(Lottery(bot))
        else:
            raise RuntimeError("You need to run 'pip3 install tabulate'")
