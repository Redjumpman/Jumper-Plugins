#  Roulette.py was created by Redjumpman for Redbot
#  This will create a rrgame.JSON file and a data folder
import os
import random
import asyncio
from time import gmtime, strftime
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help


kill_message = ["I was really pulling for {0} too. Oh well!",
                "I guess {0} really wasn't a pea-brain!",
                "Ahhh now that {0} is gone we can quit playing! No? Ok fine!",
                ("All things considered, I think we can all agree that {0} was a "
                 "straight shooter."),
                "Noooooooo. Not {0}!", "I call dibs on {0}\'s stuff. Too soon?",
                "Well I guess {0} and I won't be doing that thing anymore...",
                "Here lies {0}. A loser.", "RIP {0}.", "I kinda hated {0} anyway.",
                "Hey {0}! I'm back with your snacks! Oh...",
                "{0}, you\'re like modern art now!", "Called it!",
                "Really guys? {0}\'s dead? Well this server officially blows now.",
                "Does this mean I don't have to return the book {0} lent me?",
                "Oh come on! Now {0}\'s blood is all over my server!",
                "I\'ll always remember {0}...", "Well at least {0} stopped crying.",
                "Don\'t look at me. You guys are cleaning up {0}.",
                "What I'm not crying. *sniff*", "I TOLD YOU, YOU COULD DO IT!",
                "Well I'm sure someone will miss you, {0}.", "Never forget. {0}."
                "Yeah. Real smart guys. Just kill off all the fun people.",
                "I think I got some splatter on me. Gross",
                "I told you it would blow your mind!", "Well this is fun...",
                "I go to get popcorn and you all start without me. Rude.",
                "Oh God. Just before {0} pulled the trigger they shit their pants.",
                "I guess I\'ll dig this hole a little bigger...",
                "10/10 would watch {0} blow their brains out again.",
                "Well I hope {0} has life insurance...",
                "See you in the next life, {0}", "AND THEIR OFF! Oh... wrong game."
                "I don\'t know how, but I think {1} cheated.",
                "{0} always said they wanted to go out with a bang.",
                "So don\'t sing *another one bites the dust* ?",
                "I can\'t tell if the smile on {1}\'s face is relief or insanity.",
                "Oh stop crying {1}. {0} knew what they were getting into.",
                "So that\'s what a human looks like on the inside!",
                "My condolences {1}. I know you were *so* close to {0}.",
                "GOD NO. PLEASE NO. PLEASE GOD NO. NOOOOOOOOOOOOOOOOOOOOOOO!",
                "Time of death {2}. Cause: Stupidity.", "BOOM HEADSHOT! Sorry..."
                "Don\'t act like you didn\'t enjoy that, {1}!",
                "Is it weird that I wish {1} was dead instead?",
                "Oh real great. {0} dies and I\'m still stuck with {1}. Real. Great.",
                "Are you eating cheetos? Have some respect {1}! {0} just died!"]


