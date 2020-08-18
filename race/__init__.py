from .race import Race

__end_user_data_statement__="This cog stores your statistics for wins and losses in the racing game.\nYou may request data deletion through the mydata command."

def setup(bot):
    bot.add_cog(Race())
