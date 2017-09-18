# Developed by Redjumpman for Redbot by Twentysix26
# Inspired by Danny/Rapptz pokedex for Robo Danny

# Standard Library
import aiohttp
import ast
import csv
import re
from collections import namedtuple

# Discord and Redbot
import discord
from discord.ext import commands
from __main__ import send_cmd_help

# Third Party Libraries
from bs4 import BeautifulSoup
from tabulate import tabulate

switcher = {
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7}

exceptions = {'ho-oh', 'jangmo-o', 'hakamo-o', 'kommo-o', 'porygon-z', 'nidoran-f', 'nidoran-m'}
tm_exceptions = {"Beldum", "Burmy", "Cascoon", "Caterpie", "Combee", "Cosmoem", "Cosmog",
                 "Ditto", "Kakuna", "Kricketot", "Magikarp", "Unown", "Weedle", "Wobbuffet",
                 "Wurmple", "Wynaut", "Tynamo", "Metapod", "MissingNo.", "Scatterbug",
                 "Silcoon", "Smeargle"}

url = "https://bulbapedia.bulbagarden.net/wiki/{}_(Pokémon\)"
url2 = "https://bulbapedia.bulbagarden.net/wiki/"
url4 = 'test'

class Pokedex:
    """Search for Pokemon."""

    def __init__(self, bot):
        self.bot = bot
        self.version = "2.3.02"

    @commands.group(pass_context=True)
    async def pokemon(self, ctx):
        """This is the list of Pokémon queries you can perform."""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @pokemon.command(name="version", pass_context=False)
    async def _version_pokemon(self):
        """Display running version of Pokedex

            Returns:
                Text ouput of your installed version of Pokedex
        """
        await self.bot.say("You are running pokedex version {}".format(self.version))

    @commands.command(aliases=["dex"])
    async def pokedex(self, *, pokemon: str):
        """Search for information on a Pokémon

            Args:
                pokemon: variable length string.

            Returns:
                Embed output of pokemon data.

            Raises:
                AttributeError: Pokémon not found.

            Examples:
                Regular:    [p]pokedex pikachu
                Megas:      [p]pokedex charizard-mega y
                Alola:      [p]pokedex geodude-alola
                Forms:      [p]pokedex hoopa-unbound
                Variants:   [p]pokedex floette-orange
        """

        link_name = self.link_builder(pokemon)
        poke = self.search_pokemon(pokemon.title(), link_name)

        try:
            color = self.color_lookup(poke.types)
        except AttributeError:
            await self.bot.say('A Pokémon with that name could not be found.')
        else:
            abilities = self.ability_builder(poke.abilities)

            # Build embed
            embed = discord.Embed(colour=color, description='\n'.join(poke.header))
            embed.set_thumbnail(url=poke.image)
            embed.add_field(name="Stats", value="\n".join(poke.stats))
            embed.add_field(name="Types", value=poke.types)
            embed.add_field(name="Resistances", value="\n".join(poke.resist))
            embed.add_field(name="Weaknesses", value="\n".join(poke.weak))
            embed.add_field(name="Abilities", value="\n".join(abilities))
            embed.set_footer(text=poke.desc)

            await self.bot.say(embed=embed)

    @pokemon.command(name="moveset", pass_context=False)
    async def _moveset_pokemon(self, generation: str, *, poke: str):
        """Search for a Pokémon's moveset

        If the generation specified is not found, it will default to 7

            Args:
                generation: variable length string 1-7 or I-VII.
                poke:       variable length string

            Returns:
                Tabular output of Pokémon data.

            Raises:
                AttributeError: Pokémon not found.

            Examples:
                Roman:      [p]moveset III pikachu
                Numbers:    [p]moveset 4 charizard
        """
        gen = switcher.get(generation, 7)
        move_url = "http://pokemondb.net/pokedex/{}/moves/{}".format(poke, gen)
        try:
            with aiohttp.ClientSession() as session:
                async with session.get(move_url) as response:
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
            await self.bot.say("Could not locate a Pokémon with that name.")

    @pokemon.command(name="tmset")
    async def _tmset_pokemon(self, generation: str, *, poke: str):
        """Get a Pokémon's learnset by generation(1-7).

          Example: !pokedex tmset V pikachu """
        if poke.title() in tm_exceptions:
            return await self.bot.say("This Pokémon cannot learn TMs.")

        gen = switcher.get(generation, 7)
        try:
            tm_url = "http://pokemondb.net/pokedex/{}/moves/{}".format(poke, gen)
            with aiohttp.ClientSession() as session:
                async with session.get(tm_url) as response:
                    soup = BeautifulSoup(await response.text(), "html.parser")
                    div1 = soup.find_all('div', attrs={'class': 'col desk-span-6 lap-span-12'})
                    div2 = div1[1].find_all('div', attrs={'class': 'colset span-full'})
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
            await self.bot.say("Oh no! That Pokémon was not available in that generation.")
        except AttributeError:
            await self.bot.say("Could not locate a Pokémon with that name.")

    @pokemon.command(name="item")
    async def _item_pokemon(self, *, item: str):
        """Get a description of an item.
        """
        item = item.replace(" ", "-").lower()
        item_url = "http://pokemondb.net/item/{}".format(item)
        try:
            with aiohttp.ClientSession() as session:
                async with session.get(item_url) as response:
                    soup = BeautifulSoup(await response.text(), "html.parser")
                    divs = soup.find('p')
                    info = divs.get_text()
                    await self.bot.say("**{}:**\n```{}```".format(item.title(), info))
        except AttributeError:
            await self.bot.say("Cannot find an item with this name")

    @pokemon.command(name="location")
    async def _location_pokemon(self, *, poke: str):
        """Get a Pokémon's catch location.
        Example !pokedex location voltorb
        """
        location_url = "http://pokemondb.net/pokedex/{}".format(poke)
        with aiohttp.ClientSession() as session:
            async with session.get(location_url) as response:
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

    def link_builder(self, name):
        link = name.lower().replace(' ', '_')
        if link in exceptions:
            if 'nidoran' in link:
                link = 'nidoran_({}\)'.format(name[-1].upper())
            return link
        else:
            link = link.split('-')[0]
            return link

    def ability_builder(self, abilities):
        pattern = '( or )|(\(.*\))'
        pattern2 = '(\(.*\))'

        fmt1 = "[{}]({}{}_(Ability\)) or [{}]({}{}_(Ability\)) {}"
        fmt2 = "[{}]({}{}_(Ability\)) or [{}]({}{}_(Ability\))"
        fmt3 = "[{}]({}{}_(Ability\)) {}"
        fmt4 = "[{}]({}{}_(Ability\))"

        linked = []

        for ability in abilities:
            if ' or ' in ability and '(' in ability:
                ab_set = [x for x in re.split(pattern, ability) if x and x != ' or ']
                params = [ab_set[0], url2, ab_set[0].replace(' ', '_'), ab_set[1],
                          url2, ab_set[1].replace(' ', '_'), ab_set[2]]
                linked.append(fmt1.format(*params))
            elif ' or ' in ability:
                ab_set = [x for x in re.split(pattern, ability) if x and x != ' or ']
                params = [ab_set[0], url2, ab_set[0].replace(' ', '_'), ab_set[1],
                          url2, ab_set[1].replace(' ', '_')]
                linked.append(fmt2.format(*params))
            elif '(' in ability:
                ab_set = [x for x in re.split(pattern2, ability) if x]
                params = [ab_set[0], url2, ab_set[0].replace(' ', '_'), ab_set[1]]
                linked.append(fmt3.format(*params))
            else:
                linked.append(fmt4.format(ability, url2, ability.replace(' ', '_')))

        return linked

    def color_lookup(self, element):
        primary = element.split('/')[0]
        color_table = {"Normal": 0x999966, "Fire": 0xFF6600, "Fighting": 0xFF0000, "Ice": 0x99FFFF,
                       "Water": 0x3399FF, "Flying": 0x9999FF, "Grass": 0x33FF00, "Poison": 0x660099,
                       "Electric": 0xFFFF00, "Ground": 0xFFCC33, "Psychic": 0xFF3399,
                       "Rock": 0xCC9966, "Bug": 0x669900, "Dragon": 0x003399, "Dark": 0x333333,
                       "Ghost": 0x9933FF, "Steel": 0x999999, "Fairy": 0xFF99FF}
        color = color_table.get(primary, 0xFFFFFF)
        return color

    def search_pokemon(self, name, link_name):
        Pokemon = namedtuple('Pokemon', ['id', 'name', 'wiki', 'header', 'types', 'image', 'desc',
                                         'stats', 'abilities', 'weak', 'resist'])
        try:
            with open('data/pokedex/Pokemon.csv', 'rt', encoding='iso-8859-15') as f:
                reader = csv.reader(f, delimiter=',')
                for row in reader:
                    if name == row[1]:
                        num = row[0]
                        wiki = "[{} {}]({})".format(name, row[0], url.format(link_name))
                        header = [wiki, row[2], row[3]]
                        types, img, desc = row[5], row[8], row[9]
                        stats, abilities = ast.literal_eval(row[4]), ast.literal_eval(row[10])
                        resist, weak = ast.literal_eval(row[6]), ast.literal_eval(row[7])
                        return Pokemon(num, name, wiki, header, types, img, desc, stats, abilities,
                                       weak, resist)
        except FileNotFoundError:
            print("The csv file Pokemon.csv could not be found in data/pokedex/Pokemon.csv")
            return None


def setup(bot):
    bot.add_cog(Pokedex(bot))
