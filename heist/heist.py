#  Bankheist.py was created by Redjumpman for Redbot
#  This will create a system.JSON file and a data folder
#  This will modify values your bank.json from economy.py
import os
import asyncio
import random
import time
from operator import itemgetter
from discord.ext import commands
from .utils.dataIO import dataIO
from random import randint
from .utils import checks
from __main__ import send_cmd_help
try:   # Check if Tabulate is installed
    from tabulate import tabulate
    tabulateAvailable = True
except:
    tabulateAvailable = False


class Heist:
    """Bankheist system inspired by Deepbot, a Twitch bot. Integrates with Economy"""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/bankheist/system.json"
        self.system = dataIO.load_json(self.file_path)
        self.good = [["{} had the car gassed up and ready to go +25 points.", 25],
                     ["{} cut the power to the bank +50 points.", 50],
                     ["{} erased the video footage +50 points", 50],
                     ["{} hacked the security system and put it on a loop feed +75 points", 75],
                     ["{} stopped the teller from triggering the silent alarm +50 points", 50],
                     ["{} knocked out the local security +50 points", 50],
                     ["{} stopped a local from being a hero +50 points", 50],
                     ["{} got the police negotiator to deliver everyone pizza +25 points", 25],
                     ["{} brought masks of former presidents to hide our identity +25 points", 25],
                     ["{} found an escape route +25 points", 25],
                     ["{} brought extra ammunition for the crew +25 points", 25],
                     ["{} cut through that safe like butter +25 points", 25],
                     ["{} kept the hostages under control +25 points", 25],
                     ["{} counter sniped a sniper +100 points", 100],
                     ["{} distracted the guard +25 points", 25],
                     ["{} brought a Go-Bag for the team +25 points", 25],
                     ["{} found a secret stash in the deposit box room +50 points", 25],
                     ["{} found a box of jewelry on a civilian, +25 points", 25]]
        self.bad = ["A shoot out with local authorities began and {} was hit." + "\n" +
                    "```{} dropped out.```",
                    "The cops dusted for finger prints and arrested {}" + "\n" +
                    "```{} dropped out.```",
                    "{} thought they could double cross the crew and paid for it." + "\n" +
                    "```{} dropped out.```",
                    "{} blew a tire in the getaway car" + "\n" +
                    "```{} dropped out.```",
                    "{}'s gun jammed while trying to fight with local security and was shot" + "\n" +
                    "```{} dropped out.```",
                    "{} held off the police while the crew was making their getaway" + "\n" +
                    "```{} dropped out.```",
                    "A hostage situation went south, and {} was captured" + "\n" +
                    "```{} dropped out.```",
                    "{} showed up to the heist high as kite, and was subsequently apprehended." + "\n" +
                    "```{} dropped out.```",
                    "{}'s bag of money contained exploding blue ink and was later caught" + "\n" +
                    "```{} dropped out.```",
                    "{} was sniped by a swat sniper" + "\n" +
                    "```{} dropped out.```",
                    "The crew decided to shaft {}" + "\n" +
                    "```{} dropped out.```",
                    "{} was hit by friendly fire" + "\n" +
                    "```{} dropped out.```",
                    "Security system's redundancies caused {} to be caught" + "\n" +
                    "```{} dropped out.```",
                    "{} accidentally revealed their identity." + "\n" +
                    "```{} dropped out.```",
                    "The swat team released sleeping gas, {} is sleeping like a baby" + "\n" +
                    "```{} dropped out.```",
                    "'FLASH BANG OUT!', was the last thing {} heard" + "\n" +
                    "```{} dropped out.```",
                    "'GRENADE OUT!', {} is now sleeping with the fishes" + "\n" +
                    "```{} dropped out.```",
                    "{} tripped a laser wire and was caught" + "\n" +
                    "```{} dropped out.```",
                    "Before the crew could intervene a security guard tazed {} and is now incapacitated." + "\n" +
                    "```{} dropped out.```",
                    "Swat came through the vents, and neutralized {}." + "\n" +
                    "```{} dropped out.```"]

    @commands.group(pass_context=True, no_pm=True)
    async def heist(self, ctx):
        """General heist related commands"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @heist.command(name="play", pass_context=True)
    async def _play_heist(self, ctx, bet: int):
        """This begin's a heist"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if bet >= 50:
            if self.account_check(user):
                if self.enough_points(user.id, bet, server):
                    if await self.check_cooldowns(settings):  # time between heists
                        if self.heist_started(settings):  # Checks if a heist is currently happening
                            if self.heist_plan(settings):  # checks if a heist is being planned or not
                                settings["Config"]["Min Bet"] = bet
                                self.heist_ptoggle(settings)
                                self.heist_stoggle(settings)
                                self.crew_add(user.id, user.name, bet, settings)
                                self.subtract_bet(user.id, bet, server)
                                wait = settings["Config"]["Wait Time"]
                                wait_time = int(wait / 2)
                                half_time = int(wait_time / 2)
                                split_time = int(half_time / 2)
                                await self.bot.say("A heist as been started by " + user.name +
                                                   "\n" + str(wait) + " seconds until the heist begins")
                                await asyncio.sleep(wait_time)
                                await self.bot.say(str(wait_time) + " seconds until the heist begins")
                                await asyncio.sleep(half_time)
                                await self.bot.say(str(half_time) + " seconds until the heist begins")
                                await asyncio.sleep(split_time)
                                await self.bot.say("Hurry up! " + str(split_time) + " seconds until the heist begins")
                                await asyncio.sleep(split_time)
                                await self.bot.say("Lock and load. The heist is starting")
                                settings["Config"]["Bankheist Running"] = "Yes"
                                dataIO.save_json(self.file_path, self.system)
                                bank = self.check_banks(settings)
                                await self.bot.say("The crew has decided to hit " + bank)
                                j = self.game_outcomes(settings)
                                j_temp = j[:]
                                while j_temp is not None:
                                    result = random.choice(j_temp)
                                    j_temp.remove(result)
                                    await asyncio.sleep(10)
                                    await self.bot.say(result)
                                    if len(j_temp) == 0:
                                        settings["Config"]["Bankheist Running"] = "No"
                                        dataIO.save_json(self.file_path, self.system)
                                        await asyncio.sleep(2)
                                        await self.bot.say("The Heist is over.")
                                        await asyncio.sleep(2)
                                        if settings["Heist Winners"]:
                                            target = settings["Config"]["Bank Target"]
                                            amount = settings["Banks"][target]["Vault"] / settings["Config"]["Players"]
                                            winners_names = [subdict["Name"] for subdict in settings["Heist Winners"].values()]
                                            pullid = ', '.join(subdict["User ID"] for subdict in settings["Heist Winners"].values())
                                            winners_bets = [subdict["Bet"] for subdict in settings["Heist Winners"].values()]
                                            winners_bonuses = [subdict["Bonus"] for subdict in settings["Heist Winners"].values()]
                                            winners = pullid.split()
                                            vtotal = settings["Banks"][target]["Vault"]
                                            vault_remainder = vtotal - amount * len(winners)
                                            settings["Banks"][target]["Vault"] = int(round(vault_remainder))
                                            dataIO.save_json(self.file_path, self.system)
                                            multiplier = settings["Banks"][target]["Multiplier"]
                                            sm_raw = [int(round(x)) * multiplier for x in winners_bets]
                                            success_multiplier = [int(round(x)) for x in sm_raw]
                                            cs_raw = [amount] * int(round(settings["Config"]["Players"]))
                                            credits_stolen = [int(round(x)) for x in cs_raw]
                                            total_winnings = [int(round(x)) + int(round(y)) + int(round(z)) for x, y, z in zip(success_multiplier, credits_stolen, winners_bonuses)]
                                            self.add_total(winners, total_winnings, server)
                                            z = list(zip(winners_names, winners_bets, success_multiplier, credits_stolen, winners_bonuses, total_winnings))
                                            t = tabulate(z, headers=["Players", "Bets", "Bet Payout", "Credits Stolen", "Bonuses", "Total Haul"])
                                            await self.bot.say("The total haul was split " +
                                                               "among the winners: ")
                                            await self.bot.say("```Python" + "\n" + t + "```")
                                            settings["Config"]["Time Remaining"] = int(time.perf_counter())
                                            dataIO.save_json(self.file_path, self.system)
                                            self.heistclear(settings)
                                            self.winners_clear(settings)
                                            break
                                        else:
                                            await self.bot.say("No one made it out safe.")
                                            settings["Config"]["Time Remaining"] = int(time.perf_counter())
                                            dataIO.save_json(self.file_path, self.system)
                                            self.heistclear(settings)
                                            break
                                    else:
                                        continue
                            elif settings["Config"]["Bankheist Running"] == "No":
                                if bet >= settings["Config"]["Min Bet"]:
                                    if self.crew_check(user.id, settings):  # join a heist that was started
                                        self.crew_add(user.id, user.name, bet, settings)
                                        self.subtract_bet(user.id, bet, server)
                                        await self.bot.say(user.name + " has joined the crew")
                                    else:
                                        await self.bot.say("You are already in the crew")
                                else:
                                    minbet = settings["Config"]["Min Bet"]
                                    await self.bot.say("Your bet must be equal to a greater" +
                                                       " than the starting bet of " + str(minbet))
                            elif settings["Config"]["Bankheist Started"] == "Yes":
                                await self.bot.say("You can't join a heist in progress")
                            else:
                                await self.bot.say("If you are seeing this, I dun fucked up.")
                        else:
                            await self.bot.say("You can't join an ongoing heist")
                else:
                    await self.bot.say("You don't have enough points to cover the minimum bet.")
            else:
                await self.bot.say("You need a bank account to place bets")
        else:
            await self.bot.say("Starting bet must at least be 50 points.")

    @heist.command(name="reset", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _reset_heist(self, ctx):
        """Try using this only if shit is broken!"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        self.heistclear(settings)
        await self.bot.say("Bankheist has been reset.")

    @heist.command(name="banks", pass_context=True)
    async def _banks_heist(self, ctx):
        """Shows banks info"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        column1 = [subdict["Name"] for subdict in settings["Banks"].values()]
        column2 = [subdict["Crew"] for subdict in settings["Banks"].values()]
        column3 = [subdict["Multiplier"] for subdict in settings["Banks"].values()]
        column4 = [subdict["Vault"] for subdict in settings["Banks"].values()]
        column5 = [subdict["Success"] for subdict in settings["Banks"].values()]
        sr = [str(x) + "%" for x in column5]
        m = list(zip(column1, column2, column3, column4, sr))
        m = sorted(m, key=itemgetter(1), reverse=True)
        t = tabulate(m, headers=["Bank", "Crew", "Bet Multiplier", "Vault", "Success Rate"])
        await self.bot.say("```Python" + "\n" + t + "```")

    @heist.command(name="info", pass_context=True)
    async def _info_heist(self, ctx):
        """Displays information about the game"""
        msg = "```\n"
        msg += "To begin a heist type !heist play. " + "\n"
        msg += "The initial bet will set the minimum bet required for other crew members." + "\n"
        msg += "A planning period will allow you to gather more crew." + "\n"
        msg += "Other players can join by typing !heist play" + "\n"
        msg += "Once the heist begins you can no longer add crew members." + "\n"
        msg += "The game will run through scenarios, resulting in some sucesses and failures for the crew." + "\n"
        msg += "Those who are successful will take a portion of the vaults credits, and their bet times a multiplier" + "\n"
        msg += "Bigger banks have bigger vaults, and higher bet multipliers, but you will need a larger crew." + "\n"
        msg += "Banks will gradually refill their vaults over time." + "\n"
        msg += "To check out the banks, type !heist banks" + "\n"
        msg += "To change heist settings, type !setheist (admins only)" + "```"
        await self.bot.say(msg)

    @commands.group(pass_context=True, no_pm=True)
    async def setheist(self, ctx):
        """Set different options in the heist config"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @setheist.command(name="bankname", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _bankname_setheist(self, ctx, level: int, *, name: str):
        """Sets the name of the bank for each level (1-5).
        """
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if level > 0 and level <= 5:
            banklvl = "Lvl " + str(level) + " Bank"
            settings["Banks"][banklvl]["Name"] = name
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("Changed {}'s name to {}".format(banklvl, name))
        else:
            await self.bot.say("You need to pick a level from 1 to 5")

    @setheist.command(name="vaultmax", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _vaultmax_setheist(self, ctx, banklvl: int, maximum: int):
        """Sets the maximum credit amount a vault can hold.
        """
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if banklvl > 0 and banklvl <= 5:
            if maximum > 0:
                banklvl = "Lvl " + str(banklvl) + " Bank"
                settings["Banks"][banklvl]["Max"] = maximum
                dataIO.save_json(self.file_path, self.system)
                await self.bot.say("Changed {}'s vault max to {}".format(banklvl, maximum))
            else:
                await self.bot.say("Need to set a maximum higher than 0.")
        else:
            await self.bot.say("You need to pick a level from 1 to 5.")

    @setheist.command(name="multiplier", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _multiplier_setheist(self, ctx, multiplier: float, banklvl: int):
        """Set the payout multiplier for a bank
        """
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if multiplier > 0:
            if banklvl > 0 and banklvl <= 5:
                banklvl = "Lvl " + str(banklvl) + " Bank"
                settings["Banks"][banklvl]["Multiplier"] = multiplier
                dataIO.save_json(self.file_path, self.system)
                await self.bot.say("```" + banklvl + "'s multiplier is now set to " +
                                   str(multiplier) + "```")
            else:
                await self.bot.say("This bank name does not exist")
        else:
            await self.bot.say("You need to specify a multiplier")

    @setheist.command(name="time", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _time_setheist(self, ctx, seconds: int):
        """Set the wait time for a heist to start
        """
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if seconds > 0:
            settings["Config"]["Wait Time"] = seconds
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("I have now set the wait time to " + str(seconds) + " seconds.")
        else:
            await self.bot.say("Time must be greater than 0.")

    @setheist.command(name="cooldown", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _cooldown_setheist(self, ctx):
        """Toggles cooldowns on/off and sets the time"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if settings["Config"]["Cooldown"]:
            settings["Config"]["Cooldown"] = False
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("Heist cooldowns are now OFF.")
        else:
            settings["Config"]["Cooldown"] = True
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("heist cooldowns are now ON.")

    @setheist.command(name="cdtime", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _cdtime_setheist(self, ctx, timer: int):
        """Set's the cooldown timer in seconds. 3600"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if timer > 0:
            settings["Config"]["Default CD"] = timer
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("Setting the cooldown timer to {}".format(self.time_format(timer)))
        else:
            await self.bot.say("Needs to be higher than 0. If you don't want a cooldown turn it off.")

    @setheist.command(name="success", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _success_setheist(self, ctx, rate: int, banklvl: int):
        """Set the success rate for a bank. 1-100 %
        """
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if banklvl > 0 and banklvl <= 5:
            banklvl = "Lvl " + str(banklvl) + " Bank"
            if rate > 0 and rate <= 100:
                settings["Banks"][banklvl]["Success"] = rate
                dataIO.save_json(self.file_path, self.system)
                await self.bot.say("I have now set the success rate for " + banklvl + " to " + str(rate) + ".")
            else:
                await self.bot.say("Success rate must be greater than 0 or less than or equal to 100.")

    @setheist.command(name="crew", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _crew_setheist(self, ctx, crew: int, banklvl: int):
        """Sets the crew size needed for each bank level
        """
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if banklvl > 0 and banklvl <= 5:
            if banklvl < 2:
                nlvl = "Lvl " + str(banklvl + 1) + " Bank"
                lvl = "Lvl " + str(banklvl) + " Bank"
                if crew < settings["Banks"][nlvl]["Crew"]:
                    settings["Banks"][lvl]["Crew"] = crew
                    dataIO.save_json(self.file_path, self.system)
                    await self.bot.say("```Python\nSetting Level 1 Bank to crew size {}.```".format(str(crew)))
                else:
                    await self.bot.say("Level 1 bank's crewsize should be lower than the Level 2 Bank.")
            elif banklvl > 1 and banklvl < 5:
                nlvl = "Lvl " + str(banklvl + 1) + " Bank"
                lvl = "Lvl " + str(banklvl) + " Bank"
                plvl = "Lvl " + str(banklvl - 1) + " Bank"
                if crew < settings["Banks"][nlvl]["Crew"] and crew > settings["Banks"][plvl]["Crew"]:
                    settings["Banks"][lvl]["Crew"] = crew
                    dataIO.save_json(self.file_path, self.system)
                    await self.bot.say("```Python\nSetting {} to crew size {}.```".format(lvl, str(crew)))
                else:
                    await self.bot.say("The crew size for {} must be higher than {}, but lower than {}".format(lvl, plvl, nlvl))
            else:
                lvlfive = "Lvl " + str(banklvl) + " Bank"
                lvlfour = "Lvl " + str(banklvl - 1) + " Bank"
                if crew > settings["Banks"][lvlfour]["Crew"]:
                    settings["Banks"][lvlfive]["Crew"] = crew
                    dataIO.save_json(self.file_path, self.system)
                    await self.bot.say("```Python\nSetting Level 5 Bank to crew size {}.```".format(str(crew)))
                else:
                    await self.bot.say("The crewsize for the Lvl 5 bank must be higher than the lvl 4 bank.")
        else:
            await self.bot.say("You need to pick a level from 1 to 5")

    @setheist.command(name="vault", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _vault_setheist(self, ctx, amount: int, banklvl: int):
        """Set the amount of credits in a bank's vault.
        """
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if amount > 0:
            if banklvl > 0 and banklvl <= 5:
                banklvl = "Lvl " + str(banklvl) + " Bank"
                settings["Banks"][banklvl]["Vault"] = amount
                dataIO.save_json(self.file_path, self.system)
                await self.bot.say("I have set " + banklvl + "'s vault to " + str(amount) + " credits.")
            else:
                await self.bot.say("That bank level does not exist. Use levels 1 through 5")
        else:
            await self.bot.say("You need to enter an amount higher than 0.")

    async def vault_update(self):
        while self == self.bot.get_cog("Heist"):
            server_objs = list(self.bot.servers)
            server_ids = [x.id for x in server_objs]
            for serverid in server_ids:
                if serverid in self.system["Servers"]:
                    if self.system["Servers"][serverid]["Banks"]["Lvl 1 Bank"]["Vault"] < self.system["Servers"][serverid]["Banks"]["Lvl 1 Bank"]["Max"]:
                        self.system["Servers"][serverid]["Banks"]["Lvl 1 Bank"]["Vault"] += 22
                    if self.system["Servers"][serverid]["Banks"]["Lvl 2 Bank"]["Vault"] < self.system["Servers"][serverid]["Banks"]["Lvl 2 Bank"]["Max"]:
                        self.system["Servers"][serverid]["Banks"]["Lvl 2 Bank"]["Vault"] += 31
                    if self.system["Servers"][serverid]["Banks"]["Lvl 3 Bank"]["Vault"] < self.system["Servers"][serverid]["Banks"]["Lvl 3 Bank"]["Max"]:
                        self.system["Servers"][serverid]["Banks"]["Lvl 3 Bank"]["Vault"] += 48
                    if self.system["Servers"][serverid]["Banks"]["Lvl 4 Bank"]["Vault"] < self.system["Servers"][serverid]["Banks"]["Lvl 4 Bank"]["Max"]:
                        self.system["Servers"][serverid]["Banks"]["Lvl 4 Bank"]["Vault"] += 53
                    if self.system["Servers"][serverid]["Banks"]["Lvl 5 Bank"]["Vault"] < self.system["Servers"][serverid]["Banks"]["Lvl 5 Bank"]["Max"]:
                        self.system["Servers"][serverid]["Banks"]["Lvl 5 Bank"]["Vault"] += 60
                    dataIO.save_json(self.file_path, self.system)
                else:
                    pass
            await asyncio.sleep(120)  # task runs every 120 seconds

    def account_check(self, uid):
        bank = self.bot.get_cog('Economy').bank
        if bank.account_exists(uid):
            return True
        else:
            return False

    async def check_cooldowns(self, settings):
        if settings["Config"]["Cooldown"] is False:
            return True
        elif abs(settings["Config"]["Time Remaining"] - int(time.perf_counter())) >= settings["Config"]["Default CD"]:
            return True
        elif settings["Config"]["Time Remaining"] == 0:
            return True
        else:
            s = abs(settings["Config"]["Time Remaining"] - int(time.perf_counter()))
            seconds = abs(s - settings["Config"]["Default CD"])
            await self.bot.say("The police are on high alert after the last job. Let's let things cool off before another heist.")
            await self.time_formatting(seconds)
            return False

    def time_format(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            msg = "{} hours, {} minutes, {} seconds".format(h, m, s)
        elif h == 0 and m > 0:
            msg = "{} minutes, {} seconds".format(m, s)
        elif m == 0 and h == 0 and s > 0:
            msg = "{} seconds".format(s)
        elif m == 0 and h == 0 and s == 0:
            msg = "No cooldown"
        return msg

    async def time_formatting(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            await self.bot.say("```{} hours, {} minutes and {} seconds remaining```".format(h, m, s))
        elif h == 0 and m > 0:
            await self.bot.say("{} minutes, {} seconds remaining".format(m, s))
        elif m == 0 and h == 0 and s > 0:
            await self.bot.say("{} seconds remaining".format(s))

    def heistclear(self, settings):
        self.winners_clear(settings)
        del settings["Players"]
        del settings["Heist Winners"]
        settings["Players"] = {}
        settings["Config"]["Bankheist Running"] = "No"
        settings["Config"]["Planning Heist"] = "No"
        settings["Config"]["Bankheist Started"] = "No"
        settings["Heist Winners"] = {}
        settings["Config"]["Min Bet"] = 0
        settings["Config"]["Players"] = 0
        settings["Config"]["Bank Target"] = ""
        dataIO.save_json(self.file_path, self.system)

    def enough_points(self, uid, amount, server):
        bank = self.bot.get_cog('Economy').bank
        mobj = server.get_member(uid)
        if self.account_check(mobj):
            if bank.can_spend(mobj, amount):
                return True
            else:
                return False
        else:
            return False

    def check_banks(self, settings):
        if settings["Config"]["Players"] <= settings["Banks"]["Lvl 1 Bank"]["Crew"]:
            settings["Config"]["Bank Target"] = "Lvl 1 Bank"
            dataIO.save_json(self.file_path, self.system)
            return settings["Banks"]["Lvl 1 Bank"]["Name"]
        elif settings["Config"]["Players"] <= settings["Banks"]["Lvl 2 Bank"]["Crew"]:
            settings["Config"]["Bank Target"] = "Lvl 2 Bank"
            dataIO.save_json(self.file_path, self.system)
            return settings["Banks"]["Lvl 2 Bank"]["Name"]
        elif settings["Config"]["Players"] <= settings["Banks"]["Lvl 3 Bank"]["Crew"]:
            settings["Config"]["Bank Target"] = "Lvl 3 Bank"
            dataIO.save_json(self.file_path, self.system)
            return settings["Banks"]["Lvl 3 Bank"]["Name"]
        elif settings["Config"]["Players"] <= settings["Banks"]["Lvl 4 Bank"]["Crew"]:
            settings["Config"]["Bank Target"] = "Lvl 4 Bank"
            dataIO.save_json(self.file_path, self.system)
            return settings["Banks"]["Lvl 4 Bank"]["Name"]
        elif settings["Config"]["Players"] > settings["Banks"]["Lvl 5 Bank"]["Crew"]:
            settings["Config"]["Bank Target"] = "Lvl 5 Bank"
            dataIO.save_json(self.file_path, self.system)
            return settings["Banks"]["Lvl 5 Bank"]["Name"]

    def game_outcomes(self, settings):
        players = []
        for subdict in settings["Players"].values():
            players.append(subdict)
        temp_good_things = self.good[:]  # coping the lists
        temp_bad_things = self.bad[:]
        chance = self.heist_chance(settings)
        results = []
        for player in players:
            if randint(0, 100) <= chance:
                key = player["Name"]
                good_thing = random.choice(temp_good_things)
                temp_good_things.remove(good_thing)
                results.append(good_thing[0].format(key))
                settings["Heist Winners"][key] = {"Name": key,
                                                  "User ID": player["User ID"],
                                                  "Bet": player["Bet"],
                                                  "Bonus": good_thing[1]}
                dataIO.save_json(self.file_path, self.system)
            else:
                key = player["Name"]
                bad_thing = random.choice(temp_bad_things)
                temp_bad_things.remove(bad_thing)
                results.append(bad_thing.format(key, key))
        return results

    def heist_chance(self, settings):
        if settings["Config"]["Bank Target"] == "Lvl 1 Bank":
            return settings["Banks"]["Lvl 1 Bank"]["Success"]
        elif settings["Config"]["Bank Target"] == "Lvl 2 Bank":
            return settings["Banks"]["Lvl 2 Bank"]["Success"]
        elif settings["Config"]["Bank Target"] == "Lvl 3 Bank":
            return settings["Banks"]["Lvl 3 Bank"]["Success"]
        elif settings["Config"]["Bank Target"] == "Lvl 4 Bank":
            return settings["Banks"]["Lvl 4 Bank"]["Success"]
        elif settings["Config"]["Bank Target"] == "Lvl 5 Bank":
            return settings["Banks"]["Lvl 5 Bank"]["Success"]

    def winners_clear(self, settings):
        del settings["Heist Winners"]
        settings["Heist Winners"] = {}
        dataIO.save_json(self.file_path, self.system)

    def crew_add(self, uid, name, bet, settings):
        settings["Players"][uid] = {"Name": name,
                                    "Bet": int(bet),
                                    "User ID": uid}
        settings["Config"]["Players"] = settings["Config"]["Players"] + 1
        dataIO.save_json(self.file_path, self.system)

    def crew_check(self, uid, settings):
        if uid not in settings["Players"]:
            return True
        else:
            return False

    def add_total(self, winners, totals, server):
        bank = self.bot.get_cog('Economy').bank
        i = -1
        for winner in winners:
            i = i + 1
            userid = winner.replace(',', '')
            mobj = server.get_member(userid)
            bank.deposit_credits(mobj, totals[i])

    def subtract_bet(self, userid, bet, server):
        bank = self.bot.get_cog('Economy').bank
        mobj = server.get_member(userid)
        if self.account_check(mobj):
            bank.withdraw_credits(mobj, bet)

    def check_server_settings(self, server):
        if server.id not in self.system["Servers"]:
            self.system["Servers"][server.id] = {"Players": {},
                                                 "Config": {"Bankheist Started": "No", "Planning Heist": "No",
                                                            "Cooldown": False, "Time Remaining": 0, "Default CD": 0,
                                                            "Bankheist Running": "No", "Players": 0,
                                                            "Min Bet": 0, "Wait Time": 120, "Bank Target": ""},
                                                 "Heist Winners": {},
                                                 "Banks": {"Lvl 1 Bank": {"Name": "The Local Bank", "Crew": 3, "Multiplier": 0.25, "Success": 46, "Vault": 2000, "Max": 2000},
                                                           "Lvl 2 Bank": {"Name": "First National Bank", "Crew": 5, "Multiplier": 0.31, "Success": 40, "Vault": 5000, "Max": 5000},
                                                           "Lvl 3 Bank": {"Name": "PNC Bank", "Crew": 8, "Multiplier": 0.35, "Success": 37, "Vault": 8000, "Max": 8000},
                                                           "Lvl 4 Bank": {"Name": "Bank of America", "Crew": 10, "Multiplier": 0.42, "Success": 32, "Vault": 12000, "Max": 12000},
                                                           "Lvl 5 Bank": {"Name": "Fort Knox", "Crew": 15, "Multiplier": 0.5, "Success": 28, "Vault": 20000, "Max": 20000},
                                                           },
                                                 }
            dataIO.save_json(self.file_path, self.system)
            print("Creating default heist settings for Server: {}".format(server.name))
            path = self.system["Servers"][server.id]
            return path
        else:
            path = self.system["Servers"][server.id]
            return path

    def player_counter(self, number, settings):
        settings["Players"] = self.system["Players"] + number
        dataIO.save_json(self.file_path, self.system)

    def heist_plan(self, settings):
        if settings["Config"]["Planning Heist"] == "No":
            return True
        else:
            return False

    def heist_started(self, settings):
        if settings["Config"]["Bankheist Started"] == "No":
            return True
        else:
            return False

    def heist_stoggle(self, settings):
        if settings["Config"]["Bankheist Started"] == "Yes":
            settings["Config"]["Bankheist Started"] = "No"
            dataIO.save_json(self.file_path, self.system)
        elif settings["Config"]["Bankheist Started"] == "No":
            settings["Config"]["Bankheist Started"] = "Yes"
            dataIO.save_json(self.file_path, self.system)

    def heist_ptoggle(self, settings):
        if settings["Config"]["Planning Heist"] == "No":
            settings["Config"]["Planning Heist"] = "Yes"
            dataIO.save_json(self.file_path, self.system)
        elif settings["Config"]["Planning Heist"] == "Yes":
            settings["Config"]["Planning Heist"] = "No"
            dataIO.save_json(self.file_path, self.system)


def check_folders():
    if not os.path.exists("data/bankheist"):
        print("Creating data/bankheist folder...")
        os.makedirs("data/bankheist")


def check_files():
    default = {"Servers": {}
               }

    f = "data/bankheist/system.json"
    if not dataIO.is_valid_json(f):
        print("Creating default bankheist system.json...")
        dataIO.save_json(f, default)


def setup(bot):
    check_folders()
    check_files()
    n = Heist(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.vault_update())
