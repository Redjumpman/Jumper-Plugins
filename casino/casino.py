# Developed by Redjumpman for Redbot.

# Standard Library
import asyncio
import calendar
import logging
import re
from typing import Union, Final, Literal
from operator import itemgetter


# Casino
from . import utils
from .data import Database
from .games import Core, Blackjack, Double, War
from .utils import is_input_unsupported

# Red
from redbot.core.i18n import Translator
from redbot.core import bank, commands, checks
from redbot.core.errors import BalanceTooHigh
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import box, humanize_number
from redbot.core.utils.predicates import MessagePredicate

# Discord
import discord

# Third-Party Libraries
from tabulate import tabulate

__version__ = "2.4.8"
__author__ = "Redjumpman"

_ = Translator("Casino", __file__)

log = logging.getLogger("red.jumper-plugins.casino")
_SCHEMA_VERSION: Final[int] = 2


class Casino(Database, commands.Cog):
    __slots__ = ("bot", "cycle_task")

    def __init__(self, bot):
        self.bot = bot
        self.cycle_task = self.bot.loop.create_task(self.membership_updater())
        super().__init__()

    async def initialise(self):
        self.migration_task = self.bot.loop.create_task(
            self.data_schema_migration(
                from_version=await self.config.schema_version(), to_version=_SCHEMA_VERSION
            )
        )

    async def red_delete_data_for_user(
        self, *, requester: Literal["discord", "owner", "user", "user_strict"], user_id: int
    ):
        await super().config.user_from_id(user_id).clear()
        all_members = await super().config.all_members()
        async for guild_id, guild_data in AsyncIter(all_members.items(), steps=100):
            if user_id in guild_data:
                await super().config.member_from_ids(guild_id, user_id).clear()

    # --------------------------------------------------------------------------------------------------

    @commands.command()
    @commands.guild_only()
    async def allin(self, ctx: commands.Context, multiplier: int):
        """Bets all your currency for a chance to win big!

        The higher your multiplier the lower your odds of winning.
        """
        if multiplier < 2:
            return await ctx.send("Your multiplier must be 2 or higher.")

        bet = await bank.get_balance(ctx.author)
        await Core(self.old_message_cache).play_allin(ctx, bet, multiplier)

    @commands.command(name="blackjack", aliases=["bj", "21"])
    @commands.guild_only()
    async def _blackjack(self, ctx, bet: int):
        """Play a game of blackjack.

        Blackjack supports doubling down, but not split.
        """
        await Blackjack(self.old_message_cache).play(ctx, bet)

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

        await Core(self.old_message_cache).play_craps(ctx, bet)

    @commands.command()
    @commands.guild_only()
    async def coin(self, ctx: commands.Context, bet: int, choice: str):
        """Coin flip game with a 50/50 chance to win.

        Pick heads or tails and place your bet.
        """
        if choice.lower() not in ("heads", "tails", "h", "t"):
            return await ctx.send("You must bet heads or tails.")

        await Core(self.old_message_cache).play_coin(ctx, bet, choice)

    @commands.command()
    @commands.guild_only()
    async def cups(self, ctx: commands.Context, bet: int, cup: str):
        """Guess which cup of three is hiding the coin.

        Must pick 1, 2, or 3.
        """
        await Core(self.old_message_cache).play_cups(ctx, bet, cup)

    @commands.command()
    @commands.guild_only()
    async def dice(self, ctx: commands.Context, bet: int):
        """Roll a set of dice and win on 2, 7, 11, 12.

        Just place a bet. No need to pick a number.
        """
        await Core(self.old_message_cache).play_dice(ctx, bet)

    @commands.command(aliases=["don", "x2"])
    @commands.guild_only()
    async def double(self, ctx: commands.Context, bet: int):
        """Play a game of Double Or Nothing.

        Continue to try to double your bet until
        you cash out or lose it all.
        """
        await Double(self.old_message_cache).play(ctx, bet)

    @commands.command(aliases=["hl"])
    @commands.guild_only()
    async def hilo(self, ctx: commands.Context, bet: int, choice: str):
        """Pick high, low, or 7 in a dice rolling game.

        Acceptable choices are high, hi, low, lo, 7, or seven.
        """
        await Core(self.old_message_cache).play_hilo(ctx, bet, choice)

    @commands.command()
    @commands.guild_only()
    async def war(self, ctx: commands.Context, bet: int):
        """Play a modified game of war."""
        await War(self.old_message_cache).play(ctx, bet)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def bjmock(self, ctx, bet: int, *, hands: str):
        """Test function for blackjack

        This will mock the blackjack game, allowing you to insert a player hand
        and a dealer hand.

        Example: [p]bjmock 50 :clubs: 10, :diamonds: 10 | :clubs: Ace, :clubs: Queen
        """
        ph, dh = hands.split(" | ")
        ph = [(x[0], int(x[2:])) if x[2:].isdigit() else (x[0], x[2:]) for x in ph.split(", ")]
        dh = [(x[0], int(x[2:])) if x[2:].isdigit() else (x[0], x[2:]) for x in dh.split(", ")]
        await Blackjack(self.old_message_cache).mock(ctx, bet, ph, dh)

    # --------------------------------------------------------------------------------------------------

    @commands.group()
    @commands.guild_only()
    async def casino(self, ctx):
        """Interacts with the Casino system.

        Use help on Casino (upper case) for more commands.
        """
        pass

    @casino.command()
    async def memberships(self, ctx):
        """Displays a list of server/global memberships."""
        data = await super().get_data(ctx)
        settings = await data.all()
        memberships = list(settings["Memberships"].keys())

        if not memberships:
            return await ctx.send(_("There are no memberships to display."))

        await ctx.send(
            _("Which of the following memberships would you like to know more about?\n`{}`").format(
                utils.fmt_join(memberships)
            )
        )

        pred = MessagePredicate.contained_in(memberships, ctx=ctx)

        try:
            membership = await ctx.bot.wait_for("message", timeout=25.0, check=pred)
        except asyncio.TimeoutError:
            return await ctx.send(_("No Response."))

        games = settings["Games"]
        perks = settings["Memberships"][membership.content]
        playable = [x for x, y in games.items() if y["Access"] <= perks["Access"]]

        reqs = _("Credits: {Credits}\nRole: {Role}\nDays on Server: {DOS}").format(**perks)
        color = utils.color_lookup(perks["Color"])
        desc = _(
            "Access: {Access}\n"
            "Cooldown Reduction: {Reduction} seconds\n"
            "Bonus Multiplier: {Bonus}x\n"
            "Color: {Color}"
        ).format(**perks)

        info = _(
            "Memberships are automatically assigned to players when they meet it's "
            "requirements. If a player meets multiple membership requirements, they will be "
            "assigned the one with the highest access level. If a membership is assigned "
            "manually however, then the updater will skip that player until their membership "
            "has been revoked."
        )

        # Embed
        embed = discord.Embed(colour=color, description=desc)
        embed.title = membership.content
        embed.add_field(name=_("Playable Games"), value="\n".join(playable))
        embed.add_field(name=_("Requirements"), value=reqs)
        embed.set_footer(text=info)
        await ctx.send(embed=embed)

    @casino.command()
    @checks.admin_or_permissions(administrator=True)
    async def releasecredits(self, ctx, player: Union[discord.Member, discord.User]):
        """Approves pending currency for a user.

        If this casino has maximum winnings threshold set, and a user makes a bet that
        exceeds this amount, then they will have those credits with held. This command will
        Allow you to release those credits back to the user. This system is designed to limit
        earnings when a player may have found a way to cheat a game.
        """

        player_data = await super().get_data(ctx, player=player)
        amount = await player_data.Pending_Credits()

        if amount <= 0:
            return await ctx.send(_("This user doesn't have any credits pending."))

        await ctx.send(
            _("{} has {} credits pending. Would you like to release this amount?").format(player.name, amount)
        )

        pred = MessagePredicate.yes_or_no(ctx=ctx)
        try:
            choice = await ctx.bot.wait_for("message", timeout=25.0, check=pred)
        except asyncio.TimeoutError:
            return await ctx.send(_("No response. Action canceled."))

        if choice.content.lower() == "yes":
            try:
                await bank.deposit_credits(player, amount)
                await player_data.Pending_Credits.clear()
                await ctx.send(
                    _(
                        "{0.mention} Your pending amount of {1} has been approved by "
                        "{2.name}, and was deposited into your account."
                    ).format(player, amount, ctx.author)
                )
            except BalanceTooHigh as e:
                await ctx.send(
                    _(
                        "{0.mention} Your pending amount of {1} has been approved by "
                        "{2.name}, but could not be deposited because your balance is at "
                        "the maximum amount of credits."
                    ).format(player, amount, ctx.author)
                )
        else:
            await ctx.send(_("Action canceled."))

    @casino.command()
    @checks.admin_or_permissions(administrator=True)
    async def resetuser(self, ctx: commands.Context, user: discord.Member):
        """Reset a user's cooldowns, stats, or everything."""

        if await super().casino_is_global() and not await ctx.bot.is_owner(ctx.author):
            return await ctx.send(_("While the casino is in global mode, only the bot owner may use this command."))

        options = (_("cooldowns"), _("stats"), _("all"))
        await ctx.send(_("What would you like to reset?\n`{}`.").format(utils.fmt_join(options)))

        pred = MessagePredicate.lower_contained_in(options, ctx=ctx)
        try:
            choice = await ctx.bot.wait_for("message", timeout=25.0, check=pred)
        except asyncio.TimeoutError:
            return await ctx.send(_("No response. Action canceled."))

        if choice.content.lower() == _("cooldowns"):
            await super()._reset_player_cooldowns(ctx, user)
        elif choice.content.lower() == _("stats"):
            await super()._reset_player_stats(ctx, user)
        else:
            await super()._reset_player_all(ctx, user)

    @casino.command()
    @checks.admin_or_permissions(administrator=True)
    async def resetinstance(self, ctx: commands.Context):
        """Reset global/server cooldowns, settings, memberships, or everything."""
        if await super().casino_is_global() and not await ctx.bot.is_owner(ctx.author):
            return await ctx.send(_("While the casino is in global mode, only the bot owner may use this command."))

        options = (_("settings"), _("games"), _("cooldowns"), _("memberships"), _("all"))
        await ctx.send(_("What would you like to reset?\n`{}`.").format(utils.fmt_join(options)))
        pred = MessagePredicate.lower_contained_in(options, ctx=ctx)
        await ctx.send(_("What would you like to reset?\n`{}`.").format(utils.fmt_join(options)))

        try:
            choice = await ctx.bot.wait_for("message", timeout=25.0, check=pred)
        except asyncio.TimeoutError:
            return await ctx.send(_("No response. Action canceled."))

        if choice.content.lower() == _("cooldowns"):
            await super()._reset_cooldowns(ctx)
        elif choice.content.lower() == _("settings"):
            await super()._reset_settings(ctx)
        elif choice.content.lower() == _("games"):
            await super()._reset_games(ctx)
        elif choice.content.lower() == _("memberships"):
            await super()._reset_memberships(ctx)
        else:
            await super()._reset_all_settings(ctx)

    @casino.command()
    @checks.is_owner()
    async def wipe(self, ctx: commands.Context):
        """Completely wipes casino data."""
        await ctx.send(
            _(
                "You are about to delete all casino and user data from the bot. Are you "
                "sure this is what you wish to do?"
            )
        )

        pred = MessagePredicate.yes_or_no(ctx=ctx)
        try:
            choice = await ctx.bot.wait_for("message", timeout=25.0, check=pred)
        except asyncio.TimeoutError:
            return await ctx.send(_("No Response. Action canceled."))

        if choice.content.lower() == "yes":
            return await super()._wipe_casino(ctx)
        else:
            return await ctx.send(_("Wipe canceled."))

    @casino.command()
    @checks.admin_or_permissions(administrator=True)
    async def assignmem(
        self,
        ctx: commands.Context,
        player: Union[discord.Member, discord.User],
        *,
        membership: str,
    ):
        """Manually assigns a membership to a user.

        Users who are assigned a membership no longer need to meet the
        requirements set. However, if the membership is revoked, then the
        user will need to meet the requirements as usual.

        """
        settings = await super().get_data(ctx)
        memberships = await settings.Memberships.all()
        if membership not in memberships:
            return await ctx.send(_("{} is not a registered membership.").format(membership))

        player_instance = await super().get_data(ctx, player=player)
        await player_instance.Membership.set({"Name": membership, "Assigned": True})

        msg = _("{0.name} ({0.id}) manually assigned {1.name} ({1.id}) the {2} membership.").format(
            ctx.author, player, membership
        )
        await ctx.send(msg)

    @casino.command()
    @checks.admin_or_permissions(administrator=True)
    async def revokemem(self, ctx: commands.Context, player: Union[discord.Member, discord.User]):
        """Revoke an assigned membership.

        Members will still keep this membership until the next auto cycle (5mins).
        At that time, they will be re-evaluated and downgraded/upgraded appropriately.
        """
        player_data = await super().get_data(ctx, player=player)

        if not await player_data.Membership.Assigned():
            return await ctx.send(_("{} has no assigned membership.").format(player.name))
        else:
            await player_data.Membership.set({"Name": "Basic", "Assigned": False})
        return await ctx.send(
            _(
                "{} has unassigned {}'s membership. They have been set "
                "to `Basic` until the next membership update cycle."
            ).format(ctx.author.name, player.name)
        )

    @casino.command()
    @checks.admin_or_permissions(administrator=True)
    async def admin(self, ctx: commands.Context):
        """A list of Admin level and above commands for Casino."""
        cmd_list = []
        cmd_list2 = []
        for cmd in ctx.bot.get_command("casino").commands:
            if cmd.requires.privilege_level.name == "ADMIN":
                if await cmd.requires.verify(ctx):
                    cmd_list.append((cmd.qualified_name, cmd.short_doc))

        for cmd in ctx.bot.get_command("casinoset").commands:
            if await cmd.requires.verify(ctx):
                cmd_list2.append((cmd.qualified_name, cmd.short_doc))
        cmd_list = "\n".join(["**{}** - {}".format(x, y) for x, y in cmd_list])
        cmd_list2 = "\n".join(["**{}** - {}".format(x, y) for x, y in cmd_list2])
        wiki = "[Casino Wiki](https://github.com/Redjumpman/Jumper-Plugins/wiki/Casino-RedV3)"
        embed = discord.Embed(colour=0xFF0000, description=wiki)
        embed.set_author(name="Casino Admin Panel", icon_url=ctx.bot.user.avatar_url)
        embed.add_field(name="__Casino__", value=cmd_list)
        embed.add_field(name="__Casino Settings__", value=cmd_list2)
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
        instance = await super().get_data(ctx)
        settings = await instance.Settings.all()
        game_data = await instance.Games.all()

        t = sorted(
            [
                [x] + [b for a, b in sorted(y.items(), key=itemgetter(0)) if a != "Cooldown"]
                for x, y in game_data.items()
            ]
        )
        cool = [
            utils.cooldown_formatter(y["Cooldown"])
            for x, y in sorted(game_data.items(), key=itemgetter(0))
        ]
        table = [x + [y] for x, y in zip(t, cool)]

        headers = (_("Game"), _("Access"), _("Max"), _("Min"), _("Payout"), _("On"), _("CD"))
        t = tabulate(table, headers=headers)
        msg = _(
            "{}\n\n"
            "Casino Name: {Casino_Name} Casino\n"
            "Casino Open: {Casino_Open}\n"
            "Global: {Global}\n"
            "Payout Limit ON: {Payout_Switch}\n"
            "Payout Limit: {Payout_Limit}"
        ).format(t, **settings)
        await ctx.send(box(msg, lang="cpp"))

    @casino.command()
    async def stats(
        self, ctx: commands.Context, player: Union[discord.Member, discord.User] = None
    ):
        """Shows your play statistics for Casino"""
        if player is None:
            player = ctx.author

        casino = await super().get_data(ctx)
        casino_name = await casino.Settings.Casino_Name()

        coro = await super().get_data(ctx, player=player)
        player_data = await coro.all()

        mem, perks = await super()._get_player_membership(ctx, player)
        color = utils.color_lookup(perks["Color"])

        games = sorted(await casino.Games.all())
        played = [y for x, y in sorted(player_data["Played"].items(), key=itemgetter(0))]
        won = [y for x, y in sorted(player_data["Won"].items(), key=itemgetter(0))]
        cool_items = [y for x, y in sorted(player_data["Cooldowns"].items(), key=itemgetter(0))]

        reduction = perks["Reduction"]
        fmt_reduct = utils.cooldown_formatter(reduction)
        cooldowns = self.parse_cooldowns(ctx, cool_items, reduction)
        description = _(
            "Membership: {0}\nAccess Level: {Access}\nCooldown Reduction: {1}\nBonus Multiplier: {Bonus}x"
        ).format(mem, fmt_reduct, **perks)

        headers = ("Games", "Played", "Won", "Cooldowns")
        table = tabulate(zip(games, played, won, cooldowns), headers=headers)
        disclaimer = _("Wins do not take into calculation pushed bets or surrenders.")

        # Embed
        embed = discord.Embed(colour=color, description=description)
        embed.title = _("{} Casino").format(casino_name)
        embed.set_author(name=str(player), icon_url=player.avatar_url)
        embed.add_field(name="\u200b", value="\u200b")
        embed.add_field(name="-" * 65, value=box(table, lang="md"))
        embed.set_footer(text=disclaimer)
        await ctx.send(embed=embed)

    @casino.command()
    @commands.max_concurrency(1, commands.BucketType.guild)
    @checks.admin_or_permissions(administrator=True)
    async def memdesigner(self, ctx: commands.Context):
        """A process to create, edit, and delete memberships."""
        timeout = ctx.send(_("Process timed out. Exiting membership process."))

        await ctx.send(_("Do you wish to `create`, `edit`, or `delete` an existing membership?"))

        pred = MessagePredicate.lower_contained_in(("edit", "create", "delete"), ctx=ctx)
        try:
            choice = await ctx.bot.wait_for("Message", timeout=25.0, check=pred)
        except asyncio.TimeoutError:
            return await timeout

        await Membership(ctx, timeout, choice.content.lower()).process()

    @casino.command()
    async def version(self, ctx: commands.Context):
        """Shows the current Casino version."""
        await ctx.send("Casino is running version {}.".format(__version__))

    # --------------------------------------------------------------------------------------------------

    async def global_casino_only(ctx):
        if await ctx.cog.config.Settings.Global() and not await ctx.bot.is_owner(ctx.author):
            return False
        else:
            return True

    @commands.check(global_casino_only)
    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def casinoset(self, ctx: commands.Context):
        """Changes Casino settings"""
        pass

    @casinoset.command(name="oldstyle")
    async def change_style(self, ctx: commands.Context):
        """Toggle between editing and sending new messages for casino games.."""

        current = await self.old_message_cache.get_guild(guild=ctx.guild)
        await self.old_message_cache.set_guild(guild=ctx.guild, set_to=not current)

        await ctx.send(
            _("Casino message type set to {type}.").format(
                type=_("**edit existing message**") if current else _("**send new message**")
            )
        )

    @casinoset.command(name="mode")
    @checks.is_owner()
    async def mode(self, ctx: commands.Context):
        """Toggles Casino between global and local modes.

        When casino is set to local mode, each server will have its own
        unique data, and admin level commands can be used on that server.

        When casino is set to global mode, data is linked between all servers
        the bot is connected to. In addition, admin level commands can only be
        used by the owner or co-owners.
        """

        mode = "global" if await super().casino_is_global() else "local"
        alt = "local" if mode == "global" else "global"
        await ctx.send(
            _("Casino is currently set to {} mode. Would you like to change to {} mode instead?").format(mode, alt)
        )
        pred = MessagePredicate.yes_or_no(ctx=ctx)

        try:
            choice = await ctx.bot.wait_for("message", timeout=25.0, check=pred)
        except asyncio.TimeoutError:
            return await ctx.send(_("No response. Action canceled."))
        if choice.content.lower() != _("yes"):
            return await ctx.send(_("Casino will remain {}.").format(mode))

        await ctx.send(
            _(
                "Changing casino to {0} will **DELETE ALL** current casino data. Are "
                "you sure you wish to make casino {0}?"
            ).format(alt)
        )
        try:
            final = await ctx.bot.wait_for("message", timeout=25.0, check=pred)
        except asyncio.TimeoutError:
            return await ctx.send(_("No response. Action canceled."))

        if final.content.lower() == _("yes"):
            if not await bank.is_global() and alt == "global":
                return await ctx.send(
                    "You cannot make casino global while economy is "
                    "in local mode. To change your economy to global "
                    "use `{}bankset toggleglobal`".format(ctx.prefix)
                )
            await super().change_mode(alt)
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

        if limit < 0 or is_input_unsupported(limit):
            return await ctx.send(_("Go home. You're drunk."))

        settings = await super().get_data(ctx)
        await settings.Settings.Payout_Limit.set(limit)
        msg = _("{0.name} ({0.id}) set the payout limit to {1}.").format(ctx.author, limit)
        await ctx.send(msg)

    @casinoset.command()
    async def payouttoggle(self, ctx: commands.Context):
        """Turns on a payout limit.

        The payout limit will withhold winnings from players until they are approved by the
        appropriate authority. To set the limit, use payoutlimit.
        """
        settings = await super().get_data(ctx)
        status = await settings.Settings.Payout_Switch()
        await settings.Settings.Payout_Switch.set(not status)
        msg = _("{0.name} ({0.id}) turned the payout limit {1}.").format(ctx.author, "OFF" if status else "ON")
        await ctx.send(msg)

    @casinoset.command()
    async def toggle(self, ctx: commands.Context):
        """Opens and closes the Casino for use.

        This command only restricts the use of playing games.
        """
        settings = await super().get_data(ctx)
        name = await settings.Settings.Casino_Name()

        status = await settings.Settings.Casino_Open()
        await settings.Settings.Casino_Open.set(not status)
        msg = _("{0.name} ({0.id}) {2} the {1} Casino.").format(ctx.author, name, "closed" if status else "opened")
        await ctx.send(msg)

    @casinoset.command()
    async def name(self, ctx: commands.Context, *, name: str):
        """Sets the name of the Casino.

        The casino name may only be 30 characters in length.
        """
        if len(name) > 30:
            return await ctx.send(_("Your Casino name must be 30 characters or less."))

        settings = await super().get_data(ctx)
        await settings.Settings.Casino_Name.set(name)
        msg = _("{0.name} ({0.id}) set the casino name to {1}.").format(ctx.author, name)
        await ctx.send(msg)

    @casinoset.command()
    async def multiplier(self, ctx: commands.Context, game: str, multiplier: float):
        """Sets the payout multiplier for a game.
        """
        settings = await super().get_data(ctx)
        games = await settings.Games.all()
        if is_input_unsupported(multiplier):
            return await ctx.send(_("Go home. You're drunk."))

        if game.title() == "Allin" or game.title() == "Double":
            return await ctx.send(_("This games's multiplier is determined by the user."))

        if not await self.basic_check(ctx, game, games, multiplier):
            return

        await settings.Games.set_raw(game.title(), "Multiplier", value=multiplier)
        msg = _("{0.name} ({0.id}) set {1}'s multiplier to {2}.").format(ctx.author, game.title(), multiplier)
        if multiplier == 0:
            msg += _(
                "\n\nWait a minute...Zero?! Really... I'm a bot and that's more "
                "heartless than me! ... who hurt you human?"
            )
        await ctx.send(msg)

    @casinoset.command()
    async def cooldown(self, ctx: commands.Context, game: str, cooldown: str):
        """Sets the cooldown for a game.

        You can use the format DD:HH:MM:SS to set a time, or just simply
        type the number of seconds.
        """
        settings = await super().get_data(ctx)
        games = await settings.Games.all()

        try:
            seconds = utils.time_converter(cooldown)
        except ValueError:
            return await ctx.send(_("Invalid cooldown format. Must be an integer or in HH:MM:SS style."))

        if seconds < 0:
            return await ctx.send(_("Nice try McFly, but this isn't Back to the Future."))

        if game.title() not in games:
            return await ctx.send(
                _("Invalid game name. Must be one of the following:\n`{}`.").format(utils.fmt_join(list(games)))
            )

        await settings.Games.set_raw(game.title(), "Cooldown", value=seconds)
        cool = utils.cooldown_formatter(seconds)
        msg = _("{0.name} ({0.id}) set {1}'s cooldown to {2}.").format(ctx.author, game.title(), cool)
        await ctx.send(msg)

    @casinoset.command(name="min")
    async def _min(self, ctx: commands.Context, game: str, minimum: int):
        """Sets the minimum bid for a game."""
        settings = await super().get_data(ctx)
        games = await settings.Games.all()

        if not await self.basic_check(ctx, game, games, minimum):
            return

        if is_input_unsupported(minimum):
            return await ctx.send(_("Go home. You're drunk."))

        if game.title() == "Allin":
            return await ctx.send(_("You cannot set a minimum bid for Allin."))

        if minimum > games[game.title()]["Max"]:
            return await ctx.send(_("You can't set a minimum higher than the game's maximum bid."))

        await settings.Games.set_raw(game.title(), "Min", value=minimum)
        msg = _("{0.name} ({0.id}) set {1}'s minimum bid to {2}.").format(ctx.author, game.title(), minimum)
        await ctx.send(msg)

    @casinoset.command(name="max")
    async def _max(self, ctx: commands.Context, game: str, maximum: int):
        """Sets the maximum bid for a game."""
        settings = await super().get_data(ctx)
        games = await settings.Games.all()

        if not await self.basic_check(ctx, game, games, maximum):
            return

        if is_input_unsupported(maximum):
            return await ctx.send(_("Go home. You're drunk."))

        if game.title() == "Allin":
            return await ctx.send(_("You cannot set a maximum bid for Allin."))

        if maximum < games[game.title()]["Min"]:
            return await ctx.send(_("You can't set a maximum lower than the game's minimum bid."))

        await settings.Games.set_raw(game.title(), "Max", value=maximum)
        msg = _("{0.name} ({0.id}) set {1}'s maximum bid to {2}.").format(ctx.author, game.title(), maximum)
        await ctx.send(msg)

    @casinoset.command()
    async def access(self, ctx, game: str, access: int):
        """Sets the access level required to play a game.

        Access levels are used in conjunction with memberships. To read more on using
        access levels and memberships please refer to the casino wiki."""
        data = await super().get_data(ctx)
        games = await data.Games.all()

        if not await self.basic_check(ctx, game, games, access):
            return

        if is_input_unsupported(access):
            return await ctx.send(_("Go home. You're drunk."))

        await data.Games.set_raw(game.title(), "Access", value=access)
        msg = _("{0.name} ({0.id}) changed the access level for {1} to {2}.").format(ctx.author, game, access)
        await ctx.send(msg)

    @casinoset.command()
    async def gametoggle(self, ctx, game: str):
        """Opens/Closes a specific game for use."""
        instance = await super().get_data(ctx)
        games = await instance.Games.all()
        if game.title() not in games:
            return await ctx.send("Invalid game name.")

        status = await instance.Games.get_raw(game.title(), "Open")
        await instance.Games.set_raw(game.title(), "Open", value=(not status))
        msg = _("{0.name} ({0.id}) {2} the game {1}.").format(ctx.author, game, "closed" if status else "opened")
        await ctx.send(msg)

    # --------------------------------------------------------------------------------------------------

    async def membership_updater(self):
        await self.bot.wait_until_ready()
        try:
            while True:
                await asyncio.sleep(300)  # Wait 5 minutes to cycle again
                is_global = await super().casino_is_global()
                if is_global:
                    await self.global_updater()
                else:
                    await self.local_updater()
        except Exception:
            log.error("Casino error in membership_updater:\n", exc_info=True)

    async def global_updater(self):
        while True:
            users = await self.config.all_users()
            if not users:
                break
            memberships = await self.config.Memberships.all()
            if not memberships:
                break
            for user in users:
                user_obj = self.bot.get_user(user)
                if not user_obj:
                    # user isn't in the cache so we can probably
                    # ignore them without issue
                    continue
                async with self.config.user(user_obj).Membership() as user_data:
                    if user_data["Name"] not in memberships:
                        user_data["Name"] = "Basic"
                        user_data["Assigned"] = False
                await self.process_user(memberships, user_obj, _global=True)
            break

    async def local_updater(self):
        while True:
            guilds = await self.config.all_guilds()
            if not guilds:
                break
            for guild in guilds:
                guild_obj = self.bot.get_guild(guild)
                if not guild_obj:
                    continue
                users = await self.config.all_members(guild_obj)
                if not users:
                    continue
                memberships = await self.config.guild(guild_obj).Memberships.all()
                if not memberships:
                    continue
                for user in users:
                    user_obj = guild_obj.get_member(user)
                    if not user_obj:
                        continue
                    async with self.config.member(user_obj).Membership() as user_data:
                        if user_data["Name"] not in memberships:
                            user_data["Name"] = "Basic"
                            user_data["Assigned"] = False
                    await self.process_user(memberships, user_obj)
            break

    async def process_user(self, memberships, user, _global=False):
        qualified = []
        try:
            bal = await bank.get_balance(user)
        except AttributeError:
            log.error(
                "Casino is in global mode, while economy is in local mode. "
                "Economy must be global if Casino is global. Either change casino "
                "back to local with the casinoset mode command or make your economy "
                "global with the bankset toggleglobal command."
            )
        for name, requirements in memberships.items():
            if _global:
                if requirements["Credits"] and bal < requirements["Credits"]:
                    continue
                elif (
                    requirements["DOS"]
                    and requirements["DOS"] > (user.created_at.now() - user.created_at).days
                ):
                    continue
                else:
                    qualified.append((name, requirements["Access"]))
            else:
                if requirements["Credits"] and bal < requirements["Credits"]:
                    continue
                elif requirements["Role"] and requirements["Role"] not in [
                    x.name for x in user.roles
                ]:
                    continue
                elif (
                    requirements["DOS"]
                    and requirements["DOS"] > (user.joined_at.now() - user.joined_at).days
                ):
                    continue
                else:
                    qualified.append((name, requirements["Access"]))

        membership = max(qualified, key=itemgetter(1))[0] if qualified else "Basic"
        if _global:
            async with self.config.user(user).Membership() as data:
                data["Name"] = membership
                data["Assigned"] = False
        else:
            async with self.config.member(user).Membership() as data:
                data["Name"] = membership
                data["Assigned"] = False

    @staticmethod
    async def basic_check(ctx, game, games, base):
        if game.title() not in games:
            await ctx.send(
                "Invalid game name. Must be on of the following:\n`{}`".format(utils.fmt_join(list(games)))
            )
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
            results.append(utils.cooldown_formatter(seconds, custom_msg="<Ready to Play!>"))
        return results

    def cog_unload(self):
        self.__unload()

    def __unload(self):
        self.cycle_task.cancel()
        if self.migration_task:
            self.migration_task.cancel()

    async def cog_before_invoke(self, ctx: commands.Context) -> None:
        if not self.cog_ready_event.is_set():
            async with ctx.typing():
                await self.cog_ready_event.wait()


