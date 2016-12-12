# Developed by Redjumpman for Redbot by Twentysix26
# Requires BeautifulSoup4, and Tabulate to work.
import aiohttp
from discord.ext import commands
from __main__ import send_cmd_help
try:   # check if BeautifulSoup4 is installed
    from bs4 import BeautifulSoup
    soupAvailable = True
except ImportError:
    soupAvailable = False
try:   # Check if Tabulate is installed
    from tabulate import tabulate
    tabulateAvailable = True
except ImportError:
    tabulateAvailable = False


class Pokedex:
    """Search for Pokemon."""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True, aliases=["dex"])
    async def pokedex(self, ctx):
        """This is the list of pokemon queries you can perform."""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @pokedex.command(name="pokemon", pass_context=False)
    async def _pokemon_pokedex(self, pokemon):
        """Get a pokemon's pokedex info.
        Example !pokedex pokemon gengar"""
        if len(pokemon) > 0:
            url = "http://pokemondb.net/pokedex/{}".format(pokemon)
            try:
                async with aiohttp.get(url) as response:
                    soup = BeautifulSoup(await response.text(), "html.parser")
                    # FIXME This scrapes the pokemon image
                    img_par = soup.find('div', attrs={'class': "col desk-span-4 lap-span-6 figure"})
                    img = img_par.find("img")["src"]
                    print(img)
                    poke = []
                    pokeh = []
                    table = soup.find('table', attrs={'class': 'vitals-table'})
                    table_body = table.find('tbody')
                    headers = table_body.find_all('tr')
                # -------------------Pokedex-Info----------------------------
                    dex_table = soup.find_all('table', attrs={'class': 'vitals-table'})
                    dex_rows = dex_table[4].find_all('tr')
                    dex_info1 = dex_rows[0]
                    dex_info2 = dex_rows[1]
                    dex_text1 = dex_info1.get_text().replace("RedBlue", "")
                    dex_text2 = dex_info2.get_text().replace("Yellow", "")
                # -------------------Pokedex-Info-End---------------------------
                    for head in headers:
                        hols = head.find_all('th')
                        hols = [ele.text.strip() for ele in hols]
                        pokeh.append([ele for ele in hols if ele])

                    rows = table_body.find_all('tr')

                    for row in rows:
                        cols = row.find_all('td')
                        cols = [ele.text.strip() for ele in cols]
                        poke.append([ele for ele in cols if ele])

                    poke2 = [x for xs in poke for x in xs]
                    pokeh2 = [x for xs in pokeh for x in xs]
                    m = list(zip(pokeh2, poke2))

                    t = tabulate(m, headers=["Pokedex", "Data"])

                    await self.bot.say("\n```{}```".format(t))
                    await self.bot.say("```" + dex_text1 + "\n" + dex_text2 + "```")
                    await self.bot.say(img)
            except:
                    await self.bot.say("Could not locate that pokemon." +
                                       " Please try a different name"
                                       )
        else:
            await self.bot.say("Oh no! You didn't input a name. Type a pokemon name to search")

    @pokedex.command(name="stats", pass_context=False)
    async def _stats_pokedex(self, pokemon):
        """Get a pokemon's base stats.
        Example: !pokedex stats squirtle"""
        if len(pokemon) > 0:
            url = "http://pokemondb.net/pokedex/{}".format(pokemon)
            async with aiohttp.get(url) as response:
                try:
                    soup = BeautifulSoup(await response.text(), "html.parser")
                    stats = []

                    base = [["HP"], ["Def"], ["ATK"], ["Sp.Atk"], ["Sp.Def"],
                            ["Speed"]
                            ]
                    divs = soup.find('div', attrs={'class': 'col span-8 '})
                    table = divs.find('table', attrs={'class': 'vitals-table'})
                    table_body = table.find('tbody')

                    rows = table_body.find_all('tr')
                    for row in rows:
                        cols = row.find_all('td')
                        cols = [ele.text.strip() for ele in cols]
                        stats.append([ele for ele in cols if ele])

                    statbase = [from_a2 + from_a1
                                for from_a2, from_a1 in zip(base, stats)]

                    k = filter(None, statbase)

                    t = tabulate(k, headers=["Stat", "Base", "Min", "Max"])
                    await self.bot.say("```" + t + "```")
                except:
                    await self.bot.say("Could not locate that pokemon's" +
                                       " stats. Please try a different name"
                                       )
        else:
            await self.bot.say("Looks like you forgot to put in a pokemon" +
                               " name. Input a name to search"
                               )

    @pokedex.command(name="moveset", pass_context=False)
    async def _moveset_pokedex(self, generation: str, pokemon):
        """Get a pokemon's moveset by generation(1-6).

          Example: !pokedex moveset V pikachu """
        if len(pokemon) > 0:
            if generation == "6" or generation == "VI":
                try:
                    url = "http://pokemondb.net/pokedex/{}/moves/6".format(pokemon)
                    async with aiohttp.get(url) as response:
                        soup = BeautifulSoup(await response.text(),
                                             "html.parser"
                                             )
                        moves = []
                        table = soup.find('table',
                                          attrs={'class':
                                                 'data-table wide-table'
                                                 }
                                          )
                        table_body = table.find('tbody')
                        rows = table_body.find_all('tr')
                        for row in rows:
                            cols = row.find_all('td')
                            cols = [ele.text.strip() for ele in cols]
                            moves.append([ele for ele in cols if ele])

                        t = tabulate(moves, headers=["Level", "Moves", "Type",
                                                     "Category", "Power",
                                                     "Accuracy"])
                        await self.bot.say("```{}```".format(t))
                except:
                    await self.bot.say("Could not locate a pokemon with that" +
                                       " name. Try a different name.")

            elif generation == "5" or generation == "V":
                try:
                    url = "http://pokemondb.net/pokedex/{}/moves/5".format(pokemon)
                    async with aiohttp.get(url) as response:
                        soup = BeautifulSoup(await response.text(),
                                             "html.parser")
                        moves = []
                        table = soup.find('table', attrs={'class':
                                          'data-table wide-table'}
                                          )
                        table_body = table.find('tbody')

                        rows = table_body.find_all('tr')
                        for row in rows:
                            cols = row.find_all('td')
                            cols = [ele.text.strip() for ele in cols]
                            moves.append([ele for ele in cols if ele])

                        t = tabulate(moves, headers=["Level", "Moves", "Type",
                                                     "Category", "Power",
                                                     "Accuracy"])
                        await self.bot.say("```{}```".format(t))
                except:
                    await self.bot.say("Could not locate a pokemon with that" +
                                       " name. Try a different name.")

            elif generation == "4" or generation == "IV":
                try:
                    url = "http://pokemondb.net/pokedex/{}/moves/4".format(pokemon)
                    async with aiohttp.get(url) as response:
                        soup = BeautifulSoup(await response.text(),
                                             "html.parser")
                        moves = []
                        table = soup.find('table',
                                          attrs={'class':
                                                 'data-table wide-table'}
                                          )
                        table_body = table.find('tbody')

                        rows = table_body.find_all('tr')
                        for row in rows:
                            cols = row.find_all('td')
                            cols = [ele.text.strip() for ele in cols]
                            moves.append([ele for ele in cols if ele])

                        t = tabulate(moves, headers=["Level", "Moves", "Type",
                                                     "Category", "Power",
                                                     "Accuracy"])
                        await self.bot.say("```{}```".format(t))
                except:
                    await self.bot.say("Could not locate a pokemon with that" +
                                       " name. Try a different name.")

            elif generation == "3" or generation == "III":
                try:
                    url = "http://pokemondb.net/pokedex/{}/moves/3".format(pokemon)
                    async with aiohttp.get(url) as response:
                        soup = BeautifulSoup(await response.text(),
                                             "html.parser")
                        moves = []
                        table = soup.find('table', attrs={'class':
                                          'data-table wide-table'}
                                          )
                        table_body = table.find('tbody')

                        rows = table_body.find_all('tr')
                        for row in rows:
                            cols = row.find_all('td')
                            cols = [ele.text.strip() for ele in cols]
                            moves.append([ele for ele in cols if ele])

                        t = tabulate(moves, headers=["Level", "Moves", "Type",
                                                     "Category", "Power",
                                                     "Accuracy"])
                        await self.bot.say("```{}```".format(t))
                except:
                    await self.bot.say("Could not locate a pokemon with that" +
                                       " name. Try a different name.")

            elif generation == "2" or generation == "II":
                try:
                    url = "http://pokemondb.net/pokedex/{}/moves/2".format(pokemon)
                    async with aiohttp.get(url) as response:
                        soup = BeautifulSoup(await response.text(),
                                             "html.parser")
                        moves = []
                        table = soup.find('table', attrs={'class':
                                          'data-table wide-table'}
                                          )
                        table_body = table.find('tbody')

                        rows = table_body.find_all('tr')
                        for row in rows:
                            cols = row.find_all('td')
                            cols = [ele.text.strip() for ele in cols]
                            moves.append([ele for ele in cols if ele])

                        t = tabulate(moves, headers=["Level", "Moves", "Type",
                                                     "Category", "Power",
                                                     "Accuracy"])
                        await self.bot.say("```{}```".format(t))
                except:
                    await self.bot.say("Could not locate a pokemon with that" +
                                       " name. Try a different name.")

            elif generation == "1" or generation == "I":
                try:
                    url = "http://pokemondb.net/pokedex/{}/moves/1".format(pokemon)
                    url += "/moves/1"
                    async with aiohttp.get(url) as response:
                        soup = BeautifulSoup(await response.text(),
                                             "html.parser")
                        moves = []
                        table = soup.find('table', attrs={'class':
                                          'data-table wide-table'}
                                          )
                        table_body = table.find('tbody')

                        rows = table_body.find_all('tr')
                        for row in rows:
                            cols = row.find_all('td')
                            cols = [ele.text.strip() for ele in cols]
                            moves.append([ele for ele in cols if ele])

                        t = tabulate(moves, headers=["Level", "Moves", "Type",
                                                     "Category", "Power",
                                                     "Accuracy"])
                        await self.bot.say("```{}```".format(t))
                except:
                    await self.bot.say("Could not locate a pokemon with that" +
                                       " name. Try a different name.")
            else:
                await self.bot.say("Generation must be " + "**" + "1-6" +
                                   "**" + " or **" + "I-VI**.")

        else:
            await self.bot.say("You need to input a pokemon name to search. "
                               "Input a name and try again.")

    @pokedex.command(name="item", pass_context=False)
    async def _item_pokedex(self, *, item):
        """Get a description of an item.
        Use '-' for spaces. Example: !pokedex item master-ball
        """
        if len(item) > 0:
            item = item.replace(" ", "-").lower()
            url = "http://pokemondb.net/item/{}".format(item)
            async with aiohttp.get(url) as response:
                try:
                    soup = BeautifulSoup(await response.text(), "html.parser")
                    divs = soup.find('p')
                    info = divs.get_text()

                    await self.bot.say("**{}:**\n```{}```".format(item.title(), info))
                except:
                    await self.bot.say("Cannot find an item with this name")
        else:
            await self.bot.say("Please input an item name.")

    @pokedex.command(name="location", pass_context=False)
    async def _location_pokedex(self, pokemon):
        """Get a pokemon's catch location.
        Example !pokedex location voltorb
        """
        if len(pokemon) > 0:
            url = "http://pokemondb.net/pokedex/{}".format(pokemon)
            async with aiohttp.get(url) as response:
                soup = BeautifulSoup(await response.text(), "html.parser")
                loc = []
                version = []
                div2 = soup.find('div', attrs={'class':
                                               'col desk-span-7 lap-span-12'})
                tables = div2.find_all('table', attrs={'class':
                                       'vitals-table'})
                for table in tables:
                    cols = table.find_all('td')
                    cols = [ele.text.strip() for ele in cols]
                    loc.append([ele for ele in cols if ele])
                tables2 = div2.find_all('table', attrs={'class':
                                        'vitals-table'})
                for table2 in tables2:
                    tcols = table2.find_all('th')
                    tcols = [ele.text.strip() for ele in tcols]
                    version.append([ele for ele in tcols if ele])
                # We have to extract out the base index, because it scrapes as
                # a list of a list. Then we can stack and tabulate.
                extract_loc = loc[0]
                extract_version = version[0]
                m = list(zip(extract_version, extract_loc))
                t = tabulate(m, headers=["Game Version", "Location"])

                await self.bot.say("```{}```".format(t))
        else:
            await self.bot.say("Unable to find any locations" +
                               "Check your spelling or try a different name."
                               )

    @pokedex.command(name="evolution", pass_context=False)
    async def _evolution_pokedex(self, pokemon):
        """Show a pokemon's evolution chain
        Example !pokedex evolution bulbasaur"""
        if len(pokemon) > 0:
            url = "http://pokemondb.net/pokedex/{}".format(pokemon)
            async with aiohttp.get(url) as response:
                try:
                    soup = BeautifulSoup(await response.text(), "html.parser")
                    div = soup.find('div', attrs={'class':
                                                  'infocard-evo-list'})
                    evo = div.text.strip()
                    await self.bot.say("```{}```".format(evo))
                except:
                    await self.bot.say("{} does not have an evolution chain".format(pokemon))
        else:
            await self.bot.say("Please input a pokemon name.")


def setup(bot):
    if not soupAvailable:
        raise RuntimeError("You need to run \'pip3 install beautifulsoup4\' in command prompt.")
    elif not tabulateAvailable:
        raise RuntimeError("You need to run \'pip3 install tabulate\' in command prompt.")
    else:
        bot.add_cog(Pokedex(bot))
