from .compendium import Compendium

async def setup(bot):
  await bot.add_cog(Compendium(bot))
