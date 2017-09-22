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

switcher = {"1": "I", "2": "II", "3": "III", "4": "IV", "5": "V", "6": "VI", "7": "VII"}

exceptions = {'ho-oh', 'jangmo-o', 'hakamo-o', 'kommo-o', 'porygon-z', 'nidoran-f', 'nidoran-m'}
tm_exceptions = {"Beldum", "Burmy", "Cascoon", "Caterpie", "Combee", "Cosmoem", "Cosmog",
                 "Ditto", "Kakuna", "Kricketot", "Magikarp", "Unown", "Weedle", "Wobbuffet",
                 "Wurmple", "Wynaut", "Tynamo", "Metapod", "MissingNo.", "Scatterbug",
                 "Silcoon", "Smeargle"}

url = "https://bulbapedia.bulbagarden.net/wiki/{}_(Pokémon\)"
url2 = "https://bulbapedia.bulbagarden.net/wiki/"


class Pokedex:
    """Search for Pokemon."""

    def __init__(self, bot):
        self.bot = bot
        self.version = "2.4.01"

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
        poke = self.search_csv(pokemon.title(), 'data/pokedex/Pokemon.csv', link_name=link_name)

        try:
            color = self.color_lookup(poke.types.split('/')[0])
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

    @pokemon.command(name="moves", pass_context=False)
    async def _moves_pokemon(self, *, poke: str):
        """Search for a Pokémon's moveset

        If the generation specified is not found, it will default to 7

            Args:
                poke: variable length string

            Returns:
                Tabular output of Pokémon data.

            Raises:
                AttributeError: Pokémon not found.

            Examples:
                Numbers:    [p]pokemon moves charizard-4
                Alolan:     [p]pokemon moves geodude-alola
        """
        moves = self.search_csv(poke.lower(), 'data/pokedex/Moves.csv', data_type='m')

        try:
            table = tabulate(moves.moves, headers=['Level', 'Moves', 'Type', 'Power', 'Accuracy'])
        except AttributeError:
            await self.bot.say('A Pokémon with that name could not be found.')
        else:
            embed = discord.Embed(title=moves.pokemon, colour=moves.color,
                                  description="```{}```".format(table))
            embed.add_field(name="Versions", value='\n'.join(moves.versions))
            embed.set_footer(text="This moveset is based on generation {}.".format(moves.gen))

            await self.bot.say(embed=embed)

    @pokemon.command(name="item")
    async def _item_pokemon(self, *, item_name: str):
        """Search for an item in the Pokémon universe

            Args:
                item_name: variable length string

            Returns:
                Discord embed

            Raises:
                AttributeError: Item not found

            Examples:
                pokemon item master ball
        """
        item = self.search_csv(item_name.title(), 'data/pokedex/Items.csv', data_type='i')
        try:
            color = self.color_lookup(item.category)
        except AttributeError:
            await self.bot.say("An item with that name could not be found.")
        else:
            embed = discord.Embed(colour=color, title=item.name)
            embed.set_thumbnail(url=item.image)
            embed.add_field(name="Cost", value=item.cost)
            embed.add_field(name="Category", value=item.category)
            embed.add_field(name="Effect", value=item.effect)
            await self.bot.say(embed=embed)

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
                div = soup.find('div', attrs={'class': 'col desk-span-7 lap-span-12'})
                table = div.find('table', attrs={'class': 'vitals-table'})

                cols = [ele.text.strip() for ele in table.find_all('td') if ele]
                loc.append(cols)

                tcols = [ele.strings for ele in table.find_all('th') if ele]
                version.append([', '.join(x) for x in tcols])
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

    def color_lookup(self, key):
        color_table = {"Normal": 0x999966, "Fire": 0xFF6600, "Fighting": 0xFF0000, "Ice": 0x99FFFF,
                       "Water": 0x3399FF, "Flying": 0x9999FF, "Grass": 0x33FF00, "Poison": 0x660099,
                       "Electric": 0xFFFF00, "Ground": 0xFFCC33, "Psychic": 0xFF3399,
                       "Rock": 0xCC9966, "Bug": 0x669900, "Dragon": 0x003399, "Dark": 0x333333,
                       "Ghost": 0x9933FF, "Steel": 0x999999, "Fairy": 0xFF99FF,
                       "Key Item": 0xAC00EB, "Berries": 0xF5F794, "Battle Items": 0xED002B,
                       "General Items": 0xFFFFFF, "Hold Items": 0xC976A8, "Machines": 0x999999,
                       "Medicine": 0x79EdA1, "Poké Balls": 0xFF0000}
        color = color_table.get(key, 0xFFFFFF)
        return color

    def search_csv(self, name, file_path, data_type='p', link_name=None):
        try:
            with open(file_path, 'rt', encoding='iso-8859-15') as f:
                reader = csv.reader(f, delimiter=',')
                if data_type == 'p':
                    return self.collect_pokemon(reader, name, link_name)
                elif data_type == 'm':
                    return self.collect_moves(reader, name)
                elif data_type == 'i':
                    return self.collect_items(reader, name)
                else:
                    return None
        except FileNotFoundError:
            print("The csv file could not be found in data/pokedex/")
            return None

    def collect_pokemon(self, reader, name, link_name):
        Pokemon = namedtuple('Pokemon', ['id', 'name', 'wiki', 'header', 'types', 'image', 'desc',
                                         'stats', 'abilities', 'weak', 'resist'])
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

    def collect_moves(self, reader, name):
        Moves = namedtuple('Moves', ['pokemon', 'gen', 'color', 'moves', 'versions'])
        if name.split('-')[-1].isdigit():
            for row in reader:
                if name == row[0]:
                    pokemon = name.split('-')[0].title()
                    generation, color = switcher[row[1]], int(ast.literal_eval(row[2]))
                    moves, versions = ast.literal_eval(row[3]), ast.literal_eval(row[4])
                    return Moves(pokemon, generation, color, moves, versions)
        else:
            for row in reader:
                if name in row[0]:
                    pokemon = name.title()
                    generation, color = switcher[row[1]], int(ast.literal_eval(row[2]))
                    moves, versions = ast.literal_eval(row[3]), ast.literal_eval(row[4])
                    return Moves(pokemon, generation, color, moves, versions)

    def collect_items(self, reader, name):
        Item = namedtuple('Item', ['name', 'category', 'effect', 'cost', 'image'])
        for row in reader:
            if name == row[0]:
                category, effect, cost, image = row[1], row[2], row[3], row[4]
                return Item(name, category, effect, cost, image)


def setup(bot):
    bot.add_cog(Pokedex(bot))
