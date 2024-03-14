from .pokemontcg import PokemonTCG

async def setup(bot):
  await bot.add_cog(PokemonTCG(bot))
