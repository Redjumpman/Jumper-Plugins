import asyncio
import discord
from tabulate import tabulate
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
            msg.edit(embed=embed)
        else:
            msg = await self.ctx.send(embed=embed)
        return msg, groups

    async def inv_loop(self, groups, msg):
        page = 0
        maximum = len(groups) - 1
        while True:
            check = MenuCheck(self.ctx, groups, page, maximum)
            choice = await self.ctx.bot.wait_for('message', timeout=35.0, check=check.predicate)
            if choice.content.isdigit() and int(choice.content) in range(1, len(groups[page]) + 1):
                await choice.delete()
                await msg.delete()
                return groups[page][int(choice.content) - 1][0]
            elif choice.content.lower() in ('>', 'n', 'next'):
                page += 1
            elif choice.content.lower() in ('bd', '<' 'back'):
                page -= 1
            elif choice.content.lower() in ('e', 'x', 'exit'):
                await choice.delete()
                await msg.delete()
                raise ExitMenu
            elif choice.content.lower() in ('p', 'prev'):
                continue
            else:
                msg, _ = await self.setup(groups=groups, page=page, msg=msg)
                await msg.edit(embed=msg)

    def splitter(self):
        return [self.data[i:i + 10] if len(self.data) > 10 else self.data
                for i in range(0, len(self.data), 10)]

    def update(self, groups, page=0):
        headers = ('#', 'Item', 'Qty', 'Type', 'Info')
        fmt = [(idx, x[0], x[1]['Qty'], x[1]['Type'], x[1]['Info']) for idx, x in
               enumerate(groups[page], 1)]
        fmt = self.truncate(fmt)
        return "```{}```".format(tabulate(fmt, headers=headers, numalign="left"))

    def build_embed(self, options, page, groups):
        title = "{}'s Inventory".format(self.ctx.author.name)
        footer = "You are viewing page {} of {}.".format(page if page > 0 else 1, len(groups))
        instructions = "Type the number for your selection.\nType `next` and `back` to advance."
        embed = discord.Embed(color=0x5EC6FF)
        embed.add_field(name=title, value=options, inline=False)
        embed.set_footer(text='\n'.join((instructions, footer)))

        return embed

    @staticmethod
    def truncate(rows):
        updated = []
        for idx, row in enumerate(rows):
            row = list(row)
            description = row[-1]
            line = ''.join(str(x) for x in row)
            if len(line) > 33:
                new = description[:12] + '...'
                row[-1] = new
            elif len(description) > 18:
                new = description[:12] + '...'
                row[-1] = new
            tuple(row)
            updated.append(row)
        return updated


class ExitMenu(Exception):
    pass
