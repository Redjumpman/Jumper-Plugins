# Developed by Redjumpman for Redbot.

# Standard Library
import asyncio
import calendar
import logging
import random
import re
from functools import wraps
from operator import itemgetter
from collections import namedtuple

# Casino
from . import utils
from .deck import Deck
from .checks import Checks

# Red
from redbot.core.i18n import Translator
from redbot.core import Config, bank, commands, checks

# Discord
import discord

# Third-Party Libraries
from tabulate import tabulate

__version__ = "2.3.01"
__author__ = "Redjumpman"

log = logging.getLogger("red.casino")
_ = Translator("Casino", __file__)

deck = Deck()

# Thanks Toby
_DataNamedTuple = namedtuple("Casino", "foo")
_DataObj = _DataNamedTuple(foo=None)


def game_engine(name=None, choice=None, choices=None):
    def wrapper(coro):
        @wraps(coro)
        async def wrapped(*args, **kwargs):
            engine = Engine(name, choice, choices, args[1], args[2])
            if await engine.check_conditions():
                result = await coro(*args, **kwargs)
                await engine.game_teardown(result)

        return wrapped

    return wrapper


class Data:
    user_defaults = {
        "Membership": {
            "Name": "Basic",
            "Assigned": False},
        "Pending_Credits": 0,
        "Played": {
            "Allin": 0,
            "Blackjack": 0,
            "Coin": 0,
            "Craps": 0,
            "Cups": 0,
            "Dice": 0,
            "Hilo": 0,
            "War": 0,
            "Double": 0},
        "Won": {
            "Allin": 0,
            "Blackjack": 0,
            "Coin": 0,
            "Craps": 0,
            "Cups": 0,
            "Dice": 0,
            "Hilo": 0,
            "War": 0,
            "Double": 0},
        "Cooldowns": {
            "Allin": 0,
            "Blackjack": 0,
            "Coin": 0,
            "Craps": 0,
            "Cups": 0,
            "Dice": 0,
            "Hilo": 0,
            "War": 0,
            "Double": 0}
    }
    member_defaults = user_defaults

    casino_defaults = {
        "Settings": {
            "Casino_Name": "Redjumpman's",
            "Casino_Open": True,
            "Payout_Switch": False,
            "Payout_Limit": 10000
        },
        "Memberships": {},
        "Games": {
            "Allin": {
                "Access": 0,
                "Cooldown": 43200,
                "Min": None,
                "Max": None,
                "Multiplier": None,
                "Open": True

            },
            "Blackjack": {
                "Access": 0,
                "Cooldown": 5,
                "Min": 50,
                "Max": 500,
                "Multiplier": 2.0,
                "Open": True,
            },
            "Coin": {
                "Access": 0,
                "Cooldown": 5,
                "Max": 10,
                "Min": 10,
                "Multiplier": 1.5,
                "Open": True
            },
            "Craps": {
                "Access": 0,
                "Cooldown": 5,
                "Max": 500,
                "Min": 50,
                "Multiplier": 2.0,
                "Open": True
            },
            "Cups": {
                "Access": 0,
                "Cooldown": 5,
                "Max": 100,
                "Min": 25,
                "Multiplier": 1.8,
                "Open": True
            },
            "Dice": {
                "Access": 0,
                "Cooldown": 5,
                "Max": 100,
                "Min": 25,
                "Multiplier": 1.8,
                "Open": True
            },
            "Hilo": {
                "Access": 0,
                "Cooldown": 5,
                "Min": 25,
                "Max": 75,
                "Multiplier": 1.7,
                "Open": True
            },
            "War": {
                "Access": 0,
                "Cooldown": 5,
                "Min": 25,
                "Max": 75,
                "Multiplier": 1.5,
                "Open": True
            },
            "Double": {
                "Access": 0,
                "Cooldown": 5,
                "Min": 10,
                "Max": 250,
                "Multiplier": None,
                "Open": True
            }
        }
    }
    global_defaults = casino_defaults
    global_defaults['Settings']["Global"] = False

    db = Config.get_conf(_DataObj, 5074395001, force_registration=True)

    def __init__(self):
        self.db.register_guild(**self.casino_defaults)
        self.db.register_global(**self.global_defaults)
        self.db.register_member(**self.member_defaults)
        self.db.register_user(**self.user_defaults)

    # -----------------RESETS-----------------------------

    async def reset_server_cooldowns(self, ctx):
        author = ctx.author
        if await self.casino_is_global():
            for player in await self.db.all_users():
                user = ctx.bot.get_user(player)
                await self.db.user(user).Cooldowns.clear()
            msg = _("{0.name} ({0.id}) reset all global cooldowns.").format(author)
        else:
            guild = ctx.guild
            for player in await self.db.all_members(guild):
                user = guild.get_member(player)
                await self.db.member(user).Cooldowns.clear()
            msg = _("{0.name} ({0.id}) reset all cooldowns on {1.name}.").format(author, guild)

        log.info(msg)
        await ctx.send(msg)

    async def reset_server_settings(self, ctx):
        author = ctx.author
        instance = await self.get_instance(ctx, settings=True)
        await instance.Settings.clear()
        msg = _("{0.name} ({0.id}) reset all settings.").format(author)
        log.info(msg)
        await ctx.send(msg)

    async def reset_server_memberships(self, ctx):
        author = ctx.author
        instance = await self.get_instance(ctx, settings=True)
        await instance.Memberships.clear()
        msg = _("{0.name} ({0.id}) cleared all memberships.").format(author)
        log.info(msg)
        await ctx.send(msg)

    async def reset_server_games(self, ctx):
        author = ctx.author
        if await self.casino_is_global():
            await self.db.Games.clear()
            msg = _("{0.name} ({0.id}) restored global game defaults.").format(author)
        else:
            guild = ctx.guild
            await self.db.guild(guild).Games.clear()
            msg = _("{0.name} ({0.id}) restored {1}'s game defaults.").format(author, guild.name)

        log.info(msg)
        await ctx.send(msg)

    async def reset_server_all(self, ctx):
        author = ctx.author
        if await self.casino_is_global():
            await self.db.clear_all_globals()
            msg = _("{0.name} ({0.id}) reset global data.").format(author)
        else:
            guild = ctx.guild
            await self.db.guild(guild).clear()
            msg = _("{0.name} ({0.id}) reset server data for {1} ({1.id}).").format(author, guild)

        log.info(msg)
        await ctx.send(msg)

    async def reset_player_stats(self, ctx, user):
        author = ctx.author
        if await self.casino_is_global():
            coro = self.db.user(user)
        else:
            coro = self.db.member(user)

        await coro.Played.clear()
        await coro.Won.clear()

        msg = _("{0.name} ({0.id}) reset all stats for {1.name} ({1.id}).").format(author, user)
        log.info(msg)
        await ctx.send(msg)

    async def reset_player_all(self, ctx, user):
        author = ctx.author
        if await self.casino_is_global():
            await self.db.user(user).clear()
        else:
            await self.db.member(user).clear()

        msg = _("{0.name} ({0.id}) reset all data for {1.name} ({1.id}).").format(author, user)
        log.info(msg)
        await ctx.send(msg)

    async def reset_player_cooldowns(self, ctx, user):
        author = ctx.author
        if await self.casino_is_global():
            await self.db.user(user).Cooldowns.clear()
        else:
            await self.db.member(user).Cooldowns.clear()

        msg = _("{0.name} ({0.id}) reset all cooldowns for {1.name} ({1.id}).").format(author, user)
        log.info(msg)
        await ctx.send(msg)

    async def wipe_casino(self, ctx):
        await self.db.clear_all()
        msg = _("{0.name} ({0.id}) wiped all casino data.").format(ctx.author)
        log.info(msg)
        await ctx.send(msg)

    # --------------DATA-RETRIEVAL------------------------

    async def get_instance(self, ctx, settings=False, user=None):
        if not user:
            user = ctx.author

        if await self.casino_is_global():
            if settings:
                return self.db
            else:
                return self.db.user(user)
        else:
            if settings:
                return self.db.guild(ctx.guild)
            else:
                return self.db.member(user)

    # -------------------HELPERS---------------------------

    async def get_perks(self, ctx, player, membership):
        basic = {"Reduction": 0, "Access": 0, "Color": "grey", "Bonus": 1}
        if membership == 'Basic':
            return basic, "Basic"

        instance = await self.get_instance(ctx, settings=True)
        memberships = await instance.Memberships.all()
        try:
            perks = memberships[membership]
        except KeyError:
            player_db = await self.get_instance(ctx, user=player)
            await player_db.Membership.set({"Name": "Basic", "Assigned": False})
            perks, mem = basic, "Basic"
        else:
            mem = membership

        return perks, mem

    async def get_reduction(self, ctx, player):
        instance = await self.get_instance(ctx, user=player)
        membership = await instance.Membership.Name()
        perks, _ = await self.get_perks(ctx, player, membership)
        return perks["Reduction"]

    async def casino_is_global(self):
        return await self.db.Settings.Global()

    async def change_mode(self, mode):
        if mode == 'global':
            await self.db.clear_all_members()
            await self.db.clear_all_guilds()
            await self.db.Settings.Global.set(True)
        else:
            await self.db.clear_all_users()
            await self.db.clear_all_globals()
            await self.db.Settings.Global.set(False)


