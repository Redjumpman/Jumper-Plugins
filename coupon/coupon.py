import uuid
import os
from discord.ext import commands
from .utils.dataIO import fileIO
from __main__ import send_cmd_help
from .utils import checks


class Coupon:
    """Creates redeemable coupons for points"""

    def __init__(self, bot):
        self.bot = bot
        self.coupons = fileIO("data/coupon/coupons.json", "load")

    @commands.group(name="coupon", pass_context=True)
    async def _coupon(self, ctx):
        """Coupon commands"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_coupon.command(pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def create(self, ctx, points: int):
        """Generates a unique coupon code"""
        code = str(uuid.uuid4())
        self.coupon_add(code, points)
        await self.bot.whisper("I have created a coupon for " + str(points) +
                               " points. The code is: " + "\n" + code)

    @_coupon.command(pass_context=True)
    async def redeem(self, ctx, coupon):
        """Redeems a coupon code, can be done through PM with the bot"""
        user = ctx.message.author
        if len(coupon) == 36:
            if coupon in self.coupons:
                points = self.coupons[coupon]["Points"]
                econ = self.bot.get_cog('Economy')
                econ.add_money(user.id, points)
                del self.coupons[coupon]
                fileIO("data/coupon/coupons.json", "save", self.coupons)
                await self.bot.say("I have added " + str(points) + " to your account")
            else:
                await self.bot.say("This coupon either does not exist or has already been redeemed.")
        else:
            await self.bot.say("This is not a valid coupon code.")

    def coupon_add(self, coupon, points):
        self.coupons[coupon] = {"Points": points}
        fileIO("data/coupon/coupons.json", "save", self.coupons)

    def coupon_redeem(self, coupon):
        if coupon in self.coupons:
            del self.coupons[coupon]
            fileIO("data/coupon/coupons.json", "save", self.coupons)
        else:
            return False


def check_folders():
    if not os.path.exists("data/coupon"):
        print("Creating data/coupon folder...")
        os.makedirs("data/coupon")


def check_files():
    f = "data/coupon/coupons.json"
    if not fileIO(f, "check"):
        print("Creating default coupon/coupons.json...")
        fileIO(f, "save", {})


def setup(bot):
    check_folders()
    check_files()
    n = Coupon(bot)
    bot.add_cog(n)
