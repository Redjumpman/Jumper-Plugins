#  Shop.py was created by Redjumpman for Redbot
#  This will create a data folder with 3 JSON files and 1 logger
#  The logger will contain information for admin use
import uuid
import discord
import os
import logging
import time
from operator import itemgetter
from discord.ext import commands
from .utils.dataIO import fileIO
from __main__ import send_cmd_help
from .utils import checks
from datetime import datetime
try:   # Check if Tabulate is installed
    from tabulate import tabulate
    tabulateAvailable = True
except:
    tabulateAvailable = False


class Shop:
    """Allows you to purchase items created by the Admins with your credits"""
    # We have to define all the different files were going to load and save
    def __init__(self, bot):
        self.bot = bot
        self.players = fileIO("data/shop/players.json", "load")
        self.shopsys = fileIO("data/shop/shop.json", "load")
        self.pending = fileIO("data/shop/pending.json", "load")
        self.config = fileIO("data/shop/config.json", "load")

    @commands.command(pass_context=True, no_pm=True)
    async def inventory(self, ctx):
        """Shows a list of items you have purchased"""
        user = ctx.message.author
        if user.id in self.players:
            if not self.players[user.id]["Inventory"]:
                await self.bot.say("You have not purchased any items for me to display")
            else:
                    column1 = [subdict["Item Name"] for subdict in self.players[user.id]["Inventory"].values()]
                    column2 = [subdict["Item Quantity"] for subdict in self.players[user.id]["Inventory"].values()]
                    m = list(zip(column1, column2))
                    m.sort()
                    t = tabulate(m, headers=["Item Name", "Item Quantity"])
                    header = "```"
                    header += self.bordered("I N V E N T O R Y")
                    header += "```"
                    if self.config["Inventory Output"] == "Whisper":
                        await self.bot.whisper(header + "```\n" + t + "```")
                    elif self.config["Inventory Output"] == "Chat":
                        await self.bot.say(header + "```\n" + t + "```")
                    else:
                        await self.bot.whisper(header + "```\n" + t + "```")
        else:
            await self.bot.say("You need to join the shop. Type use the `shop join` command.")

    @commands.group(pass_context=True, no_pm=True)
    async def shop(self, ctx):
        """Shop Commands. Use !help Shop for other command groups"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    # We want to seperate the store so it doesn't have a shop prefix
    @shop.command(name="list", pass_context=True)
    async def _list_shop(self, ctx):
        """Shows a list of items that can be purchased"""
        shop_name = self.config["Shop Name"]
        column1 = [subdict["Item Name"] for subdict in self.shopsys.values()]
        column2 = [subdict["Item Cost"] for subdict in self.shopsys.values()]
        print(str(column1))
        if not column1:
            await self.bot.say("There are no items for sale in the shop.")
        else:
            m = list(zip(column1, column2))
            if self.config["Sort Method"] == "Alphabet":
                m = sorted(m)
            elif self.config["Sort Method"] == "Lowest":
                m = sorted(m, key=itemgetter(1), reverse=True)
            elif self.config["Sort Method"] == "Highest":
                m = sorted(m, key=itemgetter(1))
            t = tabulate(m, headers=["Item Name", "Item Cost"])
            header = "```"
            header += self.bordered(shop_name + " Store Listings")
            header += "```"
            if len(t) > 2000:
                first_msg1, first_msg2 = column1[::2], column1[1::2]
                second_msg1, second_msg2 = column2[::2], column2[1::2]
                m1 = list(zip(first_msg1, second_msg1))
                m2 = list(zip(first_msg2, second_msg2))
                if self.config["Sort Method"] == "Alphabet":
                    sorted(m1)
                    sorted(m2)
                elif self.config["Sort Method"] == "Lowest":
                    m1 = sorted(m1, key=itemgetter(1))
                    m2 = sorted(m2, key=itemgetter(1))
                elif self.config["Sort Method"] == "Highest":
                    m1 = sorted(m1, key=itemgetter(1), reverse=True)
                    m2 = sorted(m2, key=itemgetter(1), reverse=True)
                t1 = tabulate(m1, headers=["Item Name", "Item Cost"])
                t2 = tabulate(m2, headers=["Item Name", "Item Cost"])
                if self.config["Store Output"] == "Whisper":
                    await self.bot.whisper(header + "```\n" + t1 + "```")
                    await self.bot.whisper("```" + t2 + "```")
                elif self.config["Store Output"] == "Chat":
                    await self.bot.say(header + "```\n" + t1 + "```")
                    await self.bot.say("```" + t2 + "```")
                else:
                    await self.bot.whisper(header + "```\n" + t1 + "```")
                    await self.bot.whisper("```" + t2 + "```")
            else:
                if self.config["Store Output"] == "Whisper":
                    await self.bot.whisper(header + "```\n" + t + "```")
                elif self.config["Store Output"] == "Chat":
                    await self.bot.say(header + "```\n" + t + "```")
                else:
                    await self.bot.whisper(header + "```\n" + t + "```")

    @shop.command(name="add", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _add_shop(self, ctx, cost: int, *, itemname):
        """Adds an item to the shop list. Max 100 items"""
        if self.config["Shop Items"] < 100:
            self.config["Shop Items"] += 1
            fileIO("data/shop/config.json", "save", self.config)
            shop_name = self.config["Shop Name"]
            self.shopsys[itemname] = {"Item Name": itemname, "Item Cost": cost}
            fileIO("data/shop/shop.json", "save", self.shopsys)
            item_count = len(list(self.shopsys.keys()))
            await self.bot.say("```{} has been added to {} shop for purchase.\nThere is now {} items for sale in the store.```".format(itemname, shop_name, str(item_count)))
        else:
            await self.bot.say("You can only have 100 items for sale in the store.\nDelete an item to add more.")

    @shop.command(name="remove", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _remove_shop(self, ctx, *, itemname):
        """Removes an item from the shop list"""
        shop_name = self.config["Shop Name"]
        if itemname in self.shopsys:
            self.config["Shop Items"] -= 1
            fileIO("data/shop/config.json", "save", self.config)
            del self.shopsys[itemname]
            fileIO("data/shop/shop.json", "save", self.shopsys)
            await self.bot.say("```{} has been removed from {} shop.```".format(itemname, shop_name))
        else:
            await self.bot.say("That item is not in {}'s store listings".format(shop_name))

    @shop.command(name="redeem", pass_context=True, no_pm=True)
    async def _redeem_shop(self, ctx, *, itemname):
        """Sends a request to redeem an item"""
        user = ctx.message.author
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        role = self.config["Shop Role"]
        if self.inventory_item_check(user.id, itemname):
            confirmation_number = str(uuid.uuid4())
            self.pending[confirmation_number] = {"Confirmation Number": confirmation_number,
                                                 "Time Stamp": time_now,
                                                 "Name": user.name,
                                                 "ID": user.id,
                                                 "Item": itemname}
            fileIO("data/shop/pending.json", "save", self.pending)
            self.inventory_remove(user.id, itemname)
            if self.config["Shop Notify"]:
                names = self.role_check(role, ctx)
                destinations = [m for m in ctx.message.server.members if m.name in names]
                for destination in destinations:
                    await self.bot.send_message(destination, "{} was added to the pending list by {}.".format(itemname, user.name))
                await self.bot.say("```{} has been added to pending list. Your confirmation number is {}.```".format(itemname, confirmation_number))
            await self.bot.say("```{} has been added to pending list. Your confirmation number is {}.```".format(itemname, confirmation_number))
        else:
            await self.bot.say("You do not have that item to redeem")

    @shop.command(name="buy", pass_context=True, no_pm=True)
    async def _buy_shop(self, ctx, *, itemname):
        """Buy an item from the store list"""
        shop_name = self.config["Shop Name"]
        user = ctx.message.author
        if self.config["Shop Open"]:
            if self.inventory_check(user.id):
                if itemname in self.shopsys:
                    points = self.shopsys[itemname]["Item Cost"]
                    if self.account_check(user):
                        if self.enough_points(user, points):
                            points = self.shopsys[itemname]["Item Cost"]
                            self.inventory_add(user.id, itemname)
                            bank = self.bot.get_cog("Economy").bank
                            bank.withdraw_credits(user, points)
                            await self.bot.say("```You have purchased a {} for {} credits.\n{} has been added to your inventory.```".format(itemname, str(points), itemname))
                        else:
                            await self.bot.say("You don't have enough credits to purchase this item.")
                    else:
                        await self.bot.say("You do not have a bank account.")
                else:
                    await self.bot.say("This item is not in the shop.")
            else:
                await self.bot.say("You need to join the {} shop to purchase items. Example: !shop join".format(shop_name))
        else:
            await self.bot.say("{} shop is currently closed.".format(shop_name))

    @shop.command(name="gift", pass_context=True, no_pm=True)
    async def _gift_shop(self, ctx, user: discord.Member, *, itemname):
        """Send a gift in your inventory to another member"""
        author = ctx.message.author
        if author == user:
            await self.bot.say("You can't give an item to yourself.")
            return
        if len(itemname) < 0:
            await self.bot.say("You need to tell me what you want to transfer.")
            return
        if user.id in self.players:
            if self.inventory_item_check(author.id, itemname):
                if self.inventory_item_amount(author.id, itemname):
                    nametwo = self.shopsys[itemname]["Item Name"]
                    self.inventory_remove(author.id, itemname)
                    self.inventory_add(user.id, itemname)
                    logger.info("{}({}) gifted a {} item to {}({})".format(author.name, author.id, itemname, user.name, user.id))
                    await self.bot.say("```I have gifted {} to {}'s inventory```".format(nametwo, user.name))
                else:
                    await self.bot.say("You currently don't own any of these.")
            else:
                await self.bot.say("You do not own this shop item.")
        else:
            shop_name = self.config["Shop Name"]
            await self.bot.say("I cant find a user with that name." +
                               " Check to see if that user has joined {} shop. They need to type !shop join before they can recieve a gift.".format(shop_name))

    @shop.command(name="trade", pass_context=True, no_pm=True)
    async def _trade_shop(self, ctx, user: discord.Member, *, tradeoffer: str):
        """Requests a trade with another shop member"""
        author = ctx.message.author
        if author.id in self.players:
            if user.id in self.players:
                if not self.players[user.id]["Block Trades"]:
                    if await self.check_cooldowns(user.id):
                        if tradeoffer in self.players[author.id]["Inventory"]:
                            await self.bot.say("{} requests a trade with {}. Do you wish to trade for {}?".format(author.mention, user.mention, tradeoffer))
                            answer = await self.bot.wait_for_message(timeout=15, author=user)
                            if not answer:
                                await self.bot.say("No response. Cancelling trade with {}.".format(user.name))
                            elif answer.content.title() == "No":
                                await self.bot.say("{} has rejected your trade.".format(user.name))
                            elif answer.content.title() == "Yes":
                                await self.bot.say("Please say which item you would like to trade.")
                                response = await self.bot.wait_for_message(timeout=15, author=user)
                                if not response:
                                    await self.bot.say("No response. Cancelling trade with {}.".format(user.name))
                                elif response.content.title() in self.players[user.id]["Inventory"]:
                                    await self.bot.say("{} has offered {}, do you wish to accept this trade, {}?".format(user.mention, response.content, author.mention))
                                    reply = await self.bot.wait_for_message(timeout=15, author=author)
                                    if not reply:
                                        await self.bot.say("No response. Cancelling trade with {}.".format(user.name))
                                    elif reply.content.title() == "No" or reply.content.title() == "Cancel":
                                        await self.bot.say("Trade Rejected. Cancelling trade.")
                                    elif reply.content.title() == "Yes" or reply.content.title() == "Accept":
                                        self.inventory_remove(author.id, tradeoffer)
                                        self.inventory_remove(user.id, response.content.title())
                                        self.inventory_add(user.id, tradeoffer)
                                        self.inventory_add(author.id, response.content.title())
                                        await self.bot.say("Trading items... {} recieved {}, and {} recieved {}.".format(author.mention, response.content, user.mention, tradeoffer))
                                        await self.bot.say("Trade complete.")
                                    else:
                                        await self.bot.say("Invalid response. Cancelling trade with {}.".format(user.name))
                                else:
                                    await self.bot.say("You don't have this item. Cancelling trade.")
                            else:
                                await self.bot.say("Invalid response. Cancelling trade with {}.".format(user.name))
                        else:
                            await self.bot.say("You don't have this item. Cancelling trade.")
                else:
                    await self.bot.say("This player is currently blocking trades.")
            else:
                await self.bot.say("This person is not a member of the shop.")
        else:
            await self.bot.say("You need to join the shop before you can trade items.")

    @shop.command(name="join", pass_context=True, no_pm=True)
    async def _join_shop(self, ctx):
        """Adds you to the shop. Only need to do this once."""
        shop_name = self.config["Shop Name"]
        user = ctx.message.author
        if user.id not in self.players:
            self.players[user.id] = {}
            fileIO("data/shop/players.json", "save", self.players)
            self.players[user.id] = {"Inventory": {},
                                     "Block Trades": False,
                                     "Trade Cooldown": 0}
            fileIO("data/shop/players.json", "save", self.players)
            await self.bot.say("```You have joined {} shop. You can now buy items with credits.```".format(shop_name))
        else:
            await self.bot.say("```You have already a member of the {} shop```".format(shop_name))

    @shop.command(name="blocktrades", pass_context=True, no_pm=True)
    async def _blocktrades_shop(self, ctx, cooldown: int):
        """Toggles blocking trade requests on and off."""
        user = ctx.message.author
        if user.id in self.players:
            if self.players[user.id]["Block Trades"] is False:
                self.players[user.id]["Block Trades"] = True
                fileIO("data/shop/config.json", "save", self.config)
                await self.bot.say("Now blocking all trades")
            else:
                self.players[user.id]["Block Trades"] = False
                fileIO("data/shop/config.json", "save", self.config)
                await self.bot.say("Trades are now enabled.")

    @commands.group(pass_context=True, no_pm=True)
    async def setshop(self, ctx):
        """Shop configuration settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @setshop.command(name="notify", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _notify_setshop(self, ctx):
        """PM's all users with Shopkeeper role. Add this role to be notified.
        This command will toggle notifications on/off"""
        if self.config["Shop Notify"]:
            self.config["Shop Notify"] = not self.config["Shop Notify"]
            fileIO("data/shop/config.json", "save", self.config)
            await self.bot.say("Shop notifications are now OFF!")
        else:
            self.config["Shop Notify"] = True
            fileIO("data/shop/config.json", "save", self.config)
            await self.bot.say("Shop notifcations are now ON!")

    @setshop.command(name="output", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _output_setshop(self, ctx, command: str, output: str):
        """Sets the output to chat/whisper for inventory & shop list"""
        command = command.title()
        output = output.title()
        if command == "Shop":
            if output == "Chat":
                self.config["Store Output"] = "Chat"
                fileIO("data/shop/config.json", "save", self.config)
                await self.bot.say("Store listings will now display in chat.")
            elif output == "Whisper" or output == "Pm" or output == "Dm":
                self.config["Store Output"] = "Whisper"
                fileIO("data/shop/config.json", "save", self.config)
                await self.bot.say("Store listings will now display in whisper.")
            else:
                await self.bot.say("Output must be Chat or Whisper/DM/PM.")
        elif command == "Inventory":
            if output == "Chat":
                self.config["Inventory Output"] = "Chat"
                fileIO("data/shop/config.json", "save", self.config)
                await self.bot.say("Inventory will now display in chat.")
            elif output == "Whisper" or output == "Pm" or output == "Dm":
                self.config["Inventory Output"] = "Whisper"
                fileIO("data/shop/config.json", "save", self.config)
                await self.bot.say("Inventory will now display in whisper.")
            else:
                await self.bot.say("Output must be Chat or Whisper/DM/PM.")
        else:
            await self.bot.say("Command must be Shop or Inventory.")

    @setshop.command(name="tradecd", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _tcd_setshop(self, ctx, cooldown: int):
        """Sets the cooldown timer for trading, in seconds."""
        self.config["Trade Cooldown"] = cooldown
        fileIO("data/shop/config.json", "save", self.config)
        await self.bot.say("Trading cooldown set to {}".format(self.time_format(cooldown)))

    @setshop.command(name="role", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _role_sethop(self, ctx, *, rolename: str):
        """Change the name of the notification role"""
        self.config["Shop Role"] = rolename
        fileIO("data/shop/config.json", "save", self.config)
        await self.bot.say("Notify role set to {}. Assign this role to users you want to haven notifed of pending items.".format(rolename))

    @setshop.command(name="toggle", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _toggle_setshop(self, ctx):
        """Opens and closes the shop"""
        shop_name = self.config["Shop Name"]
        if self.config["Shop Open"]:
            self.config["Shop Open"] = not self.config["Shop Open"]
            fileIO("data/shop/config.json", "save", self.config)
            await self.bot.say("The shop is now closed.")
        else:
            self.config["Shop Open"] = True
            fileIO("data/shop/config.json", "save", self.config)
            await self.bot.say("{} shop is now open for business!".format(shop_name))

    @setshop.command(name="sorting", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _sort_setshop(self, ctx, choice: str):
        """Changes the sorting method for shop listings. Alphabet, Lowest, Highest"""
        choice = choice.title()
        if choice == "Alphabet":
            self.config["Sort Method"] = "Alphabet"
            fileIO("data/shop/config.json", "save", self.config)
            await self.bot.say("Changing sorting method to Alphabetical.")
        elif choice == "Lowest":
            self.config["Sort Method"] = "Lowest"
            fileIO("data/shop/config.json", "save", self.config)
            await self.bot.say("Setting sorting method to Lowest.")
        elif choice == "Highest":
            self.config["Sort Method"] = "Highest"
            fileIO("data/shop/config.json", "save", self.config)
            await self.bot.say("Setting sorting method to Highest.")
        else:
            await self.bot.say("Please choose Alphabet, Lowest, or Highest.")

    @setshop.command(name="name", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _name_setshop(self, ctx, *, name):
        """Renames the shop"""
        shop_name = self.config["Shop Name"]
        if len(name) > 0:
            self.config["Shop Name"] = name
            fileIO("data/shop/config.json", "save", self.config)
            shop_name = self.config["Shop Name"]
            await self.bot.say("I have renamed the shop to {}.".format(shop_name))
        else:
            await self.bot.say("You need to enter a name for the shop.")

    @commands.group(name="pending", pass_context=True)
    async def _pending(self, ctx):
        """List of pending commands for redemable items"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_pending.command(pass_context=True, no_pm=True)
    async def check(self, ctx, *, code):
        """Checks if an item is on the pending list with conf #"""
        if code in self.pending:
            item = self.pending[code]["Item"]
            await self.bot.say("{} is still on the pending list.".format(item))
        else:
            await self.bot.say("This code is either not valid, or the item is no longer on the list.")

    @_pending.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def show(self, ctx):
        """Shows a list of items waiting to be redeemed"""
        if len(self.pending) > 0:
            keys = ["Item", "User Name", "User ID", "Time Stamp", "Confirmation Number"]
            items = []
            user_names = []
            user_ids = []
            time_stamps = []
            conf_nums = []
            for x in self.pending:
                items.append(self.pending[x]["Item"])
                user_names.append(self.pending[x]["Name"])
                time_stamps.append(self.pending[x]["Time Stamp"])
                conf_nums.append(self.pending[x]["Confirmation Number"])
                user_ids.append(self.pending[x]["ID"])
            table = list(zip(items, user_names, user_ids, time_stamps, conf_nums))
            t = tabulate(table, headers=keys, numalign="left")
            await self.bot.say("```" + t + "```")
        else:
            await self.bot.say("The pending list is empty.")

    @_pending.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def clear(self, ctx, *, number):
        """Allows you to clear one item by confirmation number"""
        if len(self.pending) > 0:
            if number in self.pending:
                name = self.pending[number]["Name"]
                item = self.pending[number]["Item"]
                del self.pending[number]
                fileIO("data/shop/pending.json", "save", self.pending)
                await self.bot.say("{}'s {} has been cleared from the pending list.'.".format(name, item))
            else:
                await self.bot.say("Could not find this code in the pending. It may have been cleared or does not exist.")
        else:
            await self.bot.say("The pending list is empty.")

    @_pending.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def clearall(self, ctx):
        """Clears all items from the pending list"""
        if len(self.pending) > 0:
            del self.pending
            self.pending = {}
            fileIO("data/shop/pending.json", "save", self.pending)
            await self.bot.say("Pending list now cleared.")
        else:
            await self.bot.say("Nothing in pending list to clear.")

    async def check_cooldowns(self, userid):
        if abs(self.players[userid]["Trade Cooldown"] - int(time.perf_counter())) >= self.config["Trade Cooldown"]:
            self.players[userid]["Trade Cooldown"] = int(time.perf_counter())
            fileIO("data/shop/players.json", "save", self.players)
            return True
        elif self.players[userid]["Trade Cooldown"] == 0:
            self.players[userid]["Trade Cooldown"] = int(time.perf_counter())
            fileIO("data/shop/players.json", "save", self.players)
            return True
        else:
            s = abs(self.players[userid]["Trade Cooldown"] - int(time.perf_counter()))
            seconds = abs(s - self.config["Trade Cooldown"])
            await self.bot.say("You must wait before trading again. You still have: {}".format(self.time_format(seconds)))
            return False

    def bordered(self, text):
        lines = text.splitlines()
        width = max(len(s) for s in lines)
        res = ["┌" + "─" * width + "┐"]
        for s in lines:
            res.append("│" + (s + " " * width)[:width] + "│")
        res.append("└" + "─" * width + "┘")
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

    def account_check(self, uid):
        bank = self.bot.get_cog("Economy").bank
        if bank.account_exists(uid):
            return True
        else:
            return False

    def role_check(self, role, ctx):
        return [m.name for m in ctx.message.server.members if role.lower() in [str(r).lower() for r in m.roles] and str(m.status) != "offline"]

    def enough_points(self, uid, amount):
        bank = self.bot.get_cog("Economy").bank
        if self.account_check(uid):
            if bank.can_spend(uid, amount):
                return True
            else:
                return False

    def inventory_check(self, uid):
        if uid in self.players:
            return True
        else:
            return False

    def inventory_item_check(self, uid, itemname):
        if self.inventory_check(uid):
            if itemname in self.players[uid]["Inventory"]:
                return True
            else:
                return False
        else:
            False

    def inventory_item_amount(self, uid, itemname):
            if self.inventory_check(uid):
                if self.inventory_item_check(uid, itemname):
                    if self.players[uid]["Inventory"][itemname]["Item Quantity"] > 0:
                        return True
                    else:
                        return False
                else:
                    return False
            else:
                return False

    def inventory_add(self, uid, itemname):
        if self.inventory_check(uid):
            if self.inventory_item_check(uid, itemname):
                self.players[uid]["Inventory"][itemname]["Item Quantity"] += 1
                fileIO("data/shop/players.json", "save", self.players)
            else:
                self.players[uid]["Inventory"][itemname] = {"Item Name": itemname,
                                                            "Item Quantity": 1}
                fileIO("data/shop/players.json", "save", self.players)
        else:
            return False

    def inventory_remove(self, uid, itemname):
        if self.inventory_check(uid):
            if self.inventory_item_check(uid, itemname):
                self.players[uid]["Inventory"][itemname]["Item Quantity"] -= 1
                fileIO("data/shop/players.json", "save", self.players)
                if self.players[uid]["Inventory"][itemname]["Item Quantity"] < 1:
                    del self.players[uid]["Inventory"][itemname]
                    fileIO("data/shop/players.json", "save", self.players)
            else:
                return False
        else:
            return False


def check_folders():
    if not os.path.exists("data/shop"):
        print("Creating data/shop folder...")
        os.makedirs("data/shop")


def check_files():
    pconfig = {"Block Trades": False,
               "Trade Cooldown": 0}
    # For people using an old version of shop. Will be removed at a later date NOTE
    try:
        shop_dict = fileIO("data/shop/shop.json", "load")
        shop_item_count = len(list(shop_dict.keys()))
        system = {"Shop Name": "RedJumpman",
                  "Shop Open": True,
                  "Shop Notify": False,
                  "Shop Items": shop_item_count,
                  "Shop Role": "Shopkeeper",
                  "Trade Cooldown": 30,
                  "Store Output": "Whisper",
                  "Inventory Output": "Whisper",
                  "Sort Method": "Alphabet"}
    except:
        system = {"Shop Name": "RedJumpman",
                  "Shop Open": True,
                  "Shop Notify": False,
                  "Shop Items": 0,
                  "Trade Cooldown": 30,
                  "Store Message": "Whisper",
                  "Inventory Output": "Whisper",
                  "Shop Role": "Shopkeeper",
                  "Sort Method": "Alphabet"}

    f = "data/shop/pending.json"
    if not fileIO(f, "check"):
        print("Creating default shop pending.json...")
        fileIO(f, "save", {})

    f = "data/shop/shop.json"
    if not fileIO(f, "check"):
        print("Creating default shop shop.json...")
        fileIO(f, "save", {})

    f = "data/shop/players.json"
    if not fileIO(f, "check"):
        print("Adding shop player.json...")
        fileIO(f, "save", {})
    else:
        current = fileIO(f, "load")
        if current.keys() is not None:
            for player in current:
                    for key in pconfig.keys():
                        if key not in current[player].keys():
                            current[player][key] = pconfig[key]
                            print("Adding " + str(key) + " field to shop players.json")
                            fileIO(f, "save", current)
    f = "data/shop/config.json"
    if not fileIO(f, "check"):
        print("Adding shop config.json...")
        fileIO(f, "save", system)
    else:  # consistency check
        current = fileIO(f, "load")
        if current.keys() != system.keys():
            for key in system.keys():
                if key not in current.keys():
                    current[key] = system[key]
                    print("Adding " + str(key) +
                          " field to shop config.json")
            fileIO(f, "save", current)


def setup(bot):
    global logger
    check_folders()
    check_files()
    logger = logging.getLogger("shop")
    if logger.level == 0:  # Prevents the logger from being loaded again in case of module reload
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(filename="data/shop/shop.log", encoding="utf-8", mode="a")
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
    if tabulateAvailable:
        bot.add_cog(Shop(bot))
    else:
        raise RuntimeError("You need to run 'pip3 install tabulate'")
