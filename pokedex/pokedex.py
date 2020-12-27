# Developed by Redjumpman for Redbot

# Standard Library
import ast
import csv
import logging
import re
from collections import namedtuple

# Discord
import discord

# Redbot
from redbot.core import commands
from redbot.core.data_manager import bundled_data_path
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.utils.chat_formatting import box

# Third-Party Requirements
from tabulate import tabulate


log = logging.getLogger("red.jumper-plugins.pokedex")

__version__ = "3.1.4"
__author__ = "Redjumpman"

switcher = {
    "1": "I",
    "2": "II",
    "3": "III",
    "4": "IV",
    "5": "V",
    "6": "VI",
    "7": "VII",
    "8": "VIII",
}

exceptions = (
    "ho-oh",
    "jangmo-o",
    "hakamo-o",
    "kommo-o",
    "porygon-z",
    "nidoran-f",
    "nidoran-m",
    "wormadam-plant",
    "wormadam-sandy",
    "wormadam-trash",
    "shaymin-Land",
    "shaymin-Sky",
    "hoopa-confined",
    "hoopa-unbound",
    "lycanroc-midday",
    "lycanroc-midnight",
    "lycanroc-dusk",
    "kyurem-white",
    "kyurem-black",
)

tm_exceptions = (
    "Beldum",
    "Cascoon",
    "Caterpie",
    "Combee",
    "Cosmoem",
    "Cosmog",
    "Ditto",
    "Kakuna",
    "Kricketot",
    "Magikarp",
    "Unown",
    "Weedle",
    "Wobbuffet",
    "Wurmple",
    "Wynaut",
    "Tynamo",
    "Metapod",
    "MissingNo.",
    "Scatterbug",
    "Silcoon",
    "Smeargle",
)

url = r"https://bulbapedia.bulbagarden.net/wiki/{}_(Pokémon\)"
url2 = "https://bulbapedia.bulbagarden.net/wiki/"


