import asyncio
import discord
from redbot.core.utils.chat_formatting import box
from .menu import MenuCheck


class Inventory:
    def __init__(self, ctx, data):
        self.ctx = ctx
        self.data = data

    async def display(self):
        msg, groups = await self.setup()
        try:
            return await self.inv_loop(groups, msg)
        except asyncio.TimeoutError:
            await msg.delete()
            await self.ctx.send("Menu timed out.")
            raise RuntimeError
        except ExitMenu:
            await self.ctx.send("Exited inventory.")
            raise RuntimeError

    async def setup(self, groups=None, page=0, msg=None):
        if not groups:
            groups = self.splitter()
        options = self.update(groups, page)
        embed = self.build_embed(options, page, groups)
        if msg:
            await msg.edit(embed=embed)
        else:
            msg = await self.ctx.send(embed=embed)
        return msg, groups

    async def inv_loop(self, groups, msg):
        page = 0
        maximum = len(groups) - 1
        while True:
            check = MenuCheck(self.ctx, groups, page, maximum)
            choice = await self.ctx.bot.wait_for("message", timeout=35.0, check=check.predicate)
            if choice.content.isdigit() and int(choice.content) in range(1, len(groups[page]) + 1):
                try:
                    await choice.delete()
                    await msg.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass
                return groups[page][int(choice.content) - 1][0]
            elif choice.content.lower() in (">", "n", "next"):
                page += 1
            elif choice.content.lower() in ("b", "<", "back"):
                page -= 1
            elif choice.content.lower() in ("e", "x", "exit"):
                try:
                    await choice.delete()
                    await msg.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass
                raise ExitMenu
            elif choice.content.lower() in ("p", "prev"):
                continue
            else:
                msg, _ = await self.setup(groups=groups, page=page, msg=msg)
                await msg.edit(embed=msg)
            msg, _ = await self.setup(groups=groups, page=page, msg=msg)

    def splitter(self):
        return [self.data[i : i + 5] if len(self.data) > 5 else self.data for i in range(0, len(self.data), 5)]

    def update(self, groups, page=0):
        header = f"{'#':<3} {'Items':<29} {'Qty':<7} {'Type':<8}\n{'--':<3} {'-'*29:<29} {'-'*4:<7} {'-'*8:<8}"
        fmt = [header]
        for idx, x in enumerate(groups[page], 1):
            line_one = f"{f'{idx}.': <{3}} {x[0]: <{28}s} {x[1]['Qty']: < {9}}{x[1]['Type']: <{7}s}"
            fmt.append(line_one)
            fmt.append(f'< {x[1]["Info"][:50]} >' if len(x[1]["Info"]) < 50 else f'< {x[1]["Info"][:47]}... >')
            fmt.append("",)
        return box("\n".join(fmt), lang="md")

    def build_embed(self, options, page, groups):
        title = "{}'s Inventory".format(self.ctx.author.name)
        footer = "You are viewing page {} of {}.".format(page + 1 if page > 0 else 1, len(groups))
        instructions = (
            "Type the number for your selection or one of the words below "
            "for page navigation if there are multiple pages available.\n"
            "Next page: Type n, next, or >\n"
            "Previous page: Type b, back, or <\n"
            "Exit menu system: Type e, x, or exit"
        )
        embed = discord.Embed(color=0x5EC6FF)
        embed.add_field(name=title, value=options, inline=False)
        embed.set_footer(text="\n".join((instructions, footer)))

        return embed


class ExitMenu(Exception):
    pass