class Casino(Data):
    __slots__ = ('bot', 'cycle_task')

    def __init__(self, bot):
        self.bot = bot
        self.cycle_task = self.bot.loop.create_task(self.membership_updater())
        super().__init__()

    # --------------------------------------------------------------------------------------------------
    @commands.command(aliases=['bj', '21'])
    @commands.guild_only()
    async def blackjack(self, ctx: commands.Context, bet: int):
        """Play a game of blackjack.
        Blackjack supports doubling down, but not split.
        """
        await Blackjack().play(ctx, bet)

    @commands.command()
    @commands.guild_only()
    async def allin(self, ctx: commands.Context, multiplier: int):
        """Bets all your currency for a chance to win big!
        The higher your multiplier the lower your odds of winning.
        """
        if multiplier < 2:
            return await ctx.send("You're multiplier must be 2 or higher.")

        bet = await bank.get_balance(ctx.author)
        await Core().play_allin(ctx, bet, multiplier)

    @commands.command()
    @commands.guild_only()
    async def coin(self, ctx: commands.Context, bet: int, choice: str):
        """Coin flip game with a 50/50 chance to win.
        Pick heads or tails and place your bet.
        """
        if choice.lower() not in ('heads', 'tails'):
            return await ctx.send("You must bet heads or tails.")

        await Core().play_coin(ctx, bet, choice)

    @commands.command()
    @commands.guild_only()
    async def dice(self, ctx: commands.Context, bet: int):
        """Roll a set of dice and win on 2, 7, 11, 12.
        Just place a bet. No need to pick a number.
        """
        await Core().play_dice(ctx, bet)

    @commands.command()
    @commands.guild_only()
    async def cups(self, ctx: commands.Context, bet: int, cup: str):
        """Guess which cup of three is hiding the coin.
        Must pick 1, 2, or 3.
        """
        await Core().play_cups(ctx, bet, cup)

    @commands.command(aliases=['hl'])
    @commands.guild_only()
    async def hilo(self, ctx: commands.Context, bet: int, choice: str):
        """Pick high, low, or 7 in a dice rolling game.
        Acceptable choices are high, hi, low, lo, 7, or seven.
        """
        await Hilo().play(ctx, bet, choice)

    @commands.command()
    @commands.guild_only()
    async def war(self, ctx: commands.Context, bet: int):
        """Play a modified game of war."""
        await War().play(ctx, bet)

    @commands.command()
    @commands.guild_only()
    async def craps(self, ctx: commands.Context, bet: int):
        """Plays a modified version of craps
        The player wins 7x their bet on a come-out roll of 7.
        A comeout roll of 11 is an automatic win (standard mutlipliers apply).
        The player will lose on a comeout roll of 2, 3, or 12.
        Otherwise a point will be established. The player will keep
        rolling until they hit a 7 (and lose) or their point number.
        Every bet is considered a 'Pass Line' bet.
        """

        await Craps().play(ctx, bet)

    @commands.command(aliases=['don', 'x2'])
    @commands.guild_only()
    async def double(self, ctx: commands.Context, bet: int):
        """Play a game of Double Or Nothing.
        Continue to try to double your bet until
        you cash out or lose it all.
        """
        await Double().play(ctx, bet)

    # --------------------------------------------------------------------------------------------------

    @commands.group(autohelp=True)
    @commands.guild_only()
    async def casino(self, ctx: commands.Context):
        """Interacts with the Casino system.
        Use help on Casino (uppper case) for more commands.
        """
        pass

    @casino.command()
    async def memberships(self, ctx: commands.Context):
        """Displays a list of server/global memberships."""
        instance = await super().get_instance(ctx, settings=True)
        memberships = await instance.Memberships.all()

        if not memberships:
            return await ctx.send(_("There are no memberships to display."))

        names = [x.replace('_', ' ') for x in memberships]
        msg = await ctx.send(_("Which of the following memberships would you like to know more "
                               "about?\n{}.").format(utils.fmt_join(names)))

        preds = Checks(ctx, custom=[x.lower() for x in names])
        try:
            membership = await ctx.bot.wait_for('message', timeout=25.0, check=preds.content)
        except asyncio.TimeoutError:
            await msg.delete()
            return await ctx.send(_("No Response."))

        games = await instance.Games.all()
        try:
            data = memberships[membership.content.title().replace(' ', '_')]
        except KeyError:
            return await ctx.send("Could not find this membership.")
        playable = [x for x, y in games.items() if y['Access'] <= data['Access']]
        reqs = _("Credits: {Credits}\nRole: {Role}\nDays on Server: {DOS}").format(**data)
        color = utils.color_lookup(data['Color'])
        desc = _("Access: {Access}\n"
                 "Cooldown Reduction: {Reduction}\n"
                 "Bonus Multiplier: {Bonus}x\n"
                 "Color: {Color}").format(**data)

        info = _("Memberships are automatically assigned to players when they meet it's "
                 "requirements. If a player meets multiple membership requirements, they will be "
                 "assigned the one with the highest access level. If a membership is assigned "
                 "manually however, then the updater will skip that player until their membership "
                 "has been revoked.")

        # Embed
        embed = discord.Embed(colour=color, description=desc)
        embed.title = membership.content
        embed.add_field(name=_("Playable Games"), value='\n'.join(playable))
        embed.add_field(name=_("Requirements"), value=reqs)
        embed.set_footer(text=info)
        await msg.delete()
        await membership.delete()
        await ctx.send(embed=embed)

    @casino.command()
    @checks.admin_or_permissions(administrator=True)
    async def releasecredits(self, ctx: commands.Context, user: discord.Member):
        """Approves pending currency for a user."""
        author = ctx.author

        instance = await super().get_instance(ctx, user=user)
        amount = await instance.Pending_Credits()

        if amount <= 0:
            return await ctx.send(_("This user doesn't have any credits pending."))

        await ctx.send(_("{} has {} credits pending. "
                         "Would you like to release this amount?").format(user.name, amount))

        try:
            choice = ctx.bot.wait_for('message', timeout=25.0, check=Checks.confirm)
        except asyncio.TimeoutError:
            return await ctx.send(_("No response. Action canceled."))

        if choice.content.lower() == 'yes':
            await instance.Pending.clear()
            await bank.deposit_credits(user, amount)
            log.info(_("{0.name} ({0.id}) released {1} credits to {2.name} "
                       "({2.id}).").format(author, amount, user))
            await ctx.send(_("{0.mention} Your pending amount of {1} has been approved by "
                             "{2.name}, and was deposited into your "
                             "account.").format(user, amount, author))

        else:
            await ctx.send(_("Action canceled."))

    @casino.command()
    @checks.admin_or_permissions(administrator=True)
    async def resetuser(self, ctx: commands.Context, user: discord.Member):
        """Reset a user's cooldowns, stats, or everything."""
        options = (_("cooldowns"), _("stats"), _("all"))

        await ctx.send(_("What would you like to reset?\n{}.").format(utils.fmt_join(options)))

        preds = Checks(ctx, options)
        try:
            choice = await ctx.bot.wait_for('message', timeout=25.0, check=preds.content)
        except asyncio.TimeoutError:
            return await ctx.send(_("No response. Action canceled."))

        if choice.content.lower() == _('cooldowns'):
            await super().reset_player_cooldowns(ctx, user)
        elif choice.content.lower() == _('stats'):
            await super().reset_player_stats(ctx, user)
        else:
            await super().reset_player_all(ctx, user)

    @casino.command()
    @checks.admin_or_permissions(administrator=True)
    async def resetinstance(self, ctx: commands.Context):
        """Reset global/server cooldowns, settings, memberships, or everything."""
        author = ctx.author

        if not await ctx.bot.is_owner(author):
            return await ctx.send(_("You don't have permissions to delete a server."))
        options = (_("cooldowns"), _("settings"), _("games"), _("memberships"), _("all"))

        preds = Checks(ctx, options)

        await ctx.send(_("What would you like to reset?\n{}.").format(utils.fmt_join(options)))

        try:
            choice = await ctx.bot.wait_for('message', timeout=25.0, check=preds.content)
        except asyncio.TimeoutError:
            return await ctx.send(_("No response. Action canceled."))

        if choice.content.lower() == _('cooldowns'):
            await super().reset_server_cooldowns(ctx)
        elif choice.content.lower() == _('settings'):
            await super().reset_server_settings(ctx)
        elif choice.content.lower() == _('games'):
            await super().reset_server_games(ctx)
        elif choice.content.lower() == _('memberships'):
            await super().reset_server_memberships(ctx)
        else:
            await super().reset_server_all(ctx)

    @casino.command()
    @checks.is_owner()
    async def wipe(self, ctx: commands.Context):
        """Completely wipes casino data."""
        await ctx.send(_("You are about to delete all casino and user data from the bot. Are you "
                         "sure this is what you wish to do?"))

        try:
            choice = await ctx.bot.wait_for('message', timeout=25.0, check=Checks.confirm)
        except asyncio.TimeoutError:
            return await ctx.send(_("No Response. Action canceled."))

        if choice.content.lower() == 'yes':
            return await super().wipe_casino(ctx)
        else:
            return await ctx.send(_("Wipe canceled."))

    @casino.command()
    @checks.admin_or_permissions(administrator=True)
    async def assignmem(self, ctx: commands.Context, user: discord.Member, *, membership: str):
        """Manually assigns a membership to a user.
        Users who are assigned a membership no longer need to meet the
        requirements set. However, if the membership is revoked, then the
        user will need to meet the requirements as usual.
        """
        author = ctx.author
        instance = await super().get_instance(ctx, settings=True)
        memberships = await instance.Memberships.all()
        if membership.replace(' ', '_') not in memberships:
            return await ctx.send(_("{} is not a registered membership.").format(membership))

        player_instance = await super().get_instance(ctx, user=user)
        await player_instance.Membership.set({'Name': membership.replace(' ', '_'),
                                              'Assigned': True})

        msg = _("{0.name} ({0.id}) manually assigned {1.name} ({1.id}) the "
                "{2} membership.").format(author, user, membership)
        log.info(msg)
        await ctx.send(msg)

    @casino.command()
    @checks.admin_or_permissions(administrator=True)
    async def revokemem(self, ctx: commands.Context, user: discord.Member):
        """Revoke an assigned membership.
        Members will still keep this membership until the next auto cycle (5mins).
        At that time, they will be re-evaluated and downgraded/upgraded appropriately.
        """
        author = ctx.author
        instance = await super().get_instance(ctx, user=user)

        if not await instance.Membership.Assigned():
            return await ctx.send(_("This user has no assigned membership."))
        else:
            await instance.Membership.set({"Name": "Basic", "Assigned": False})
        return await ctx.send(_("{} has unassigned {}'s membership. They have been set "
                                "to `Basic` until the next membership update cycle."
                                "").format(author.name, user.name))

    @casino.command()
    @checks.admin_or_permissions(administrator=True)
    async def admin(self, ctx: commands.Context):
        """A list of Admin level and above commands for Casino."""
        cmds = ('casinoset access', 'casino assignmem', 'casinoset cooldown',
                'casinoset max', 'casino memprocess', 'casinoset min', 'casinoset multiplier',
                'casinoset name', 'casinoset payoutlimit', 'casinoset payouttoggle',
                'casino releasecredits', 'casino resetinstance', 'casino resetuser',
                'casino revokemem', 'casino wipe')

        cmd_list = '\n'.join(["**{}** - {}".format(x, y) for x, y in
                              [(com, ctx.bot.get_command(com).short_doc) for com in cmds]])

        wiki = '[Casino Wiki](https://github.com/Redjumpman/Jumper-Cogs/wiki/Casino)'
        embed = discord.Embed(colour=0xFF0000, description=wiki)
        embed.set_author(name='Casino Admin Panel', icon_url=ctx.bot.user.avatar_url)
        embed.add_field(name='__Commands__', value=cmd_list)
        embed.set_footer(text=_("With great power, comes great responsibility."))
        await ctx.send(embed=embed)

    @casino.command()
    async def info(self, ctx: commands.Context):
        """Shows information about Casino.
        Displays a list of games with their set parameters:
        Access Levels, Maximum and Minimum bets, if it's open to play,
        cooldowns, and multipliers. It also displays settings for the
        server (or global) if enabled.
        """
        instance = await super().get_instance(ctx, settings=True)
        settings = await instance.Settings.all()
        game_data = await instance.Games.all()

        t = sorted([[x] + [b for a, b in sorted(y.items(), key=itemgetter(0)) if a != 'Cooldown']
                    for x, y in game_data.items()])
        cool = [utils.cooldown_formatter(y["Cooldown"]) for x, y in
                sorted(game_data.items(), key=itemgetter(0))]
        table = [x + [y] for x, y in zip(t, cool)]

        headers = (_("Game"), _("Access"), _("Max"), _("Min"), _("Payout"), _("On"), _("CD"))
        t = tabulate(table, headers=headers)
        msg = _("```CPP\n{}\n\n"
                "Casino Name: {Casino_Name} Casino\n"
                "Casino Open: {Casino_Open}\n"
                "Global: {Global}\n"
                "Payout Limit ON: {Payout_Switch}\n"
                "Payout Limit: {Payout_Limit}```").format(t, **settings)
        await ctx.send(msg)

    @casino.command()
    async def stats(self, ctx: commands.Context):
        """Shows your play statistics for Casino"""
        author = ctx.author

        casino = await super().get_instance(ctx, settings=True)
        casino_name = await casino.Settings.Casino_Name()

        instance = await super().get_instance(ctx, user=author)
        player = await instance.all()

        perks, mem = await super().get_perks(ctx, author, player['Membership']["Name"])
        color = utils.color_lookup(perks['Color'])

        # FIXME Fix this fucking mess
        games = sorted(await casino.Games.all())

        played = [y for x, y in sorted(player["Played"].items(), key=itemgetter(0))]
        won = [y for x, y in sorted(player["Won"].items(), key=itemgetter(0))]
        cool_items = [y for x, y in sorted(player["Cooldowns"].items(), key=itemgetter(0))]

        reduction = await super().get_reduction(ctx, author)
        fmt_reduct = utils.cooldown_formatter(reduction)
        cooldowns = self.parse_cooldowns(ctx, cool_items, reduction)
        description = _("Membership: {0}\nAccess Level: {Access}\nCooldown Reduction: "
                        "{1}\nBonus Multiplier {Bonus}x").format(mem, fmt_reduct, **perks)

        headers = ("Games", "Played", "Won", "Cooldowns")
        table = tabulate(zip(games, played, won, cooldowns), headers=headers)
        disclaimer = _("Wins do not take into calculation pushed bets or surrenders.")

        # Embed
        embed = discord.Embed(colour=color, description=description)
        embed.title = _("{} Casino").format(casino_name)
        embed.set_author(name=str(author), icon_url=author.avatar_url)
        embed.add_field(name='-' * 90, value="```cpp\n{}```".format(table))
        embed.set_footer(text=disclaimer)
        await ctx.send(embed=embed)

    @casino.command()
    @checks.admin_or_permissions(administrator=True)
    async def memprocess(self, ctx: commands.Context):
        """A process to create, edit, and delete memberships."""
        timeout = ctx.send(_("Process timed out. Exiting membership process."))

        await ctx.send(_("Do you wish to `create`, `edit`, or `delete` an existing membership?"))

        preds = Checks(ctx, (_('edit'), _('create'), _('delete')))
        try:
            choice = await ctx.bot.wait_for('Message', timeout=25.0, check=preds.content)
        except asyncio.TimeoutError:
            return await timeout

        if choice.content.lower() == _("edit"):
            instance = await super().get_instance(ctx, settings=True)
            if await instance.Memberships():
                await Membership(ctx, timeout, 'edit').process()
            else:
                return await ctx.send(_("There are no memberships to edit."))
        elif choice.content.lower() == _('delete'):
            await Membership(ctx, timeout, 'delete').process()
        else:
            await Membership(ctx, timeout, 'create').process()

    @casino.command()
    async def version(self, ctx: commands.Context):
        """Shows the current Casino version."""
        await ctx.send("Casino is running version {}.".format(__version__))

    # --------------------------------------------------------------------------------------------------

    @commands.group(autohelp=True)
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def casinoset(self, ctx: commands.Context):
        """Changes Casino settings"""
        pass

    @casinoset.command(name='mode')
    @checks.is_owner()
    async def mode(self, ctx: commands.Context):
        """Toggles Casino between global and local modes.
        When casino is set to local mode, each server will have its own
        unique data, and admin level commands can be used on that server.
        When casino is set to global mode, data is linked between all servers
        the bot is connected to. In addition, admin level commands can only be
        used by the owner or co-owners.
        """
        author = ctx.author
        mode = 'global' if await super().casino_is_global() else 'local'
        alt = 'local' if mode == 'global' else 'global'
        await ctx.send(_("Casino is currently set to {} mode. Would you like to change to {} "
                         "mode instead?").format(mode, alt))
        preds = Checks(ctx)
        try:
            choice = await ctx.bot.wait_for('message', timeout=25.0, check=preds.confirm)
        except asyncio.TimeoutError:
            return await ctx.send(_("No response. Action canceled."))

        if choice.content.lower() != _('yes'):
            return await ctx.send(_("Casino will remain {}.").format(mode))
        await ctx.send(_("Changing casino to {0} will **DELETE ALL** current casino data. Are "
                         "you sure you wish to make casino {0}?").format(alt))
        try:
            final = await ctx.bot.wait_for('message', timeout=25.0, check=preds.confirm)
        except asyncio.TimeoutError:
            return await ctx.send(_("No response. Action canceled."))

        if final.content.lower() == _('yes'):
            if not await bank.is_global() and alt == "global":
                return await ctx.send("You cannot make casino global while economy is "
                                      "in local mode. To change your economy to global "
                                      "use `{}bankset toggleglobal`".format(ctx.prefix))
            await super().change_mode(alt)
            log.info(_("{} ({}) changed the casino mode to "
                       "{}.").format(author.name, author.id, alt))
            await ctx.send(_("Casino data deleted! Casino mode now set to {}.").format(alt))
        else:
            await ctx.send(_("Casino will remain {}.").format(mode))

    @casinoset.command()
    async def payoutlimit(self, ctx: commands.Context, limit: int):
        """Sets a payout limit.
        Users who exceed this amount will have their winnings witheld until they are
        reviewed and approved by the appropriate authority. Limits are only triggered if
        payout limits are ON. To turn on payout limits, use payouttoggle.
        """
        author = ctx.author

        if limit < 0:
            return await ctx.send(_("Go home. You're drunk."))

        instance = await super().get_instance(ctx, settings=True)
        await instance.Settings.Payout_Limit.set(limit)
        msg = _("{0.name} ({0.id}) set the payout limit to {1}.").format(author, limit)
        log.info(msg)
        await ctx.send(msg)

    @casinoset.command()
    async def payouttoggle(self, ctx: commands.Context):
        """Turns on a payout limit.
        The payout limit will withhold winnings from players until they are approved by the
        appropriate authority. To set the limit, use payoutlimit.
        """
        author = ctx.author
        instance = await super().get_instance(ctx, settings=True)
        status = await instance.Settings.Payout_Switch()
        await instance.Settings.Payout_Switch.set(not status)
        msg = _("{0.name} ({0.id}) turned the payout limit "
                "{1}.").format(author, "OFF" if status else "ON")
        log.info(msg)
        await ctx.send(msg)

    @casinoset.command()
    async def toggle(self, ctx: commands.Context):
        """Opens and closes the Casino for use.
        This command only restricts the use of playing games.
        """
        author = ctx.author
        instance = await super().get_instance(ctx, settings=True)
        name = await instance.Settings.Casino_Name()

        status = await instance.Settings.Casino_Open()
        await instance.Settings.Casino_Open.set(not status)
        msg = _("{0.name} ({0.id}) {2} the {1} "
                "Casino.").format(author, name, "closed" if status else "opened")
        log.info(msg)
        await ctx.send(msg)

    @casinoset.command()
    async def name(self, ctx: commands.Context, *, name: str):
        """Sets the name of the Casino.
        The casino name may only be 30 characters in length.
        """
        author = ctx.author
        if len(name) > 30:
            return await ctx.send(_("Your Casino name must be 30 characters or less."))

        instance = await super().get_instance(ctx, settings=True)
        await instance.Settings.Casino_Name.set(name)
        msg = _("{0.name} ({0.id}) set the casino name to {1}.").format(author, name)
        log.info(msg)
        await ctx.send(msg)

    @casinoset.command()
    async def multiplier(self, ctx: commands.Context, game: str, multiplier: float):
        """Sets the payout multiplier for a game.
        """
        author = ctx.author
        instance = await super().get_instance(ctx, settings=True)
        games = await instance.Games.all()

        if game.title() == 'Allin' or game.title() == 'Double':
            return await ctx.send(_("This games's multiplier is determined by the user."))

        if not await self.basic_check(ctx, game, games, multiplier):
            return

        await instance.Games.set_raw(game.title(), 'Multiplier', value=multiplier)
        msg = _("{0.name} ({0.id}) set "
                "{1}'s multiplier to {2}.").format(author, game.title(), multiplier)
        log.info(msg)
        if multiplier == 0:
            msg += _("\n\nWait a minute...Zero?! Really... I'm a bot and that's more "
                     "heartless than me! ... who hurt you human?")
        await ctx.send(msg)

    @casinoset.command()
    async def cooldown(self, ctx: commands.Context, game: str, cooldown: str):
        """Sets the cooldown for a game.
        You can use the format DD:HH:MM:SS to set a time, or just simply
        type the number of seconds.
        """
        author = ctx.author
        instance = await super().get_instance(ctx, settings=True)
        games = await instance.Games.all()

        try:
            seconds = utils.time_converter(cooldown)
        except ValueError:
            return await ctx.send(_("Invalid cooldown format. Must be an integer or in HH:MM:SS "
                                    "style."))

        if seconds < 0:
            return await ctx.send(_("Nice try McFly, but this isn't back to the future."))

        if game.title() not in games:
            return await ctx.send(_("Invalid game name. Must be on of the following:\n"
                                    "{}.").format(utils.fmt_join(list(games))))

        await instance.Games.set_raw(game.title(), 'Cooldown', value=seconds)
        cool = utils.cooldown_formatter(seconds)
        msg = _("{0.name} ({0.id}) set {1}'s cooldown to {2}.").format(author, game.title(), cool)
        log.info(msg)
        await ctx.send(msg)

    @casinoset.command(name="min")
    async def _min(self, ctx: commands.Context, game: str, minimum: int):
        """Sets the minimum bid for a game."""
        author = ctx.author
        instance = await super().get_instance(ctx, settings=True)
        games = await instance.Games.all()

        if not await self.basic_check(ctx, game, games, minimum):
            return

        if game.title() == "Allin":
            return await ctx.send(_("You cannot set a minimum bid for Allin."))

        if minimum > games[game.title()]["Max"]:
            return await ctx.send(_("You can't set a minimum higher than the game's maximum bid."))

        await instance.Games.set_raw(game.title(), "Min", value=minimum)
        msg = _("{0.name} ({0.id}) set {1}'s "
                "minimum bid to {2}.").format(author, game.title(), minimum)
        log.info(msg)
        await ctx.send(msg)

    @casinoset.command(name="max")
    async def _max(self, ctx: commands.Context, game: str, maximum: int):
        """Sets the maximum bid for a game."""
        author = ctx.author
        instance = await super().get_instance(ctx, settings=True)
        games = await instance.Games.all()

        if not await self.basic_check(ctx, game, games, maximum):
            return

        if game.title() == "Allin":
            return await ctx.send(_("You cannot set a maximum bid for Allin."))

        if maximum < games[game.title()]["Min"]:
            return await ctx.send(_("You can't set a maximum lower than the game's minimum bid."))

        await instance.Games.set_raw(game.title(), "Max", value=maximum)
        msg = _("{0.name} ({0.id}) set {1}'s "
                "maximum bid to {2}.").format(author, game.title(), maximum)
        log.info(msg)
        await ctx.send(msg)

    @casinoset.command()
    async def access(self, ctx, game: str, access: int):
        """Sets the access level required to play a game.
        Access levels are used in conjunction with memberships. To read more on using
        access levels and memberships please refer to the casino wiki."""
        author = ctx.author
        instance = await super().get_instance(ctx, settings=True)
        games = await instance.Games.all()

        if not await self.basic_check(ctx, game, games, access):
            return

        await instance.Games.set_raw(game.title(), 'Access', value=access)
        msg = _("{0.name} ({0.id}) changed the access level "
                "for {1} to {2}.").format(author, game, access)
        log.info(msg)
        await ctx.send(msg)

    @casinoset.command()
    async def gametoggle(self, ctx, game: str):
        """Opens/Closes a specific game for use."""
        author = ctx.author
        instance = await super().get_instance(ctx, settings=True)
        games = await instance.Games.all()
        if game.title() not in games:
            return await ctx.send("Invalid game name.")

        status = await instance.Games.get_raw(game.title(), 'Open')
        await instance.Games.set_raw(game.title(), 'Open', value=(not status))
        msg = _("{0.name} ({0.id}) {2} the game "
                "{1}.").format(author, game, "closed" if status else "opened")
        log.info(msg)
        await ctx.send(msg)

    # --------------------------------------------------------------------------------------------------

    async def membership_updater(self):
        await self.bot.wait_until_ready()
        try:
            while True:
                await asyncio.sleep(10)  # Wait 5 minutes to cycle again
                is_global = await super().casino_is_global()
                if is_global:
                    await self.global_updater()
                else:
                    await self.local_updater()
        except Exception as e:
            print(e)

    async def global_updater(self):
        while True:
            users = await self.db.all_users()
            if not users:
                break
            memberships = await self.db.Memberships.all()
            if not memberships:
                continue
            for user in users:
                user_obj = self.bot.get_user(user)
                if user_obj is None:
                    continue
                if await self.db.user(user_obj).Membership.Assigned():
                    user_mem = await self.db.user(user_obj).Membership.Name()
                    if user_mem not in memberships:
                        basic = {"Name": "Basic", "Assigned": False}
                        await self.db.user(user_obj).Membership.set(basic)
                    else:
                        continue
                await self.process_user(memberships, user_obj, _global=True)

            break

    async def local_updater(self):
        while True:
            guilds = await self.db.all_guilds()
            if not guilds:
                break
            for guild in guilds:
                guild_obj = self.bot.get_guild(guild)
                if not guild_obj:
                    continue
                users = await self.db.all_members(guild_obj)
                if not users:
                    continue
                memberships = await self.db.guild(guild_obj).Memberships.all()
                if not memberships:
                    continue
                for user in users:
                    user_obj = guild_obj.get_member(user)
                    if user_obj is None:
                        continue
                    if await self.db.member(user_obj).Membership.Assigned():
                        user_mem = await self.db.member(user_obj).Membership.Name()
                        if user_mem not in memberships:
                            basic = {"Name": "Basic", "Assigned": False}
                            await self.db.member(user_obj).Membership.set(basic)
                        else:
                            continue
                    await self.process_user(memberships, user_obj)
            break

    async def process_user(self, memberships, user, _global=False):
        qualified = []
        try:
            bal = await bank.get_balance(user)
        except AttributeError:
            raise RuntimeError("Casino is in global mode, while economy is in local mode. "
                               "Economy must be global if Casino is global. Either change casino "
                               "back to local or make your economy global.")
        for name, requirements in memberships.items():
            if _global:
                if requirements['Credits'] and bal < requirements['Credits']:
                    continue
                elif (requirements['DOS'] and
                      requirements['DOS'] > (user.created_at.now() - user.created_at).days):
                    continue
                else:
                    qualified.append((name, requirements['Access']))
            else:
                if requirements['Credits'] and bal < requirements['Credits']:
                    continue
                elif (requirements['Role'] and requirements['Role'] not in
                      [x.name for x in user.roles]):
                    continue
                elif (requirements['DOS'] and requirements['DOS'] >
                      (user.joined_at.now() - user.joined_at).days):
                    continue
                else:
                    qualified.append((name, requirements['Access']))

        membership = max(qualified, key=itemgetter(1))[0] if qualified else 'Basic'
        if _global:
            print("well we made it.")
            async with self.db.user(user).Membership() as data:
                data['Name'] = membership
                data['Assigned'] = False
        else:
            print("we out here.")
            async with self.db.member(user).Membership() as data:
                data['Name'] = membership
                data['Assigned'] = False

    @staticmethod
    async def basic_check(ctx, game, games, base):
        if game.title() not in games:
            await ctx.send("Invalid game name. Must be on of the following:\n"
                           "{}.".format(utils.fmt_join(list(games))))
            return False
        elif base < 0:
            await ctx.send(_("Go home. You're drunk."))
            return False
        else:
            return True

    @staticmethod
    def parse_cooldowns(ctx, cooldowns, reduction):
        now = calendar.timegm(ctx.message.created_at.utctimetuple())
        results = []
        for cooldown in cooldowns:
            seconds = int((cooldown + reduction - now))
            results.append(utils.cooldown_formatter(seconds, custom_msg="<<Ready to Play!"))
        return results

    def __unload(self):
        self.cycle_task.cancel()


