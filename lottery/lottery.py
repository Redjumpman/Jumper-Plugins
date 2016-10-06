#  Lottery was created by Redjumpman for Redbot
#  This will create 2 data folders with 1 JSON file
import os
import asyncio
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help
from random import choice as randchoice


class Lottery:
    """Hosts lotteries on the server"""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/JumperCogs/lottery/system.json"
        self.system = dataIO.load_json(self.file_path)
        self.funny = ["Rigging the system...",
                      "Removing tickets that didn't pay me off...",
                      "Adding fake tickets...", "Throwing out the bad names..",
                      "Switching out the winning ticket...",
                      "Picking from highest bribe...",
                      "Looking for a marked ticket...",
                      "Eeny, meeny, miny, moe...",
                      "I lost the tickets so...",
                      "Stop messaging me, I'm picking...",
                      "May the odds be ever in your favor...",
                      "I'm going to ban that guy who keeps spamming me, 'please!'... ",
                      "Winner winner, chicken dinner...",
                      "Can someone tell the guy who keeps yelling 'Bingo!' that he is playing the wrong game..."]

    @commands.group(name="setlottery", pass_context=True)
    async def setlottery(self, ctx):
        """Lottery Settings"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @setlottery.command(name="prize", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _prize_setlottery(self, ctx, amount: int):
        """Set's the prize amount for a lottery. Set to 0 to cancel."""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if amount > 0:
            settings["Lottery Prize"] = True
            settings["Prize Amount"] = amount
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("A prize for the next lottery has been set for {} credits".format(amount))
        elif amount == 0:
            settings["Lottery Prize"] = False
            settings["Prize Amount"] = amount
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("Prize for the next lottery drawing removed.")
        else:
            await self.bot.say("You can't use negative values.")

    @setlottery.command(name="autofreeze", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _autofreeze_setlottery(self, ctx):
        """Turns on auto account freeze. Will freeze/unfreeze every 60 seconds."""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if settings["Membership Freeze"]:
            settings["Membership Freeze"] = False
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("Now turning off auto freeze. Please wait for the previous cycle to expire.")
        else:
            settings["Membership Freeze"] = True
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("Now turning on auto freeze. This will cycle through server accounts and freeze/unfreeze accounts that require the signup role.")
            self.bot.loop.create_task(self.auto_freeze(ctx, settings))

    @setlottery.command(name="fun", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _fun_setlottery(self, ctx):
        """Toggles fun text on and off"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if settings["Fun Text"]:
            settings["Fun Text"] = False
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("Fun Text is now disabled.")
        else:
            settings["Fun Text"] = True
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("Fun Text is now enabled.")

    @setlottery.command(name="role", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _role_setlottery(self, ctx, role: str):
        """Set the required role for membership sign-up. Default: None"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        settings["Signup Role"] = role
        dataIO.save_json(self.file_path, self.system)
        await self.bot.say("Setting the required role to sign-up to **{}**.\nUnless set to **None**, users must be assigned this role to signup!".format(role))

    @commands.group(name="lottery", pass_context=True)
    async def lottery(self, ctx):
        """Lottery Group Command"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @lottery.command(name="version", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _version_lottery(self):
        """Shows the version of lottery cog you are running."""
        version = self.system["Version"]
        await self.bot.say("```Python\nYou are running Lottery Cog version {}.```".format(version))

    @lottery.command(name="start", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _start_lottery(self, ctx, restriction=False, timer=0):
        """Starts a lottery. Can optionally restrict particpation and set a timer."""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if not settings["Lottery Active"]:
            settings["Lottery Count"] += 1
            if restriction:
                if not settings["Signup Role"]:  # Checks if admin set a role to mention, otherwise default to lottery members
                    lottery_role = "lottery members"
                else:
                    lottery_role = "@" + settings["Signup Role"]
                settings["Lottery Member Requirement"] = True
            else:
                lottery_role = "everyone on the server"
            settings["Lottery Active"] = True
            dataIO.save_json(self.file_path, self.system)
            if timer:
                await self.bot.say("A lottery has been started by {}, for {}. It will end in {} seconds.".format(user.name, lottery_role, timer))  # TODO Change timer to time formatter function
                await self.run_timer(timer, ctx.prefix, server, settings)
            else:
                await self.bot.say("A lottery has been started by {}, for {}.".format(user.name, lottery_role))
        else:
            await self.bot.say("I cannot start a new lottery until the current one has ended.")

    @lottery.command(name="end", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _end_lottery(self, ctx):
        """Manually ends an on-going lottery"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if settings["Lottery Active"]:
            if server.id in self.system["Lottery Players"]:
                players = list(self.system["Lottery Players"][server.id].keys())
                winner = randchoice(players)
                mention = self.system["Lottery Players"][server.id][winner]["Mention"]
                await self.display_lottery_winner(winner, mention, server, settings)
                self.update_win_stats(winner, server.id)
                self.lottery_clear(settings)
            else:
                await self.bot.say("There are no players playing in the lottery. Resetting lottery settings.")
                self.lottery_clear(settings)
        else:
            await self.bot.say("There is no lottery for me to end.")

    @lottery.command(name="play", pass_context=True)
    async def _play_lottery(self, ctx):
        """Enters a user into an on-going lottery."""
        server = ctx.message.server
        user = ctx.message.author
        settings = self.check_server_settings(server)
        if settings["Lottery Active"]:
            if await self.requirement_check(ctx, settings):
                if server.id not in self.system["Lottery Players"]:
                    self.system["Lottery Players"][server.id] = {}
                if user.id not in self.system["Lottery Players"][server.id]:
                    self.system["Lottery Players"][server.id][user.id] = {"Mention": user.mention}
                    players = len(self.system["Lottery Players"][server.id].keys())
                    dataIO.save_json(self.file_path, self.system)
                    self.update_play_stats(user.id, server.id)
                    await self.bot.say("{} you have been added to the lottery. Good luck.".format(user.mention))
                    await self.bot.say("There are now {} users participating in the lottery.".format(players))
                else:
                    await self.bot.say("You have already entered into the lottery.")
        else:
            await self.bot.say("There is no on-going lottery.")

    @lottery.command(name="signup", pass_context=True)
    async def _signup_lottery(self, ctx):
        """Allows a user to sign-up to participate in lotteries"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        role = settings["Signup Role"]
        if role:
            if self.role_check(ctx, role, user.id):
                await self.member_creation(user, server.id, ctx.prefix)
            else:
                await self.bot.say("You do not have the {} role required to become a member".format(role))
        else:
            await self.member_creation(user, server.id, ctx.prefix)

    @lottery.command(name="info", pass_context=True)
    async def _info_lottery(self, ctx):
        """General information about this plugin"""
        msg = """```
    General Information about Lottery Plugin\n
    =========================================\n
    • When starting a lottery you can optionally set a timer and/or restrict to members only.\n
    • By defualt all users can sign up for lottery membership. To retrict sign-ups to a role type {}setlottery role.\n
    • {}lottery stats will show your stats if you are signed-up.\n
    • You can freeze accounts that no longer have the sign-up role periodically by turning on {}setlottery freeze.\n
    • Autofreeze feature will need to be enabled again if you shutdown your bot.\n
    • Members who have a frozen account will no longer gain stats or particpate in member only lotteries.\n
    • If a member gets their role back after their account was frozen, they need to type {}lottery activate to unfreeze the account.\n
    • Lotteries can be hosted on different servers with the same bot without conflicts.\n
    • Powerballs have not yet been implemented, but the framework is complete. Ignore powerball stats.\n
    • Anyone can join a lottery without restrictions.```""".format(ctx.prefix, ctx.prefix, ctx.prefix, ctx.prefix, ctx.prefix)
        await self.bot.say(msg)

    @lottery.command(name="stats", pass_context=True)
    async def _stats_lottery(self, ctx):
        """Shows your membership stats"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        role = settings["Signup Role"]
        if server.id in self.system["Lottery Members"]:
            if user.id in self.system["Lottery Members"][server.id]:
                if not self.system["Lottery Members"][server.id][user.id]["Account Frozen"]:
                    member = self.system["Lottery Members"][server.id][user.id]
                    lotteries_played = member["Lotteries Played"]
                    lotteries_won = member["Lotteries Won"]
                    account_status = member["Account Frozen"]
                    msg = "```"
                    msg += "\n{}'s Lottery Stats on {}".format(user.name, server.name)
                    msg += "\n================================================="
                    msg += "\nLotteries Played:                   {}".format(lotteries_played)
                    msg += "\nLotteries Won:                      {}".format(lotteries_won)
                    if account_status:
                        msg += "\nAccount Status:                     Frozen"
                    else:
                        msg += "\nAccount Status:                     Active"
                    msg += "```"
                    await self.bot.say(msg)
                else:
                    await self.bot.say("Your account is frozen. You require the {} role on this server to track stats.\n".format(role) +
                                       "If you are given back this role, type {}lottery activate to restore your account.".format(ctx.prefix))
            else:
                await self.bot.say("You are not a lottery member. Only members can view/track stats.")
        else:
            await self.bot.say("There are no Lottery Members on this server.")

    def add_credits(self, userid, amount, server):
        bank = self.bot.get_cog('Economy').bank
        mobj = server.get_member(userid)
        bank.deposit_credits(mobj, amount)
        msg = "```{} credits have ben deposited into your account.```".format(amount)
        return msg

    def update_play_stats(self, userid, serverid):
        if serverid in self.system["Lottery Members"]:
            if userid in self.system["Lottery Members"][serverid]:
                self.system["Lottery Members"][serverid][userid]["Lotteries Played"] += 1
                dataIO.save_json(self.file_path, self.system)

    def update_win_stats(self, winner, server):
        if server in self.system["Lottery Members"]:
            if winner in self.system["Lottery Members"][server]:
                self.system["Lottery Members"][server][winner]["Lotteries Won"] += 1
                dataIO.save_json(self.file_path, self.system)

    def lottery_clear(self, settings):
        self.system["Lottery Players"] = {}
        settings["Lottery Prize"] = 0
        settings["Lottery Member Requirement"] = False
        settings["Lottery Active"] = False
        dataIO.save_json(self.file_path, self.system)

    def role_check(self, ctx, role, userid):
        if userid in [m.id for m in ctx.message.server.members if role.lower() in [str(r).lower() for r in m.roles]]:
            return True
        else:
            return False

    def check_server_settings(self, server):
        if server.id not in self.system["Config"]:
            self.system["Config"][server.id] = {server.name: {"Lottery Count": 0,
                                                              "Lottery Active": False,
                                                              "Fun Text": False,
                                                              "Lottery Winners": 1,
                                                              "Prize Amount": 0,
                                                              "Powerball Active": False,
                                                              "Powerball Reoccuring": True,
                                                              "Powerball Jackpot": 3000,
                                                              "Powerball Ticket Limit": 0,
                                                              "Powerball Ticket Cost": 0,
                                                              "Powerball Winning Ticket": None,
                                                              "Powerball Grace Period": 1,
                                                              "Powerball Day": "Sunday",
                                                              "Powerball Time": "1700",
                                                              "Powerball Combo Payouts": [2.0, 3.0, 10],
                                                              "Powerball Jackpot Type": "Preset",
                                                              "Powerball Jackpot Percentage": 0.31,
                                                              "Powerball Jackpot Multiplier": 2.0,
                                                              "Powerball Jackpot Preset": 500,
                                                              "Signup Role": None,
                                                              "Lottery Member Requirement": False,
                                                              "Membership Freeze": False,
                                                              }
                                                }
            dataIO.save_json(self.file_path, self.system)
            print("Creating default lottery settings for Server: {}".format(server.name))
            path = self.system["Config"][server.id][server.name]
            return path
        else:
            path = self.system["Config"][server.id][server.name]
            return path

    async def member_check(self, userid, serverid):
        if serverid in self.system["Lottery Members"]:
            if userid in self.system["Lottery Members"][serverid]:
                return True
            else:
                await self.bot.say("This requires a lottery membership.")
                return False
        else:
            await self.bot.say("This requires a lottery membership, but there are no members on this server.")
            return False

    async def requirement_check(self, ctx, settings):
        server = ctx.message.server
        user = ctx.message.author
        if settings["Lottery Member Requirement"]:
            if server.id in self.system["Lottery Members"]:
                if user.id in self.system["Lottery Members"][server.id]:
                    if self.system["Lottery Members"][server.id][user.id]["Account Frozen"]:
                        await self.bot.say("Your account is frozen. If you meet the role requirement use {}lottery activate to restore your account.".format(ctx.prefix))
                        return False
                    else:
                        return True
                else:
                    await self.bot.say("You do not meet the role requirment to participate in this lottery.")
                    return False
            else:
                return False
        else:
            return True

    async def run_timer(self, timer, prefix, server, settings):
        half_time = timer / 2
        quarter_time = half_time / 2
        await asyncio.sleep(half_time)
        if settings["Lottery Active"] is True:
            await self.bot.say("{} seconds remaining for the lottery. Type {}lottery play to join.".format(half_time, prefix))
            await asyncio.sleep(quarter_time)
            if settings["Lottery Active"] is True:
                await self.bot.say("{} seconds remaining for the lottery. Type {}lottery play to join.".format(quarter_time, prefix))
                await asyncio.sleep(quarter_time)
                if settings["Lottery Active"] is True:
                    await self.bot.say("The lottery is now ending...")
                    await asyncio.sleep(1)
                    await self.end_lottery_timer(server, settings)

    async def end_lottery_timer(self, server, settings):
        if settings["Lottery Active"]:
            if server.id in self.system["Lottery Players"]:
                players = self.system["Lottery Players"][server.id].keys()
                winner = randchoice(list(players))
                mention = "<@" + winner + ">"
                self.update_win_stats(winner, server.id)
                await self.display_lottery_winner(winner, mention, server, settings)
                self.lottery_clear(settings)
            else:
                await self.bot.say("There are no players in the lottery.")
                self.lottery_clear(settings)
        else:
            pass

    async def display_lottery_winner(self, winner, mention, server, settings):
        await self.bot.say("The winner is...")
        await asyncio.sleep(2)
        if settings["Fun Text"]:
            fun_text = randchoice(self.funny)
            await self.bot.say(fun_text)
            await asyncio.sleep(2)
        await self.bot.say("Congratulations {}. You won the lottery!".format(mention))
        if settings["Prize Amount"] > 0:
            prize = settings["Prize Amount"]
            await self.deposit_prize(winner, prize, server)
            settings["Prize Amount"] = 0
            dataIO.save_json(self.file_path, self.system)

    async def deposit_prize(self, winner, prize, server):
        bank = self.bot.get_cog('Economy').bank
        member_object = server.get_member(winner)
        bank.deposit_credits(member_object, prize)
        await self.bot.say("{} credits have been deposited into your account.".format(prize))

    async def member_creation(self, user, serverid, prefix):
        if serverid not in self.system["Lottery Members"]:
            self.system["Lottery Members"][serverid] = {}
            dataIO.save_json(self.file_path, self.system)
        if user.id not in self.system["Lottery Members"][serverid]:
            self.system["Lottery Members"][serverid][user.id] = {"Name": user.name,
                                                                 "ID": user.id,
                                                                 "Lotteries Played": 0,
                                                                 "Lotteries Won": 0,
                                                                 "Powerballs Played": 0,
                                                                 "Powerballs Won": 0,
                                                                 "Powerball Tickets": [],
                                                                 "Powerball Count": 0,
                                                                 "Account Frozen": False}
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("Lottery Account created for {}. You may now particpate in on-going lotteries.\nCheck your stats with {}lottery stats".format(user.name, prefix))
        else:
            await self.bot.say("You are already member.")

    async def auto_freeze(self, ctx, settings):
        server = ctx.message.server
        while settings["Membership Freeze"]:
            role = settings["Signup Role"]
            print("Loop started for {}".format(server.name))
            if server.id in self.system["Lottery Members"]:
                users = list(self.system["Lottery Members"][server.id].keys())
                for user in users:
                    if self.role_check(ctx, role, user):
                        if self.system["Lottery Members"][server.id][user]["Account Frozen"]:
                            self.system["Lottery Members"][server.id][user]["Account Frozen"] = False
                        else:
                            pass
                    else:
                        if self.system["Lottery Members"][server.id][user]["Account Frozen"]:
                            pass
                        else:
                            self.system["Lottery Members"][server.id][user]["Account Frozen"] = True
            dataIO.save_json(self.file_path, self.system)
            await asyncio.sleep(5)


def check_folders():
    if not os.path.exists("data/JumperCogs"):   # Checks for parent directory for all Jumper cogs
        print("Creating JumperCogs default directory")
        os.makedirs("data/JumperCogs")

    if not os.path.exists("data/JumperCogs/lottery"):
        print("Creating JumperCogs lottery folder")
        os.makedirs("data/JumperCogs/lottery")


def check_files():
    default = {"Config": {},
               "Lottery Members": {},
               "Lottery Players": {},
               "Version": 2.001
               }

    f = "data/JumperCogs/lottery/system.json"

    if not dataIO.is_valid_json(f):
        print("Adding system.json to data/JumperCogs/lottery/")
        dataIO.save_json(f, default)
    else:
        current = dataIO.load_json(f)
        if current["Version"] != default["Version"]:
            print("Updating Lottery Cog from version {} to version {}".format(current["Version"], default["Version"]))
            current["Version"] = default["Version"]
            dataIO.save_json(f, current)


def setup(bot):
    check_folders()
    check_files()
    n = Lottery(bot)
    bot.add_cog(n)
