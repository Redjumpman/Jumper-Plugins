import asyncio
import logging
from copy import deepcopy

import discord
from redbot.core import Config, bank
from collections import namedtuple

from .cache import OldMessageTypeManager
from .utils import is_input_unsupported, min_int, max_int

user_defaults = {
    "Pending_Credits": 0,
    "Membership": {"Name": "Basic", "Assigned": False},
    "Played": {
        "Allin": 0,
        "Blackjack": 0,
        "Coin": 0,
        "Craps": 0,
        "Cups": 0,
        "Dice": 0,
        "Hilo": 0,
        "War": 0,
        "Double": 0,
    },
    "Won": {
        "Allin": 0,
        "Blackjack": 0,
        "Coin": 0,
        "Craps": 0,
        "Cups": 0,
        "Dice": 0,
        "Hilo": 0,
        "War": 0,
        "Double": 0,
    },
    "Cooldowns": {
        "Allin": 0,
        "Blackjack": 0,
        "Coin": 0,
        "Craps": 0,
        "Cups": 0,
        "Dice": 0,
        "Hilo": 0,
        "War": 0,
        "Double": 0,
    },
}

guild_defaults = {
    "use_old_style": False,
    "Memberships": {},
    "Settings": {
        "Global": False,
        "Casino_Name": "Redjumpman's",
        "Casino_Open": True,
        "Payout_Switch": False,
        "Payout_Limit": 10000,
    },
    "Games": {
        "Allin": {
            "Access": 0,
            "Cooldown": 43200,
            "Min": None,
            "Max": None,
            "Multiplier": None,
            "Open": True,
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
            "Open": True,
        },
        "Craps": {
            "Access": 0,
            "Cooldown": 5,
            "Max": 500,
            "Min": 50,
            "Multiplier": 2.0,
            "Open": True,
        },
        "Cups": {
            "Access": 0,
            "Cooldown": 5,
            "Max": 100,
            "Min": 25,
            "Multiplier": 1.8,
            "Open": True,
        },
        "Dice": {
            "Access": 0,
            "Cooldown": 5,
            "Max": 100,
            "Min": 25,
            "Multiplier": 1.8,
            "Open": True,
        },
        "Hilo": {
            "Access": 0,
            "Cooldown": 5,
            "Min": 25,
            "Max": 75,
            "Multiplier": 1.7,
            "Open": True,
        },
        "Double": {
            "Access": 0,
            "Cooldown": 5,
            "Min": 10,
            "Max": 250,
            "Multiplier": None,
            "Open": True,
        },
        "War": {"Access": 0, "Cooldown": 5, "Min": 25, "Max": 75, "Multiplier": 1.5, "Open": True},
    },
}

member_defaults = deepcopy(user_defaults)
global_defaults = deepcopy(guild_defaults)
global_defaults["Settings"]["Global"] = True


_DataNamedTuple = namedtuple("Casino", "foo")
_DataObj = _DataNamedTuple(foo=None)


log = logging.getLogger("red.jumper-plugins.casino")