class Engine(Data):
    """A class that handles setup and teardown for games.
        This is a helper class to make games easier to create and to
        provide a level of consistency. This class is only to be used
        in conjunction with the game_engine decorator.
        These attributes are created via the game_engine decorator.
        Attributes
        -----------
        game: str
            The name of the game.
        choice: str
            The decision the player chose for the game. This attribute can
            also be None.
        choices: list
            A list of choices the player must pick from. This attribute can
            also be None.
        ctx: object
            The Red context object necessary for the player object, guild object
            and sending/waiting for messages.
        player: object
            The author object from the Red Context object. This is used to pull data
            from config.
        guild: object
            The guild object from the Red Context object. This is used to pull data
            from config.
        bet: int
            The amount the player has wagered.
    """
    __slots__ = ('game', 'choice', 'choices', 'ctx', 'bet', 'player', 'guild')

    def __init__(self, game, choice, choices, ctx, bet):
        self.game = game
        self.choice = choice
        self.choices = choices
        self.bet = bet
        self.ctx = ctx
        self.player = ctx.author
        self.guild = ctx.guild
        super().__init__()

    async def check_conditions(self):
        instance = await super().get_instance(self.ctx, settings=True)
        user_instance = await super().get_instance(self.ctx, user=self.player)
        guild_data = await instance.all()
        user_data = await user_instance.all()
        user_access = await self.access_calculator(guild_data['Memberships'],
                                                   user_data["Membership"]["Name"])
        game_data = guild_data['Games'][self.game]
        minmax_fail = self.minmax_check(game_data)

        if self.choices is not None and self.choice not in self.choices:
            error = _("Incorrect response. Accepted response are:"
                      "\n{}.").format(utils.fmt_join(self.choices))
        elif not guild_data["Settings"]["Casino_Open"]:
            error = _("The Casino is closed.")
        elif not game_data['Open']:
            error = _("{} is closed.".format(self.game))
        elif game_data['Access'] > user_access:
            error = (_("{} requires an access level of {}. Your current access level is {}. Obtain "
                       "a higher membership to play this "
                       "game.").format(self.game, game_data['Access'], user_access))
        elif minmax_fail:
            error = minmax_fail
        elif not await bank.can_spend(self.player, self.bet):
            error = _("You do not have enough credits to cover the bet.")
        else:
            error = await self.check_cooldown(game_data, user_instance)

        if error:
            await self.ctx.send(error)
            return False
        else:
            await bank.withdraw_credits(self.player, self.bet)
            await self.stats_update(method='Played')
            return True

    async def stats_update(self, method):
        instance = await self.get_instance(self.ctx, user=self.player)
        current = await instance.get_raw(method, self.game)
        await instance.set_raw(method, self.game, value=current + 1)

    async def check_cooldown(self, game_data, user_instance):
        user_time = await user_instance.get_raw("Cooldowns", self.game)
        now = calendar.timegm(self.ctx.message.created_at.utctimetuple())
        base = game_data["Cooldown"]
        reduction = await super().get_reduction(self.ctx, self.player)

        if now >= user_time - reduction:
            await user_instance.set_raw("Cooldowns", self.game, value=now + base)
        else:
            seconds = int((user_time + reduction - now))
            remaining = utils.time_formatter(seconds)
            msg = _("{} is still on a cooldown. You still have: {} "
                    "remaining.").format(self.game, remaining)
            return msg

    async def game_teardown(self, result):
        coro = await super().get_instance(self.ctx, settings=True)
        settings = await coro.Settings.all()
        casino_name = settings['Casino_Name']
        win, amount, embed = result
        embed.title = _("{} Casino | {}").format(casino_name, self.game)
        if not win:
            bal_msg = await self.get_bal_msg()
            loss = _("Sorry, you didn't win anything.\n{}").format(bal_msg)
            embed.add_field(name='-' * 90, value=loss)
            return await self.ctx.send(self.player.mention, embed=embed)

        player_instance = await super().get_instance(self.ctx, user=self.player)
        await self.stats_update(method='Won')

        if self.limit_check(settings, amount):
            return await self.limit_handler(embed, amount, player_instance, coro)

        if self.game == 'Allin':
            await self.deposit_winnings(amount, player_instance, coro)
            bal_msg = await self.get_bal_msg()
            txt = "{}".format(bal_msg)
            embed.add_field(name='-' * 90, value=txt)
            return await self.ctx.send(self.player.mention, embed=embed)
        elif self.game == 'Double':
            await self.deposit_winnings(amount, player_instance, coro)
            currency = await bank.get_currency_name(self.guild)
            bal_msg = await self.get_bal_msg()
            txt = _("Congratulations, you just won {} {}!\n"
                    "{}").format(amount, currency, bal_msg)
            embed.add_field(name='-' * 90, value=txt)
            return await self.ctx.send(self.player.mention, embed=embed)
        else:
            total, bonus = await self.deposit_winnings(amount, player_instance, coro)
            currency = await bank.get_currency_name(self.guild)
            bal_msg = await self.get_bal_msg()
            txt = _("Congratulations, you just won {} {} {}!\n"
                    "{}").format(total, currency, bonus, bal_msg)
            embed.add_field(name='-' * 90, value=txt)
            return await self.ctx.send(self.player.mention, embed=embed)

    async def get_bal_msg(self):
        balance = await bank.get_balance(self.player)
        currency = await bank.get_currency_name(self.guild)
        bal_msg = _("**Remaining Balance:** {} {}").format(balance, currency)
        return bal_msg

    async def limit_handler(self, embed, amount, player_instance, coro):
        await player_instance.Pending.set(amount)

        await self.ctx.send(self.player.mention, embed=embed)
        limit = await coro.Settings.Payout_Limit()
        msg = _("{} Your winnings exceeded the maximum credit limit allowed ({}). The amount "
                "of {} credits will be pending on your account until reviewed. Until an "
                "Administrator or higher authority has released the pending currency, "
                "**DO NOT** attempt to place a bet that will exceed the payout limit. You "
                "may only have **ONE** pending payout at a "
                "time.").format(self.player.name, limit, amount)

        log.info(_("{0.name} ({0.id}) exceeded the payout limit!").format(self.player))
        await self.player.send(msg)

    async def deposit_winnings(self, amount, player_instance, coro):

        if amount > self.bet:
            if self.game == 'Allin' or self.game == 'Double':
                await bank.deposit_credits(self.player, amount)
                return
            total, amt, msg = await self.calculate_bonus(round(amount), player_instance, coro)
            await bank.deposit_credits(self.player, total)
            return total, msg

        multiplier = await coro.Games.get_raw(self.game, "Multiplier")
        initial = round(amount * multiplier)
        total, amt, msg = await self.calculate_bonus(initial, player_instance, coro)
        await bank.deposit_credits(self.player, total)
        return total, msg

    @staticmethod
    async def access_calculator(memberships, user_membership):
        if user_membership == 'Basic':
            return 0

        try:
            access = memberships[user_membership]["Access"]
        except KeyError:
            return 0
        else:
            return access

    @staticmethod
    async def calculate_bonus(amount, player_instance, coro):
        membership = await player_instance.Membership.Name()
        data = await coro.Memberships.all()
        try:
            bonus_multiplier = data[membership]['Bonus']
        except KeyError:
            bonus_multiplier = 1
        total = round(amount * bonus_multiplier)
        bonus = total - amount
        return total, amount, "(+{})".format(bonus if bonus_multiplier > 1 else 0)

    @staticmethod
    def limit_check(settings, amount):
        if settings["Payout_Switch"]:
            if amount > settings["Payout_Limit"]:
                return True
            else:
                return False
        else:
            return False

    def minmax_check(self, game_data):
        minimum, maximum = game_data["Min"], game_data["Max"]
        if self.game == "Allin":
            return None

        if minimum <= self.bet <= maximum:
            return None

        if minimum != maximum:
            return (_("Your bet needs to be {} or higher, but cannot be higher than "
                      "{}.").format(minimum, maximum))
        else:
            return _("Your bet must be exactly {}.").format(minimum)


