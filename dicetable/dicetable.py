# DiceTable was created by Redjumpman for Red Bot

# Standard Library
import random
import re

# Discord
import discord

# Red
from redbot.core import commands

# Third Party Libraries
from tabulate import tabulate


__version__ = "2.0.05"
__author__ = "Redjumpman"


class DiceTable(commands.Cog):
    """Rolls a table of dice"""

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete."""
        return

    @commands.group(autohelp=True)
    async def dtable(self, ctx: commands.Context):
        """Dice Table Group"""
        pass

    @dtable.command()
    async def version(self, ctx: commands.Context):
        """Shows the current version of dicetable."""
        await ctx.send("You are running Dice Table version {}".format(__version__))

    @dtable.command()
    async def roll(self, ctx: commands.Context, dice: str, times=1, modifier=0):
        """Rolls a set of die in the format 2d12.

        By default only one set of die is rolled, without a
        modifier. Example 3d20 5 1 will roll three 1d20 dice for
        five seperate instances, with a +1 modifier added to the total.
        """

        if times < 1:
            return await ctx.send("You need to have at least one roll instance.")

        if times > 20:
            return await ctx.send("Cannot roll more than 20 instances at a time.")

        try:
            die, maximum = self.parse_dice(dice)
        except IndexError:
            return await ctx.send(
                "Must be in the format of `number` `die` `number` Example:\n2d12, 1d20, 5d6, 2d4 3 4"
            )

        if modifier < 0:
            sign = ""
        else:
            sign = "+"

        rolls = [
            ("{}".format(x), self.roll_dice(die, maximum), sign + str(modifier))
            for idx, x in enumerate(range(1, times + 1))
        ]
        final = [x + (str(x[1] + modifier),) for x in rolls]

        # Add row at bottom to show sums
        sum_total = sum([int(x[1] + modifier) for x in rolls])
        sum_base = sum([int(x[1]) for x in rolls])
        sum_modifier = int(modifier) * len(rolls)
        sum_row = ("Sum:", sum_base, sum_modifier, sum_total)
        final.append(sum_row)

        headers = ["Roll", "Result", "Modifier", "Total"]
        t = "**Dice:** {}\n```{}```".format(dice, tabulate(final, headers=headers))
        embed = discord.Embed(title="Dice Table Output", color=0x3366FF)
        embed.add_field(name="\u200b", value=t, inline=False)
        embed.add_field(name="\u200b", value="\u200b")
        await ctx.message.delete()
        await ctx.send(embed=embed)

    @staticmethod
    def parse_dice(dice):
        parts = re.findall("([0-9]+|[A-Z])", dice, re.I)
        if parts[0].isdigit() and parts[2].isdigit() and parts[1] == "d":
            die = parts[0]
            maximum = parts[2]
            return int(die), int(maximum)
        else:
            raise IndexError

    @staticmethod
    def roll_dice(die, maximum):
        return sum(random.randint(1, maximum) for _ in range(die))
