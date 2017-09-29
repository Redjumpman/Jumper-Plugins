# Developed by Redjumpman for Redbot.
# Inspired by the snail race mini game

import asyncio
import random

from discord.ext import commands
from __main__ import send_cmd_help


class Race:
    """Cog for racing Turtles"""

    def __init__(self, bot):
        self.bot = bot
        self.system = {}
        self.version = "1.0.03"

    @commands.group(pass_context=True, no_pm=True)
    async def race(self, ctx):
        """Race cog's group command"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @race.command(name="version")
    async def _version_race(self):
        """Displays the version of race"""
        await self.bot.say("You are running race version {}".format(self.version))

    @race.command(name="start", pass_context=True)
    @commands.cooldown(1, 120, commands.BucketType.server)
    async def _start_race(self, ctx):
        """Start a turtle race

            Returns:
                Two text outputs. One to start the race,
                and the second to represent the race. The second
                msg will be edited multiple times to represent the race.

            Notes:
                Must wait 2 minutes after every race to start a new one.
                You cannot start a race if a race is already active.
                A race is considered active once this command is used.
                A race is considered started once the track is displayed.
                The user who starts a race, will be automatically entered.
                The bot will always join a race.
                There are no cheaters and it isn't rigged.
        """
        author = ctx.message.author
        data = self.check_server(author.server)

        if data['Race Active']:
            return

        data['Race Active'] = True
        data['Players'][author.id] = {}

        await self.bot.say(":triangular_flag_on_post: A turtle race has begun! Type {}race enter "
                           "to join the race! :triangular_flag_on_post:\n{}The race will "
                           "begin in 30 seconds!".format(ctx.prefix, ' ' * 25))
        await asyncio.sleep(30)
        await self.bot.say(":checkered_flag: The race is now in progress :checkered_flag:")

        data['Race Start'] = True

        temp = ":carrot: **{}** :flag_black:  [{}]"
        track, racers = self.game_setup(author, temp, data)
        race_msg = await self.bot.say('\n'.join([x[0] for x in racers]))
        winner = await self.run_game(author, racers, track, temp, race_msg, data)

        if winner != self.bot.user:
            await self.bot.say("Congratulations {}, you won the turtle race! You have 2 minutes "
                               "to claim your prize! Type {}race claim to get your "
                               "winnings.".format(winner.mention, ctx.prefix))
        else:
            await self.bot.say("Sorry, looks like the winnings are all mine!")
            data['Winner'] = None

        self.game_teardown(data)

    @race.command(name="enter", pass_context=True)
    async def _enter_race(self, ctx):
        """Enter a turtle race

        Returns:
            Text informing the user they have joined the race.
            If they cannot join for any reason (look at notes) then
            it will return silently with no response.

        Notes:
            Users cannot join if a race is not active, has 5 (exluding the bot)
            or more players, or is already in the race.
        """
        author = ctx.message.author
        data = self.check_server(author.server)

        if data['Race Start']:
            return
        elif not data['Race Active']:
            return
        elif author.id in data['Players']:
            return
        elif len(data['Players']) == 5:
            return
        else:
            data['Players'][author.id] = {}
            await self.bot.say("**{}** joined the race!".format(author.name))

    @race.command(name="claim", pass_context=True)
    async def _claim_race(self, ctx):
        """Claim your prize from the turtle race

        Returns:
                One of three outcomes based on result
            :Text output giving random credits from 10-100
            :Text output telling you are not the winner
            :Text output telling you to get a bank account

        Raises:
            cogs.economy.NoAccount Error when bank account not found.

        Notes:
            If you do not have a bank account with economy, the bot will take your money
            and spend it on cheap booze and potatoes.
        """
        author = ctx.message.author
        data = self.check_server(author.server)

        if data['Winner'] != author.id:
            return await self.bot.say("Scram kid. You didn't win nothing yet.")

        bank = self.bot.get_cog('Economy').bank
        prize = data['Prize']

        try:  # Because people will play games for money without a fucking account smh
            bank.deposit_credits(author, prize)
        except Exception as e:
            print('{} raised {} because they are stupid.'.format(author.name, type(e)))
            await self.bot.say("We wanted to give you a prize, but you didn't have a bank "
                               "account.\nTo teach you a lesson, your winnings are mine this "
                               "time. Now go register!")
        else:
            await self.bot.say("After paying for turtle food, entrance fees, track fees, "
                               "you get {} credits.".format(prize))
        finally:
            data['Winner'] = None
            data['Prize'] = 0

    def check_server(self, server):
        if server.id in self.system:
            return self.system[server.id]
        else:
            self.system[server.id] = {'Race Start': False,
                                      'Race Active': False,
                                      'Players': {},
                                      'Winner': None,
                                      'Prize': 0}
            return self.system[server.id]

    def game_teardown(self, data):
        data['Race Active'] = False
        data['Race Start'] = False
        data['Players'].clear()

    def game_setup(self, author, temp, data):

        # Track is 60 characters long, 3 character increments
        track = '•   ' * 20

        # Add the bot
        racers = [[temp.format(track + ":turtle:", self.bot.user), self.bot.user]]

        # Add the players
        for user in data['Players']:
            mobj = author.server.get_member(user)
            racers.append([temp.format(track + ":turtle:", mobj), mobj])

        return track, racers

    async def run_game(self, author, racers, track, temp, game, data):
        while True:
            await asyncio.sleep(1.0)
            for idx, racer in enumerate(racers):
                # One move is 3 characters long
                # Pick movement 0-2 at random and multiply by 3
                move = random.randint(0, 3) * 3
                pos = racer[0].find(':turtle:')
                if pos > 0:
                    new = (track[:max(0, pos - move)] + ':turtle:' + track[max(0, pos - move):])
                    new_pos = new.find(':turtle:')
                    if not data['Winner'] and new_pos == 0:
                        data['Winner'] = racer[1].id
                    racers[idx][0] = new
            field = [temp.format(x[0], x[1]) for x in racers]
            await self.bot.edit_message(game, '\n'.join(field))

            if [racer[0].find(':turtle:') for racer in racers].count(0) == len(racers):
                break

        prize = random.randint(10, 100)
        data['Prize'] = prize
        winner = author.server.get_member(data['Winner'])
        return winner


def setup(bot):
    bot.add_cog(Race(bot))