class Russianroulette:
    """Allows 6 players to play Russian Roulette"""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/JumperCogs/roulette/russian.json"
        self.system = dataIO.load_json(self.file_path)
        self.version = "2.2.02"

    @commands.group(pass_context=True, no_pm=True)
    async def setrussian(self, ctx):
        """Russian Roulette Settings"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @commands.command(name="rrversion", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _version_setrussian(self):
        """Shows the version of Russian Roulette"""
        await self.bot.say("You are currently running Russian Roulette version "
                           "{}".format(self.version))

    @setrussian.command(name="minbet", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _minbet_setrussian(self, ctx, bet: int):
        """Set the minimum starting bet for Russian Roulette games"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if bet > 0:
            settings["System"]["Min Bet"] = bet
            dataIO.save_json(self.file_path, self.system)
            msg = "The initial bet to play russian roulette is set to {}".format(bet)
        else:
            msg = "I need a number higher than 0."
        await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def resetrr(self, ctx):
        """Reset command if game is stuck."""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        self.reset_game(settings)
        await self.bot.say("Russian Roulette system has been reset.")

    @commands.command(pass_context=True, no_pm=True, aliases=["rr"])
    async def russian(self, ctx, bet: int):
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        bank = self.bot.get_cog("Economy").bank
        if await self.logic_checks(settings, user, bet):
            if settings["System"]["Roulette Initial"]:
                if user.id in settings["Players"]:
                    msg = "You are already in the circle. Don\'t be so eager to die."
                elif len(settings["Players"].keys()) >= 6:
                    msg = "Sorry. The max amount of players is 6."
                else:
                    if bet == settings["System"]["Start Bet"]:
                        self.player_add(settings, user, bet)
                        self.subtract_credits(settings, user, bet)
                        msg = "{} has joined the roulette circle".format(user.name)
                    else:
                        start_bet = settings["System"]["Start Bet"]
                        msg = "Your bet must be  equal to {}.".format(start_bet)
                await self.bot.say(msg)
            else:
                self.initial_set(settings, bet)
                self.player_add(settings, user, bet)
                self.subtract_credits(settings, user, bet)
                await self.bot.say("{} has started a game of roulette with a starting bet of "
                                   "{}\nThe game will start in 30 seconds or when 5 more "
                                   "players join.".format(user.name, bet))
                await asyncio.sleep(30)
                if len(settings["Players"].keys()) == 1:
                    await self.bot.say("Sorry I can't let you play by yourself, that's just "
                                       "suicide.\nTry again when you find some 'friends'.")
                    player = list(settings["Players"].keys())[0]
                    mobj = server.get_member(player)
                    initial_bet = settings["Players"][player]["Bet"]
                    bank.deposit_credits(mobj, initial_bet)
                    self.reset_game(settings)
                else:
                    settings["System"]["Active"] = True
                    await self.bot.say("Gather around! The game of russian roulette is starting.\n"
                                       "I'm going to load a round into this six shot **revolver**, "
                                       "give it a good spin, and pass it off to someone at random. "
                                       "**If** everyone is lucky enough to have a turn, I\'ll "
                                       "start all over. Good luck!")
                    await asyncio.sleep(5)
                    await self.roulette_game(settings, server)
                    self.reset_game(settings)

    async def logic_checks(self, settings, user, bet):
        if settings["System"]["Active"]:
            await self.bot.say("A game of roulette is already active. Wait for it to end.")
            return False
        elif bet < settings["System"]["Min Bet"]:
            min_bet = settings["System"]["Min Bet"]
            await self.bot.say("Your bet must be greater than or equal to {}.".format(min_bet))
            return False
        elif len(settings["Players"].keys()) >= 6:
            await self.bot.say("There are too many players playing at the moment")
            return False
        elif not self.enough_credits(user, bet):
            await self.bot.say("You do not have enough credits or may need to register a bank "
                               "account")
            return False
        else:
            return True

    async def roulette_game(self, settings, server):
        pot = settings["System"]["Pot"]
        turn = 0
        count = len(settings["Players"].keys())
        while count > 0:
            players = [server.get_member(x) for x in list(settings["Players"].keys())]
            if count > 1:
                count -= 1
                turn += 1
                await self.roulette_round(settings, server, players, turn)
            else:
                winner = players[0]
                await self.bot.say("Congratulations {}, you're the only person alive. Enjoy your "
                                   "blood money...\n{} credits were deposited into {}\'s "
                                   "account".format(winner.mention, pot, winner.name))
                bank = self.bot.get_cog("Economy").bank
                bank.deposit_credits(winner, pot)
                break

    async def roulette_round(self, settings, server, players, turn):
        roulette_circle = players[:]
        chamber = 6
        await self.bot.say("*{} put one round into the six shot revolver and gave it a good spin. "
                           "With a flick of the wrist, it locks in place."
                           "*".format(self.bot.user.name))
        await asyncio.sleep(4)
        await self.bot.say("Let's begin round {}.".format(turn))
        while chamber >= 1:
            if not roulette_circle:
                roulette_circle = players[:]  # Restart the circle when list is exhausted
            chance = random.randint(1, chamber)
            player = random.choice(roulette_circle)
            await self.bot.say("{} presses the revolver to their temple and slowly squeezes the "
                               "trigger...".format(player.name))
            if chance == 1:
                await asyncio.sleep(4)
                msg = "**BOOM**\n```{} died and was removed from the group.```".format(player.name)
                await self.bot.say(msg)
                msg2 = random.choice(kill_message)
                settings["Players"].pop(player.id)
                remaining = [server.get_member(x) for x in list(settings["Players"].keys())]
                player2 = random.choice(remaining)
                death_time = strftime("%H:%M:%S", gmtime())
                await asyncio.sleep(5)
                await self.bot.say(msg2.format(player.name, player2.name, death_time))
                await asyncio.sleep(5)
                break
            else:
                await asyncio.sleep(4)
                await self.bot.say("**CLICK**\n```{} survived and passed the "
                                   "revolver.```".format(player.name))
                await asyncio.sleep(3)
                roulette_circle.remove(player)
                chamber -= 1

    def reset_game(self, settings):
        settings["System"]["Pot"] = 0
        settings["System"]["Active"] = False
        settings["System"]["Start Bet"] = 0
        settings["System"]["Roulette Initial"] = False
        settings["Players"] = {}

    def player_add(self, settings, user, bet):
        settings["System"]["Pot"] += bet
        settings["Players"][user.id] = {"Name": user.name,
                                        "Mention": user.mention,
                                        "Bet": bet}

    def initial_set(self, settings, bet):
        settings["System"]["Start Bet"] = bet
        settings["System"]["Roulette Initial"] = True

    def subtract_credits(self, settings, user, bet):
        bank = self.bot.get_cog('Economy').bank
        bank.withdraw_credits(user, bet)

    def enough_credits(self, user, amount):
        bank = self.bot.get_cog('Economy').bank
        if bank.account_exists(user):
            if bank.can_spend(user, amount):
                return True
            else:
                return False
        else:
            return False

    def check_server_settings(self, server):
        if server.id not in self.system["Servers"]:
            default = {"System": {"Pot": 0,
                                  "Active": False,
                                  "Start Bet": 0,
                                  "Roulette Initial": False,
                                  "Min Bet": 50},
                       "Players": {}
                       }
            self.system["Servers"][server.id] = default
            dataIO.save_json(self.file_path, self.system)
            print("Creating default russian roulette settings for Server: {}".format(server.name))
            path = self.system["Servers"][server.id]
            return path
        else:
            path = self.system["Servers"][server.id]
            return path


def check_folders():
    if not os.path.exists("data/JumperCogs/roulette"):
        print("Creating data/JumperCogs/roulette folder...")
        os.makedirs("data/JumperCogs/roulette")


def check_files():
    system = {"Servers": {}}

    f = "data/JumperCogs/roulette/russian.json"
    if not dataIO.is_valid_json(f):
        print("Creating default russian.json...")
        dataIO.save_json(f, system)


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Russianroulette(bot))
