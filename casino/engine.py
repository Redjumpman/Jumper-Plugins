# Standard Library
import calendar
from functools import wraps

# Casino
from typing import Optional

from redbot.core.utils.chat_formatting import humanize_number

from . import utils
from .data import Database

# Red
from redbot.core import bank
from redbot.core.errors import BalanceTooHigh
from redbot.core.i18n import Translator

# Discord
import discord

_ = Translator("Casino", __file__)


def game_engine(name=None, choice=None, choices=None):
    def wrapper(coro):
        @wraps(coro)
        async def wrapped(*args, **kwargs):
            try:
                user_choice = args[3]
            except IndexError:
                user_choice = None
            engine = GameEngine(name, user_choice, choice, args[1], args[2])
            if await engine.check_conditions():
                result = await coro(*args, **kwargs)
                await engine.game_teardown(result)

        return wrapped

    return wrapper


class GameEngine(Database):
    """A class that handles setup and teardown for games.

        This is a helper class to make games easier to create games and to
        provide a level of consistency. This class is only to be used
        in conjunction with the game_engine decorator.

        You only need to specify the name, and depending on the game, a choice or
        a list of choices to choose from. The decorater will obtain the rest of the
        attributes.

        Attributes
        -----------
        game: str
            The name of the game.
        choice: str
            The decision the player chose for the game. When a decision is not
            required, leave it None.
        choices: list
            A list of choices the player must pick from. If a list of choices is not
            required, leave it None.
        ctx: object
            The Red context object necessary for sending/waiting for messages.
        player: object
            User or member object necessary for interacting with the player.
        guild: object
            The guild object from the Red Context object. This is used to pull data
            from config.
        bet: int
            The amount the player has wagered.

    """

    __slots__ = ("game", "choice", "choices", "ctx", "bet", "player", "guild")

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
        """

        Performs all the necessary checks for a game. Every game must validate under these specific
        checks. The following conditions are checked:

        - Checking to see if the casino is open
        - Checking to see if the game is open
        - Checking to see if the player has a high enough access level to play the game.
        - Validating that the player's choice is in the list of declared choices.
        - Checking that the bet is within the range of the set min and max.
        - Checking to see that has enough currency in the bank account to cover the bet.
        - Checking to see if the game is on cooldown.

        Cooldowns must be checked last so that the game doesn't trigger a cooldown if another
        condition has failed.


        """
        settings, player_data = await super().get_all(self.ctx, self.player)
        access = self.access_calculator(settings["Memberships"], player_data["Membership"]["Name"])

        if not settings["Settings"]["Casino_Open"]:
            error = _("The Casino is closed.")

        elif not settings["Games"][self.game]["Open"]:
            error = _("{} is closed.".format(self.game))

        elif settings["Games"][self.game]["Access"] > access:
            error = _(
                "{} requires an access level of {}. Your current access level is {}. Obtain "
                "a higher membership to play this game."
            ).format(self.game, settings["Games"][self.game]["Access"], access)

        elif self.choices is not None and self.choice not in self.choices:
            error = _("Incorrect response. Accepted responses are:\n{}.").format(utils.fmt_join(self.choices))

        elif not self.bet_in_range(
            settings["Games"][self.game]["Min"], settings["Games"][self.game]["Max"]
        ):
            error = _(
                "Your bet must be between "
                "{} and {}.".format(
                    settings["Games"][self.game]["Min"], settings["Games"][self.game]["Max"]
                )
            )

        elif not await bank.can_spend(self.player, self.bet):
            error = _("You do not have enough credits to cover the bet.")

        else:
            error = await self.check_cooldown(settings["Games"][self.game], player_data)

        if error:
            await self.ctx.send(error)
            return False
        else:
            await bank.withdraw_credits(self.player, self.bet)
            await self.update_stats(stat="Played")
            return True

    async def update_stats(self, stat: str):
        """

        :param stat: string
            Must be Played or Won
        :return: None

        Updates either a player's win or played stat.
        """
        instance = await self.get_data(self.ctx, player=self.player)
        current = await instance.get_raw(stat, self.game)
        await instance.set_raw(stat, self.game, value=current + 1)

    async def check_cooldown(self, game_data, player_data):
        """

        :param game_data: Dictionary
            Contains all the data pertaining to a particular game.
        :param player_data: Object
            User or member Object
        :return: String or None
            Returns a string when a cooldown is remaining on a game, otherwise it will
            return None

        Checks the time a player last played a game, and compares it with the set cooldown
        for that game. If a user is still on cooldown, then a string detailing the time
        remaining will be returned. Otherwise this will update their cooldown, and return None.

        """
        user_time = player_data["Cooldowns"][self.game]
        now = calendar.timegm(self.ctx.message.created_at.utctimetuple())
        base = game_data["Cooldown"]
        membership = await super()._get_player_membership(self.ctx, self.player)
        reduction = membership[1]["Reduction"]
        if now >= user_time - reduction:
            await super()._update_cooldown(self.ctx, self.game, now + base)
        else:
            seconds = int((user_time + reduction - now))
            remaining = utils.time_formatter(seconds)
            msg = _("{} is still on a cooldown. You still have: {} remaining.").format(self.game, remaining)
            return msg

    async def game_teardown(self, result):
        data = await super().get_data(self.ctx)
        settings = await data.all()
        message_obj: Optional[discord.Message]

        win, amount, msg, message_obj = result

        if not win:
            embed = await self.build_embed(msg, settings, win, total=amount, bonus="(+0)")
            if (not await self.old_message_cache.get_guild(self.ctx.guild)) and message_obj:
                return await message_obj.edit(content=self.player.mention, embed=embed)
            else:
                return await self.ctx.send(self.player.mention, embed=embed)

        player_data = await super().get_data(self.ctx, player=self.player)
        await self.update_stats(stat="Won")
        if self.limit_check(settings, amount):
            embed = await self.build_embed(msg, settings, win, total=amount, bonus="(+0)")
            return await self.limit_handler(
                embed,
                amount,
                player_data,
                settings["Settings"]["Payout_Limit"],
                message=message_obj,
            )

        total, bonus = await self.deposit_winnings(amount, player_data, settings)
        embed = await self.build_embed(msg, settings, win, total=total, bonus=bonus)
        if (not await self.old_message_cache.get_guild(self.ctx.guild)) and message_obj:
            return await message_obj.edit(content=self.player.mention, embed=embed)
        else:
            return await self.ctx.send(self.player.mention, embed=embed)

    async def limit_handler(self, embed, amount, player_instance, limit, message):
        await player_instance.Pending_Credits.set(int(amount))

        if (not await self.old_message_cache.get_guild(self.ctx.guild)) and message:
            await message.edit(content=self.player.mention, embed=embed)
        else:
            await self.ctx.send(self.player.mention, embed=embed)
        msg = _(
            "{} Your winnings exceeded the maximum credit limit allowed ({}). The amount "
            "of {} credits will be pending on your account until reviewed. Until an "
            "Administrator or higher authority has released the pending currency, "
            "**DO NOT** attempt to place a bet that will exceed the payout limit. You "
            "may only have **ONE** pending payout at a "
            "time."
        ).format(self.player.name, limit, amount)

        await self.player.send(msg)

    async def deposit_winnings(self, amount, player_instance, settings):
        multiplier = settings["Games"][self.game]["Multiplier"]
        if self.game == "Allin" or self.game == "Double":
            try:
                await bank.deposit_credits(self.player, amount)
                return amount, "(+0)"
            except BalanceTooHigh as e:
                return await bank.set_balance(self.player, e.max_balance), "(+0)"

        initial = round(amount * multiplier)
        total, amt, msg = await self.calculate_bonus(initial, player_instance, settings)
        try:
            await bank.deposit_credits(self.player, total)
        except BalanceTooHigh as e:
            await bank.set_balance(self.player, e.max_balance)
        return total, msg

    def bet_in_range(self, minimum, maximum):
        if self.game == "Allin":
            return True

        if minimum <= self.bet <= maximum:
            return True
        else:
            return False

    async def build_embed(self, msg, settings, win, total, bonus):
        balance = await bank.get_balance(self.player)
        currency = await bank.get_currency_name(self.guild)
        bal_msg = _("**Remaining Balance:** {} {}").format(humanize_number(balance), currency)
        embed = discord.Embed()
        embed.title = _("{} Casino | {}").format(settings["Settings"]["Casino_Name"], self.game)

        if isinstance(msg, discord.Embed):
            for field in msg.fields:
                embed.add_field(**field.__dict__)
        else:
            embed.description = msg

        if win:
            embed.colour = 0x00FF00
            end = _("Congratulations, you just won {} {} {}!\n{}").format(
                humanize_number(total), currency, bonus, bal_msg
            )
        else:
            embed.colour = 0xFF0000
            end = _("Sorry, you didn't win anything.\n{}").format(bal_msg)
        embed.add_field(name="-" * 65, value=end)
        return embed

    @staticmethod
    def access_calculator(memberships, user_membership):
        if user_membership == "Basic":
            return 0

        try:
            access = memberships[user_membership]["Access"]
        except KeyError:
            return 0
        else:
            return access

    @staticmethod
    async def calculate_bonus(amount, player_instance, settings):
        membership = await player_instance.Membership.Name()
        try:
            bonus_multiplier = settings["Memberships"][membership]["Bonus"]
        except KeyError:
            bonus_multiplier = 1
        total = round(amount * bonus_multiplier)
        bonus = total - amount
        return total, amount, "(+{})".format(humanize_number(bonus) if bonus_multiplier > 1 else 0)

    @staticmethod
    def limit_check(settings, amount):
        if settings["Settings"]["Payout_Switch"]:
            if amount > settings["Settings"]["Payout_Limit"]:
                return True
            else:
                return False
        else:
            return False
