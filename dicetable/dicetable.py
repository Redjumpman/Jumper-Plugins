# DiceTable was created by Redjumpman for Red Bot

# Standard Library
import random
import re

# Discord
from discord.ext import commands
from __main__ import send_cmd_help

# Third Party Libraries
try:
    from tabulate import tabulate
    tabulateAvailable = True
except:
    tabulateAvailable = False


class FormatError(Exception):
    pass


class NegativeValue(Exception):
    pass


class RollError(Exception):
    pass


class DiceTable:
    """Rolls a table of dice"""

    def __init__(self, bot):
        self.bot = bot
        self.group = []
        self.version = 2.0

    @commands.group(pass_context=True)
    async def dtable(self, ctx):
        """Shows a list under this group commands."""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @dtable.command(name="version")
    async def _version_dtable(self):
        await self.bot.say("You are running dicetable version {}".format(self.version))

    @dtable.command(name="roll", pass_context=False)
    async def _roll_dtable(self, dice: str, times=1, modifier=0):
        """Rolls a set of die in the format 2d12
        By default only one set of die is rolled, without a
        modifier. Example 3d20 5 1 will roll three 1d20 dice for
        five seperate instances, with a +1 modifier added to the total."""

        if modifier < 0:
            raise NegativeValue("Modifier can't be less than 0.")

        if times < 1:
            raise RollError("You need to have at least one roll instance.")
        elif times > 20:
            raise RollError("Cannot roll more than 20 instances at a time.")

        die, maximum = self.parse_dice(dice)
        rolls_raw = list(range(times))
        rolls = [(str("Roll {}".format(x + 1)), self.roll_dice(die, maximum), "+" + str(modifier))
                 for x in rolls_raw]
        print(rolls)
        final = [x + (str(x[1] + modifier),) for x in rolls]
        headers = ["Roll", "Result", "Modifier", "Total"]
        t = tabulate(final, headers=headers)
        await self.bot.say("```{}```".format(t))

    def parse_dice(self, dice):
        parts = re.findall("([0-9]+|[A-Z])", dice, re.I)
        try:
            if parts[0].isdigit() and parts[2].isdigit() and parts[1] == "d":
                die = parts[0]
                maximum = parts[2]
                return int(die), int(maximum)
            else:
                raise FormatError("Must be in the format of 2d12.")
        except IndexError:
            raise FormatError("Must be in the format of 2d12.")

    def roll_dice(self, die, maximum):
        roll = 0
        for x in range(die):
            roll += random.randint(1, maximum)
        return roll


def setup(bot):
    if tabulateAvailable:
        bot.add_cog(DiceTable(bot))
    else:
        raise RuntimeError("You need to run 'pip3 install tabulate'")
