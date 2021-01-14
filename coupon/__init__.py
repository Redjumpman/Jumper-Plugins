from .coupon import Coupon

__red_end_user_data_statement__ = "This cog does not persistently store data or metadata about users."


async def setup(bot):
    bot.add_cog(Coupon(bot))
