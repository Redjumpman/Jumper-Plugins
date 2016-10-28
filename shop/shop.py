# Shop System designed by Redjumpman
# This cog requires tabulate, and creates 1 json file and 2 folders
# Check out my wiki on my github page for more information
# https://github.com/Redjumpman/Jumper-Cogs

import uuid
import os
import time
import random
import discord
from operator import itemgetter
from discord.ext import commands
from .utils.dataIO import dataIO
from __main__ import send_cmd_help
from .utils import checks
from datetime import datetime
try:   # Check if Tabulate is installed
    from tabulate import tabulate
    tabulateAvailable = True
except:
    tabulateAvailable = False


class Shop:
    """Purchase server created items with credits."""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/JumperCogs/shop/system.json"
        self.system = dataIO.load_json(self.file_path)

    @commands.command(pass_context=True, no_pm=True)
    async def inventory(self, ctx):
        """Shows a list of items you have purchased"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        self.user_check(settings, user)
        if settings["Users"][user.id]["Inventory"]:
            column1 = [subdict["Item Name"] for subdict in settings["Users"][user.id]["Inventory"].values()]
            column2 = [subdict["Item Quantity"] for subdict in settings["Users"][user.id]["Inventory"].values()]
            m = sorted(list(zip(column1, column2)))
            t = tabulate(m, headers=["Item Name", "Item Quantity"])
            header = "```{}```".format(self.bordered("{}'s\nI N V E N T O R Y".format(user.name)))
            if settings["Config"]["Inventory Output Method"] == "Whisper":
                await self.bot.whisper("{}```\n{}```".format(header, t))
            else:
                await self.bot.say("{}```\n{}```".format(header, t))
        else:
            await self.bot.say("Your inventory is empty.")

    @commands.group(pass_context=True, no_pm=True)
    async def shop(self, ctx):
        """Shop Commands. Use !help Shop for other command groups"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @shop.command(name="version", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _version_lottery(self):
        """Shows the version of lottery cog you are running."""
        version = self.system["Version"]
        await self.bot.say("```Python\nYou are running Shop Cog version {}.```".format(version))

    @shop.command(name="redeem", pass_context=True, no_pm=True)
    async def _redeem_shop(self, ctx, *, itemname):
        """Sends a request to redeem an item"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        itemname = itemname.title()
        if itemname in settings["Users"][user.id]["Inventory"]:
            confirmation_number = str(uuid.uuid4())
            if self.redeem_handler(settings, user, itemname, confirmation_number):
                self.user_remove_item(settings, user, itemname)
                await self.notify_handler(settings, ctx, itemname, user, confirmation_number)
            else:
                await self.bot.say("You have too many items pending! You can only have 12 items pending at one time.")
        else:
            await self.bot.say("You do not have that item to redeem")

    @shop.command(name="add", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _add_shop(self, ctx, quantity: int, cost: int, *, itemname):
        """Adds items to the shop. Use 0 in quantity for infinite."""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        shop_name = settings["Config"]["Shop Name"]
        item_count = len(settings["Shop List"].keys())
        itemname = itemname.title()
        if item_count < 100:
            self.shop_item_add(settings, itemname, cost, quantity)
            item_count = len(settings["Shop List"].keys())
            await self.bot.say("```{} has been added to {} shop.\n{} items available for purchase in the store.```".format(itemname, shop_name, item_count))
        else:
            await self.bot.say("You can only have 100 items for sale in the store.\nPlease remove an item with {}shop remove to add more.".format(ctx.prefix))

    @shop.command(name="remove", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _remove_shop(self, ctx, *, itemname):
        """Removes an item from the shop."""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        shop_name = settings["Config"]["Shop Name"]
        itemname = itemname.title()
        if itemname in settings["Shop List"]:
            del settings["Shop List"][itemname]
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("```{} has been removed from {} shop.```".format(itemname, shop_name))
        else:
            await self.bot.say("There is no item with that name in the {} shop. Please check your spelling.".format(shop_name))

    @shop.command(name="buy", pass_context=True, no_pm=True)
    async def _buy_shop(self, ctx, *, itemname):
        """Purchase a shop item with credits."""
        server = ctx.message.server
        user = ctx.message.author
        settings = self.check_server_settings(server)
        self.user_check(settings, user)
        shop_name = settings["Config"]["Shop Name"]
        itemname = itemname.title()
        if settings["Config"]["Shop Open"]:
            if await self.shop_check(user, settings, itemname):
                if settings["Config"]["Pending Type"] == "Manual":
                    self.user_add_item(settings, user, itemname)
                    cost = self.discount_calc(settings, itemname)
                    self.shop_item_remove(settings, itemname)
                    await self.bot.say("```You have purchased {} for {} credits.\n{} has been added to your inventory.```".format(itemname, cost, itemname))
                else:
                    msgs = settings["Shop List"][itemname]["Buy Msg"]
                    if not msgs:
                        msg = "Oops! The admin forgot to set enough msgs for this item. Please contact them immediately."
                        await self.bot.say(msg)
                    else:
                        msg = random.choice(msgs)
                        msgs.remove(msg)
                        cost = self.discount_calc(settings, itemname)
                        self.shop_item_remove(settings, itemname)
                        await self.bot.whisper("You purchased {} for {} credits. Details for this item are:\n```{}```".format(itemname, cost, msg))
        else:
            await self.bot.say("The {} shop is currently closed.".format(shop_name))

    @shop.command(name="give", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _give_shop(self, ctx, user: discord.Member, *, itemname):
        """Adds an item to a users inventory. Item must be in the shop."""
        server = ctx.message.server
        author = ctx.message.author
        settings = self.check_server_settings(server)
        itemname = itemname.title()
        self.user_check(settings, user)
        if itemname in settings["Shop List"]:
            self.user_add_item(settings, user, itemname)
            await self.bot.say("{} was given {} by {}".format(user.mention, itemname, author.mention))
        else:
            await self.bot.say("No such item in the shop.")

    @shop.command(name="trash", pass_context=True, no_pm=True)
    async def _trash_shop(self, ctx, *, itemname):
        """Throws away an item in your inventory."""
        server = ctx.message.server
        user = ctx.message.author
        settings = self.check_server_settings(server)
        self.user_check(settings, user)
        itemname = itemname.title()
        if itemname in settings["Users"][user.id]["Inventory"]:
            await self.bot.say("Are you sure you wish to trash {}? Please think carefully as all instances of this item will be gone forever.".format(itemname))
            choice = await self.bot.wait_for_message(timeout=15, author=user)
            if choice is None:
                await self.bot.say("No response. Cancelling the destruction of {}.".format(itemname))
            elif choice.content.title() == "Yes":
                self.user_remove_item(settings, user, itemname)
                await self.bot.say("Removed all {}s from your inventory".format(itemname))
            elif choice.content.title() == "No":
                await self.bot.say("Cancelling the destruction of {}.".format(itemname))
            else:
                await self.bot.say("Improper response. Must choose Yes or No. Cancelling the destruction of {}.".format(itemname))
        else:
            await self.bot.say("You do not own this item.")

    @shop.command(name="gift", pass_context=True, no_pm=True)
    async def _gift_shop(self, ctx, user: discord.Member, *, itemname):
        """Send an item from your inventory to another user"""
        author = ctx.message.author
        server = ctx.message.server
        itemname = itemname.title()
        settings = self.check_server_settings(server)
        self.user_check(settings, author)
        self.user_check(settings, user)
        if author == user:
            await self.bot.say("This is awkward. You can't do this action with yourself.")
        else:
            await self.user_gifting(settings, user, author, itemname)

    @shop.command(name="trade", pass_context=True, no_pm=True)
    async def _trade_shop(self, ctx, user: discord.Member, *, tradeoffer: str):
        """Request a trade with another user"""
        author = ctx.message.author
        server = ctx.message.server
        tradeoffer = tradeoffer.title()
        settings = self.check_server_settings(server)
        self.user_check(settings, author)
        self.user_check(settings, user)
        if author == user:
            await self.bot.say("This is awkward. You can't do this action with yourself.")
        else:
            await self.user_trading(settings, user, author, tradeoffer)

    @shop.command(name="blocktrades", pass_context=True, no_pm=True)
    async def _blocktrades_shop(self, ctx):
        """Toggles blocking trade requests."""
        server = ctx.message.server
        user = ctx.message.author
        settings = self.check_server_settings(server)
        self.user_check(settings, user)
        if settings["Users"][user.id]["Block Trades"] is False:
            settings["Users"][user.id]["Block Trades"] = True
            await self.bot.say("You can no longer recieve trade requests.")
        else:
            settings["Users"][user.id]["Block Trades"] = False
            await self.bot.say("You can now accept trade requests.")
        dataIO.save_json(self.file_path, self.system)

    @shop.command(name="list", pass_context=True)
    async def _list_shop(self, ctx):
        """Shows a list of all the shop items."""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        shop_name = settings["Config"]["Shop Name"]
        column1 = [subdict["Item Name"] for subdict in settings["Shop List"].values()]
        column2 = [subdict["Quantity"] for subdict in settings["Shop List"].values()]
        column3 = [subdict["Item Cost"] for subdict in settings["Shop List"].values()]
        column4_raw = [subdict["Discount"] for subdict in settings["Shop List"].values()]
        column4 = [x + "%" for x in list(map(str, column4_raw))]
        if not column1:
            await self.bot.say("There are no items for sale in the shop.")
        else:
            data, header = self.table_builder(settings, column1, column2, column3, column4, shop_name)
            msg = await self.shop_table_split(user, data)
            await self.shop_list_output(settings, msg, header)

    @commands.group(pass_context=True, no_pm=True)
    async def setshop(self, ctx):
        """Shop configuration settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @setshop.command(name="ptype", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _ptype_setshop(self, ctx):
        """Change the pending method to automatic."""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        current_method = settings["Config"]["Pending Type"]
        if current_method == "Manual":
            await self.bot.say("Your current pending method is manual. Changing this to automatic requires you to set a msg for each item in the shop.\nI am not responsible for any lost information as a result of using this method.\n If you would still like to change your pending method, type 'I Agree'.")
            response = await self.bot.wait_for_message(timeout=15, author=user)
            if response is None:
                await self.bot.say("No response. Pending type will remain manual.")
            elif response.content.title() == "I Agree":
                settings["Config"]["Pending Type"] = "Automatic"
                dataIO.save_json(self.file_path, self.system)
                await self.bot.say("Pending type is now automatic. Please set a buy msg with your items with {}setshop buymsg.".format(ctx.prefix))
            else:
                await self.bot.say("Incorrect response. Pending type will stay manual.")
        elif current_method == "Automatic":
            settings["Config"]["Pending Type"] = "Manual"
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("Pending type changed to Manual")
        else:
            pass

    @setshop.command(name="buymsg", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _buymsg_setshop(self, ctx, *, itemname):
        """Set a msg for item redemption. """
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        itemname = itemname.title()
        if itemname in settings["Shop List"]:
            if len(settings["Shop List"][itemname]["Buy Msg"]) < settings["Shop List"][itemname]["Quantity"]:
                await self.bot.whisper("What msg do you want users to recieve when purchasing, {}?".format(itemname))
                response = await self.bot.wait_for_message(timeout=25, author=user)
                if response is None:
                    await self.bot.whisper("No response. No msg will be set.")
                else:
                    settings["Shop List"][itemname]["Buy Msg"].append(response.content)
                    dataIO.save_json(self.file_path, self.system)
                    await self.bot.whisper("Setting {}'s, buy msg to:\n{}".format(itemname, response.content))
            else:
                await self.bot.say("You can't set anymore buymsgs to {}, because there are only {} left".format(itemname, settings["Shop List"][itemname]["Quantity"]))
        else:
            await self.bot.say("That item is not in the shop.")

    @setshop.command(name="notify", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _notify_setshop(self, ctx):
        """Turn on shop pending notifications."""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if settings["Config"]["Shop Notify"]:
            settings["Config"]["Shop Notify"] = False
            await self.bot.say("Shop notifications are now OFF!")
        else:
            settings["Config"]["Shop Notify"] = True
            await self.bot.say("Shop notifcations are now ON!")
        dataIO.save_json(self.file_path, self.system)

    @setshop.command(name="role", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _role_sethop(self, ctx, *, rolename: str):
        """Set the server role that will recieve pending notifications"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        server_roles = [x.name for x in server.roles]
        if rolename in server_roles:
            settings["Config"]["Shop Role"] = rolename
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("Notify role set to {}. Server users assigned this role will be notifed when a item is redeemed.".format(rolename))
        else:
            role_output = ", ".join(server_roles).replace("@everyone,", "")
            await self.bot.say("{} is not a role on your server. The current roles on your server are:\n```{}```".format(rolename, role_output))

    @setshop.command(name="discount", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _discount_setshop(self, ctx, discount: int, *, itemname):
        """Discounts an item in the shop by a percentage. 0-99"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        itemname = itemname.title()
        if itemname in settings["Shop List"]:
            if discount == 0:
                settings["Shop List"][itemname]["Discount"] = ""
                dataIO.save_json(self.file_path, self.system)
                await self.bot.say("Remove discount from {}".format(itemname))
            elif discount > 0 and discount <= 99:
                settings["Shop List"][itemname]["Discount"] = discount
                dataIO.save_json(self.file_path, self.system)
                await self.bot.say("Adding {}% discount to item {}".format(discount, itemname))
            else:
                await self.bot.say("Discount must be 0 to 99.")
        else:
            await self.bot.say("That item is not in the shop listing.")

    @setshop.command(name="output", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _output_setshop(self, ctx, listing: str, output: str):
        """Sets the output to chat/whisper for inventory or shop"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        listing = listing.title()
        output = output.title()
        if listing == "Shop":
            if output == "Chat":
                settings["Config"]["Store Output Method"] = "Chat"
                dataIO.save_json(self.file_path, self.system)
                await self.bot.say("Store listings will now display in chat.")
            elif output == "Whisper" or output == "Pm" or output == "Dm":
                settings["Config"]["Store Output Method"] = "Whisper"
                dataIO.save_json(self.file_path, self.system)
                await self.bot.say("Store listings will now display in whisper.")
            else:
                await self.bot.say("Output must be Chat or Whisper/DM/PM.")
        elif listing == "Inventory":
            if output == "Chat":
                settings["Config"]["Inventory Output Method"] = "Chat"
                dataIO.save_json(self.file_path, self.system)
                await self.bot.say("Inventory will now display in chat.")
            elif output == "Whisper" or output == "Pm" or output == "Dm":
                settings["Config"]["Inventory Output Method"] = "Whisper"
                dataIO.save_json(self.file_path, self.system)
                await self.bot.say("Inventory will now display in whisper.")
            else:
                await self.bot.say("Output must be Chat or Whisper/DM/PM.")
        else:
            await self.bot.say("Must be Shop or Inventory.")

    @setshop.command(name="tradecd", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _tcd_setshop(self, ctx, cooldown: int):
        """Sets the cooldown timer for trading, in seconds."""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        settings["Config"]["Trade Cooldown"] = cooldown
        dataIO.save_json(self.file_path, self.system)
        await self.bot.say("Trading cooldown set to {}".format(self.time_format(cooldown)))

    @setshop.command(name="toggle", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _toggle_setshop(self, ctx):
        """Opens and closes the shop"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        shop_name = settings["Config"]["Shop Name"]
        if settings["Config"]["Shop Open"]:
            settings["Config"]["Shop Open"] = False
            await self.bot.say("The {} shop is now closed.".format(shop_name))
        else:
            settings["Config"]["Shop Open"] = True
            await self.bot.say("{} shop is now open for business!".format(shop_name))
        dataIO.save_json(self.file_path, self.system)

    @setshop.command(name="sorting", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _sort_setshop(self, ctx, choice: str):
        """Changes the sorting method for shop listings. Alphabetical, Lowest, Highest"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        choice = choice.title()
        if choice == "Alphabetical":
            settings["Config"]["Sort Method"] = "Alphabet"
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("Changing sorting method to Alphabetical.")
        elif choice == "Lowest":
            settings["Config"]["Sort Method"] = "Lowest"
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("Setting sorting method to Lowest.")
        elif choice == "Highest":
            settings["Config"]["Sort Method"] = "Highest"
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("Setting sorting method to Highest.")
        else:
            await self.bot.say("Please choose Alphabet, Lowest, or Highest.")

    @setshop.command(name="name", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _name_setshop(self, ctx, *, name):
        """Renames the shop"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        settings["Config"]["Shop Name"] = name
        dataIO.save_json(self.file_path, self.system)
        await self.bot.say("I have renamed the shop to {}.".format(name))

    @commands.group(pass_context=True, no_pm=True)
    async def pending(self, ctx):
        """Pending list commands"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @pending.command(name="showall", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _showall_pending(self, ctx):
        """Shows entire pending list"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if settings["Pending"]:
            column1 = [subdict["Name"] for users in settings["Pending"] for subdict in settings["Pending"][users].values()]
            column2 = [subdict["Time Stamp"] for users in settings["Pending"] for subdict in settings["Pending"][users].values()]
            column3 = [subdict["Item"] for users in settings["Pending"] for subdict in settings["Pending"][users].values()]
            column4 = [subdict["Confirmation Number"] for users in settings["Pending"] for subdict in settings["Pending"][users].values()]
            column5 = [subdict["Status"] for users in settings["Pending"] for subdict in settings["Pending"][users].values()]
            data = list(zip(column2, column1, column3, column4, column5))
            if len(data) > 12:
                msg, msg2 = await self.table_split(user, data)
                await self.bot.say(msg)
                await self.bot.say(msg2)
            else:
                table = tabulate(data, headers=["Time Stamp", "Name", "Item", "Confirmation#", "Status"], numalign="left",  tablefmt="simple")
                await self.bot.say("```{}\n\n\nYou are viewing page 1 of 1. {} pending items```".format(table, len(data)))
        else:
            await self.bot.say("There are no pending items to show.")

    @pending.command(name="search", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _search_pending(self, ctx, method, number):
        """Search by user and userid or code and confirmation#"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if method.title() == "User":
            mobj = server.get_member(number)
            await self.check_user_pending(settings, mobj)
        elif method.title() == "Code":
            await self.search_code(settings, number)
        else:
            await self.bot.say("Method of search needs to be specified as user or code.")

    @pending.command(name="user", pass_context=True, no_pm=True)
    async def _user_pending(self, ctx):
        """Shows all of your pending items"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        await self.check_user_pending(settings, user)

    @pending.command(name="code", pass_context=True, no_pm=True)
    async def _code_pending(self, ctx, code):
        """Searches for a pending item by your confirmation code"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if user.id in settings["Pending"]:
            if code in settings["Pending"][user.id]:
                col1 = settings["Pending"][user.id][code]["Name"]
                col2 = settings["Pending"][user.id][code]["Time Stamp"]
                col3 = settings["Pending"][user.id][code]["Item"]
                col4 = settings["Pending"][user.id][code]["Confirmation Number"]
                col5 = settings["Pending"][user.id][code]["Status"]
                data = [(col2, col1, col3, col4, col5)]
                table = tabulate(data, headers=["Time Stamp", "Name", "Item", "Confirmation#", "Status"], numalign="left",  tablefmt="simple")
                await self.bot.say("```{}```".format(table))
            else:
                await self.bot.say("Could not find that code in your pending items.")
        else:
            await self.bot.say("You have no pending items.")

    @pending.command(name="clearall", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _clearall_pending(self, ctx):
        """Clears entire pending list"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        await self.bot.say("This commmand will clear the **entire** pending list. If you understand this, type Yes to continue or No to abort.")
        response = await self.bot.wait_for_message(timeout=15, author=user)
        if response is None:
            await self.bot.say("No response. Aborting pending purge.")
        elif response.content.title() == "No":
            await self.bot.say("Aborting pending purge.")
        elif response.content.title() == "Yes":
            settings["Pending"] = {}
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("Pending list deleted")
        else:
            await self.bot.say("unrecognized response. Aborting pending purge.")

    @pending.command(name="clear", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _clear_pending(self, ctx, method, number):
        """Clear single item or entire user list. user/code and id/confirmation#"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if method.title() == "User":
            await self.user_clear(settings, server, user, number)
        elif method.title() == "Code":
            await self.code_clear(settings, server, user, number)
        else:
            await self.bot.say("Method must be either user or code.")

    @pending.command(name="status", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _status_pending(self, ctx, code, status):
        """Changes the status of a pending item."""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if len(status) <= 10:
            userid = [subdict for subdict in settings["Pending"] if code in settings["Pending"][subdict]]
            if userid:
                settings["Pending"][userid][code]["Status"] = status
                await self.bot.say("The status for {}, has been changed to {}".format(code, status))
            else:
                await self.bot.say("The confirmation code you provided cannot be found.")
        else:
            await self.bot.say("Status must be 10 characters or less.")

    async def code_clear(self, settings, server, user, number):
        userid = [subdict for subdict in settings["Pending"] if number in settings["Pending"][subdict]]
        if userid:
            mobj = server.get_member(userid)
            await self.bot.say("Do you want to clear this pending item for {}?".format(mobj.name))
            response = await self.bot.wait_for_message(timeout=15, author=user)
            if response is None:
                await self.bot.say("Timeout response, cancelling clear command.")
            elif response.content.title() == "No":
                await self.bot.say("Cancelling clear command.")
            elif response.content.title() == "Yes":
                settings["Pending"][mobj.id].pop(number, None)
                await self.bot.say("Pending item {}, cleared for user {}".format(number, mobj.name))
            else:
                await self.bot.say("Incorrect response, cancelling clear command.")
        else:
            await self.bot.say("The confirmation code provided could not be found.")

    async def user_clear(self, settings, server, user, number):
        if number in settings["Pending"]:
            mobj = server.get_member(number)
            await self.bot.say("Do you want to clear all pending items for {}".format(mobj.name))
            response = await self.bot.wait_for_message(timeout=15, author=user)
            if response is None:
                await self.bot.say("Timeout response, cancelling clear command.")
            elif response.content.title() == "No":
                await self.bot.say("Cancelling clear command.")
            elif response.content.title() == "Yes":
                settings["Pending"].pop(number)
                await self.bot.say("Pending list cleared for user {}".format(mobj.name))
            else:
                await self.bot.say("Incorrect response, cancelling clear command.")
        else:
            await self.bot.say("Unable to find that userid in the pendingl list.")

    async def search_code(self, settings, code):
        userid = [subdict for subdict in settings["Pending"] if code in settings["Pending"][subdict]]
        if userid:
            col1 = settings["Pending"][userid][code]["Name"]
            col2 = settings["Pending"][userid][code]["Time Stamp"]
            col3 = settings["Pending"][userid][code]["Item"]
            col4 = settings["Pending"][userid][code]["Confirmation Number"]
            col5 = settings["Pending"][userid][code]["Status"]
            data = [(col1, col2, col3, col4, col5)]
            table = tabulate(data, headers=["Name", "Time Stamp", "Item", "Confirmation#", "Status"], numalign="left",  tablefmt="simple")
            await self.bot.say("```{}```".format(table))
        else:
            await self.bot.say("Could not find that confirmation number in the pending list.")

    async def check_user_pending(self, settings, user):
        try:
            if user.id in settings["Pending"]:
                column1 = [subdict["Name"] for subdict in settings["Pending"][user.id].values()]
                column2 = [subdict["Time Stamp"] for subdict in settings["Pending"][user.id].values()]
                column3 = [subdict["Item"] for subdict in settings["Pending"][user.id].values()]
                column4 = [subdict["Confirmation Number"] for subdict in settings["Pending"][user.id].values()]
                column5 = [subdict["Status"] for subdict in settings["Pending"][user.id].values()]
                data = list(zip(column2, column1, column3, column4, column5))
                table = tabulate(data, headers=["Time Stamp", "Name", "Item", "Confirmation#", "Status"], numalign="left",  tablefmt="simple")
                await self.bot.say("```{}```".format(table))
            else:
                await self.bot.say("There are no pending items for this user.")
        except AttributeError:
            await self.bot.say("You did not provide a valid user id.")

    async def shop_table_split(self, user, data):
        groups = [data[i:i+20] for i in range(0, len(data), 20)]
        pages = len(groups)
        await self.bot.say("There are {} pages of shop items. Which page would you like to display?".format(pages))
        response = await self.bot.wait_for_message(timeout=15, author=user)
        if response is None:
            page = 0
        else:
            try:
                page = int(response.content) - 1
                table = tabulate(groups[page], headers=["Item Name", "Item Quantity", "Item Cost", "Discount"], stralign="center", numalign="center")
                msg = "```{}``````Python\nYou are viewing page {} of {}. There are {} items available.```".format(table, page + 1, pages, len(data))
                return msg
            except ValueError:
                await self.bot.say("Sorry your response was not a correct number. Defaulting to page 1")
                page = 0
                table = tabulate(groups[page], headers=["Item Name", "Item Quantity", "Item Cost", "Discount"], stralign="center", numalign="center")
                msg = "```{}``````Python\nYou are viewing page 1 of {}. There are {} items available.```".format(table, pages, len(data))
                return msg

    async def shop_list_output(self, settings, message, header):
        if settings["Config"]["Store Output Method"] == "Whisper":
            await self.bot.whisper("{}\n{}".format(header, message))
        elif settings["Config"]["Store Output Method"] == "Chat":
            await self.bot.say("{}\n{}".format(header, message))
        else:
            await self.bot.whisper("{}\n{}".format(header, message))

    async def table_split(self, user, data):
        groups = [data[i:i+12] for i in range(0, len(data), 12)]
        pages = len(groups)
        await self.bot.say("There are {} pages of pending items. Which page would you like to display?".format(pages))
        response = await self.bot.wait_for_message(timeout=15, author=user)
        if response is None:
            page = 0
        else:
            try:
                page = int(response.content) - 1
                table = tabulate(groups[page], headers=["Time Stamp", "Name", "Item", "Confirmation#", "Status"], numalign="left",  tablefmt="simple")
                msg = "```{}``````Python\nYou are viewing page {} of {}. {} pending items```".format(table, page + 1, pages, len(data))
                return msg
            except ValueError:
                await self.bot.say("Sorry your response was not a number. Defaulting to page 1")
                page = 0
                table = tabulate(groups[page], headers=["Time Stamp", "Name", "Item", "Confirmation#", "Status"], numalign="left",  tablefmt="simple")
                msg = "```{}``````Python\nYou are viewing page 1 of {}. {} pending items```".format(table, pages, len(data))
                return msg

    async def check_cooldowns(self, settings, userid):
        if abs(settings["Users"][userid]["Trade Cooldown"] - int(time.perf_counter())) >= settings["Config"]["Trade Cooldown"]:
            settings["Users"][userid]["Trade Cooldown"] = int(time.perf_counter())
            dataIO.save_json(self.file_path, self.system)
            return True
        elif settings["Users"][userid]["Trade Cooldown"] == 0:
            settings["Users"][userid]["Trade Cooldown"] = int(time.perf_counter())
            dataIO.save_json(self.file_path, self.system)
            return True
        else:
            s = abs(settings["Users"][userid]["Trade Cooldown"] - int(time.perf_counter()))
            seconds = abs(s - settings["Config"]["Trade Cooldown"])
            await self.bot.say("You must wait before trading again. You still have: {}".format(self.time_format(seconds)))
            return False

    async def notify_handler(self, settings, ctx, itemname, user, confirmation_number):
        if settings["Config"]["Shop Notify"]:
            role = settings["Config"]["Shop Role"]
            names = self.role_check(role, ctx)
            destinations = [m for m in ctx.message.server.members if m.name in names]
            for destination in destinations:
                await self.bot.send_message(destination, "{} was added to the pending list by {}.\nConfirmation#: {}.\nUser ID: {} ".format(itemname, user.name, confirmation_number, user.id))
            await self.bot.say("""```{} has been added to pending list. Your confirmation number is {}.
                               \nYou can check the status of your pending items, use the command {}pending check```""".format(itemname, confirmation_number, ctx.prefix))
        else:
            await self.bot.say("""```{} has been added to pending list. Your confirmation number is {}.
                               \nYou can check the status of your pending items, use the command {}pending check```""".format(itemname, confirmation_number, ctx.prefix))

    async def user_trading(self, settings, user, author, itemname):
        if not settings["Users"][user.id]["Block Trades"]:
            if itemname in settings["Users"][author.id]["Inventory"]:
                if await self.check_cooldowns(settings, author.id):
                    await self.bot.say("{} requests a trade with {}. Do you wish to trade for {}?".format(author.mention, user.mention, itemname))
                    answer = await self.bot.wait_for_message(timeout=15, author=user)
                    if answer:
                        user_response = await self.user_trade_reply(settings, user, author, answer)
                        if user_response:
                            author_response, offer = await self.author_trade_reply(settings, user, author, user_response)
                            if author_response:
                                await self.trade_conclusion(settings, user, author, offer, itemname, author_response)
                            else:
                                await self.bot.say("No response. Cancelling trade with {}.".format(user.name))
                        else:
                            await self.bot.say("No response. Cancelling trade with {}.".format(user.name))
                    else:
                        await self.bot.say("No response. Cancelling trade with {}.".format(user.name))
            else:
                await self.bot.say("This item is not in your inventory.")
        else:
            await self.bot.say("This user is currently blocking trade requests.")

    async def user_trade_reply(self, settings, user, author, answer):
        if answer.content.title() == "No":
            await self.bot.say("{} has rejected your trade.".format(user.name))
        elif answer.content.title() == "Yes":
            await self.bot.say("Please say which item you would like to trade.")
            response = await self.bot.wait_for_message(timeout=15, author=user)
            return response

    async def author_trade_reply(self, settings, user, author, response):
        if not response:
            await self.bot.say("No response. Cancelling trade with {}.".format(user.name))
        elif response.content.title() in settings["Users"][user.id]["Inventory"]:
            await self.bot.say("{} has offered {}, do you wish to accept this trade, {}?".format(user.mention, response.content, author.mention))
            reply = await self.bot.wait_for_message(timeout=15, author=author)
            return reply, response.content

    async def trade_conclusion(self, settings, user, author, tradeoffer, itemname, reply):
        if reply.content.title() == "No" or reply.content.title() == "Cancel":
            await self.bot.say("Trade Rejected. Cancelling trade.")
        elif reply.content.title() == "Yes" or reply.content.title() == "Accept":
            self.user_add_item(settings, author, tradeoffer)
            self.user_add_item(settings, user, itemname)
            self.user_remove_item(settings, author, itemname)
            self.user_remove_item(settings, author, tradeoffer)
            await self.bot.say("Trading items... {} recieved {}, and {} recieved {}.".format(author.mention, tradeoffer, user.mention, tradeoffer))
            await self.bot.say("Trade complete.")

    async def user_gifting(self, settings, user, author, itemname):
        if itemname in settings["Users"][author.id]["Inventory"]:
            self.user_add_item(settings, user, itemname)
            self.user_remove_item(settings, author, itemname)
            await self.bot.say("{} just sent a gift({}) to {}.".format(author.mention, itemname, user.mention))
        else:
            await self.bot.say("This item is not in your inventory.")

    async def shop_check(self, user, settings, itemname):
        if itemname in settings["Shop List"]:
            cost = self.discount_calc(settings, itemname)
            if await self.subtract_credits(user, cost):
                return True
            else:
                return False
        else:
            await self.bot.say("This item is not in the shop.")
            return False

    async def subtract_credits(self, user, number):
        bank = self.bot.get_cog("Economy").bank
        if bank.account_exists(user):
            if bank.can_spend(user, number):
                bank.withdraw_credits(user, number)
                return True
            else:
                await self.bot.say("You do not have enough credits in your account.")
                return False
        else:
            await self.bot.say("You do not have a bank account.")
            return False

    def role_check(self, role, ctx):
        return [m.name for m in ctx.message.server.members if role.lower() in [str(r).lower() for r in m.roles] and str(m.status) != "offline"]

    def bordered(self, text):
        lines = text.splitlines()
        width = max(len(s) + 9 for s in lines)
        res = ["+" + "-" * width + '+']
        for s in lines:
            res.append("│" + (s + " " * width)[:width] + "│")
        res.append("+" + "-" * width + "+")
        return "\n".join(res)

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

    def redeem_handler(self, settings, user, itemname, confirmation_number):
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if user.id in settings["Pending"]:
            if len(settings["Pending"][user.id].keys()) <= 12:
                settings["Pending"][user.id][confirmation_number] = {"Name": user.name,
                                                                     "Confirmation Number": confirmation_number,
                                                                     "Time Stamp": time_now,
                                                                     "Item": itemname,
                                                                     "Status": "Pending"}
                dataIO.save_json(self.file_path, self.system)
                return True
            else:
                return False
        else:
            settings["Pending"][user.id] = {}
            settings["Pending"][user.id][confirmation_number] = {"Name": user.name,
                                                                 "Confirmation Number": confirmation_number,
                                                                 "Time Stamp": time_now,
                                                                 "Item": itemname,
                                                                 "Status": "Pending"}
            dataIO.save_json(self.file_path, self.system)
            return True

    def user_check(self, settings, user):
        if user.id in settings["Users"]:
            pass
        else:
            settings["Users"][user.id] = {"Inventory": {}, "Block Trades": False, "Trade Cooldown": 0, "Member": False}
            dataIO.save_json(self.file_path, self.system)

    def discount_calc(self, settings, itemname):
        base_cost = settings["Shop List"][itemname]["Item Cost"]
        discount = settings["Shop List"][itemname]["Discount"]
        if discount > 0:
            discount_amount = base_cost * discount / 100
            true_cost = round(base_cost - discount_amount)
            return true_cost
        else:
            return base_cost

    def table_builder(self, settings, column1, column2, column3, column4, shop_name):
        header = "```"
        header += self.bordered(shop_name + " Store Listings")
        header += "```"
        m = list(zip(column1, column2, column3, column4))
        if settings["Config"]["Sort Method"] == "Alphabet":
            m = sorted(m)
            return m, header
        elif settings["Config"]["Sort Method"] == "Highest":
            m = sorted(m, key=itemgetter(2), reverse=True)
            return m, header
        elif settings["Config"]["Sort Method"] == "Lowest":
            m = sorted(m, key=itemgetter(2))
            return m, header

    def shop_item_add(self, settings, itemname, cost, quantity):
        if quantity == 0:
            settings["Shop List"][itemname] = {"Item Name": itemname, "Item Cost": cost,
                                               "Quantity": "∞", "Discount": 0,
                                               "Members Only": "No", "Buy Msg": []}
        else:
            settings["Shop List"][itemname] = {"Item Name": itemname, "Item Cost": cost,
                                               "Quantity": quantity, "Discount": 0,
                                               "Members Only": "No", "Buy Msg": []}
        dataIO.save_json(self.file_path, self.system)

    def shop_item_remove(self, settings, itemname):
        if settings["Shop List"][itemname]["Quantity"] == "∞":
            pass
        elif settings["Shop List"][itemname]["Quantity"] > 1:
            settings["Shop List"][itemname]["Quantity"] -= 1
            dataIO.save_json(self.file_path, self.system)
        else:
            settings["Shop List"].pop(itemname, None)
            dataIO.save_json(self.file_path, self.system)

    def user_add_item(self, settings, user, itemname):
        if itemname in settings["Users"][user.id]["Inventory"]:
            settings["Users"][user.id]["Inventory"][itemname]["Item Quantity"] += 1
        else:
            settings["Users"][user.id]["Inventory"][itemname] = {"Item Name": itemname, "Item Quantity": 1}
        dataIO.save_json(self.file_path, self.system)

    def user_remove_item(self, settings, user, itemname):
        if itemname in settings["Users"][user.id]["Inventory"]:
            if settings["Users"][user.id]["Inventory"][itemname]["Item Quantity"] > 1:
                settings["Users"][user.id]["Inventory"][itemname]["Item Quantity"] -= 1
            else:
                settings["Users"][user.id]["Inventory"].pop(itemname, None)
            dataIO.save_json(self.file_path, self.system)

    def check_server_settings(self, server):
        if server.id not in self.system["Servers"]:
            self.system["Servers"][server.id] = {"Shop List": {},
                                                 "Users": {},
                                                 "Pending": {},
                                                 "Config": {"Shop Name": "Jumpman's",
                                                            "Shop Open": True,
                                                            "Shop Notify": False,
                                                            "Trade Cooldown": 30,
                                                            "Store Output Method": "Chat",
                                                            "Inventory Output Method": "Chat",
                                                            "Notify Role": "Shopkeeper",
                                                            "Sort Method": "Alphabet",
                                                            "Member Discount": None,
                                                            "Pending Type": "Manual"}
                                                 }
            dataIO.save_json(self.file_path, self.system)
            print("Creating default Shop settings for Server: {}".format(server.name))
            path = self.system["Servers"][server.id]
            return path
        else:
            path = self.system["Servers"][server.id]
            return path


def check_folders():
    if not os.path.exists("data/JumperCogs"):   # Checks for parent directory for all Jumper cogs
        print("Creating JumperCogs default directory")
        os.makedirs("data/JumperCogs")

    if not os.path.exists("data/JumperCogs/shop"):
        print("Creating JumperCogs shop folder")
        os.makedirs("data/JumperCogs/shop")


def check_files():
    default = {"Servers": {},
               "Version": "2.1"
               }

    f = "data/JumperCogs/shop/system.json"
    if not dataIO.is_valid_json(f):
        print("Creating default shop system.json...")
        dataIO.save_json(f, default)
    else:
        current = dataIO.load_json(f)
        if current["Version"] != default["Version"]:
            print("Updating Shop Cog from version {} to version {}".format(current["Version"], default["Version"]))
            current["Version"] = default["Version"]
            dataIO.save_json(f, current)


def setup(bot):
    check_folders()
    check_files()
    if tabulateAvailable:
        bot.add_cog(Shop(bot))
    else:
        raise RuntimeError("You need to run 'pip3 install tabulate'")