class Membership(Database):
    """This class handles membership processing."""

    __slots__ = ("ctx", "timeout", "cancel", "mode", "coro")

    colors = {
        _("blue"): "blue",
        _("red"): "red",
        _("green"): "green",
        _("orange"): "orange",
        _("purple"): "purple",
        _("yellow"): "yellow",
        _("turquoise"): "turquoise",
        _("teal"): "teal",
        _("magenta"): "magenta",
        _("pink"): "pink",
        _("white"): "white",
    }

    requirements = (_("days on server"), _("credits"), _("role"))

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
        instance = await super().get_data(self.ctx)
        self.coro = instance.Memberships
        try:
            await action()
        except asyncio.TimeoutError:
            await self.timeout
        except ExitProcess:
            await self.ctx.send(_("Process exited."))

    async def delete(self):
        memberships = await self.coro.all()

        def mem_check(m):
            valid_name = m.content
            return (
                m.author == self.ctx.author
                and valid_name in memberships
                or valid_name == self.cancel
            )

        if not memberships:
            await self.ctx.send(_("There are no memberships to delete."))
            raise ExitProcess()

        await self.ctx.send(
            _("Which membership would you like to delete?\n`{}`").format(utils.fmt_join(list(memberships.keys())))
        )
        membership = await self.ctx.bot.wait_for("message", timeout=25.0, check=mem_check)

        if membership.content == self.cancel:
            raise ExitProcess()
        await self.ctx.send(
            _("Are you sure you wish to delete `{}`? This cannot be reverted.").format(membership.content)
        )

        choice = await self.ctx.bot.wait_for(
            "message", timeout=25.0, check=MessagePredicate.yes_or_no(ctx=self.ctx)
        )
        if choice.content.lower() == self.cancel:
            raise ExitProcess()
        elif choice.content.lower() == "yes":
            name = membership.content
            async with self.coro() as data:
                del data[name]
            await self.ctx.send(_("{} has been deleted.").format(membership.content))
        else:
            await self.ctx.send(_("Deletion canceled."))

    async def creator(self):

        await self.ctx.send(
            _(
                "You are about to create a new membership. You may exit this "
                "process at any time by typing `{}cancel`."
            ).format(self.ctx.prefix)
        )

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
        memberships = await self.coro.all()

        def mem_check(m):
            return (
                m.author == self.ctx.author
                and m.content in memberships
                or m.content == self.cancel
            )

        if not memberships:
            await self.ctx.send(_("There are no memberships to edit."))
            raise ExitProcess()

        await self.ctx.send(
            _("Which of the following memberships would you like to edit?\n`{}`").format(
                utils.fmt_join(list(memberships.keys()))
            )
        )

        membership = await self.ctx.bot.wait_for("message", timeout=25.0, check=mem_check)
        if membership.content == self.cancel:
            raise ExitProcess()

        attrs = (_("Requirements"), _("Name"), _("Access"), _("Color"), _("Reduction"), _("Bonus"))
        await self.ctx.send(
            _("Which of the following attributes would you like to edit?\n`{}`").format(utils.fmt_join(attrs))
        )

        pred = MessagePredicate.lower_contained_in(
            (
                _("requirements"),
                _("access"),
                _("color"),
                _("name"),
                _("reduction"),
                _("bonus"),
                self.cancel,
            ),
            ctx=self.ctx,
        )
        attribute = await self.ctx.bot.wait_for("message", timeout=25.0, check=pred)

        valid_name = membership.content
        if attribute.content.lower() == self.cancel:
            raise ExitProcess()
        elif attribute.content.lower() == _("requirements"):
            await self.req_loop(valid_name)
        elif attribute.content.lower() == _("access"):
            await self.set_access(valid_name)
        elif attribute.content.lower() == _("bonus"):
            await self.set_bonus(valid_name)
        elif attribute.content.lower() == _("reduction"):
            await self.set_reduction(valid_name)
        elif attribute.content.lower() == _("color"):
            await self.set_color(valid_name)
        elif attribute.content.lower() == _("name"):
            await self.set_name(valid_name)
        else:
            await self.set_color(valid_name)

        await self.ctx.send(_("Would you like to edit another membership?"))

        choice = await self.ctx.bot.wait_for(
            "message", timeout=25.0, check=MessagePredicate.yes_or_no(ctx=self.ctx)
        )
        if choice.content.lower() == _("yes"):
            await self.editor()
        else:
            raise ExitProcess()

    async def set_color(self, membership):
        await self.ctx.send(_("What color would you like to set?\n`{}`").format(utils.fmt_join(list(self.colors))))

        color_list = list(self.colors)
        color_list.append(str(self.cancel))
        pred = MessagePredicate.lower_contained_in(color_list, ctx=self.ctx)
        color = await self.ctx.bot.wait_for("message", timeout=25.0, check=pred)

        if color.content.lower() == self.cancel:
            raise ExitProcess()

        if self.mode == "create":
            membership["Color"] = color.content.lower()
            return

        async with self.coro() as membership_data:
            membership_data[membership]["Color"] = color.content.lower()

        await self.ctx.send(_("Color set to {}.").format(color.content.lower()))

    async def set_name(self, membership=None):
        memberships = await self.coro.all()

        def mem_check(m):
            if not m.channel == self.ctx.channel and m.author == self.ctx.author:
                return False
            if m.author == self.ctx.author:
                if m.content == self.cancel:
                    raise ExitProcess
                conditions = (
                    m.content not in memberships,
                    (True if re.match("^[a-zA-Z0-9 -]*$", m.content) else False),
                )
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

        valid_name = name.content
        if self.mode == "create":
            return name.content, valid_name

        async with self.coro() as membership_data:
            membership_data[valid_name] = membership_data.pop(membership)

        await self.ctx.send(_("Name set to {}.").format(name.content))

    async def set_access(self, membership):
        await self.ctx.send(_("What access level would you like to set?"))
        access = await self.ctx.bot.wait_for(
            "message", timeout=25.0, check=self.positive_int_predicate
        )

        user_input = int(access.content)
        if is_input_unsupported(user_input):
            await self.ctx.send(_("Can't set the reduction to this value."))
            return

        if self.mode == "create":
            membership["Access"] = user_input
            return

        async with self.coro() as membership_data:
            membership_data[membership]["Access"] = user_input

        await self.ctx.send(_("Access set to {}.").format(user_input))

    async def set_reduction(self, membership):
        await self.ctx.send(_("What is the cooldown reduction of this membership in seconds?"))
        reduction = await self.ctx.bot.wait_for(
            "message", timeout=25.0, check=self.positive_int_predicate
        )

        user_input = int(reduction.content)
        if is_input_unsupported(user_input):
            await self.ctx.send(_("Can't set the reduction to this value."))
            return

        if self.mode == "create":
            membership["Reduction"] = user_input
            return

        async with self.coro() as membership_data:
            membership_data[membership]["Reduction"] = user_input

    async def set_bonus(self, membership):
        await self.ctx.send(_("What is the bonus payout multiplier for this membership?\n*Defaults to 1.0*"))
        bonus = await self.ctx.bot.wait_for("message", timeout=25.0, check=self.positive_float_predicate)

        if bonus.content.lower() == self.cancel:
            raise ExitProcess
        user_input = bonus.content
        if is_input_unsupported(user_input):
            await self.ctx.send(_("Can't set the bonus multiplier to this value."))
            return

        if self.mode == "create":
            membership["Bonus"] = float(user_input)
            return

        async with self.coro() as membership_data:
            membership_data[membership]["Bonus"] = float(bonus.content)

        await self.ctx.send(_("Bonus multiplier set to {}.").format(bonus.content))

    async def req_loop(self, membership):
        while True:
            await self.ctx.send(
                _("Which requirement would you like to add or modify?\n`{}`").format(
                    utils.fmt_join(self.requirements)
                )
            )

            pred = MessagePredicate.lower_contained_in(
                (_("credits"), _("role"), _("dos"), _("days on server"), self.cancel), ctx=self.ctx
            )

            req = await self.ctx.bot.wait_for("message", timeout=25.0, check=pred)
            if req.content.lower() == self.cancel:
                raise ExitProcess()
            elif req.content.lower() == _("credits"):
                await self.credits_requirement(membership)
            elif req.content.lower() == _("role"):
                await self.role_requirement(membership)
            else:
                await self.dos_requirement(membership)

            await self.ctx.send(_("Would you like to continue adding or modifying requirements?"))

            choice = await self.ctx.bot.wait_for(
                "message", timeout=25.0, check=MessagePredicate.yes_or_no(ctx=self.ctx)
            )
            if choice.content.lower() == _("no"):
                break
            elif choice.content.lower() == self.cancel:
                raise ExitProcess()
            else:
                continue

    async def credits_requirement(self, membership):
        await self.ctx.send(_("How many credits does this membership require?"))

        amount = await self.ctx.bot.wait_for(
            "message", timeout=25.0, check=self.positive_int_predicate
        )

        amount = int(amount.content)
        if is_input_unsupported(amount):
            await self.ctx.send(_("Can't set the credit requirement to this value."))
            return
        if self.mode == "create":
            membership["Credits"] = amount
            return

        async with self.coro() as membership_data:
            membership_data[membership]["Credits"] = amount

        await self.ctx.send(_("Credits requirement set to {}.").format(humanize_number(amount)))

    async def role_requirement(self, membership):
        await self.ctx.send(
            _(
                "What role does this membership require?\n"
                "*Note this is skipped in global mode. If you set this as the only "
                "requirement in global, it will be accessible to everyone!*"
            )
        )
        pred = MessagePredicate.valid_role(ctx=self.ctx)
        role = await self.ctx.bot.wait_for("message", timeout=25.0, check=pred)

        if self.mode == "create":
            membership["Role"] = role.content
            return

        async with self.coro() as membership_data:
            membership_data[membership]["Role"] = role.content

        await self.ctx.send(_("Role requirement set to {}.").format(role.content))

    async def dos_requirement(self, membership):
        await self.ctx.send(
            _(
                "How many days on server does this membership require?\n"
                "*Note in global mode this will calculate based on when the user "
                "account was created.*"
            )
        )
        days = await self.ctx.bot.wait_for(
            "message", timeout=25.0, check=self.positive_int_predicate
        )

        if self.mode == "create":
            membership["DOS"] = int(days.content)
            return

        async with self.coro() as membership_data:
            membership_data[membership]["DOS"] = int(days.content)
        await self.ctx.send(_("Time requirement set to {}.").format(days.content))

    @staticmethod
    def build_embed(name, data):
        description = _(
            "Membership sucessfully created.\n\n"
            "**Name:** {0}\n"
            "**Access:** {Access}\n"
            "**Bonus:** {Bonus}x\n"
            "**Reduction:** {Reduction} seconds\n"
            "**Color:** {Color}\n"
            "**Credits Required:** {Credits}\n"
            "**Role Required:** {Role}\n"
            "**Days on Server/Discord Required:** {DOS}"
        ).format(name, **data)
        return discord.Embed(colour=0x2CD22C, description=description)

    def positive_int_predicate(self, m: discord.Message):
        if not m.channel == self.ctx.channel and m.author == self.ctx.author:
            return False
        if m.author == self.ctx.author:
            if m.content == self.cancel:
                raise ExitProcess
        try:
            int(m.content)
        except ValueError:
            return False
        if int(m.content) < 1:
            return False
        else:
            return True

    def positive_float_predicate(self, m: discord.Message):
        if not m.channel == self.ctx.channel and m.author == self.ctx.author:
            return False
        if m.author == self.ctx.author:
            if m.content == self.cancel:
                raise ExitProcess
        try:
            float(m.content)
        except ValueError:
            return False
        if float(m.content) > 0:
            return True
        else:
            return False


class ExitProcess(Exception):
    pass
