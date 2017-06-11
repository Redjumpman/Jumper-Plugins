# Developed by Redjumpman for Redbot by Twentysix26
# Inspired by Danny/Rapptz pokedex for Robo Danny

# Standard Library
import aiohttp
import random
import re

# Discord and Redbot
import discord
from discord.ext import commands
from __main__ import send_cmd_help

# Third Party Libraries
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

switcher = {
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6,
}

pokemon_exceptions = ["Beldum", "Burmy", "Cascoon", "Caterpie", "Combee", "Cosmoem", "Cosmog",
                      "Ditto", "Kakuna", "Kricketot", "Magikarp", "Unown", "Weedle", "Wobbuffet",
                      "Wurmple", "Wynaut", "Tynamo", "Metapod", "MissingNo.", "Scatterbug",
                      "Silcoon", "Smeargle"]

alolan_variants = ["Rattata", "Raticate", "Raichu", "Sandshrew", "Sandslash", "Vulpix", "Ninetales",
                   "Diglett", "Dugtrio", "Meowth", "Persian", "Geodude", "Graveler", "Golem",
                   "Grimer", "Muk", "Exeggutor", "Marowak"]


class Pokedex:
    """Search for Pokemon."""

    def __init__(self, bot):
        self.bot = bot
        self.version = "2.0.5"

    @commands.group(pass_context=True, aliases=["dex"])
    async def pokedex(self, ctx):
        """This is the list of pokemon queries you can perform."""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @pokedex.command(name="version", pass_context=False)
    async def _version_pokedex(self):
        """Get pokedex's version."""
        await self.bot.say("You are running pokedex version {}".format(self.version))

    @pokedex.command(name="pokemon", pass_context=False)
    async def _pokemon2_pokedex(self, pokemon: str):
        """Get a pokemon's pokedex info.
        Example !pokedex pokemon gengar"""
        url = "http://bulbapedia.bulbagarden.net/wiki/{}".format(pokemon)
        async with aiohttp.get(url) as response:
            try:
                soup = BeautifulSoup(await response.text(), "html.parser")
                tables = soup.find_all("table", attrs={"class": "roundy"})
                side_bar = tables[0]

                a_attrs = {"title": "List of Pokémon by National Pokédex number"}
                species = side_bar.find("a", attrs={"title": "Pokémon category"}).text.strip()
                national_number = side_bar.find("a", attrs=a_attrs).text.strip()
                japanese_name = side_bar.find("i").text.strip()

                # Abilities
                alolan = "Alolan {} Hidden Ability".format(pokemon.title())
                rep1 = {alolan: "*({})".format(alolan)}
                rep2 = {"Alolan {}".format(pokemon.title): "*(Alolan {})".format(pokemon.title())}
                rep3 = {"Battle Bond Ash-Greninja": "Battle Bond (Ash-Greninja)",
                        "{}".format(pokemon.title()): "({})".format(pokemon.title()),
                        "Cosplay Pikachu": " (Cosplay Pikachu)",
                        " Greninja": "",
                        "Gen. V-V I": "",  # Entei and Raikou
                        "Hidden Ability": "(Hidden Ability)"}
                rep1 = dict((re.escape(k), v) for k, v in rep1.items())
                pattern1 = re.compile("|".join(rep1.keys()))
                rep2 = dict((re.escape(k), v) for k, v in rep2.items())
                pattern2 = re.compile("|".join(rep2.keys()))
                rep3 = dict((re.escape(k), v) for k, v in rep3.items())
                pattern3 = re.compile("|".join(rep3.keys()))

                td1 = side_bar.find_all('td', attrs={'class': 'roundy', 'colspan': '2'})
                ab_raw = td1[1].find_all('td')
                exclusions = ["Cacophony", "CacophonySummer Form", "CacophonyAutumn Form"]
                if any(x for x in [x.get_text(strip=True) for x in ab_raw] for y in exclusions if y in x):
                    ab_strip = [x.get_text(strip=True)
                                for x in ab_raw if "Cacophony" not in x.get_text()]
                    ab_strip2 = [re.sub(r'\B(?=[A-Z])', r' ', x) for x in ab_strip]
                    ab_split = [" ".join([x.split()[0], "({} {})".format(x.split()[1], x.split()[2])])
                                if "Forme" in x else x for x in ab_strip2]
                    if [x for x in ab_split if "Forme" in x]:
                        formes = ab_split
                    else:
                        formes = None

                    ab = [pattern3.sub(lambda m: rep3[re.escape(m.group(0))], x) for x in ab_split]
                else:
                    td_attrs = {'width': '50%', 'style': 'padding-top:3px; padding-bottom:3px'}
                    td1 = side_bar.find_all('td', attrs=td_attrs)
                    ab = [td1[0].find('span').get_text()]
                    formes = None

                ab_format = self.abilities_parser(ab, pokemon, formes)

                # Types
                search_type = side_bar.find_all("table", attrs={"class": "roundy"})
                types_raw = search_type[2].find_all('b')
                types = [x.text.strip() for x in types_raw if x.text.strip() != "Unknown"]

                try:
                    types_output = "{}/{}".format(types[0], types[1])
                    if pokemon.title() == "Rotom":
                        types_temp = ("{0}/{1}  (Rotom)\n{2}/{3}  (Heat Rotom)\n"
                                      "{4}/{5}  (Wash Rotom)\n{6}/{7}  (Frost Rotom)\n"
                                      "{8}/{9}  (Fan Rotom)\n{10}/{11}  (Mow Rotom)\n")
                        types_output = types_temp.format(*types)
                except IndexError:
                    types_output = types[0]

                # Image
                img_raw = tables[2].find('a', attrs={'class', 'image'})
                img = "https:" + img_raw.find('img')['src']
                if pokemon.title() in ["Sawsbuck", "Deerling"]:
                    img_raw = tables[2].find_all('a', attrs={'class', 'image'})
                    img_set = [x.find('img')['src'] for x in img_raw]
                    img = "https:" + random.choice(img_set)

                # Stats
                rep_text = "Other Pokémon with this total"
                div = soup.find('div', attrs={'id': 'mw-content-text', 'lang': 'en', 'dir': 'ltr',
                                'class': 'mw-content-ltr'})
                stat_table = div.find('table', attrs={'align': 'left'})
                raw_stats = [x.get_text(strip=True) for x in stat_table.find_all('table')]
                stats = [x.replace(rep_text, "").replace(":", ": ") for x in raw_stats]

                # Weaknesses / Resistances
                if pokemon.title() != "Eevee":
                    wri_table = soup.find('table', attrs={'class': 'roundy', 'width': '100%',
                                          'align': 'center', 'cellpadding': 0})
                else:
                    tb_attrs = {'class': 'roundy', 'width': '100%',
                                'align': 'center', 'cellpadding': 0,
                                'style': 'border: 3px solid #6D6D4E; background: #A8A878;'}
                    wri_table = soup.find('table', attrs=tb_attrs)
                wri_stripped = wri_table.text.strip()
                wri_raw = wri_stripped.replace("\n", "")
                weak, resist = self.weak_resist_builder(wri_raw)

                # Color
                color = self.color_lookup(types[0])

                # Description
                table_attrs = {'width': '100%', 'class': 'roundy',
                               'style': 'background: transparent; border-collapse:collapse;'}
                info_search = div.find_all('table', attrs=table_attrs)
                info_table = info_search[0].find_all('td', attrs={'class': 'roundy'})
                description = info_table[0].text.strip()

                # Title
                wiki = "[{} {}]({})".format(pokemon.title(), national_number, url)
                embed_disc = "\n".join([wiki, japanese_name, species])

                # Build embed
                embed = discord.Embed(colour=color, description=embed_disc)
                embed.set_thumbnail(url=img)
                embed.add_field(name="Stats", value="\n".join(stats))
                embed.add_field(name="Types", value=types_output)
                embed.add_field(name="Resistances", value="\n".join(resist))
                embed.add_field(name="Weaknesses", value="\n".join(weak))
                embed.add_field(name="Abilities", value="\n".join(ab_format))
                embed.set_footer(text=description)

                await self.bot.say(embed=embed)
            except IndexError:
                await self.bot.say("I couldn't find a pokemon with that name.")

    @pokedex.command(name="moveset", pass_context=False)
    async def _moveset_pokedex(self, generation: str, pokemon: str):
        """Get a pokemon's moveset by generation(1-6).

          Example: !pokedex moveset V pikachu """
        if len(pokemon) > 0:
            gen = switcher.get(generation, 1)
            try:
                url = "http://pokemondb.net/pokedex/{}/moves/{}".format(pokemon, gen)
                async with aiohttp.get(url) as response:
                    soup = BeautifulSoup(await response.text(), "html.parser")
                    table = soup.find('table', attrs={'class': 'data-table wide-table'})
                    table_body = table.find('tbody')
                    rows = table_body.find_all('tr')
                    moves = []
                    for row in rows:
                        cols = [ele.text.strip() for ele in row.find_all('td')]
                        moves.append([ele for ele in cols if ele])
                    t = tabulate(moves, headers=["Level", "Moves", "Type", "Category", "Power",
                                                 "Accuracy"])
                    await self.bot.say("```{}```".format(t))
            except AttributeError:
                await self.bot.say("Could not locate a pokemon with that" +
                                   " name. Try a different name.")
        else:
            await self.bot.say("You need to input a pokemon name to search. "
                               "Input a name and try again.")

    @pokedex.command(name="tmset", pass_context=False)
    async def _tmset_pokedex(self, generation: str, pokemon: str):
        """Get a pokemon's learnset by generation(1-6).

          Example: !pokedex tmset V pikachu """
        if pokemon.title() in pokemon_exceptions:
            return await self.bot.say("This pokemon cannot learn TMs.")

        gen = switcher.get(generation, 1)
        try:
            url = "http://pokemondb.net/pokedex/{}/moves/{}".format(pokemon, gen)
            async with aiohttp.get(url) as response:
                soup = BeautifulSoup(await response.text(), "html.parser")
                div1 = soup.find_all('div', attrs={'class': 'col desk-span-6 lap-span-12'})
                div2 = div1[1].find_all('div', attrs={'class': 'colset span-full'})
                print("THIS MANY DIVS {}".format(len(div2)))
                if len(div2) == 1:
                    index = 0
                else:
                    index = 1
                table1 = div2[index].find('table', attrs={'class': 'data-table wide-table'})
                table_body = table1.find('tbody')
                rows = table_body.find_all('tr')
                moves = []
                for row in rows:
                    cols = row.find_all('td')
                    cols = [ele.text.strip() for ele in cols]
                    moves.append([ele for ele in cols if ele])
                headers = ["TM", "Moves", "Type", "Category", "Power", "Accuracy"]
                if len(moves) <= 30:
                    t = tabulate(moves, headers=headers)
                    await self.bot.say("```{}```".format(t))
                else:
                    half = int(len(moves) / 2)
                    part1 = moves[:half]
                    part2 = moves[half:]
                    t1 = tabulate(part1, headers=headers)
                    t2 = tabulate(part2, headers=headers)
                    await self.bot.say("```{}```".format(t1))
                    await self.bot.say("```{}```".format(t2))
        except IndexError:
            await self.bot.say("Oh no! That pokemon was not available in that generation.")
        except AttributeError:
            await self.bot.say("Could not locate a pokemon with that"
                               " name. Try a different name.")

    @pokedex.command(name="item", pass_context=False)
    async def _item_pokedex(self, *, item: str):
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
                except AttributeError:
                    await self.bot.say("Cannot find an item with this name")
        else:
            await self.bot.say("Please input an item name.")

    @pokedex.command(name="location", pass_context=False)
    async def _location_pokedex(self, pokemon: str):
        """Get a pokemon's catch location.
        Example !pokedex location voltorb
        """
        url = "http://pokemondb.net/pokedex/{}".format(pokemon)
        async with aiohttp.get(url) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")
            loc = []
            version = []
            div2 = soup.find('div', attrs={'class': 'col desk-span-7 lap-span-12'})
            tables = div2.find_all('table', attrs={'class': 'vitals-table'})
            for table in tables:
                cols = [ele.text.strip() for ele in table.find_all('td')]
                loc.append([ele for ele in cols if ele])

            tables2 = div2.find_all('table', attrs={'class': 'vitals-table'})

            for table2 in tables2:
                tcols = [ele.text.strip() for ele in table2.find_all('th')]
                version.append([ele for ele in tcols if ele])
            # We have to extract out the base index, because it scrapes as
            # a list of a list. Then we can stack and tabulate.
            extract_loc = loc[0]
            extract_version = version[0]
            m = list(zip(extract_version, extract_loc))
            t = tabulate(m, headers=["Game Version", "Location"])

            await self.bot.say("```{}```".format(t))

    @pokedex.command(name="evolution", pass_context=False)
    async def _evolution_pokedex(self, pokemon: str):
        """Show a pokemon's evolution chain
        Example !pokedex evolution bulbasaur"""
        url = "http://pokemondb.net/pokedex/{}".format(pokemon)
        async with aiohttp.get(url) as response:
            try:
                soup = BeautifulSoup(await response.text(), "html.parser")
                div = soup.find('div', attrs={'class':
                                              'infocard-evo-list'})
                evo = div.text.strip()
                await self.bot.say("```{}```".format(evo))
            except AttributeError:
                await self.bot.say("{} does not have an evolution chain".format(pokemon))

    def color_lookup(self, key):
        color_table = {"Normal": 0x999966, "Fire": 0xFF6600, "Fighting": 0xFF0000,
                       "Water": 0x3399FF, "Flying": 0x9999FF, "Grass": 0x33FF00, "Poison": 0x660099,
                       "Electric": 0xFFFF00, "Ground": 0xFFCC33, "Psychic": 0xFF3399,
                       "Rock": 0xCC9966, "Ice": 0x99FFFF, "Bug": 0x669900, "Dragon": 0x003399,
                       "Ghost": 0x9933FF, "Dark": 0x333333, "Steel": 0x999999, "Fairy": 0xFF99FF}
        color = color_table.get(key, 0xFFFFFF)
        return color

    def abilities_parser(self, abilities, pokemon, formes=None):
        link = "http://bulbapedia.bulbagarden.net/wiki/"
        rep = {"(Hidden Ability)": "",
               "(Ash-Greninja)": "",
               "(Cosplay Pikachu)": "",
               "({})".format(pokemon.title()): "",
               " ": "_"}
        if formes:
            for x in formes:
                rep[x] = ""
        rep = dict((re.escape(k), v) for k, v in rep.items())
        pattern = re.compile("|".join(rep.keys()))
        fmt = "[{}]({}{}) ({})"

        if len(abilities) < 2:
            ab_linked = "[{}]({}{})".format(abilities[0], link, [abilities[0]])

        if [x for x in abilities if "or " and pokemon.title() in abilities]:
            abilities = [re.split(' or |\*', x) if 'or' in x else x for x in abilities]
            ab_linked = [fmt.format(re.sub(r'\((.*?)\)', '', x), link,
                         pattern.sub(lambda m: rep[re.escape(m.group(0))], x),
                         re.search(r'\((.*?)\)', x).group(1)) if "(Hidden Ability)" in x
                         else "[{0}]({2}{3}) or [{1}]({2}{4})".format(x[0], x[1], link,
                         pattern.sub(lambda m: rep[re.escape(m.group(0))], x[0]),
                         pattern.sub(lambda m: rep[re.escape(m.group(0))], x[1]))
                         for x in abilities]

        elif "or " in abilities[0]:
            split = abilities[0].split('or ', 1)
            del abilities[0]
            abilities.append(split)
            ab_linked = [fmt.format(re.sub(r'\((.*?)\)', '', x), link,
                         pattern.sub(lambda m: rep[re.escape(m.group(0))], x),
                         re.search(r'\((.*?)\)', x).group(1)) if "(Hidden Ability)" in x
                         else "[{0}]({2}{3}) or [{1}]({2}{4})".format(x[0], x[1], link,
                         pattern.sub(lambda m: rep[re.escape(m.group(0))], x[0]),
                         pattern.sub(lambda m: rep[re.escape(m.group(0))], x[1]))
                         for x in abilities]
            ab_linked.reverse()
        else:
            ab_linked = [fmt.format(re.sub(r' \((.*?)\)', '', x), link,
                         pattern.sub(lambda m: rep[re.escape(m.group(0))], x),
                         re.search(r'\((.*?)\)', x).group(1)) if "(" in x
                         else "[{}]({}{})".format(x, link,
                         pattern.sub(lambda m: rep[re.escape(m.group(0))], x))
                         for x in abilities]
        return ab_linked

    def weak_resist_builder(self, raw):
        output = []
        types = ["Normal", "Flying", "Poison", "Ground", "Rock", "Dragon", "Fighting",
                 "Bug", "Grass", "Electric", "Fairy", "Psychic", "Ghost", "Steel",
                 "Fire", "Water", "Ice", "Dark", "None"]

        for x in types:
            match = re.search(r'{} (\w+)'.format(x), raw)
            if match:
                item = match.group(0)
                if item.startswith('ug'):
                    item = "B" + item
                if "1" in item:
                    pass
                else:
                    output.append(item)
            else:
                pass
        result = [x.replace('½', "0.5").replace('¼', "0.25") + "x" for x in output]
        weak = [x for x in result if "2x" in x or "4x" in x]
        resist = [x for x in result if "0.5x" in x or "0.25x" in x]

        if len(weak) == 0:
            weak = ["None"]

        if len(resist) == 0:
            resist = ["None"]

        return weak, resist


def setup(bot):
    if not soupAvailable:
        raise RuntimeError("You need to run \'pip3 install beautifulsoup4\' in command prompt.")
    elif not tabulateAvailable:
        raise RuntimeError("You need to run \'pip3 install tabulate\' in command prompt.")
    else:
        bot.add_cog(Pokedex(bot))
