# Developed by Redjumpman for Redbot
# Requires BeautifulSoup4, and Tabulate
import aiohttp
import math
import calendar
from datetime import date
from discord.ext import commands
from __main__ import send_cmd_help
try:   # check if BeautifulSoup4 is installed
    from bs4 import BeautifulSoup
    soupAvailable = True
except:
    soupAvailable = False
try:   # Check if Tabulate is installed
    from tabulate import tabulate
    tabulateAvailable = True
except:
    tabulateAvailable = False


class Tibia:
    """Tibia search cog."""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True)
    async def tibia(self, ctx):
        """This is the list of tibia queries you can perform."""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @tibia.command(name="item", pass_context=False)
    async def _item_tibia(self, *, item):
        """Get a item information from tibia wiki"""
        item = item.replace(" ", "_").title()
        if len(item) > 0:
            try:
                url = "http://tibia.wikia.com/wiki/" + str(item)
                async with aiohttp.get(url) as response:
                    soup = BeautifulSoup(await response.text(), "html.parser")
                    isearch = soup.find('div', attrs={'id': 'twbox-image'})
                    img = isearch.find("img")["src"]
                    # ----------------------------------------------------
                    try:
                        div1 = soup.find('div', attrs={'id': 'twbox-look'})
                        div2 = div1.find('div', attrs={'class': 'item-look'})
                        info = div2.get_text()
                    except:
                        info = "Could not find info"
                    # ----------------------------------------------------
                    div4 = soup.find('div', attrs={'id': 'tabular-data'})
                    table = div4.find('table', attrs={'class': 'infobox'})
                    rows = table.find_all('tr')
                    column1 = []
                    column2 = []
                    for row in rows:
                        cols = row.find_all('td', attrs={'class': 'property'})
                        cols = [ele.text.strip() for ele in cols]
                        column1.append([ele for ele in cols if ele])
                    for row in rows:
                        cols = row.find_all('td', attrs={'class': 'value'})
                        cols = [ele.text.strip() for ele in cols]
                        column2.append([ele for ele in cols if ele])
                    v = [x for xs in column1 for x in xs]
                    q = [x for xs in column2 for x in xs]
                    j = list(zip(v, q))
                    t = tabulate(j,  headers=["Property", "Value"])
                    # ----------------------------------------------------
                    try:
                        div3 = soup.find('div', attrs={'class': 'item-droppedby-wrapper'})
                        uls = div3.find('ul', attrs={'class': 'creature-list-generic'})
                        lis = uls.find_all('li')
                        results = []
                        for li in lis:
                            hols = li.find_all('a')
                            hols = [ele.text.strip() for ele in hols]
                            results.append([ele for ele in hols if ele])
                        d = [x for xs in results for x in xs]
                        g = "Creatures that drop this item" + "\n" + "-" * 80 + "\n"
                        k = g + self.column_maker(d, cols=3)
                    except ValueError:
                        try:
                            diva = soup.find('div', attrs={'class': 'spoiler-content'})
                            k = diva.get_text()
                        except AttributeError:
                            k = "This item is not dropped by any creatures or quest"

                    await self.bot.say(img + "\n")
                    await self.bot.say("```" + str(info) + "```")
                    await self.bot.say("```" + str(t) + "```")
                    await self.bot.say("```" + str(k) + "```")
            except:
                await self.bot.say("I could not find this item")
        else:
            await self.bot.say("Oh no! You didn't input a name. Type an" +
                               " item name to search")

    @tibia.command(name="monster", pass_context=False)
    async def _monster_tibia(self, *, monster):
        """Get a monster's information from tibia wiki"""
        monster = monster.replace(" ", "_").title()
        if len(monster) > 0:
            try:
                url = "http://tibia.wikia.com/wiki/" + str(monster)
                async with aiohttp.get(url) as response:
                    soup = BeautifulSoup(await response.text(), "html.parser")
                    # -------------------image------------------------------
                    try:
                        isearch = soup.find('div', attrs={'id': 'twbox-image'})
                        img = isearch.find("img")["src"]
                    except:
                        img = "No image found"
                    # ------------------Abilities----------------------------

                    div1 = soup.find('div', attrs={'id': 'creature-abilities'})
                    p = div1.find('p')
                    title = "Abilities" + "\n"
                    header1 = "Abilities" + "\n" + "-" * 80 + "\n"
                    abilities = p.get_text()
                    # ------------------------Loot------------------------
                    div2 = soup.find('div', attrs={'class': 'loot-table'})
                    ul = div2.find('ul')
                    lis = ul.find_all('li')
                    items = []
                    for li in lis:
                        hols = li.find_all('a')
                        hols = [ele.text.strip() for ele in hols]
                        items.append([ele for ele in hols if ele])
                    d = [x for xs in items for x in xs]
                    header = "Loot Table" + "\n" + "-" * 85 + "\n"
                    k = header + self.column_maker(d, cols=4)
                    # -------------------Table-Info--------------------------
                    div4 = soup.find('div', attrs={'id': 'tabular-data'})
                    table = div4.find('table')
                    rows = table.find_all('tr')
                    column1 = []
                    column2 = []
                    for row in rows:
                        cols = row.find_all('td', attrs={'class': 'property'})
                        cols = [ele.text.strip() for ele in cols]
                        column1.append([ele for ele in cols if ele])
                    for row in rows:
                        cols = row.find_all('td', attrs={'class': 'value'})
                        cols = [ele.text.strip() for ele in cols]
                        column2.append([ele for ele in cols if ele])
                    v = [x for xs in column1 for x in xs]
                    q = [x for xs in column2 for x in xs]
                    splitv = self.split_list(v, wanted_parts=2)
                    halfv1 = splitv[0]
                    halfv2 = splitv[1]
                    splitq = self.split_list(q, wanted_parts=2)
                    halfq1 = splitq[0]
                    halfq2 = splitq[1]
                    j = list(zip(halfv1, halfq1, halfv2, halfq2))
                    t = tabulate(j,  headers=["Property", "Value", "Property", "Value"])

                    # ------------------------OUTPUT-------------------------
                    await self.bot.say(img + "\n")
                    await self.bot.say("```" + title + header1 + str(abilities) + "```")
                    await self.bot.say("```" + str(k) + "```")
                    await self.bot.say("```" + str(t) + "```")
            except:
                await self.bot.say("I could not find this creature.")
        else:
            await self.bot.say("Oh no! You didn't input a name. Type an" +
                               " item name to search")

    @tibia.command(name="online", pass_context=False)
    async def _online_tibia(self):
        """Get total players playing"""
        url = "http://www.tibia.com/community/?subtopic=worlds"
        try:
            async with aiohttp.get(url) as response:
                soup = BeautifulSoup(await response.text(), "html.parser")
                div1 = soup.find('div', attrs={'id': 'RightArtwork'})
                div2 = div1.find('div', attrs={'id': 'PlayersOnline'})
                test = div2.get_text()
                test1 = test.replace("Players Online", "")
                new = "Players currently playing Tibia: " + test1
                # div2 = div1.find('div', attrs={'class': 'Border_2'})
                # div3 = div2.find('div', attrs={'class': 'Border_3'})
                # table = div3.find_all('table', attrs={'class': 'Table1'})
                # tr = table.find_all('tr')
                # tbody = div4.find('div', attrs={'class': 'CaptionInnerContainer'})
                await self.bot.say(str(new))
        except:
            await self.bot.say("Could not retrive data. The webserver may be offline.")

    @tibia.command(name="server", pass_context=False)
    async def _server_tibia(self, servername):
        """Get Server Info"""
        servername = servername.title()
        url = "https://secure.tibia.com/community/?subtopic=worlds&world=" + str(servername)
        try:
            async with aiohttp.get(url) as response:
                soup = BeautifulSoup(await response.text(), "html5lib")
                b = soup.find_all("table", attrs={'class': 'Table1'})
                new = []
                rows = b[1].tbody.div.find_all('td')
                for row in rows:
                    new.append(row.get_text())
                k = new[::2]
                l = new[1::2]
                zipped = list(zip(k, l))
                t = tabulate(zipped, headers=["Category", "Info"])
                await self.bot.say("```Python" + "\n" + str(t) + "```")
        except:
            await self.bot.say("Unable to retrive server data. The webserver may be offline.")

    @tibia.command(name="rashid", pass_context=False)
    async def _rashid_tibia(self):
        """Get Rashid's Location"""
        current_date = date.today()
        if calendar.day_name[current_date.weekday()] == "Sunday":
            await self.bot.say("On Sundays you can find him in Carlin depot, one floor above.")
        elif calendar.day_name[current_date.weekday()] == "Monday":
            await self.bot.say("On Mondays you can find him in Svargrond, in Dankwart's tavern, south of the temple.")
        elif calendar.day_name[current_date.weekday()] == "Tuesday":
            await self.bot.say("On Tuesdays you can find him in Liberty Bay, in Lyonel's tavern, west of the depot.")
        elif calendar.day_name[current_date.weekday()] == "Wednesday":
            await self.bot.say("On Wednesdays you can find him in Port Hope, in Clyde's tavern, north of the ship.")
        elif calendar.day_name[current_date.weekday()] == "Thursday":
            await self.bot.say("On Thursdays you can find him in Ankrahmun, in Arito's tavern, above the post office.")
        elif calendar.day_name[current_date.weekday()] == "Friday":
            await self.bot.say("On Fridays you can find him in Darashia, in Miraia's tavern, south of the guildhalls.")
        elif calendar.day_name[current_date.weekday()] == "Saturday":
            await self.bot.say("On Saturdays you can find him in Edron, in Mirabell's tavern, above the depot.")
        else:
            pass

    def split_list(self, alist, wanted_parts=1):
        length = len(alist)
        return [alist[i*length // wanted_parts: (i+1)*length // wanted_parts]
                for i in range(wanted_parts)]

    def column_maker(self, obj, cols=4, columnwise=True, spacing=4):
        """
        Print the given list in evenly-spaced columns.

        Parameters
        ----------
        obj : list
            The list to be printed.
        cols : int
            The number of columns in which the list should be printed.
        columnwise : bool, default=True
            If True, the items in the list will be printed column-wise.
            If False the items in the list will be printed row-wise.
        gap : int
            The number of spaces that should separate the longest column
            item/s from the next column. This is the effective spacing
            between columns based on the maximum len() of the list items.
        """

        if cols > len(obj): cols = len(obj)
        max_len = max([len(item) for item in obj])
        if columnwise: cols = int(math.ceil(float(len(obj)) / float(cols)))
        plist = [obj[i: i+cols] for i in range(0, len(obj), cols)]
        if columnwise:
            if not len(plist[-1]) == cols:
                plist[-1].extend(['']*(len(obj) - len(plist[-1])))
            plist = zip(*plist)
        printer = '\n'.join([
            ''.join([c.ljust(max_len + spacing) for c in p])
            for p in plist])
        return printer


def setup(bot):
    if soupAvailable:
        if tabulateAvailable:
            n = Tibia(bot)
            bot.add_cog(n)
        else:
            raise RuntimeError("You need to run 'pip3 install tabulate'")
    else:
        raise RuntimeError("You need to run 'pip3 install beautifulsoup4'")