class Membership(Data):
    """This class handles membership processing."""

    __slots__ = ('ctx', 'timeout', 'cancel', 'mode', 'coro')

    colors = {_("blue"): "blue", _("red"): "red", _("green"): "green", _("orange"): "orange",
              _("purple"): "purple", _("yellow"): "yellow", _("turquoise"): "turquoise",
              _("teal"): "teal", _("magenta"): "magenta", _("pink"): "pink",
              _("white"): "white"}

    requirements = (_("Days On Server"), _("Credits"), _("Role"))

    def __init__(self, ctx, timeout, mode):
        self.ctx = ctx
        self.timeout = timeout
        self.cancel = ctx.prefix + _("cancel")
        self.mode = mode
        self.coro = None
        super().__init__()

    def switcher(self):
        if self.mode == "edit":
            return self.editor
        elif self.mode == "create":
            return self.creator
        else:
            return self.delete

    async def process(self):
        action = self.switcher()
        instance = await super().get_instance(self.ctx, settings=True)
        self.coro = instance.Memberships
        try:
            await action()
        except asyncio.TimeoutError:
            await self.timeout
        except ExitProcess:
            await self.ctx.send(_("Process exited."))

    async def delete(self):
        memberships_raw = await self.coro.all()

        memberships = [x.replace('_', ' ') for x in memberships_raw]

        def mem_check(m):
            valid_name = m.content
            return (m.author == self.ctx.author and
                    valid_name in memberships or valid_name == self.cancel)

        await self.ctx.send(_("Which membership would you like to delete?\n"
                              "{}.").format(utils.fmt_join(memberships)))
        membership = await self.ctx.bot.wait_for('message', timeout=25.0, check=mem_check)

        if membership.content == self.cancel:
            raise ExitProcess()
        await self.ctx.send(_("Are you sure you wish to delete {}? "
                              "This cannot be reverted.").format(membership.content))

        choice = await self.ctx.bot.wait_for('message', timeout=25.0,
                                             check=Checks(self.ctx).confirm)
        if choice.content.lower() == self.cancel:
            raise ExitProcess()
        elif choice.content.lower() == "yes":
            name = membership.content.replace(' ', '_')
            async with self.coro() as data:
                del data[name]
            await self.ctx.send(_("{} has been deleted.").format(membership.content))
        else:
            await self.ctx.send(_("Deletion canceled."))

    async def creator(self):

        await self.ctx.send(_("You are about to create a new membership. You may exit this "
                              "process at any time by typing `{}cancel`").format(self.ctx.prefix))

        data = dict.fromkeys(("Access", "Bonus", "Color", "Credits", "Role", "DOS", "Reduction"))

        name, valid_name = await self.set_name()
        await self.set_access(data)
        await self.set_color(data)
        await self.set_reduction(data)
        await self.set_bonus(data)
        await self.req_loop(data)

        async with self.coro() as mem:
            mem[valid_name] = data

        embed = self.build_embed(name, data)
        await self.ctx.send(embed=embed)
        raise ExitProcess()

    async def editor(self):
        memberships_raw = await self.coro.all()

        memberships = [x.replace('_', ' ') for x in memberships_raw]

        def mem_check(m):
            return m.author == self.ctx.author and m.content in memberships or \
                   m.content == self.cancel

        await self.ctx.send(_("Which of the following memberships would you like to edit?\n"
                              "{}.").format(utils.fmt_join(memberships)))

        membership = await self.ctx.bot.wait_for("message", timeout=25.0, check=mem_check)
        if membership.content == self.cancel:
            raise ExitProcess()

        attrs = (_('Requirements'), _('Name'), _('Access'), _('Color'), _('Reduction'), _('Bonus'))
        await self.ctx.send(_("Which of the following attributes would you like to edit?\n"
                              "{}.").format(utils.fmt_join(attrs)))

        preds = Checks(self.ctx, (_('requirements'), _('access'), _('color'), _('name'),
                                  _('reduction'), self.cancel))
        attribute = await self.ctx.bot.wait_for("message", timeout=25.0, check=preds.content)

        valid_name = membership.content.replace(' ', '_')
        if attribute.content.lower() == self.cancel:
            raise ExitProcess()
        elif attribute.content.lower() == _('requirements'):
            await self.req_loop(valid_name)
        elif attribute.content.lower() == _('access'):
            await self.set_access(valid_name)
        elif attribute.content.lower() == _('bonus'):
            await self.set_bonus(valid_name)
        elif attribute.content.lower() == _('reduction'):
            await self.set_reduction(valid_name)
        elif attribute.content.lower() == _('color'):
            await self.set_color(valid_name)
        elif attribute.content.lower() == _('name'):
            await self.set_name(valid_name)
        else:
            await self.set_color(valid_name)

        await self.ctx.send(_("Would you like to edit another membership?"))

        choice = await self.ctx.bot.wait_for("message", timeout=25.0,
                                             check=Checks(self.ctx).confirm)
        if choice.content.lower() == _("yes"):
            await self.editor()
        else:
            raise ExitProcess()

    async def set_color(self, membership):
        await self.ctx.send(_("What color would you like to set?\n"
                              "{}").format(utils.fmt_join(list(self.colors))))
        preds = Checks(self.ctx, self.colors)
        color = await self.ctx.bot.wait_for("message", timeout=25.0, check=preds.content)

        if color.content.lower() == self.cancel:
            raise ExitProcess()

        if self.mode == "create":
            membership['Color'] = color.content.lower()
            return

        async with self.coro() as membership_data:
            membership_data[membership]['Color'] = color.content.lower()

        await self.ctx.send(_('Color set to {}.').format(color.content.lower()))

    async def set_name(self, membership=None):
        memberships = await self.coro.all()

        def mem_check(m):
            raw_name = m.content
            if m.author == self.ctx.author:
                if raw_name == self.cancel:
                    raise ExitProcess
                conditions = (m.content.replace(' ', '_') not in memberships,
                              (True if re.match('^[a-zA-Z0-9 _]*$', raw_name) else False))
                if all(conditions):
                    return True
                else:
                    return False
            else:
                return False

        await self.ctx.send(_("What name would you like to set?"))
        name = await self.ctx.bot.wait_for("message", timeout=25.0, check=mem_check)

        if name.content == self.cancel:
            raise ExitProcess()

        valid_name = name.content.replace(' ', '_')
        if self.mode == "create":
            return name.content, valid_name

        async with self.coro() as membership_data:
            membership[valid_name] = membership_data.pop(membership)

        await self.ctx.send(_('Name set to {}.').format(name.content))

    async def set_access(self, membership):
        await self.ctx.send(_("What access level would you like to set?"))
        access = await self.ctx.bot.wait_for("message", timeout=25.0,
                                             check=Checks(self.ctx).positive)

        if access.content.lower() == self.cancel:
            raise ExitProcess()

        if self.mode == "create":
            membership['Access'] = int(access.content)
            return

        async with self.coro() as membership_data:
            membership_data[membership]['Access'] = int(access.content)

        await self.ctx.send(_('Access set to {}.').format(access.content.lower()))

    async def set_reduction(self, membership):
        await self.ctx.send(_("What is the cooldown reduction of this membership?"))
        reduction = await self.ctx.bot.wait_for("message", timeout=25.0,
                                                check=Checks(self.ctx).positive)

        if reduction.content.lower() == self.cancel:
            raise ExitProcess()

        if self.mode == "create":
            membership['Reduction'] = int(reduction.content)
            return

        async with self.coro() as membership_data:
            membership_data[membership]['Reduction'] = int(reduction.content)

    async def set_bonus(self, membership):
        await self.ctx.send(_("What is the bonus payout multiplier for this membership?\n"
                              "*Defaults to one*"))
        bonus = await self.ctx.bot.wait_for("message", timeout=25.0,
                                            check=Checks(self.ctx).valid_float)

        if bonus.content.lower() == self.cancel:
            raise ExitProcess

        if self.mode == 'create':
            membership['Bonus'] = float(bonus.content)
            return

        async with self.coro() as membership_data:
            membership_data[membership]['Bonus'] = float(bonus.content)

        await self.ctx.send(_("Bonus multiplier set to {}.").format(bonus.content))

    async def req_loop(self, membership):
        while True:
            await self.ctx.send(_("Which requirement would you like to add or modify?\n"
                                  "{}.").format(utils.fmt_join(self.requirements)))

            chk = Checks(self.ctx, (_('credits'), _('role'), _('dos'), _('days on server'),
                                    self.cancel))
            req = await self.ctx.bot.wait_for("message", timeout=25.0, check=chk.content)
            if req.content.lower() == self.cancel:
                raise ExitProcess()
            elif req.content.lower() == _("credits"):
                await self.credits_requirement(membership)
            elif req.content.lower() == _("role"):
                await self.role_requirement(membership)
            else:
                await self.dos_requirement(membership)

            await self.ctx.send(_("Would you like to continue adding or modifying requirements?"))

            choice = await self.ctx.bot.wait_for("message", timeout=25.0,
                                                 check=Checks(self.ctx).confirm)
            if choice.content.lower() == _("no"):
                break
            elif choice.content.lower() == self.cancel:
                raise ExitProcess()
            else:
                continue

    async def credits_requirement(self, membership):
        await self.ctx.send(_("How many credits does this membership require?"))

        amount = await self.ctx.bot.wait_for("message", timeout=25.0,
                                             check=Checks(self.ctx).positive)

        if amount.content.lower() == self.cancel:
            raise ExitProcess()

        if self.mode == "create":
            membership['Credits'] = int(amount.content)
            return

        async with self.coro() as membership_data:
            membership_data[membership]['Credits'] = int(amount.content)

        await self.ctx.send(_('Credits requirement set to {}.').format(amount.content))

    async def role_requirement(self, membership):
        await self.ctx.send(_("What role does this membership require?\n"
                              "*Note this is skipped in global mode. If you set this as the only "
                              "requirement in global, it will be accessible to everyone!*"))
        role = await self.ctx.bot.wait_for("message", timeout=25.0, check=Checks(self.ctx).role)

        if self.mode == "create":
            membership['Role'] = role.content
            return

        async with self.coro() as membership_data:
            membership_data[membership]['Role'] = role.content

        await self.ctx.send(_('Role requirement set to {}.').format(role.content))

    async def dos_requirement(self, membership):
        await self.ctx.send(_("How many days on server does this membership require?\n"
                              "*Note in global mode this will calculate based on when the user "
                              "account was created.*"))
        days = await self.ctx.bot.wait_for("message", timeout=25.0, check=Checks(self.ctx).positive)

        if self.mode == "create":
            membership['DOS'] = int(days.content)
            return

        async with self.coro() as membership_data:
            membership_data[membership]['DOS'] = int(days.content)
        await self.ctx.send(_('Time requirement set to {}.').format(days.content))

    @staticmethod
    def build_embed(name, data):
        description = _("Membership sucessfully created.\n\n"
                        "**Name:** {0}\n"
                        "**Access:** {Access}\n"
                        "**Bonus:** {Bonus}x\n"
                        "**Reduction:** {Reduction}\n"
                        "**Color:** {Color}\n"
                        "**Credits Required:** {Credits}\n"
                        "**Role Required:** {Role}\n"
                        "**Days on Server/Discord Required:** {DOS}").format(name, **data)
        return discord.Embed(colour=0x2CD22C, description=description)


