# Cookie was created by Redjumpman for Redbot
# Design credit to discord user Yukirin for commissioning this project
import os
import random
import discord
import asyncio
import time
from .utils import checks
from __main__ import send_cmd_help
from .utils.dataIO import dataIO
from discord.ext import commands


class Cookie:
    """Neko-chan loves cookies, and will steal from others for you!"""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/JumperCogs/cookie/cookie.json"
        self.system = dataIO.load_json(self.file_path)

    @commands.group(pass_context=True, no_pm=True)
    async def setcookie(self, ctx):
        """Cookie settings group command"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @setcookie.command(name="stealcd", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _stealcd_heist(self, ctx, cooldown: int):
        """Set the cooldown for stealing cookies"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if cooldown >= 0:
            settings["Config"]["Steal CD"] = cooldown
            dataIO.save_json(self.file_path, self.system)
            msg = "Cooldown for steal set to {}".format(cooldown)
        else:
            msg = "Cooldown needs to be higher than 0."
        await self.bot.say(msg)

    @setcookie.command(name="cookiecd", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _cookiecd_heist(self, ctx, cooldown: int):
        """Set the cooldown for cookie command"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if cooldown >= 0:
            settings["Config"]["Cookie CD"] = cooldown
            dataIO.save_json(self.file_path, self.system)
            msg = "Cooldown for cookie set to {}".format(cooldown)
        else:
            msg = "Cooldown needs to be higher than 0."
        await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True)
    async def give(self, ctx, user: discord.Member, gives:int):
        """Gives another user your cookies"""
        author = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        self.account_check(settings, author)
        cookies = settings["Players"][author.id]["Cookies"]
        if user is None:
           return await self.bot.say("Specify a user to give your cookies to.")
        else:
            if gives <= 0 or gives > cookies:
               return await self.bot.say("You don't have enough cookies in your account")
            if cookies <= cookies:
                settings["Players"][author.id]["Cookies"] -= gives
                settings["Players"][user.id]["Cookies"] += gives
                dataIO.save_json(self.file_path, self.system)
                return await self.bot.say("You gave **{}** cookies to {}".format(gives, user.name))
        
    @commands.command(pass_context=True, no_pm=True)
    async def cookie(self, ctx):
        """Obtain a random number of cookies. 12h cooldown"""
        author = ctx.message.author
        server = ctx.message.server
        action = "Cookie CD"
        settings = self.check_server_settings(server)
        self.account_check(settings, author)
        if await self.check_cooldowns(author.id, action, settings):
            weighted_sample = [1] * 152 + [x for x in range(49) if x > 1]
            cookies = random.choice(weighted_sample)
            settings["Players"][author.id]["Cookies"] += cookies
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("~₍˄·͈༝·͈˄₍˄·͈༝·͈˄ （（≡￣♀￣≡））˄·͈༝·͈˄₎₍˄·͈༝·͈˄₎◞ ̑̑ \nYou recieved {} "
                               "cookie(s) from the cookie Gods! Nyaaaaaan!".format(cookies))

    @commands.command(pass_context=True, no_pm=False, ignore_extra=False)
    async def jar(self, ctx):
        """See how many cookies are in your jar."""
        author = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        self.account_check(settings, author)
        cookies = settings["Players"][author.id]["Cookies"]
        await self.bot.whisper("ฅ(=＾‥ ＾=)ฅ Neko-chan sees you have **{}** cookies in the jar. "
                               "Nyaa nyaa.".format(cookies))

    @commands.command(pass_context=True, no_pm=True)
    async def steal(self, ctx, user: discord.Member=None):
        """Steal cookies from another user. 2h cooldown."""
        author = ctx.message.author
        server = ctx.message.server
        action = "Steal CD"
        settings = self.check_server_settings(server)
        self.account_check(settings, author)
        if not user:
            users = [server.get_member(x) for x in settings["Players"].keys() if x != author.id and x in settings["Players"].keys()]
            users = [x for x in users if settings["Players"][x.id]["Cookies"] > 0]
            if not users:
                user = "Fail"
            else:
                user = random.choice(users)
                self.account_check(settings, user)
        if await self.check_cooldowns(author.id, action, settings):
            if user == "Fail":
                msg = "ω(=OｪO=)ω Nyaaaaaaaan! I couldn't find anyone with cookies!"
            elif settings["Players"][user.id]["Cookies"] == 0:
                msg = ("ω(=｀ｪ ´=)ω Nyaa! Neko-chan is sorry, nothing but crumbs in this human's "
                       ":cookie: jar!")
            else:
                success_chance = random.randint(1, 100)
                if success_chance <= 90:
                    cookie_jar = settings["Players"][user.id]["Cookies"]
                    cookies_stolen = int(cookie_jar * 0.75)
                    if cookies_stolen == 0:
                        cookies_stolen = 1
                    stolen = random.randint(1, cookies_stolen)
                    settings["Players"][user.id]["Cookies"] -= stolen
                    settings["Players"][author.id]["Cookies"] += stolen
                    dataIO.save_json(self.file_path, self.system)
                    msg = ("ω(=＾ ‥ ＾=)ﾉ彡:cookie:\nYou stole {} cookies from "
                          "{}!".format(stolen, user.name))
                else:
                    msg = ("ω(=｀ｪ ´=)ω Nyaa... Neko-chan couldn't find their :cookie: jar!")
            await self.bot.say("ଲ(=(|) ɪ (|)=)ଲ Neko-chan is on the prowl to steal :cookie:")
            await asyncio.sleep(3)
            await self.bot.say(msg)

    def account_check(self, settings, userobj):
        if userobj.id not in settings["Players"]:
            settings["Players"][userobj.id] = {"Cookies": 0,
                                               "Steal CD": 0,
                                               "Cookie CD": 0}
            dataIO.save_json(self.file_path, self.system)

    async def check_cooldowns(self, userid, action, settings):
        path = settings["Config"][action]
        if abs(settings["Players"][userid][action] - int(time.perf_counter())) >= path:
            settings["Players"][userid][action] = int(time.perf_counter())
            dataIO.save_json(self.file_path, self.system)
            return True
        elif settings["Players"][userid][action] == 0:
            settings["Players"][userid][action] = int(time.perf_counter())
            dataIO.save_json(self.file_path, self.system)
            return True
        else:
            s = abs(settings["Players"][userid][action] - int(time.perf_counter()))
            seconds = abs(s - path)
            remaining = self.time_formatting(seconds)
            await self.bot.say("This action has a cooldown. You still have:\n{}".format(remaining))
            return False

    def time_formatting(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        msg = "```{} hours, {} minutes and {} seconds remaining```".format(h, m, s)
        return msg

    def check_server_settings(self, server):
        if server.id not in self.system["Servers"]:
            self.system["Servers"][server.id] = {"Players": {},
                                                 "Config": {"Steal CD": 5,
                                                            "Cookie CD": 5}
                                                 }
            dataIO.save_json(self.file_path, self.system)
            print("Creating default heist settings for Server: {}".format(server.name))
            path = self.system["Servers"][server.id]
            return path
        else:
            path = self.system["Servers"][server.id]
            return path


def check_folders():
    if not os.path.exists("data/JumperCogs/cookie"):
        print("Creating data/JumperCogs/cookie folder...")
        os.makedirs("data/JumperCogs/cookie")


def check_files():
    default = {"Servers": {}}

    f = "data/JumperCogs/cookie/cookie.json"
    if not dataIO.is_valid_json(f):
        print("Creating default cookie.json...")
        dataIO.save_json(f, default)


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Cookie(bot))
