import asyncio
import discord
from tabulate import tabulate
from redbot.core.utils.chat_formatting import box


class ShopMenu:
    def __init__(self, ctx, origin, mode=0, sorting="price"):
        self.ctx = ctx
        self.origin = origin
        self.shop = None
        self.user = None
        self.enabled = True
        self.mode = mode
        self.sorting = sorting

    async def display(self):
        data = self.origin
        msg, groups, page, maximum = await self.setup(data)
        try:
            item = await self.menu_loop(data, groups, page, maximum, msg)
        except asyncio.TimeoutError:
            await msg.delete()
            await self.ctx.send("No response. Menu exited.")
            raise RuntimeError
        except MenuExit:
            await msg.delete()
            await self.ctx.send("Exited menu.")
            raise RuntimeError
        else:
            if self.mode == 0:
                return self.shop, item
            else:
                return self.user, item

    async def setup(self, data=None, msg=None):
        if data is None:
            data = self.origin
        if (self.shop is None and self.mode == 0) or (self.user is None and self.mode == 1):
            data = await self.parse_data(data)

        groups = self.group_data(data)
        page, maximum = 0, len(groups) - 1
        e = await self.build_menu(groups, page)

        if msg is None:
            msg = await self.ctx.send(self.ctx.author.mention, embed=e)
        else:
            await msg.edit(embed=e)
        return msg, groups, page, maximum

    async def menu_loop(self, data, groups, page, maximum, msg):
        while True:
            check = MenuCheck(self.ctx, groups, page, maximum)
            choice = await self.ctx.bot.wait_for("message", timeout=35.0, check=check.predicate)
            if choice.content.isdigit() and int(choice.content) in range(1, len(groups[page]) + 1):
                selection = groups[page][int(choice.content) - 1]
                try:
                    await choice.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass
                if self.mode == 0:
                    item = await self.next_menu(data, selection, msg)
                    if not self.enabled:
                        try:
                            await msg.delete()
                        except (discord.NotFound, discord.Forbidden):
                            pass
                        return item
                else:
                    pending_id = await self.pending_menu(data, selection, msg)
                    if not self.enabled:
                        try:
                            await msg.delete()
                        except (discord.NotFound, discord.Forbidden):
                            pass
                        return pending_id
            if choice.content.lower() in (">", "n", "next"):
                page += 1
            elif choice.content.lower() in ("b", "<", "back"):
                page -= 1
            elif choice.content.lower() in ("p", "prev"):
                if (self.shop and self.mode == 0) or (self.user and self.mode == 1):
                    try:
                        await choice.delete()
                    except (discord.NotFound, discord.Forbidden):
                        pass
                    if self.mode == 0:
                        self.shop = None
                    else:
                        self.user = None
                    break
                pass
            elif choice.content.lower() in ("e", "x", "exit"):
                try:
                    await choice.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass
                raise MenuExit

            try:
                await choice.delete()
            except discord.NotFound:
                msg, groups, page, maximum = await self.setup(msg=msg)
            except discord.Forbidden:
                pass
            embed = await self.build_menu(groups, page=page)
            await msg.edit(embed=embed)

    async def parse_data(self, data):
        if self.shop is None and self.mode == 0:
            perms = self.ctx.author.guild_permissions.administrator
            author_roles = [r.name for r in self.ctx.author.roles]
            return [x for x, y in data.items() if (y["Role"] in author_roles or perms) and y["Items"]]
        else:
            try:
                return list(data.items())
            except AttributeError:
                return data

    async def build_menu(self, groups, page):
        footer = "You are viewing page {} of {}.".format(page + 1 if page > 0 else 1, len(groups))
        if self.shop is None and self.mode == 0:
            output = ["{} - {}".format(idx, ele) for idx, ele in enumerate(groups[page], 1)]
        elif self.mode == 0:
            header = f"{'#':<3} {'Name':<29} {'Qty':<7} {'Cost':<8}\n{'--':<3} {'-'*29:<29} {'-'*4:<7} {'-'*8:<8}"
            fmt = [header]
            for idx, x in enumerate(groups[page], 1):
                line_one = f"{f'{idx}.': <{3}} {x[0]: <{29}s} {x[1]['Qty']:<{8}}{x[1]['Cost']: < {7}}"
                fmt.append(line_one)
                fmt.append(f'< {x[1]["Info"][:50]} >' if len(x[1]["Info"]) < 50 else f'< {x[1]["Info"][:47]}... >')
                fmt.append("",)
            output = box("\n".join(fmt), "md")
        elif self.mode == 1 and self.user is None:
            headers = ("#", "User", "Pending Items")
            fmt = [
                (idx, discord.utils.get(self.ctx.bot.users, id=int(x[0])).name, len(x[1]))
                for idx, x in enumerate(groups[page], 1)
            ]
            output = box(tabulate(fmt, headers=headers, numalign="left"), lang="md")
        elif self.mode == 1:
            headers = ("#", "Item", "Order ID", "Timestamp")
            fmt = [(idx, x[1]["Item"], x[0], x[1]["Timestamp"]) for idx, x in enumerate(groups[page], 1)]

            output = box(tabulate(fmt, headers=headers, numalign="left"), lang="md")
        else:
            output = None
        return self.build_embed(output, footer)

    def sorter(self, groups):
        if self.sorting == "name":
            return sorted(groups, key=lambda x: x[0])
        elif self.sorting == "price":
            return sorted(groups, key=lambda x: x[1]["Cost"], reverse=True)
        else:
            return sorted(groups, key=lambda x: x[1]["Quantity"], reverse=True)

    def group_data(self, data):
        grouped = []
        for idx in range(0, len(data), 5):
            if len(data) > 5:
                grouped.append(self.sorter(data[idx : idx + 5]))
            else:
                if not isinstance(data, dict):
                    grouped.append(data)
                else:
                    grouped.append([self.sorter(data)])
        return grouped

    def build_embed(self, options, footer):
        instructions = (
            "Type the number for your selection or one of the words below "
            "for page navigation if there are multiple pages available.\n"
            "Next page: Type n, next, or >\n"
            "Previous page: Type b, back, or <\n"
            "Return to previous menu: Type p or prev\n"
            "Exit menu system: Type e, x, or exit"
        )

        if self.shop is None and self.mode == 0:
            options = "\n".join(options)

        if self.mode == 0:
            title = "{}".format(self.shop if self.shop else "List of shops")
        else:
            title = "{} Pending".format(self.user.name if self.user else "Items")

        embed = discord.Embed(color=0x5EC6FF)
        embed.add_field(name=title, value=options, inline=False)
        embed.set_footer(text="\n".join([instructions, footer]))

        return embed

    async def next_menu(self, data, selection, msg):
        try:
            items = data[selection]["Items"]
        except TypeError:
            self.enabled = False
            return selection[0]
        else:
            self.shop = selection
            new_data = await self.parse_data(items)
            msg, groups, page, maximum = await self.setup(data=new_data, msg=msg)
            return await self.menu_loop(new_data, groups, page, maximum, msg)

    async def pending_menu(self, data, selection, msg):
        try:
            items = data[selection[0]]
        except TypeError:
            self.enabled = False
            return selection[0]
        else:
            self.user = discord.utils.get(self.ctx.bot.users, id=int(selection[0]))
            new_data = await self.parse_data(items)
            msg, groups, page, maximum = await self.setup(data=new_data, msg=msg)
            return await self.menu_loop(new_data, groups, page, maximum, msg)


class MenuCheck:
    """Special check class for menu.py"""

    def __init__(self, ctx, data, page, maximum):
        self.ctx = ctx
        self.page = page
        self.maximum = maximum
        self.data = data

    def predicate(self, m):
        choices = list(map(str, range(1, len(self.data[self.page]) + 1)))
        if self.ctx.author == m.author:
            if m.content in choices:
                return True
            elif m.content.lower() in ("exit", "prev", "p", "x", "e"):
                return True
            elif m.content.lower() in ("n", ">", "next") and (self.page + 1) <= self.maximum:
                return True
            elif m.content.lower() in ("b", "<", "back") and (self.page - 1) >= 0:
                return True
            else:
                return False
        else:
            return False


class MenuExit(Exception):
    pass