class Core:
    """
    A simple class to hold the basic original Casino mini games.
    Games
    -----------
    Allin
        Bet all your credits. All or nothing gamble.
    Coin
        Coin flip game. Pick heads or tails.
    Cups
        Three cups are shuffled. Pick the one covering the ball.
    Dice
        Roll a pair of die. 2, 7, 11, or 12 wins.
    """

    @game_engine("Allin")
    async def play_allin(self, ctx, bet, multiplier):
        await ctx.send(_("You put all your chips into the machine and pull the lever..."))
        await asyncio.sleep(3)
        outcome = random.randint(0, multiplier + 1)
        if outcome == 0:
            msg = "```Python\n"
            msg += "▂▃▅▇█▓▒░ [♠]  [♥]  [♦]  [♣] ░▒▓█▇▅▃▂\n"
            msg += _("          CONGRATULATIONS YOU WON\n")
            msg += _("░▒▓█▇▅▃▂ ⚅ J A C K P O T ⚅ ▂▃▅▇█▓▒░```")
            bet *= multiplier
        else:
            msg = _("Nothing happens. You stare at the machine contemplating your decision.")
        embed = utils.build_embed(msg)
        return outcome == 0, bet, embed

    @game_engine("Coin", (_("heads"), _("tails")))
    async def play_coin(self, ctx, bet, choice):
        await ctx.send(_("The coin flips into the air..."))
        await asyncio.sleep(2)
        outcome = random.choice((_("heads"), _("tails")))
        embed = utils.build_embed(_("The coin landed on {}!").format(outcome))
        return choice.lower() in outcome, bet, embed

    @game_engine("Cups", ('1', '2', '3'))
    async def play_cups(self, ctx, bet, choice):
        await ctx.send(_("The cups start shuffling along the table..."))
        await asyncio.sleep(3)
        outcome = random.randint(1, 3)
        embed = utils.build_embed(_("The coin was under cup {}!").format(outcome))
        return int(choice) == outcome, bet, embed

    @game_engine("Dice")
    async def play_dice(self, ctx, bet):
        await ctx.send(_("The dice strike the back of the table and begin to tumble into "
                         "place..."))
        await asyncio.sleep(2)
        die_one = random.randint(1, 6)
        die_two = random.randint(1, 6)
        outcome = die_one + die_two

        msg = _("The dice landed on {} and {} ({}).").format(die_one, die_two, outcome)
        embed = utils.build_embed(msg)
        return outcome in (2, 7, 11, 12), bet, embed


