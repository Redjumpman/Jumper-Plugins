# Developed by Redjumpman for Redbot
# Credit to jonnyli1125 for the original work on Discordant
import aiohttp
import re
import urllib.parse
from discord.ext import commands


class Language:
    """Translates Languages"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
    
    def __unload(self):
        self.session.close()

    @commands.command(pass_context=True, no_pm=False)
    async def jisho(self, ctx, word):
        """Translates Japanese to English, and English to Japanese
        Works with Romaji, Hiragana, Kanji, and Katakana"""
        channel = ctx.message.channel
        word = word.lower()
        search_args = await self.dict_search_args_parse(word)
        if not search_args:
            return
        limit, query = search_args
        message = urllib.parse.quote(query, encoding='utf-8')
        url = "http://jisho.org/api/v1/search/words?keyword=" + str(message)
        try:
            async with self.session.get(url) as response:
                data = await response.json()

            results = data["data"][:limit]

            output = ""

            for result in results:
                japanese = result["japanese"]
                output += self.display_word(japanese[0], "**{reading}**",
                                            "**{word}** {reading}") + "\n"
                new_line = ""
                if result["is_common"]:
                    new_line += "Common word. "
                if result["tags"]:  # it doesn't show jlpt tags, only wk tags?
                    new_line += "Wanikani level " + ", ".join(
                        [tag[8:] for tag in result["tags"]]) + ". "
                if new_line:
                    output += new_line + "\n"
                senses = result["senses"]
                for index, sense in enumerate(senses):
                    # jisho returns null sometimes for some parts of speech... k den
                    parts = [x for x in sense["parts_of_speech"] if x is not None]
                    if parts == ["Wikipedia definition"]:
                        continue
                    if parts:
                        output += "*" + ", ".join(parts) + "*\n"
                    output += str(index + 1) + ". " + "; ".join(
                        sense["english_definitions"])
                    for attr in ["tags", "info"]:
                        if sense[attr]:
                            output += ". *" + "*. *".join(sense[attr]) + "*"
                    if sense["see_also"]:
                        output += ". *See also: " + ", ".join(sense["see_also"]) + "*"
                    output += "\n"
                if len(japanese) > 1:
                    output += "Other forms: " + ", ".join(
                        [self.display_word(x, "{reading}", "{word} ({reading})") for x in
                         japanese[1:]]) + "\n"
            await self.send_long_message(channel, output)
        except:
            await self.bot.say("I was unable to retrieve any data")

    def display_word(self, obj, *formats):
        return formats[len(obj) - 1].format(**obj)

    async def dict_search_args_parse(self, message):
        if not message:
            await self.bot.say("Error in arg parse")
            return
        limit = 1
        query = message
        result = re.match(r"^([0-9]+)\s+(.*)$", message)
        if result:
            limit, query = [result.group(x) for x in (1, 2)]
        return int(limit), query
        # keys = ["limit"]
        # kwargs = utils.get_kwargs(args, keys)
        # try:
        #     limit = int(kwargs["limit"])
        #     if limit <= 0:
        #         raise ValueError
        # except (ValueError, KeyError):
        #     limit = 1
        # query = utils.strip_kwargs(args, keys)

    async def send_long_message(self, channel, message, truncate=False,
                                max_lines=15):
        for msg in long_message(message, truncate, max_lines):
            await self.bot.send_message(channel, msg)


def split_every(s, n):
    return [s[i:i + n] for i in range(0, len(s), n)]


def long_message(output, truncate=False, max_lines=15):
    output = output.strip()
    return ["\n".join(output.split("\n")[:max_lines]) +
            "\n... *Search results truncated. " +
            "Send me a command over PM to show more!*"] \
        if truncate and output.count("\n") > max_lines \
        else split_every(output, 2000)


def setup(bot):
    n = Language(bot)
    bot.add_cog(n)
