# Developed by Redjumpman for Red DiscordBot.
# Ported from mee6bot to work for Red
# Original credit and design goes to mee6

# Standard Library
import asyncio
import aiohttp
import html
import random
import re
from xml.etree import ElementTree
from collections import namedtuple

# Red
from redbot.core import Config, commands

# Discord
import discord

switcher = ['english', 'score', 'type', 'episodes', 'volumes', 'chapters', 'status',
            'start_date', 'end_date']


class AnimeList:
    """Fetch info about an anime title"""
    global_defaults = {"Username": "", "Password": ""}
    user_defaults = {"Username": ""}

    def __init__(self, bot):
        self.bot = bot
        self.db = Config.get_conf(self, 5074395002, force_registration=True)
        self.db.register_global(**self.global_defaults)
        self.db.register_user(**self.user_defaults)
        self.connector = aiohttp.TCPConnector(force_close=True)
        self.session = aiohttp.ClientSession(connector=self.connector)

    @commands.command()
    @commands.is_owner()
    async def animeset(self, ctx):
        """Sets your username and password from myanimelist"""
        await self.owner_set(ctx)

    @commands.command()
    async def anime(self, ctx, *, title):
        """Shows MAL information on an anime"""
        cmd = "anime"
        await self.search_command(ctx, cmd, title)

    @commands.command()
    async def manga(self, ctx, *, title):
        """Shows MAL information on a manga"""
        cmd = "manga"
        await self.search_command(ctx, cmd, title)

    @commands.group()
    async def mal(self, ctx):
        """MAL Search Commands"""

        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @mal.command(name="anime")
    async def _anime(self, ctx, user: discord.Member=None):
        """Lookup another user's MAL for anime"""
        author = ctx.author
        cmd = "anime"
        if not user:
            user = author
        await self.fetch_profile(ctx, user, author, cmd)

    @mal.command(name="manga")
    async def _manga(self, ctx, user: discord.Member=None):
        """Lookup another user's MAL for manga"""
        author = ctx.author
        cmd = "manga"
        if not user:
            user = author
        await self.fetch_profile(ctx, user, author, cmd)

    @mal.command(name="set")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def _set(self, ctx, username):
        """Set your MAL username
        You can change your username once every 30 seconds.
        """
        author = ctx.author
        await self.db.user(author).Username.set(username)
        await ctx.send("MAL profile set for {}".format(ctx.author.name))

    async def search_command(self, ctx, cmd, title):
        if await self.verify_credentials():
            try:
                await self.fetch_info(ctx, cmd, title)
            except aiohttp.client_exceptions.ClientResponseError:
                return await ctx.send("Could not find a title with that name.")
        else:
            await ctx.send("The bot owner has not setup their credentials. "
                           "An account on <https://myanimelist.net> is required. "
                           "When the owner is ready, setup this cog with {}animeset "
                           "to enter the credentials".format(ctx.prefix))

    async def fetch_profile(self, ctx, user, author, cmd):
        user_name = await self.name_lookup(user)
        author_name = await self.name_lookup(author)

        url = "https://myanimelist.net/malappinfo.php?u={}&status=all&type=" + cmd
        user_col, user_data = await self.fetch_user_mal(user_name, url, cmd)
        if not user_col:
            return await ctx.send("I couldn't find a profile with that name.")
        if user == author:
            author_col = "SELF"
        else:
            author_col, _ = await self.fetch_user_mal(author_name, url, cmd)

        table_data = self.build_data(author_col, user_col, cmd, user_name, user)

        await self.send_profile(ctx, user_data, table_data)

    def build_data(self, author_col, user_col, cmd, name, user):
        share, diff = self.find_diff(author_col, user_col)
        share = '\n'.join(share) if isinstance(share, list) else share
        diff = '\n'.join(diff) if isinstance(diff, list) else diff
        medium, emoji = self.get_medium(cmd)
        description = self.build_link(name, user, cmd, user_col)
        url = "https://myanimelist.cdn-dena.com/img/sp/icon/apple-touch-icon-256.png"
        calendar = ":calendar_spiral: Days Spent {}".format(medium)
        Data = namedtuple('Data', ['share', 'diff', 'medium', 'emojis', 'desc', 'url', 'calendar'])
        return Data(share, diff, medium, emoji, description, url, calendar)

    async def owner_set(self, ctx):
        timeout = "Username and Password setup timed out."

        def predicate(m):
            return m.author == ctx.author

        await ctx.author.send("Please specify your username.\n*This data is kept on your computer*")
        try:
            username = await ctx.bot.wait_for('message', timeout=15, check=predicate)
        except asyncio.TimeoutError:
            return await ctx.author.send(timeout)

        await ctx.author.send("Ok thanks. Now what is your password?")
        try:
            password = await ctx.bot.wait_for('message', timeout=15, check=predicate)
        except asyncio.TimeoutError:
            return await ctx.author.send(timeout)

        if await self.credential_verfication(ctx, username.content, password.content):
            await self.db.Password.set(password.content)
            await self.db.Username.set(username.content)
            await ctx.author.send("Setup complete. Account details added.\nTry searching for "
                                  "an anime using {}anime".format(ctx.prefix))
            return

    async def name_lookup(self, name):
        acc_name = await self.db.user(name).Username()
        if not acc_name:
            return name.name
        else:
            return acc_name

    async def fetch_info(self, ctx, cmd, title):
        data = await self.get_xml(cmd, title)

        try:
            root = ElementTree.fromstring(data)

        except ElementTree.ParseError:
            return await ctx.send("I couldn't find anything!")

        entry, menu = await self.get_entry(root, ctx)

        link = 'http://myanimelist.net/{}/{}'.format(cmd, entry.find('id').text)
        desc = "MAL [{}]({})".format(entry.find('title').text, link)
        title = entry.find('title').text
        synopsis = self.get_synopsis(entry, title)

        # Build Embed
        embed = discord.Embed(colour=0x0066FF, description=desc)
        embed.title = title
        embed.set_thumbnail(url=entry.find('image').text)
        embed.set_footer(text=synopsis)

        for k in switcher:
            spec = entry.find(k)
            if spec is not None and spec.text is not None:
                embed.add_field(name=k.capitalize(),
                                value=html.unescape(spec.text.replace('<br />', '')))
        if menu:
            await menu.edit(embed=embed)
        else:
            await ctx.send(embed=embed)

    async def get_xml(self, nature, name):
        username = await self.db.Username()
        password = await self.db.Password()
        name = name.replace(" ", "_")
        auth = aiohttp.BasicAuth(login=username, password=password)
        url = 'https://myanimelist.net/api/{}/search.xml?q={}'.format(nature, name)
        async with self.session.request('GET', url, auth=auth) as response:
            data = await response.text()
            return data

    async def verify_credentials(self):
        username = await self.db.Username()
        password = await self.db.Password()
        if username == '' or password == '':
            return False
        else:
            return True

    async def credential_verfication(self, ctx, username, password):
        auth = aiohttp.BasicAuth(login=username, password=password)
        url = "https://myanimelist.net/api/account/verify_credentials.xml"
        async with self.session.request('GET', url, auth=auth) as response:
            status = response.status

            if status == 200:
                return True

            if status == 401:
                await ctx.send("Username and Password is incorrect.")
                return False

            if status == 403:
                msg = ("You have either failed too many login attemps, or you have not logged "
                       "on to the mal website in a long time. Run this command again when "
                       "these issues are resolved.")
                await ctx.send(msg)
                return False

    async def fetch_user_mal(self, name, url, cmd):
        async with self.session.request('GET', url.format(name)) as response:
            data = await response.text()
            try:
                root = ElementTree.fromstring(data)

            except ElementTree.ParseError:
                return '', ''

            else:
                if len(root) == 0:
                    return '', ''

                collection = {x.find('series_title').text for x in root.findall(cmd)}
                entry = root.find('myinfo')
                if cmd == "anime":
                    info = [entry.find(x).text for x in ['user_watching', 'user_completed',
                                                         'user_onhold', 'user_dropped',
                                                         'user_days_spent_watching']]
                    return collection, info
                else:
                    info = [entry.find(x).text for x in ['user_reading', 'user_completed',
                                                         'user_onhold', 'user_dropped',
                                                         'user_days_spent_watching']]
                    return collection, info

    @staticmethod
    async def get_entry(root, ctx):
        if len(root) == 1:
            return root[0], None
        else:
            msg = "**Please choose one by giving its number.**\n"
            desc = "\n".join(['{} - {}'.format(n + 1, entry[1].text)
                              for n, entry in enumerate(root) if n < 10])
            embed = discord.Embed(colour=0x0066FF, title=msg, description=desc)
            menu = await ctx.send(embed=embed)

            def predicate(m):
                if m.author == ctx.author:
                    return m.content.isdigit() and int(m.content) in range(1, len(root) + 1)
                else:
                    return False

            try:
                resp = await ctx.bot.wait_for('message', timeout=15, check=predicate)
            except asyncio.TimeoutError:
                await menu.delete()
                return
            idx = int(resp.content) - 1
            await resp.delete()
            return root[idx], menu

    @staticmethod
    async def send_profile(ctx, user_data, mal):
        embed = discord.Embed(colour=0x0066FF, description=mal.desc)
        embed.title = "My Anime List Profile"
        embed.set_thumbnail(url=mal.url)
        embed.add_field(name=mal.calendar, value=user_data[4], inline=False)
        embed.add_field(name="{[0]} {}".format(mal.emojis, mal.medium), value=user_data[0])
        embed.add_field(name="{[0]} Completed".format(mal.emojis), value=user_data[1])
        embed.add_field(name="{[2]} On Hold".format(mal.emojis), value=user_data[2])
        embed.add_field(name=":wastebasket: Dropped", value=user_data[3])
        embed.add_field(name=":link: Five Shared", value=mal.share, inline=False)
        embed.add_field(name=":trident: Five Different", value=mal.diff)
        await ctx.send(embed=embed)

    @staticmethod
    def get_synopsis(entry, title):
        syn_raw = entry.find('synopsis').text
        if syn_raw:
            replace = {'&quot;': '\"', '<br />': '', '&mdash;': ' - ', '&#039;': '\'',
                       '&ldquo;': '\"', '&rdquo;': '\"', '[i]': '*', '[/i]': '*', '[b]': '**',
                       '[/b]': '**', '[url=': '', ']': ' - ', '[/url]': ''}
            rep_sorted = sorted(replace, key=lambda s: len(s[0]), reverse=True)
            rep_escaped = [re.escape(replacement) for replacement in rep_sorted]
            pattern = re.compile("|".join(rep_escaped), re.I)
            return pattern.sub(lambda match: replace[match.group(0)], entry.find('synopsis').text)
        else:
            return "There is not a synopsis for {}".format(title)

    @staticmethod
    def find_diff(author, user):
        if author == "SELF":
            return ['Not Applicable'] * 2
        elif author:
            intersect = user.intersection(author)
            difference = author.difference(user)
            share = random.sample(intersect, len(intersect) if len(intersect) < 5 else 5)
            different = random.sample(difference, len(difference) if len(difference) < 5 else 5)
            if not share:
                share = ["Nothing Mutual"]
            if not different:
                different = ["Nothing different"]
            return share, different
        else:
            return ["Author's MAL not set"] * 2

    @staticmethod
    def get_medium(cmd):
        if cmd == "anime":
            return "Watching", [":film_frames:", ":vhs:", ":octagonal_sign:"]
        else:
            return "Reading", [":book:", ":books:", ":bookmark:"]

    @staticmethod
    def build_link(name, user, cmd, user_col):
        link = "https://myanimelist.net/animelist/{}".format(name)
        description = ("**{}**\n[{}]({})\nTotal {}: "
                       "{}".format(user.name, name, link, cmd.title(), len(user_col)))
        return description

    def __unload(self):
        self.session.close()
