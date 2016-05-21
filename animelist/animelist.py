# Developed by Redjumpman for Redbot by Twentysix26
# Ported from mee6bot to work for Red.
# Original credit and design goes to mee6
import aiohttp
import html
import os
from xml.etree import ElementTree
from discord.ext import commands
from .utils.dataIO import fileIO
from cogs.utils import checks

# Username and Password from myanime list webiste
# You need to create an account there and input the information below


class Animelist:
    """Fetch info about an anime title"""

    def __init__(self, bot):
        self.bot = bot
        self.credentials = fileIO("data/animelist/credentials.json", "load")

    @commands.command(pass_context=True, no_pm=False)
    @checks.is_owner()
    async def animeset(self, ctx):
        """Sets your username and password from myanimelist"""
        await self.bot.say("Type your user name")
        username = await self.bot.wait_for_message(timeout=8,
                                                   author=ctx.message.author)
        if username is None:
            return
        else:
            self.credentials["Username"] = username.content
            fileIO("data/animelist/credentials.json", "save", self.credentials)
            await self.bot.say("Ok thanks. Now what is your password?")
            password = await self.bot.wait_for_message(timeout=8,
                                                       author=ctx.message.author)
            if password is None:
                return
            else:
                self.credentials["Password"] = password.content
                fileIO("data/animelist/credentials.json", "save", self.credentials)
                await self.bot.say("Setup complete. Account details added. Try searching for an anime using !anime")

    @commands.command(pass_context=True, no_pm=True)
    async def anime(self, ctx, *, name):
        """Fetches info about an anime title!"""
        username = self.credentials["Username"]
        password = self.credentials["Password"]
        anime = name.replace(" ", "_")
        params = {
            'q': anime
                }
        try:
            auth = aiohttp.BasicAuth(login=username, password=password)
            url = 'http://myanimelist.net/api/anime/search.xml?q=' + anime
            with aiohttp.ClientSession(auth=auth) as session:
                async with session.get(url, params=params) as response:
                    data = await response.text()
                    if data == '':
                        await self.bot.say('I didn\'t found anything :cry: ...')
                        return
                    root = ElementTree.fromstring(data)
                    if len(root) == 0:
                        await self.bot.say('Sorry, I found nothing :cry:.')
                    elif len(root) == 1:
                        entry = root[0]
                    else:
                        msg = "**Please choose one by giving its number.**\n"
                        msg += "\n".join(['{} - {}'.format(n+1, entry[1].text) for n, entry in enumerate(root) if n < 10])

                        await self.bot.say(msg)  # Change to await response

                        check = lambda m: m.content in map(str, range(1, len(root)+1))
                        resp = await self.bot.wait_for_message(timeout=15, check=check)
                        if resp is None:
                            return

                        entry = root[int(resp.content)-1]

                    switcher = [
                        'english',
                        'score',
                        'type',
                        'episodes',
                        'volumes',
                        'chapters',
                        'status',
                        'start_date',
                        'end_date',
                        'synopsis'
                        ]

                    msg = '\n**{}**\n\n'.format(entry.find('title').text)
                    for k in switcher:
                        spec = entry.find(k)
                        if spec is not None and spec.text is not None:
                            msg += '**{}** {}\n'.format(k.capitalize()+':', html.unescape(spec.text.replace('<br />', '')))
                    msg += 'http://myanimelist.net/anime/{}'.format(entry.find('id').text)

                    await self.bot.say(msg)
        except:
            await self.bot.say("Your username or password is not correct." + "\n" +
                               "You need to create an account on myanimelist.net ." +
                               "\n" + "If you have an account use **<p>animeset** to set your credentials")


def check_folders():
    if not os.path.exists("data/animelist"):
        print("Creating data/animelist folder...")
        os.makedirs("data/animelist")


def check_files():
    system = {"Username": "",
              "Password": ""}

    f = "data/animelist/credentials.json"
    if not fileIO(f, "check"):
        print("Adding animelist credentials.json...")
        fileIO(f, "save", system)
    else:  # consistency check
        current = fileIO(f, "load")
        if current.keys() != system.keys():
            for key in system.keys():
                if key not in current.keys():
                    current[key] = system[key]
                    print("Adding " + str(key) +
                          " field to animelist credentials.json")
            fileIO(f, "save", current)


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Animelist(bot))