class Database:

    config: Config = Config.get_conf(_DataObj, 5074395001, force_registration=True)

    def __init__(self):
        self.config.register_guild(**guild_defaults)
        self.config.register_global(schema_version=1, **global_defaults)
        self.config.register_member(**member_defaults)
        self.config.register_user(**user_defaults)
        self.old_message_cache = OldMessageTypeManager(config=self.config, enable_cache=True)
        self.migration_task: asyncio.Task = None
        self.cog_ready_event: asyncio.Event = asyncio.Event()

    async def data_schema_migration(self, from_version: int, to_version: int):
        if from_version == to_version:
            self.cog_ready_event.set()
            return
        if from_version < 2 <= to_version:
            try:
                async with self.config.all() as casino_data:
                    temp = deepcopy(casino_data)
                    global_payout = casino_data["Settings"]["Payout_Limit"]
                    if is_input_unsupported(global_payout):
                        casino_data["Settings"]["Payout_Limit"] = await bank.get_max_balance()
                    for g, g_data in temp["Games"].items():
                        for g_data_key, g_data_value in g_data.items():
                            if g_data_key in ["Access", "Cooldown", "Max", "Min", "Multiplier"]:
                                if is_input_unsupported(g_data_value):
                                    if g_data_value < min_int:
                                        g_data_value_new = min_int
                                    else:
                                        g_data_value_new = max_int
                                    casino_data["Games"][g][g_data_key] = g_data_value_new
                async with self.config._get_base_group(self.config.GUILD).all() as casino_data:
                    temp = deepcopy(casino_data)
                    for guild_id, guild_data in temp.items():
                        if (
                            "Settings" in temp[guild_id]
                            and "Payout_Limit" in temp[guild_id]["Settings"]
                        ):
                            guild_payout = casino_data[guild_id]["Settings"]["Payout_Limit"]
                            if is_input_unsupported(guild_payout):
                                casino_data[guild_id]["Settings"][
                                    "Payout_Limit"
                                ] = await bank.get_max_balance(
                                    guild_payout, guild=discord.Object(id=int(guild_id))
                                )
                        if "Games" in temp[guild_id]:
                            for g, g_data in temp[guild_id]["Games"].items():
                                for g_data_key, g_data_value in g_data.items():
                                    if g_data_key in [
                                        "Access",
                                        "Cooldown",
                                        "Max",
                                        "Min",
                                        "Multiplier",
                                    ]:
                                        if is_input_unsupported(g_data_value):
                                            if g_data_value < min_int:
                                                g_data_value_new = min_int
                                            else:
                                                g_data_value_new = max_int
                                            casino_data[guild_id]["Games"][g][
                                                g_data_key
                                            ] = g_data_value_new
                await self.config.schema_version.set(2)
            except Exception as e:
                log.exception(
                    "Fatal Exception during Data migration to Scheme 2, Casino cog will not be loaded.",
                    exc_info=e,
                )
                raise
        self.cog_ready_event.set()

    async def casino_is_global(self):
        """Checks to see if the casino is storing data on
           a per server basis or globally."""
        return await self.config.Settings.Global()

    async def get_data(self, ctx, player=None):
        """

        :param ctx: Context object
        :param player: Member or user object
        :return: Database that corresponds to the given data.

        Returns the appropriate config category based on the given
        data, and wheater or not the casino is global.
        """
        if await self.casino_is_global():
            if player is None:
                return self.config
            else:
                return self.config.user(player)
        else:
            if player is None:
                return self.config.guild(ctx.guild)
            else:
                return self.config.member(player)

    async def get_all(self, ctx, player):
        """

        :param ctx: Context Object
        :param player: Member or user object
        :return: Tuple with two dictionaries

        Returns a dictionary representation of casino's settings data
        and the player data.
        """
        settings = await self.get_data(ctx)
        player_data = await self.get_data(ctx, player=player)
        return await settings.all(), await player_data.all()

    async def _wipe_casino(self, ctx):
        """
        Wipes all the casino data available

        :param ctx: context object
        :return: None

        This wipes everything, including member/user data.
        """
        await self.config.clear_all()
        msg = "{0.name} ({0.id}) wiped all casino data.".format(ctx.author)
        await ctx.send(msg)

    async def _reset_settings(self, ctx):
        """
        Resets only the settings data.
        """
        data = await self.get_data(ctx)
        await data.Settings.clear()
        msg = ("{0.name} ({0.id}) reset all casino settings.").format(ctx.author)
        await ctx.send(msg)

    async def _reset_memberships(self, ctx):
        """
        Resets all the information pertaining to memberships
        """
        data = await self.get_data(ctx)
        await data.Memberships.clear()
        msg = ("{0.name} ({0.id}) cleared all casino memberships.").format(ctx.author)
        await ctx.send(msg)

    async def _reset_games(self, ctx):
        """
        Resets all game settings, such as multipliers and bets.
        """
        data = await self.get_data(ctx)
        await data.Games.clear()
        msg = ("{0.name} ({0.id}) restored casino games to default settings.").format(ctx.author)
        await ctx.send(msg)

    async def _reset_all_settings(self, ctx):
        """
        Resets all settings, but retains all player data.
        """
        await self._reset_settings(ctx)
        await self._reset_memberships(ctx)
        await self._reset_games(ctx)
        await self._reset_cooldowns(ctx)

    async def _reset_player_stats(self, ctx, player):
        """
        :param ctx: Context object
        :param player: user or member object
        :return: None

        Resets a player's win / played stats.

        """
        data = await self.get_data(ctx, player=player)
        await data.Played.clear()
        await data.Won.clear()

        msg = ("{0.name} ({0.id}) reset all stats for {1.name} ({1.id}).").format(ctx.author, player)
        await ctx.send(msg)

    async def _reset_player_all(self, ctx, player):
        """

        :param ctx: context object
        :param player: user or member object
        :return: None

        Resets all data belonging to the user, including stats and memberships.
        """
        data = await self.get_data(ctx, player=player)
        await data.clear()

        msg = ("{0.name} ({0.id}) reset all data for {1.name} ({1.id}).").format(ctx.author, player)
        await ctx.send(msg)

    async def _reset_player_cooldowns(self, ctx, player):
        """

        :param ctx: context object
        :param player: user or member object
        :return: None

        Resets all game cooldowns for a player.
        """
        data = await self.get_data(ctx, player=player)
        await data.Cooldowns.clear()

        msg = ("{0.name} ({0.id}) reset all cooldowns for {1.name} ({1.id}).").format(ctx.author, player)
        await ctx.send(msg)

    async def _reset_cooldowns(self, ctx):
        """
        Resets all game cooldowns for every player in the database.
        """
        if await self.casino_is_global():
            for player in await self.config.all_users():
                user = discord.Object(id=player)
                await self.config.user(user).Cooldowns.clear()
            msg = ("{0.name} ({0.id}) reset all global cooldowns.").format(ctx.author)
        else:
            for player in await self.config.all_members(ctx.guild):
                user = discord.Object(id=player)
                await self.config.member(user).Cooldowns.clear()
            msg = ("{0.name} ({0.id}) reset all cooldowns on {1.name}.").format(ctx.author, ctx.guild)

        await ctx.send(msg)

    async def change_mode(self, mode):
        """

        :param mode: String, must be local or global.
        :return: None

        Toggles how data is stored for casino between local and global.
        When switching modes, all perviously stored data will be deleted.
        """
        if mode == "global":
            await self.config.clear_all_members()
            await self.config.clear_all_guilds()
            await self.config.Settings.Global.set(True)
        else:
            await self.config.clear_all_users()
            await self.config.clear_all_globals()
            await self.config.Settings.Global.set(False)

    async def _update_cooldown(self, ctx, game, time):
        player_data = await self.get_data(ctx, player=ctx.author)
        await player_data.set_raw("Cooldowns", game, value=time)

    async def _get_player_membership(self, ctx, player):
        """

        :param ctx: context object
        :param player: user or member object
        :return: Membership name and a dictionary with the perks

        Performs a lookup on the user and the created memberhips for casino.
        If the user has a memberhip that was deleted, it will return the
        default basic membership. It will also set their new membership to the
        default.
        """
        basic = {"Reduction": 0, "Access": 0, "Color": "grey", "Bonus": 1}
        player_data = await self.get_data(ctx, player=player)
        name = await player_data.Membership.Name()
        if name == "Basic":
            return name, basic

        data = await self.get_data(ctx)
        memberships = await data.Memberships.all()
        try:
            return name, memberships[name]
        except KeyError:
            await player_data.Membership.set({"Name": "Basic", "Assigned": False})
            return "Basic", basic