class Pokedex(commands.Cog):
    """Search for Pokemon."""

    def __init__(self):
        self.path = bundled_data_path(self)

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete."""
        return

    @commands.group(autohelp=True)
    async def pokemon(self, ctx):
        """This is the list of Pokémon queries you can perform."""
        pass

    @pokemon.command()
    async def version(self, ctx):
        """Display running version of Pokedex

            Returns:
                Text ouput of your installed version of Pokedex
        """
        await ctx.send("You are running pokedex version {}.".format(__version__))

    @commands.command(aliases=["dex"])
    async def pokedex(self, ctx, *, pokemon: str):
        """Search for information on a Pokémon

            Examples:
                Regular:    [p]pokedex pikachu
                Megas:      [p]pokedex charizard-mega y
                Gigas:      [p]pokedex corviknight-giga
                Alola:      [p]pokedex geodude-alola
                Galarian:   [p]pokedex meowth-galar
                Forms:      [p]pokedex hoopa-unbound
                Variants:   [p]pokedex floette-orange
        """
        if pokemon.isdigit():
            if len(pokemon) == 3:
                poke = self.build_data(f"#{pokemon}", key="ID")
            else:
                return await ctx.send(
                    "When searching by pokedex number, it must be a three digit number. Example: 001"
                )
        else:
            poke = self.build_data(pokemon.title())

        if poke is None:
            # for pokemon like Nidoran that need another name modifier like Nidoran-F or Nidoran-M
            # and return None on a search for the base of the name
            p_other_names = []
            for p_name in exceptions:
                if pokemon in p_name:
                    p_other_names.append(p_name)

            if len(p_other_names) == 0:
                extra = ""
            else:
                extra = " Try one of these instead: {}".format(", ".join(p_other_names).title())
            return await ctx.send(f"A Pokémon with that name could not be found.{extra}")

        color = self.color_lookup(poke.Types.split("/")[0])
        abilities = self.ability_builder(ast.literal_eval(poke.Abilities))
        link_name = self.link_builder(pokemon)
        wiki = "[{} {}]({})".format(poke.Pokemon, poke.ID, url.format(link_name))
        header = [wiki, poke.Japanese, poke.Species]

        # Build embed
        embed = discord.Embed(colour=color, description="\n".join(header))
        embed.set_thumbnail(url=poke.Image)
        embed.add_field(name="Stats", value="\n".join(ast.literal_eval(poke.Stats)))
        embed.add_field(name="Types", value=poke.Types)
        embed.add_field(name="Resistances", value="\n".join(ast.literal_eval(poke.Resistances)))
        embed.add_field(name="Weaknesses", value="\n".join(ast.literal_eval(poke.Weaknesses)))
        embed.add_field(name="Abilities", value="\n".join(abilities))
        embed.set_footer(text=poke.Description)

        await ctx.send(embed=embed)

    @pokemon.command()
    async def moves(self, ctx, *, pokemon: str):
        """Search for a Pokémon's moveset

            If the generation is not specified it will default to the latest generation.

            Examples:
                Numbers:    [p]pokemon moves charizard-4
                Special:    [p]pokemon moves hoopa-unbound
                Alolan:     [p]pokemon moves geodude-alola
        """

        pokemon, generation = self.clean_output(pokemon)
        poke = self.build_data(pokemon.title())

        if poke is None:
            return await ctx.send("A Pokémon with that name could not be found.")

        try:
            move_set = ast.literal_eval(poke.Moves)[generation]
        except KeyError:
            generation = "7"
            try:
                move_set = ast.literal_eval(poke.Moves)[generation]
            except KeyError:
                generation = "8"
                move_set = ast.literal_eval(poke.Moves)[generation]

        table = box(
            tabulate(move_set, headers=["Level", "Move", "Type", "Power", "Acc"], numalign="right"), lang="ml",
        )

        if len(table) <= 900:
            color = self.color_lookup(poke.Types.split("/")[0])
            embed = discord.Embed(colour=color)
            embed.set_author(name=poke.Pokemon, icon_url=poke.Image)
            embed.add_field(name="\u200b", value=table, inline=False)
            embed.add_field(name="Versions", value="\n".join(self.game_version(generation)))
            embed.set_footer(text="This moveset is based on generation {}.".format(generation))

            await ctx.send(embed=embed)
        else:
            embeds = self.embed_builder(poke, move_set, generation, moves=True)
            await menu(ctx, embeds, DEFAULT_CONTROLS)

    @pokemon.command()
    async def item(self, ctx, *, item_name: str):
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
        item = self.item_search(item_name.title())
        if item is None:
            return await ctx.send("An item with that name could not be found.")
        color = self.color_lookup(item.Category)

        embed = discord.Embed(colour=color, title=item.Item)
        embed.set_thumbnail(url=item.Image)
        embed.add_field(name="Cost", value=item.Cost)
        embed.add_field(name="Category", value=item.Category)
        embed.add_field(name="Effect", value=item.Effect)
        await ctx.send(embed=embed)

    @pokemon.command()
    async def tmset(self, ctx, *, pokemon: str):
        """Get a Pokémon's learnset by generation (1-7).

            Example: [p]pokedex tmset pikachu-5
            If the generation is not specified, it will default to the latest generation.
        """
        pokemon, generation = self.clean_output(pokemon)

        if pokemon.title() in tm_exceptions:
            return await ctx.send("This Pokémon cannot learn TMs.")

        poke = self.build_data(pokemon.title())

        if poke is None:
            return await ctx.send("A Pokémon with that name could not be found.")

        try:
            tm_set = ast.literal_eval(poke.Tms)[generation]
        except KeyError:
            try:
                generation = "7"
                tm_set = ast.literal_eval(poke.Tms)[generation]
            except KeyError:
                generation = "8"
                tm_set = ast.literal_eval(poke.Tms)[generation]

        embeds = self.embed_builder(poke, tm_set, generation)
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    def embed_builder(self, poke, data, gen, moves=False):
        color = self.color_lookup(poke.Types.split("/")[0])
        table_type = "Moves" if moves else "TMs"
        col = "Lvl" if moves else "TMs"
        headers = (col, "Name", "Type", "Power", "Acc")
        embeds = []
        for i in range(0, len(data), 12):
            table = box(tabulate(data[i : i + 12], headers=headers, numalign="right"), lang="ml")
            e = discord.Embed(colour=color)
            e.set_author(name=poke.Pokemon, icon_url=poke.Image)
            e.add_field(name="\u200b", value=table, inline=False)
            if moves:
                e.add_field(name="Versions", value="\n".join(self.game_version(gen)))
            else:
                e.add_field(name="\u200b", value="\u200b")
            embeds.append(e)
        embeds = [
            x.set_footer(
                text=f"{table_type} based on generation {switcher[gen]}.\n"
                f"You are viewing page {idx} of {len(embeds)}"
            )
            for idx, x in enumerate(embeds, 1)
        ]
        return embeds

    @pokemon.command()
    async def location(self, ctx, *, pokemon: str):
        """Get a Pokémon's catch location.
        Example !pokedex location voltorb
        """
        pokemon, generation = self.clean_output(pokemon)
        poke = self.build_data(pokemon.title())
        if poke is None:
            return await ctx.send("A Pokémon with that name could not be found.")
        link_name = self.link_builder(poke.Pokemon)
        color = self.color_lookup(poke.Types.split("/")[0])
        wiki = "[{} {}]({})".format(poke.Pokemon, poke.ID, url.format(link_name))
        header = "\n".join((wiki, "Catch Locations"))
        locations = ast.literal_eval(poke.Locations)

        embeds = []
        for idx, (key, value) in enumerate(locations.items()):
            e = discord.Embed(colour=color, description=header)
            e.set_thumbnail(url=poke.Image)
            if value is None:
                location = "Not available in this version."
            else:
                location = value
            e.add_field(name=key, value=location)
            embeds.append(e)
        embeds = [
            x.set_footer(text="You are viewing page {} of {}".format(idx, len(embeds)))
            for idx, x in enumerate(embeds, 1)
        ]

        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @staticmethod
    def game_version(generation):
        versions = {
            "1": ["Pokémon Red", "Pokémon Blue", "Pokémon Yellow"],
            "2": ["Pokémon Gold", "Pokémon Silver", "Pokémon Crystal"],
            "3": ["Pokémon Ruby", "Pokémon Sapphire", "Pokémon FireRed", "Pokémon LeafGreen", "Pokémon Emerald",],
            "4": ["Pokémon Diamond", "Pokémon Pearl", "Pokémon Platinum", "Pokémon HeartGold", "Pokémon SoulSilver",],
            "5": ["Pokémon Black", "Pokémon White", "Pokémon Black 2", "Pokémon White 2"],
            "6": ["Pokémon X", "Pokémon Y", "Pokémon Omega Ruby", "Pokémon Alpha Sapphire"],
            "7": [
                "Pokémon Sun",
                "Pokémon Moon",
                "Pokémon Ultra Sun",
                "Pokémon Ultra Moon",
                "Pokémon Sun Let's Go Pikachu",
                "Pokémon Let's Go Eevee",
            ],
            "8": ["Pokémon Sword", "Pokémon Shield"],
        }
        return versions[generation]

    @staticmethod
    def clean_output(pokemon):
        if "-" not in pokemon:
            return pokemon, "7"

        query = pokemon.split("-")
        if len(query) > 2:
            partition = pokemon.rpartition("-")
            if partition[0].lower() not in exceptions and "alola" not in partition[0].lower():
                return "", ""
            else:
                return partition[0], partition[2]
        elif len(query) == 1:
            return query[0], "7"
        else:
            if pokemon.lower() in exceptions or query[1].lower() == "alola":
                return pokemon, "7"
            elif query[1].isdigit():
                return query
            else:
                return "", ""

    def item_search(self, name):
        fp = self.path / "Items.csv"
        try:
            with fp.open("rt", encoding="iso-8859-15") as f:
                reader = csv.DictReader(f, delimiter=",")
                for row in reader:
                    if row["Item"] == name:
                        Item = namedtuple("Item", reader.fieldnames)
                        return Item(**row)
        except FileNotFoundError:
            log.error("The csv file could not be found in pokedex data folder.")
            return None

    def build_data(self, identifier, key="Pokemon"):
        fp = self.path / "Pokemon.csv"
        try:
            with fp.open("rt", encoding="iso-8859-15") as f:
                reader = csv.DictReader(f, delimiter=",")
                for row in reader:
                    if row[key] == identifier:
                        Pokemon = namedtuple("Pokemon", reader.fieldnames)
                        return Pokemon(**row)
        except FileNotFoundError:
            log.error("The csv file could not be found in pokedex data folder.")
            return None

    @staticmethod
    def link_builder(name):
        link = name.lower().replace(" ", "_")
        if link in exceptions:
            if "nidoran" in link:
                link = "nidoran_({}\\)".format(name[-1].upper())
            return link
        else:
            link = link.split("-")[0]
            return link

    @staticmethod
    def ability_builder(abilities):
        pattern = "( or )|(\\(.*\\))"
        pattern2 = "(\\(.*\\))"

        fmt1 = "[{}]({}{}_(Ability\\)) or [{}]({}{}_(Ability\\)) {}"
        fmt2 = "[{}]({}{}_(Ability\\)) or [{}]({}{}_(Ability\\))"
        fmt3 = "[{}]({}{}_(Ability\\)) {}"
        fmt4 = "[{}]({}{}_(Ability\\))"

        linked = []

        for ability in abilities:
            if " or " in ability and "(" in ability:
                ab_set = [x for x in re.split(pattern, ability) if x and x != " or "]
                params = [
                    ab_set[0],
                    url2,
                    ab_set[0].replace(" ", "_"),
                    ab_set[1],
                    url2,
                    ab_set[1].replace(" ", "_"),
                    ab_set[2],
                ]
                linked.append(fmt1.format(*params))
            elif " or " in ability:
                ab_set = [x for x in re.split(pattern, ability) if x and x != " or "]
                params = [
                    ab_set[0],
                    url2,
                    ab_set[0].replace(" ", "_"),
                    ab_set[1],
                    url2,
                    ab_set[1].replace(" ", "_"),
                ]
                linked.append(fmt2.format(*params))
            elif "(" in ability:
                ab_set = [x for x in re.split(pattern2, ability) if x]
                params = [ab_set[0], url2, ab_set[0].replace(" ", "_"), ab_set[1]]
                linked.append(fmt3.format(*params))
            else:
                linked.append(fmt4.format(ability, url2, ability.replace(" ", "_")))

        return linked

    @staticmethod
    def color_lookup(key):
        color_table = {
            "Normal": 0x999966,
            "Fire": 0xFF6600,
            "Fighting": 0xFF0000,
            "Ice": 0x99FFFF,
            "Water": 0x3399FF,
            "Flying": 0x9999FF,
            "Grass": 0x33FF00,
            "Poison": 0x660099,
            "Electric": 0xFFFF00,
            "Ground": 0xFFCC33,
            "Psychic": 0xFF3399,
            "Rock": 0xCC9966,
            "Bug": 0x669900,
            "Dragon": 0x003399,
            "Dark": 0x333333,
            "Ghost": 0x9933FF,
            "Steel": 0x999999,
            "Fairy": 0xFF99FF,
            "Key Item": 0xAC00EB,
            "Berries": 0xF5F794,
            "Battle Items": 0xED002B,
            "General Items": 0xFFFFFF,
            "Hold Items": 0xC976A8,
            "Machines": 0x999999,
            "Medicine": 0x79EDA1,
            "Poké Balls": 0xFF0000,
        }
        color = color_table.get(key, 0xFFFFFF)
        return color
