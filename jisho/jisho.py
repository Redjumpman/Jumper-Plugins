# Developed by Redjumpman for Redbot
# Credit to jonnyli1125 for the original work on Discordant

# Standard Library
import aiohttp
import re
import urllib.parse

# Red
from redbot.core import commands

# Discord
import discord


class Jisho(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete."""
        return

    @commands.command()
    async def jisho(self, ctx, word: str):
        """Translates Japanese to English, and English to Japanese

        Works with Romaji, Hiragana, Kanji, and Katakana"""
        search_args = await self.dict_search_args_parse(ctx, word.lower())
        if not search_args:
            return
        limit, query = search_args
        message = urllib.parse.quote(query, encoding="utf-8")
        url = "http://jisho.org/api/v1/search/words?keyword=" + message
        async with self.session.get(url) as response:
            data = await response.json()
        try:
            messages = [self.parse_data(result) for result in data["data"][:limit]]
        except KeyError:
            return await ctx.send("I was unable to retrieve any data")
        try:
            await ctx.send("\n".join(messages))
        except discord.HTTPException:
            await ctx.send("No data for that word.")

    def parse_data(self, result):
        japanese = result["japanese"]
        output = self.display_word(japanese[0], "**{reading}**", "**{word}** {reading}") + "\n"
        new_line = ""
        if result["is_common"]:
            new_line += "Common word. "
        if result["tags"]:
            new_line += "Wanikani level " + ", ".join([tag[8:] for tag in result["tags"]]) + ". "
        if new_line:
            output += new_line + "\n"
        senses = result["senses"]
        for index, sense in enumerate(senses, 1):
            parts = [x for x in sense["parts_of_speech"] if x is not None]
            if parts == ["Wikipedia definition"]:
                continue
            if parts:
                output += "*{}*\n".format(", ".join(parts))
            output += "{}. {}".format(index, "; ".join(sense["english_definitions"]))
            for attr in ["tags", "info"]:
                if sense[attr]:
                    output += ". *{}*.".format("".join(sense[attr]))
            if sense["see_also"]:
                output += ". *See also: {}*".format(", ".join(sense["see_also"]))
            output += "\n"
        if len(japanese) > 1:
            output += "Other forms: {}\n".format(
                ", ".join([self.display_word(x, "{reading}", "{word} ({reading})") for x in japanese[1:]])
            )
        return output

    def display_word(self, obj, *formats):
        return formats[len(obj) - 1].format(**obj)

    async def dict_search_args_parse(self, ctx, message):
        if not message:
            return await ctx.send("Error in arg parse")
        limit = 1
        query = message
        result = re.match(r"^([0-9]+)\s+(.*)$", message)
        if result:
            limit, query = [result.group(x) for x in (1, 2)]
        return int(limit), query
