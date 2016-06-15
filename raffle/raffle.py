# Developed by Redjumpman for Redbot
# This cog requires no library installs
# If you have issues contact Redjumpman#2375 on Discord
import uuid
import os
import random
import asyncio
from .utils import checks
from discord.ext import commands
from .utils.dataIO import fileIO
from __main__ import send_cmd_help


class Raffle:
    """Raffle system where you buy tickets with points"""

    def __init__(self, bot):
        self.bot = bot
        self.raffle = fileIO("data/raffle/raffle.json", "load")

    @commands.group(name="raffle", pass_context=True)
    async def _raffle(self, ctx):
        """Raffle Commands"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_raffle.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def start(self, ctx):
        """Starts a raffle"""
        user = ctx.message.author
        if not self.raffle["Config"]["Active"]:
            self.raffle["Config"]["Active"] = True
            fileIO("data/raffle/raffle.json", "save", self.raffle)
            await self.bot.say("@everyone a raffle has been started by " + user.name +
                               ".\n" + "Use the command 'raffle buy' to purchase tickets.")
        else:
            await self.bot.say("A raffle is currently active. End the current one to start a new one.")

    @_raffle.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def end(self, ctx):
        """Ends a raffle"""
        if self.raffle["Config"]["Active"]:
            self.raffle["Config"]["Active"] = False
            tickets = self.raffle["Config"]["Tickets"]
            winning_ticket = random.choice(tickets)
            winner = []
            for subdict in self.raffle["Players"]:
                if winning_ticket in self.raffle["Players"][subdict]["Tickets"]:
                    winner.append(subdict)
            mention = "<@" + winner[0] + ">"
            await self.bot.say("The winner of the raffle is...")
            await asyncio.sleep(3)
            await self.bot.say(mention + "! Congratulations, you have won!")
            self.raffle["Config"]["Tickets"] = []
            self.raffle["Players"] = {}
            fileIO("data/raffle/raffle.json", "save", self.raffle)
        else:
            await self.bot.say("You need to start a raffle for me to end one!")

    @_raffle.command(pass_context=True, no_pm=True)
    async def buy(self, ctx, number: int):
        """Buys raffle ticket(s)"""
        user = ctx.message.author
        econ = self.bot.get_cog('Economy')
        code = str(uuid.uuid4())
        if number > 0:
            if self.raffle["Config"]["Active"]:
                ticket_cost = self.raffle["Config"]["Cost"]
                points = ticket_cost * number
                if econ.enough_money(user.id, points):
                    if user.id in self.raffle["Players"]:
                        econ.withdraw_money(user.id, points)
                        self.raffle["Players"][user.id]["Tickets"] += [code] * number
                        self.raffle["Config"]["Tickets"] += [code] * number
                        fileIO("data/raffle/raffle.json", "save", self.raffle)
                        await self.bot.say(user.mention + " has purchased " + str(number) +
                                           " raffle tickets for " + str(points))
                    else:
                        econ.withdraw_money(user.id, points)
                        self.raffle["Players"][user.id] = {}
                        self.raffle["Players"][user.id] = {"Tickets": []}
                        self.raffle["Players"][user.id]["Tickets"] += [code] * number
                        self.raffle["Config"]["Tickets"] += [code] * number
                        fileIO("data/raffle/raffle.json", "save", self.raffle)
                        await self.bot.say(user.mention + " has purchased " + str(number) +
                                           " raffle tickets for " + str(points))
                else:
                    await self.bot.say("You do not have enough points to purchase that many raffle tickets" + "\n" +
                                       "Raffle tickets cost " + ticket_cost + " points each.")
            else:
                await self.bot.say("There is not a raffle currently active")
        else:
            await self.bot.say("You need to pick a number higher than 0")

    @_raffle.command(pass_context=True, no_pm=True)
    async def check(self, ctx):
        """Shows you the number of raffle tickets you bought"""
        user = ctx.message.author
        if user.id in self.raffle["Players"]:
            tickets = self.raffle["Players"][user.id]["Tickets"]
            amount = str(len(tickets))
            await self.bot.say("You currently have " + amount + " tickets")
        else:
            await self.bot.say("You have not bought any tickets for the raffle.")

    @_raffle.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def cost(self, ctx, price: int):
        """Sets the cost of raffle tickets"""
        self.raffle["Config"]["Cost"] = price
        fileIO("data/raffle/raffle.json", "save", self.raffle)
        await self.bot.say("```" + "The price for 1 raffle ticket is now set to " + str(price) + "```")


def check_folders():
    if not os.path.exists("data/raffle"):
        print("Creating data/raffle folder...")
        os.makedirs("data/raffle")


def check_files():
    system = {"Players": {},
              "Config": {"Tickets": [],
                         "Cost": 50,
                         "Active": False}}
    f = "data/raffle/raffle.json"
    if not fileIO(f, "check"):
        print("Creating default raffle/raffle.json...")
        fileIO(f, "save", system)


def setup(bot):
    check_folders()
    check_files()
    n = Raffle(bot)
    bot.add_cog(n)
