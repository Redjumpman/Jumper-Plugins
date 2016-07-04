#  Shop.py was created by Redjumpman for Redbot
#  This will create a data folder with 3 JSON files and 1 logger
#  The logger will contain information for admin use
import discord
import os
import json
import logging
from operator import itemgetter
from discord.ext import commands
from .utils.dataIO import fileIO
from __main__ import send_cmd_help
from .utils import checks
from time import strftime
try:   # Check if Tabulate is installed
    from tabulate import tabulate
    tabulateAvailable = True
except:
    tabulateAvailable = False

#  This is a global variable used for the time format
time_now = strftime("%Y-%m-%d %H:%M:%S")


class Shop:
    """Allows you to purchase items created by the Admins with your points"""
    # We have to define all the different files were going to load and save
    def __init__(self, bot):
        self.bot = bot
        self.players = fileIO("data/shop/players.json", "load")
        self.shopsys = fileIO("data/shop/shop.json", "load")
        self.pending = fileIO("data/shop/pending.json", "load")
        self.config = fileIO("data/shop/config.json", "load")

    @commands.group(pass_context=True, no_pm=True)
    async def shop(self, ctx):
        """Individual Commands:
        ---------
        inventory      Shows a list of items in your inventory
        --------
        Pending List Commands:
        --------
        show           Shows a list of items waiting to be redeemed
        clear          Clear one single item from pending list
        clear all      Clears all items from the pending list
        -------
        Shop Commands:"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    # We want to seperate the store so it doesn't have a shop prefix
    @shop.command(name="list", pass_context=True)
    async def _list_shop(self, ctx):
        """Shows a list of items that can be purchased"""
        shop_name = self.config["Shop Name"]
        column1 = [subdict['Item Name'] for subdict in self.shopsys.values()]
        column2 = [subdict['Item Cost'] for subdict in self.shopsys.values()]
        m = list(zip(column1, column2))
        if self.config["Sort Method"] == "Alphabet":
            m = m.sort()
        elif self.config["Sort Method"] == "Lowest":
            m = sorted(m, key=itemgetter(1), reverse=True)
        elif self.config["Sort Method"] == "Highest":
            m = sorted(m, key=itemgetter(1))
        t = tabulate(m, headers=["Item Name", "Item Cost"])
        print(len(t))
        header = "```"
        header += self.bordered(shop_name + " Store Listings")
        header += "```"
        if len(t) > 2000:
            first_msg1, first_msg2 = column1[::2], column1[1::2]
            second_msg1, second_msg2 = column2[::2], column2[1::2]
            m1 = list(zip(first_msg1, second_msg1))
            m2 = list(zip(first_msg2, second_msg2))
            if self.config["Sort Method"] == "Alphabet":
                m1.sort()
                m2.sort()
            elif self.config["Sort Method"] == "Lowest":
                m1 = sorted(m1, key=itemgetter(1))
                m2 = sorted(m2, key=itemgetter(1))
            elif self.config["Sort Method"] == "Highest":
                m1 = sorted(m1, key=itemgetter(1), reverse=True)
                m2 = sorted(m2, key=itemgetter(1), reverse=True)
            t1 = tabulate(m1, headers=["Item Name", "Item Cost"])
            t2 = tabulate(m2, headers=["Item Name", "Item Cost"])
            await self.bot.whisper(header + "```\n" + t1 + "```")
            await self.bot.whisper("```" + t2 + "```")
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
            await self.bot.say("```{} + has been removed from {} shop.```".format(itemname, shop_name))
        else:
            await self.bot.say("That item is not in {}'s store listings".format(shop_name))

    @shop.command(name="sort", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _sort_shop(self, ctx, choice: str):
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

    @shop.command(name="name", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _name_shop(self, ctx, *, name):
        """Renames the shop"""
        shop_name = self.config["Shop Name"]
        if len(name) > 0:
            self.config["Shop Name"] = name
            fileIO("data/shop/config.json", "save", self.config)
            shop_name = self.config["Shop Name"]
            await self.bot.say("I have renamed the shop to {}".format(shop_name))
        else:
            await self.bot.say("You need to enter a name for the shop")

    @shop.command(name="toggle", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _toggle_shop(self, ctx):
        """Opens and closes the shop"""
        shop_name = self.config["Shop Name"]
        if self.config["Shop Open"]:
            self.config['Shop Open'] = not self.config['Shop Open']
            fileIO("data/shop/config.json", "save", self.config)
            await self.bot.say("The shop is now closed")
        else:
            self.config["Shop Open"] = True
            fileIO("data/shop/config.json", "save", self.config)
            await self.bot.say("{} shop is now open for business!".format(shop_name))

    @shop.command(name="redeem", pass_context=True, no_pm=True)
    async def _redeem_shop(self, ctx, *, itemname):
        """Sends a request to redeem an item"""
        user = ctx.message.author
        role = self.config["Shop Role"]
        if self.inventory_item_check(user.id, itemname):
            if self.inventory_item_amount(user.id, itemname):
                if user.id not in self.pending:
                    self.pending[user.id] = {}
                    fileIO("data/shop/pending.json", "save", self.pending)
                    self.pending[user.id][user.name] = {}
                    fileIO("data/shop/pending.json", "save", self.pending)
                    self.pending[user.id][user.name
                                          ][itemname
                                            ] = {"Item Name": itemname,
                                                 "Time Requested": time_now}
                    fileIO("data/shop/pending.json", "save", self.pending)
                    self.inventory_remove(user.id, itemname)
                    if self.config["Shop Notify"]:
                        names = self.role_check(role, ctx)
                        destinations = [m for m in ctx.message.server.members if m.name in names]
                        for destination in destinations:
                            await self.bot.send_message(destination, itemname + " was added to the pending list by " + user.name)
                        await self.bot.say("```{} has been added to pending list. Please wait for approval before adding more of the same item.```".format(itemname))
                else:
                    self.pending[user.id][user.name][itemname] = {"Item Name": itemname,
                                                                  "Time Requested": time_now}
                    fileIO("data/shop/pending.json", "save", self.pending)
                    self.inventory_remove(user.id, itemname)
                    msg = "```"
                    msg += itemname + " has been added to the"
                    msg += " pending list. Please wait for approval before "
                    msg += "adding more of the same item."
                    msg += "```"
                    if self.config["Shop Notify"]:
                        names = self.role_check(role, ctx)
                        destinations = [m for m in ctx.message.server.members if m.name in names]
                        for destination in destinations:
                            await self.bot.send_message(destination, "{} was added to the pending list by {}".format(itemname, user.name))
                    await self.bot.say(msg)
            else:
                await self.bot.say("You do not have that item to redeem")
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
                            if not self.inventory_item_check(user.id, itemname):
                                self.inventory_add(user.id, itemname)
                                bank = self.bot.get_cog("Economy").bank
                                bank.withdraw_credits(user, points)
                                await self.bot.say("```You have purchased a {} for {} points.\n{} has been added to your inventory.".format(itemname, str(points), itemname))
                            else:
                                self.inventory_add(user.id, itemname)
                                bank = self.bot.get_cog("Economy").bank
                                bank.withdraw_credits(user, points)
                                await self.bot.say("```You have purchased a {} for {} points.\n{} has been added to your inventory.".format(itemname, str(points), itemname))
                        else:
                            await self.bot.say("You don't have enough points to purchase this item")
                    else:
                        await self.bot.say("You do not have a bank account")
                else:
                    await self.bot.say("This item is not in the shop")
            else:
                await self.bot.say("You need to join the {} shop to purchase items. Example: !shop join".format(shop_name))
        else:
            await self.bot.say("{} shop is currently closed".format(shop_name))

    @shop.command(name="gift", pass_context=True, no_pm=True)
    async def _gift_shop(self, ctx, user: discord.Member, *, itemname):
        """Send a gift in your inventory to another member"""
        author = ctx.message.author
        if author == user:
            await self.bot.say("You can't give an item to yourself.")
            return
        if len(itemname) < 0:
            await self.bot.say("You need to tell me what you want to transfer")
            return
        if user.id in self.players:
            if self.inventory_item_check(author.id, itemname):
                if self.inventory_item_amount(author.id, itemname):
                    if itemname in self.players[user.id]["Inventory"]:
                        nametwo = self.shopsys[itemname]["Item Name"]
                        self.inventory_remove(author.id, itemname)
                        self.inventory_add(user.id, itemname)
                        logger.info("{}({}) gifted a {} item to {}({})".format(author.name, author.id, itemname, user.name, user.id))
                        await self.bot.say("```" + "I have gifted {} to {}'s inventory".format(nametwo, user.name) + "```")
                    else:
                        nametwo = self.shopsys[itemname]["Item Name"]
                        self.players[user.id]["Inventory"][itemname] = {"Item Name": nametwo,
                                                                        "Item Quantity": 0}
                        self.inventory_remove(author.id, itemname)
                        self.inventory_add(user.id, itemname)
                        logger.info("{}({}) gifted a {} item to {}({})".format(author.name, author.id, itemname, user.name, user.id))
                        await self.bot.say("```" + "I have gifted {} to {}'s inventory".format(nametwo, user.name) + "```")
                else:
                    await self.bot.say("You currently don't own any of these.")
            else:
                await self.bot.say("You do not own this shop item.")
        else:
            shop_name = self.config["Shop Name"]
            await self.bot.say("I cant find a user with that name." +
                               " Check to see if that user has joined {} shop. They need to type !shop join before they can recieve a gift".format(shop_name))

    @shop.command(name="join", pass_context=True, no_pm=True)
    async def _join_shop(self, ctx):
        """Adds you to the shop. Only need to do this once."""
        shop_name = self.config["Shop Name"]
        user = ctx.message.author
        if user.id not in self.players:
            self.players[user.id] = {}
            fileIO("data/shop/players.json", "save", self.players)
            self.players[user.id]["Inventory"] = {}
            fileIO("data/shop/players.json", "save", self.players)
            await self.bot.say("```You have joined {} shop. You can now buy items with points.```".format(shop_name))
        else:
            await self.bot.say("```You have already joined```")

    @shop.command(name="notify", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _notify_shop(self, ctx):
        """PM's all users with Shopkeeper role. Add this role to be notified.
        This command will toggle notifications on/off"""
        if self.config["Shop Notify"]:
            self.config['Shop Notify'] = not self.config['Shop Notify']
            fileIO("data/shop/config.json", "save", self.config)
            await self.bot.say("Shop notifications are now OFF!")
        else:
            self.config["Shop Notify"] = True
            fileIO("data/shop/config.json", "save", self.config)
            await self.bot.say("Shop notifcations are now ON!")

    @shop.command(name="role", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _role_shop(self, ctx, *, rolename: str):
        """Change the name of the notification role"""
        self.config["Shop Role"] = rolename
        fileIO("data/shop/config.json", "save", self.config)
        await self.bot.say("Notify role set to {}. Assign this role to users you want to haven notifed of pending items.".format(rolename))

    @commands.group(name="pending", pass_context=True)
    async def _pending(self, ctx):
        """List of pending commands for redemable items"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_pending.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def show(self, ctx):
        """Shows a list of items waiting to be redeemed"""
        if len(self.pending) > 0:
            k = json.dumps(self.pending, indent=1, sort_keys=True)
            m = "```"
            m += k.replace('"', '',).replace('{', '').replace('}', '').replace(',', '')
            m += "```"
            await self.bot.say(m)
        else:
            await self.bot.say("The pending list is empty.")

    @_pending.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def clear(self, ctx, user: discord.Member, *, itemname):
        """Allows you to clear one item from the pending list"""
        if len(self.pending) > 0:
            if user.id in self.pending:
                if itemname in self.pending[user.id][user.name]:
                    del self.pending[user.id][user.name][itemname]
                    fileIO("data/shop/pending.json", "save", self.pending)
                    await self.bot.say("{} has been cleared from pending, for {}'s redeem request.".format(itemname, user.name))
                else:
                    await self.bot.say("The item is not in the pending list for this user")
            else:
                await self.bot.say("This user has no pending requests. Make sure their name is spelled correctly.")
        else:
            await self.bot.say("The pending list is empty")

    @_pending.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def clearall(self, ctx):
        """Clears all items from the pending list"""
        if len(self.pending) > 0:
            del self.pending
            self.pending = {}
            fileIO("data/shop/pending.json", "save", self.pending)
            await self.bot.say("Pending list now cleared")
        else:
            await self.bot.say("Nothing in pending list to clear")

    @commands.command(pass_context=True, no_pm=True)
    async def inventory(self, ctx):
        """Shows a list of items you have purchased"""
        user = ctx.message.author
        if user.id in self.players:
            if self.players[user.id]["Inventory"] is None:
                await self.bot.say("You have not purchased any items for me to display")
            else:
                    column1 = [subdict['Item Name'] for subdict in self.players[user.id]["Inventory"].values()]
                    column2 = [subdict["Item Quantity"] for subdict in self.players[user.id]["Inventory"].values()]
                    m = list(zip(column1, column2))
                    m.sort()
                    t = tabulate(m, headers=["Item Name", "Item Quantity"])
                    header = "```"
                    header += self.bordered("I N V E N T O R Y")
                    header += "```"
                    await self.bot.whisper(header + "```\n" + t + "```")

    def bordered(self, text):
        lines = text.splitlines()
        width = max(len(s) for s in lines)
        res = ['┌' + '─' * width + '┐']
        for s in lines:
            res.append('│' + (s + ' ' * width)[:width] + '│')
        res.append('└' + '─' * width + '┘')
        return '\n'.join(res)

    def account_check(self, uid):
        bank = self.bot.get_cog('Economy').bank
        if bank.account_exists(uid):
            return True
        else:
            return False

    def role_check(self, role, ctx):
        return [m.name for m in ctx.message.server.members if role.lower() in [str(r).lower() for r in m.roles] and str(m.status) != 'offline']

    def enough_points(self, uid, amount):
        bank = self.bot.get_cog('Economy').bank
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
    try:
        shop_dict = fileIO("data/shop/shop.json", "load")
        shop_item_count = len(list(shop_dict.keys()))
        system = {"Shop Name": "RedJumpman",
                  "Shop Open": True,
                  "Shop Notify": False,
                  "Shop Items": shop_item_count,
                  "Shop Role": "Shopkeeper",
                  "Sort Method": "Alphabet"}
    except:
        system = {"Shop Name": "RedJumpman",
                  "Shop Open": True,
                  "Shop Notify": False,
                  "Shop Items": 0}

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
        handler = logging.FileHandler(filename='data/shop/shop.log', encoding='utf-8', mode='a')
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
    if tabulateAvailable:
        bot.add_cog(Shop(bot))
    else:
        raise RuntimeError("You need to run 'pip3 install tabulate'")
