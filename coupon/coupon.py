import uuid
import discord

from redbot.core import bank, checks, commands, Config
from redbot.core.utils.chat_formatting import box, pagify


async def pred(ctx):
    global_bank = await bank.is_global()
    if not global_bank:
        return True
    else:
        return False


global_bank_check = commands.check(pred)


class Coupon(commands.Cog):
    """Creates redeemable coupons for credits.

    The bank must be in guild mode and not global mode for this cog to work."""

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete."""
        return

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 2779691001, force_registration=True)

        default_guild = {"coupons": {}}

        self.config.register_guild(**default_guild)

    @commands.guild_only()
    @commands.group()
    @global_bank_check
    async def coupon(self, ctx):
        """Coupon commands."""
        pass

    @coupon.command(name="clearall")
    @checks.mod_or_permissions(manage_guild=True)
    @global_bank_check
    async def _clearall_coupon(self, ctx):
        """Clears all unclaimed coupons."""
        await self.config.guild(ctx.guild).clear()
        await ctx.send("All unclaimed coupon codes have been cleared from the list.")

    @coupon.command(name="create")
    @checks.admin_or_permissions(manage_guild=True)
    @global_bank_check
    async def _create_coupon(self, ctx, credits: int):
        """Generates a unique coupon code."""
        code = str(uuid.uuid4())
        try:
            settings = await self.config.guild(ctx.guild).coupons()
            settings.update({coupon: credits})
            await self.config.guild(ctx.guild).coupons.set(settings)
            await ctx.author.send(f"I have created a coupon for `{credits}` credits.\nThe code is: `{code}`")
        except discord.Forbidden:
            await ctx.author.send("I was not able to DM you the code. Please open your DMs and try again.")

    @coupon.command(name="list")
    @checks.admin_or_permissions(manage_guild=True)
    @global_bank_check
    async def _list_coupon(self, ctx):
        """Shows active coupon codes."""
        settings = await self.config.guild(ctx.guild).coupons()
        SPACE = "\N{SPACE}"
        msg = f"[Code]{SPACE * 30} | [Credits]\n"
        if len(settings) == 0:
            msg += "No active codes."
        else:
            for code, credits in settings.items():
                msg += f"{code} | {credits}\n"
        for text in pagify(msg):
            await ctx.send(box(text, lang="ini"))

    @coupon.command(name="redeem")
    @global_bank_check
    async def _redeem_coupon(self, ctx, coupon: str):
        """Redeems a coupon code, can be done through DM with the bot."""
        if len(coupon) == 36:
            settings = await self.config.guild(ctx.guild).coupons()
            if coupon in settings:
                credits = settings[coupon]
                await bank.deposit_credits(ctx.author, credits)
                del settings[coupon]
                await self.config.guild(ctx.guild).coupons.set(settings)
                await ctx.send(f"I have added {credits} credits to your account.")
            else:
                await ctx.send("This coupon either does not exist or has already been redeemed.")
        else:
            await ctx.send("This is not a valid coupon code.")
