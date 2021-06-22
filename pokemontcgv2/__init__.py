from .pokemontcgv2 import PokemonTCGv2

def setup(bot):
  bot.add_cog(PokemonTCGv2(bot))
