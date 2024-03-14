from .leveler import Leveler


async def setup(bot):
    n = Leveler(bot)
    bot.add_listener(n.listener, "on_message")
    await bot.add_cog(n)
