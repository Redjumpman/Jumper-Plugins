# Developed by Redjumpman for Twentysix26's Redbot.
# Ported from mee6bot to work for Red
# Original credit and design goes to mee6
import aiohttp
import os
import html
import discord
from xml.etree import ElementTree as ET
from discord.ext import commands
from .utils.dataIO import dataIO
from cogs.utils import checks

# Username and Password is obtained from myanime list website
# You need to create an account there and input the information below

switcher = [
    'english',
    'score',
    'type',
    'episodes',
    'volumes',
    'chapters',
    'status',
    'type',
    'start_date',
    'end_date'
    ]


class Animelist:
    """Fetch info about an anime title"""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/animelist/credentials.json"
        self.credentials = dataIO.load_json(self.file_path)

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def animeset(self, ctx):
        """Sets your username and password from myanimelist"""
        await self.bot.whisper("Type your user name. You can reply in this private msg")
        username = await self.bot.wait_for_message(timeout=15, author=ctx.message.author)
        if username is None:
            return
        else:
            self.credentials["Username"] = username.content
            dataIO.save_json(self.file_path, self.credentials)
            await self.bot.whisper("Ok thanks. Now what is your password?")
            password = await self.bot.wait_for_message(timeout=15, author=ctx.message.author)
            if password is None:
                return
            else:
                self.credentials["Password"] = password.content
                dataIO.save_json(self.file_path, self.credentials)
                await self.bot.whisper("Setup complete. Account details added.\nTry searching for "
                                       "an anime using {}anime".format(ctx.prefix))

    @commands.command(pass_context=True, no_pm=True)
    async def anime(self, ctx, *, title):
        """Fetches info about an anime title!"""
        cmd = "anime"
        await self.fetch_info(ctx, cmd, title)

    @commands.command(pass_context=True, no_pm=True)
    async def manga(self, ctx, *, title):
        """Fetches info about an manga title!"""
        cmd = "manga"
        await self.fetch_info(ctx, cmd, title)

    async def fetch_info(self, ctx, cmd, title):
        data = await self.get_xml(cmd, title)

        if data == '':
            await self.bot.say("I couldn't find anything!")
            return
        try:
            root = ET.fromstring(data)
            if len(root) == 0:
                await self.bot.say("I couldn't find anything!")
            elif len(root) == 1:
                entry = root[0]
            else:
                msg = "**Please choose one by giving its number.**\n"
                msg += "\n".join(['{} - {}'.format(n+1, entry[1].text)
                                  for n, entry in enumerate(root) if n < 10
                                  ])

                await self.bot.say(msg)

                check = lambda m: m.content in map(str, range(1, len(root)+1))
                resp = await self.bot.wait_for_message(timeout=15, author=ctx.message.author,
                                                       check=check)
                if resp is None:
                    return

                entry = root[int(resp.content)-1]

            link = 'http://myanimelist.net/{}/{}'.format("anime", entry.find('id').text)
            embed = discord.Embed(colour=0x0066FF,
                                  description=("All the information you need about "
                                               "[{}]({})".format(entry.find('title').text, link)))
            embed.title = entry.find('title').text
            embed.set_thumbnail(url=entry.find('image').text)
            embed.set_footer(text=entry.find('synopsis').text)
            for k in switcher:
                spec = entry.find(k)
                if spec is not None and spec.text is not None:
                    embed.add_field(name=k.capitalize(),
                                    value=html.unescape(spec.text.replace('<br />', '')))

            await self.bot.say(embed=embed)
        except:
            await self.bot.say("Your username or password is not correct. You need to create an "
                               "account on myanimelist.net.\nIf you have an account use "
                               "**{}animeset** to set your credentials".format(ctx.prefix))

    async def get_xml(self, nature, name):
        username = self.credentials["Username"]
        password = self.credentials["Password"]
        name = name.replace(" ", "_")
        auth = aiohttp.BasicAuth(login=username, password=password)
        url = 'https://myanimelist.net/api/{}/search.xml?q={}'.format(nature, name)
        with aiohttp.ClientSession(auth=auth) as session:
            async with session.get(url) as response:
                data = await response.text()
                return data


def check_folders():
    if not os.path.exists("data/animelist"):
        print("Creating data/animelist folder...")
        os.makedirs("data/animelist")


def check_files():
    system = {"Username": "",
              "Password": ""}

    f = "data/animelist/credentials.json"
    if not dataIO.is_valid_json(f):
        print("Adding animelist credentials.json...")
        dataIO.save_json(f, system)


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Animelist(bot))