class Craps:
    """A simple class to hold the game logic for craps."""

    @game_engine(name="Craps")
    async def play(self, ctx, bet):
        return await self.craps_game(ctx, bet)

    async def craps_game(self, ctx, bet):
        roll_msg = _("The dice strike against the back of the table...")
        await ctx.send(roll_msg)
        await asyncio.sleep(2)
        d1, d2 = self.roll_dice()
        comeout = d1 + d2
        msg = _("You rolled a {} and {}.")

        if comeout == 7:
            bet *= 7
            return True, bet, utils.build_embed(msg.format(d1, d2))
        elif comeout == 11:
            return True, bet, utils.build_embed(msg.format(d1, d2))
        elif comeout in (2, 3, 12):
            return False, bet, utils.build_embed(msg.format(d1, d2))
        await ctx.send("{}\nI will keep rolling the dice until you match your comeout roll or "
                       "you crap out by rolling a 7 or 11.".format(msg.format(d1, d2)))
        await asyncio.sleep(5)
        return await self.point_loop(ctx, bet, comeout, roll_msg, msg)

    async def point_loop(self, ctx, bet, comeout, roll_msg, msg):
        count = 0
        while True:
            m = _("**Point:** {}").format(comeout)
            if count > 0:
                m += _("\nRolling again.")
                await asyncio.sleep(2)
            count += 1
            await ctx.send("{}\n{}".format(m, roll_msg))
            await asyncio.sleep(2)
            d1, d2 = self.roll_dice()
            await ctx.send(_("You rolled a {} and {}").format(d1, d2))
            if (d1 + d2) == comeout or (d1 + d2) in (7, 11) or count >= 3:
                if count >= 3:
                    msg += "\nYou automatically lost, because you exceeded the 3 re-roll limit."
                return (d1 + d2) == comeout, bet, utils.build_embed(msg.format(d1, d2))
            await asyncio.sleep(1)

    @staticmethod
    def roll_dice():
        return random.randint(1, 6), random.randint(1, 6)


