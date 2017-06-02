# Developed by Redjumpman for Redbot
from discord.ext import commands
from random import choice as randchoice


class Fortune:
    """Fortune Cookie Commands."""

    def __init__(self, bot):
        self.bot = bot
        self.fortune = ["He who laughs at himself never runs out of things to laugh at.",
                        "Man who fart in church sit in his own pew",
                        "Man who go to bed with itchy butt wake up with stinky finger",
                        "There is no I in team but U in cunt",
                        "Gay man always order same, Sum Yung Guy",
                        "Man piss in wind, wind piss back",
                        "Only listen to the fortune cookie; disreguard all other fortune telling units.",
                        "Never give up, unless defeat arouses that girl in accounting",
                        "Ignore previous fortunes",
                        "Confucious says: Go to bed with itchy bum, Wake up with stinky finger!",
                        "You will die alone and poorly dressed.",
                        "Help i'm stuck inside this crappy python script and I can't get out!",
                        "I am being held prisoner at 1403 Sherwood drive, the door code is 6969",
                        "This is the wrong fortune, you're looking for the fortune up the road",
                        "Sometimes in life we get no fortune",
                        "Today is probably a huge improvement over yesterday",
                        "Never tease an armed midget with a high five",
                        "Life will be happy, until the end when you'll pee yourself a lot.",
                        "If you think a discord bot can tell you your fortune, you're crazy.",
                        "You will be hungry again within the hou.r",
                        "How much deeper would the ocean be without sponges?",
                        "I found your boyfriend on craigslist and he wasn't selling his pool table.",
                        "Congradulations! you are not illiterate!",
                        "May you someday be carbon neutral.",
                        "I'm FREE! You've released me from my prision, I shall now cause havock across the realm!",
                        "When you squeeze an orange, orange juice comes out, because that's what's inside."]

    @commands.command(name="fortune", aliases=["cookie"])
    async def _cookie(self):
        """Ask for your fortune

        And look deeply into my scales
        """
        return await self.bot.say("`" + randchoice(self.fortune) + "`")


def setup(bot):
    bot.add_cog(Fortune(bot))
