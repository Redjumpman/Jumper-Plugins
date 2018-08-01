# Cookie was created by Redjumpman for Redbot
# Design credit to discord user Yukirin for commissioning this project

# Standard Library
import asyncio
import os
import random
import time
from operator import itemgetter

# Discord and Red
import discord
from .utils import checks
from __main__ import send_cmd_help
from .utils.dataIO import dataIO
from discord.ext import commands


class PluralDict(dict):
    """This class is used to plural strings

    You can plural strings based on the value input when using this class as a dictionary.
    """
    def __missing__(self, key):
        if '(' in key and key.endswith(')'):
            key, rest = key.split('(', 1)
            value = super().__getitem__(key)
            suffix = rest.rstrip(')').split(',')
            if len(suffix) == 1:
                suffix.insert(0, '')
            return suffix[0] if value <= 1 else suffix[1]
        raise KeyError(key)


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
    async def give(self, ctx, user: discord.Member, cookies: int):
        """Gives another user your cookies"""
        author = ctx.message.author
        settings = self.check_server_settings(author.server)
        if user.bot:
            return await self.bot.say("Nice try, us bots can't accept cookies from strangers.")
        if author.id == user.id:
            return await self.bot.say("You can't give yourself cookies.")
        self.account_check(settings, author)
        self.account_check(settings, user)
        sender_cookies = settings["Players"][author.id]["Cookies"]
        if 0 < cookies <= sender_cookies:
            settings["Players"][author.id]["Cookies"] -= cookies
            settings["Players"][user.id]["Cookies"] += cookies
            dataIO.save_json(self.file_path, self.system)
            msg = "You gave **{}** cookies to {}".format(cookies, user.name)
        else:
            msg = "You don't have enough cookies in your account"

        await self.bot.say(msg)

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
        server = author.server
        action = "Steal CD"
        settings = self.check_server_settings(author.server)
        self.account_check(settings, author)

        if user is None:
            user = self.random_user(settings, author, server)

        if user == "Fail":
            pass
        elif user == author:
            return await self.bot.say("Hold up mate! I don't know what you're smoking, but I can't allow that")
        elif user.bot:
            return await self.bot.say("Stealing failed because the picked target is a bot.\nYou "
                                      "can retry stealing again, your cooldown is not consumed.")

        if await self.check_cooldowns(author.id, action, settings):
            msg = self.steal_logic(settings, user, author)
            await self.bot.say("ଲ(=(|) ɪ (|)=)ଲ Neko-chan is on the prowl to steal :cookie:")
            await asyncio.sleep(4)
            await self.bot.say(msg)

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

    def steal_logic(self, settings, user, author):
        success_chance = random.randint(1, 100)
        if user == "Fail":
            msg = "ω(=OｪO=)ω Nyaaaaaaaan! I couldn't find anyone with cookies!"
            return msg

        if user.id not in settings["Players"]:
            self.account_check(settings, user)

        if settings["Players"][user.id]["Cookies"] == 0:
            msg = ("ω(=｀ｪ ´=)ω Nyaa! Neko-chan is sorry, nothing but crumbs in this human's "
                   ":cookie: jar!")
        else:
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
                msg = "ω(=｀ｪ ´=)ω Nyaa... Neko-chan couldn't find their :cookie: jar!"
        return msg

    def random_user(self, settings, author, server):
        filter_users = [server.get_member(x) for x in settings["Players"]
                        if hasattr(server.get_member(x), "name")]
        legit_users = [x for x in filter_users if x.id != author.id and x is not x.bot]

        users = [x for x in legit_users if settings["Players"][x.id]["Cookies"] > 0]

        if not users:
            user = "Fail"
        else:
            user = random.choice(users)
            if user == user.bot:
                users.remove(user.bot)
                settings["Players"].pop(user.bot)
                dataIO.save_json(self.file_path, self.system)
                user = random.choice(users)
            self.account_check(settings, user)
        return user

    def account_check(self, settings, userobj):
        if userobj.id not in settings["Players"]:
            settings["Players"][userobj.id] = {"Cookies": 0,
                                               "Steal CD": 0,
                                               "Cookie CD": 0}
            dataIO.save_json(self.file_path, self.system)

    def time_formatting(self, seconds):
        # Calculate the time and input into a dict to plural the strings later.
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
            msg = "None"
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