class Blackjack(Data):
    """A simple class to hold the game logic for Blackjack.
    Blackjack requires inheritance from data to verify the user
    can double down.
    """

    def __init__(self):
        super().__init__()

    @game_engine(name="Blackjack")
    async def play(self, ctx, bet):
        ph, dh, amt = await self.blackjack_game(ctx, bet)
        result = await self.blackjack_results(ctx, amt, ph, dh)
        return result

    async def blackjack_game(self, ctx, amount):
        ph = deck.deal(num=2)
        ph_count = deck.bj_count(ph)
        dh = deck.deal(num=2)

        # End game if player has 21
        if ph_count == 21:
            return ph, dh, amount

        condition1 = Checks(ctx, (_("hit"), _("stay"), _("double")))
        condition2 = Checks(ctx, (_("hit"), _("stay")))

        embed = self.bj_embed(ctx, ph, dh, ph_count, initial=True)
        await ctx.send(ctx.author.mention, embed=embed)

        try:
            choice = await ctx.bot.wait_for('message', check=condition1.content, timeout=35.0)
        except asyncio.TimeoutError:
            dh = self.dealer(dh)
            return ph, dh, amount

        if choice.content.lower() == _("stay"):
            dh = self.dealer(dh)
            return ph, dh, amount

        if choice.content.lower() == _("double"):
            return await self.double_down(ctx, ph, dh, amount, condition2)
        else:
            ph, dh = await self.bj_loop(ctx, ph, dh, ph_count, condition2)
            dh = self.dealer(dh)
            return ph, dh, amount

    async def double_down(self, ctx, ph, dh, amount, condition2):
        try:
            await bank.withdraw_credits(ctx.author, amount)
        except ValueError:
            await ctx.send(_("{} You can not cover the bet. Please choose "
                             "hit or stay.").format(ctx.author.mention))

            try:
                choice2 = await ctx.bot.wait_for('message', check=condition2.content, timeout=35.0)
            except asyncio.TimeoutError:
                return ph, dh, amount

            if choice2.content.lower() == _("stay"):
                dh = self.dealer(dh)
                return ph, dh, amount
            elif choice2.content.lower() == _("hit"):
                ph, dh = await self.bj_loop(ctx, ph, dh, deck.bj_count(ph), condition2)
                dh = self.dealer(dh)
                return ph, dh, amount
        else:
            deck.deal(hand=ph)
            dh = self.dealer(dh)
            amount *= 2
            return ph, dh, amount

    async def blackjack_results(self, ctx, amount, ph, dh):
        dc = deck.bj_count(dh)
        pc = deck.bj_count(ph)

        if dc > 21 >= pc or dc < pc <= 21:
            outcome = _("Winner!")
            instance = await super().get_instance(ctx, settings=True)
            multiplier = await instance.Games.Blackjack.Multiplier()
            amount = amount * multiplier
            result = True
        elif pc > 21:
            outcome = _("BUST!")
            result = False
        elif dc == pc <= 21:
            outcome = _("Pushed")
            await bank.deposit_credits(ctx.author, amount)
            result = False
        else:
            outcome = _("House Wins!")
            result = False
        embed = self.bj_embed(ctx, ph, dh, pc, outcome=outcome)
        return result, amount, embed

    async def bj_loop(self, ctx, ph, dh, count, condition2):
        while count < 21:
            ph = deck.deal(hand=ph)
            count = deck.bj_count(hand=ph)

            if count >= 21:
                break
            embed = self.bj_embed(ctx, ph, dh, count)
            await ctx.send(ctx.author.mention, embed=embed)
            try:
                resp = await ctx.bot.wait_for("message", check=condition2.content, timeout=35.0)
            except asyncio.TimeoutError:
                break

            if resp.content.lower() == _("stay"):
                break
            else:
                continue

        # Return player hand & dealer hand when count >= 21 or the player picks stay.
        return ph, dh

    @staticmethod
    def dealer(dh):
        count = deck.bj_count(dh)
        # forces hit if ace in first two cards without 21
        if deck.hand_check(dh, 'Ace') and count != 21:
            deck.deal(hand=dh)
            count = deck.bj_count(dh)

        # defines maximum hit score X
        while count < 16:
            deck.deal(hand=dh)
            count = deck.bj_count(dh)
        return dh

    @staticmethod
    def bj_embed(ctx, ph, dh, count1, initial=False, outcome=None):
        hand = _("{}\n**Score:** {}")
        footer = _("Cards in Deck: {}")
        start = _("**Options:** hit, stay, or double")
        after = _("**Options:** hit or stay")
        options = "**Outcome:** " + outcome if outcome else start if initial else after
        count2 = deck.bj_count(dh, hole=True) if not outcome else deck.bj_count(dh)
        hole = " ".join(deck.fmt_hand([dh[0]]))
        dealer_hand = hole if not outcome else ", ".join(deck.fmt_hand(dh))

        embed = discord.Embed(colour=0xFF0000)
        embed.add_field(name=_("{}'s Hand").format(ctx.author.name),
                        value=hand.format(", ".join(deck.fmt_hand(ph)), count1))
        embed.add_field(name=_("{}'s Hand").format(ctx.bot.user.name),
                        value=hand.format(dealer_hand, count2))
        embed.add_field(name='\u200b', value=options, inline=False)
        embed.set_footer(text=footer.format(len(deck)))
        return embed


class Hilo:
    """A simple class for the Hilo game."""

    @game_engine("Hilo", (_("low"), _("lo"), _('high'), _('hi'), _('seven'), _('7')))
    async def play(self, ctx, bet, choice):
        await ctx.send(_("The dice hit the table and slowly fall into place..."))
        await asyncio.sleep(2)

        die_one = random.randint(1, 6)
        die_two = random.randint(1, 6)
        result = die_one + die_two
        outcome = self.hilo_lookup(result)
        msg = _("The outcome was {} ({[0]})!").format(result, outcome)
        embed = utils.build_embed(msg)

        if outcome == result == 7:
            bet *= 5

        return choice.lower() in outcome, bet, embed

    @staticmethod
    def hilo_lookup(result):
        if result < 7:
            return _("low"), _("lo")
        elif result > 7:
            return _("high"), _("hi")
        else:
            return _("seven"), "7"


class War:
    """A simple class for the war card game."""

    @game_engine("War")
    async def play(self, ctx, bet):
        outcome, player_card, dealer_card, amount = await self.war_game(ctx, bet)
        return await self.war_results(outcome, player_card, dealer_card, amount)

    async def war_game(self, ctx, bet):
        player_card, dealer_card, pc, dc = self.war_draw()

        await ctx.send(_("The dealer shuffles the deck and deals 2 cards face down. One for the "
                         "player and one for the dealer..."))
        await asyncio.sleep(2)
        await ctx.send(_("**FLIP!**"))
        await asyncio.sleep(1)

        if pc != dc:
            if pc >= dc:
                outcome = "Win"
            else:
                outcome = "Loss"
            return outcome, player_card, dealer_card, bet

        await ctx.send(_("The player and dealer are both showing a **{}**!\nTHIS MEANS "
                         "WAR! You may choose to surrender and forfeit half your bet, or "
                         "you can go to war.\nIf you go to war your bet will be doubled, "
                         "but the multiplier is only applied to your original bet, the rest will "
                         "be pushed.").format(deck.fmt_card(player_card)))
        preds = Checks(ctx, (_("war"), _("surrender"), _("ffs")))
        try:
            choice = await ctx.bot.wait_for('message', check=preds.content, timeout=35.0)
        except asyncio.TimeoutError:
            return "Surrender", player_card, dealer_card, bet

        if choice is None or choice.content.title() in (_("Surrender"), _("Ffs")):
            outcome = "Surrender"
            bet /= 2
            return outcome, player_card, dealer_card, bet
        else:
            player_card, dealer_card, pc, dc = self.burn_and_draw()

            await ctx.send(_("The dealer burns three cards and deals two cards face down..."))
            await asyncio.sleep(3)
            await ctx.send(_("**FLIP!**"))

            if pc >= dc:
                outcome = "Win"
            else:
                outcome = "Loss"
            return outcome, player_card, dealer_card, bet

    @staticmethod
    async def war_results(outcome, player_card, dealer_card, amount):
        msg = _("**Player Card:** {}\n**Dealer Card:** {}\n"
                "").format(deck.fmt_card(player_card), deck.fmt_card(dealer_card))
        if outcome == "Win":
            msg += _("**Result**: Winner")
            result = True

        elif outcome == "Loss":
            msg += _("**Result**: Loser")
            result = False
        else:
            msg += _("**Result**: Surrendered")
            result = False
        embed = utils.build_embed(msg)
        return result, amount, embed

    @staticmethod
    def get_count(pc, dc):
        return deck.war_count(pc), deck.war_count(dc)

    def war_draw(self):
        player_card, dealer_card = deck.deal(num=2)
        pc, dc = self.get_count(player_card, dealer_card)
        return player_card, dealer_card, pc, dc

    def burn_and_draw(self):
        deck.burn(3)
        player_card, dealer_card = deck.deal(num=2)
        pc, dc = self.get_count(player_card, dealer_card)
        return player_card, dealer_card, pc, dc

class Double:
    """A simple class for the Double Or Nothing game."""

    @game_engine("Double")
    async def play (self, ctx, bet):
        count, amount = await self.double_game(ctx, bet)
        return await self.double_results(ctx, count, amount)

    async def double_game(self, ctx, bet):
        count = 0
        
        while bet > 0:
            count += 1

            flip = random.randint(0,1)

            if flip == 0:
                bet = 0
                break
        
            else:
                bet *= 2

            condition = Checks(ctx, (_("double"), _("cash out")))

            embed = self.double_embed(ctx, count, bet)
            await ctx.send(ctx.author.mention, embed=embed)
            try:
                resp = await ctx.bot.wait_for("message", check=condition.content, timeout=35.0)
            except asyncio.TimeoutError:
                break

            if resp.content.lower() == _("cash out"):
                break
            else:
                continue


        return count, bet

    async def double_results(self, ctx, count, amount):
        if amount > 0:
            outcome = _("Cashed Out!")
            result = True
        else:
            outcome = _("You Lost It All!")
            result = False
        embed = self.double_embed(ctx, count, amount, outcome=outcome)
        return result, amount, embed

    @staticmethod
    def double_embed(ctx, count, amount, outcome=None):
        double = _("{}\n**DOUBLE!:** x{}")
        zero = _("{}\n**NOTHING!**")
        choice = _("**Options:** double or cash out")
        options = "**Outcome:** " + outcome if outcome else choice

        if amount == 0:
            score = zero.format(amount)
        else:
            score = double.format(amount, count)

        embed = discord.Embed(colour=0xFF0000)
        embed.add_field(name=_("{}'s Score").format(ctx.author.name),
                        value=score)
        embed.add_field(name='\u200b', value=options, inline=False)
        if not outcome:
            embed.add_field(name='\u200b', value='Remeber, you can cash out at anytime.', inline=False)
        embed.set_footer(text='Try again and test your luck!')
        return embed



class ExitProcess(Exception):
    pass

