import discord
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify
from pokemontcgsdk import Card
from pokemontcgsdk import Set
from pokemontcgsdk import RestClient

# Rest Client API Token
RestClient.configure('7eea4656-f765-4ec5-b92b-9aa038b12ce9')

# The maximum number of lines the bot will post to a public server in one
# message. Anything larger will be private messaged to avoid clutter
MAX_LINES = 15

# Conversion from type name to emoji
emoji = {
    'Colorless' : '<:ecolorless:543156672219054100>',
    'Darkness'  : '<:edarkness:543156641772732438>',
    'Dragon'    : '<:edragon:543156672059670541>',
    'Fairy'     : '<:efairy:543156671824789504>',
    'Fighting'  : '<:efighting:543156617579986995>',
    'Fire'      : '<:efire:543156506485587968>',
    'Free'      : '<:efree:618879505007902750>',
    'Grass'     : '<:egrass:543154867540066307>',
    'Lightning' : '<:elightning:543156557072957441>',
    'Psychic'   : '<:epsychic:543156587100110851>',
    'Metal'     : '<:emetal:543156671648628768>',
    'Water'     : '<:ewater:543156529956651008>',
}

# Conversion from type name to hex colour
colour = {
    'Colorless' : 0xF5F5DA,
    'Darkness'  : 0x027798,
    'Dragon'    : 0xD1A300,
    'Fairy'     : 0xDD4787,
    'Fighting'  : 0xC24635,
    'Fire'      : 0xD7080C,
    'Grass'     : 0x427B18,
    'Lightning' : 0xF9D029,
    'Psychic'   : 0xB139B6,
    'Metal'     : 0xAFAFAF,
    'Water'     : 0x02B2E6,
}

# Conversion from type name to PokeBeach shorthand
short_energy = {
    'Colorless' : "[C]",
    'Darkness'  : "[D]",
    'Fairy'     : "[Y]",
    'Fighting'  : "[F]",
    'Fire'      : "[R]",
    'Free'      : "[ ]",
    'Grass'     : "[G]",
    'Lightning' : "[L]",
    'Psychic'   : "[P]",
    'Metal'     : "[M]",
    'Water'     : "[W]",
}


# Given a string, searches for cards by name using the given string. Return a
# list of matches sorted by release, and the set name and code the card was
# released in
def search(name):
    if name == "":
        return ("", 0)

    # Users will often enter 'hydreigon ex' when they really mean
    # 'hydreigon-ex'. This annoying, but simply inserting the dash does not
    # work as it makes Ruby/Sapphire era ex cards unaccessible. Instead,
    # search for both
    cards = []
    if name.lower().endswith(" ex"):
        cards.extend(Card.where(name = name.lower()))
        cards.extend(Card.where(name = name.lower().replace(" ex", "-ex")))
    # GX cards do not have the same issue, so we can simply insert the dash
    # as expected
    elif name.lower().endswith(" gx"):
        cards.extend(Card.where(name = name.lower().replace(" gx", "-gx")))
    # Delta card text replacement
    elif name.lower().endswith(" delta"):
        cards.extend(Card.where(name = name.lower().replace(" delta", " δ")))
    # Handling "N"
    elif name.lower() == "n":
        return_str = "Matches for search 'N'\n"
        return_str += "N - Noble Victories 92/101 (`bw3-92`)\n"
        return_str += "N - Noble Victories 101/101 (`bw3-101`)\n"
        return_str += "N - Dark Explorers 96/108 (`bw5-96`)\n"
        return_str += "N - BW Black Star Promos BW100 (`bwp-BW100`)\n"
        return_str += "N - Fates Collide 105/124 (`xy10-105`)\n"
        return_str += "N - Fates Collide 105a/124 (`xy10-105a`)\n"
        
        return (return_str, 6)
    # Otherwise, search for the given text
    else:
        cards = Card.where(q=f'name:"{name}"', orderBy="set.releaseDate")
    
    # Give an error if there are no matches
    if len(cards) == 0:
        return ("No matches for search '%s'" % name, 0)

    # If there is exactly one match, save time for the user and give the
    # !show output instead
    if len(cards) == 1:
        return (show(cards[0].name, cards[0].set.id), 1)

    # Create the returned string
    return_str = "Matches for search '%s'\n" % name
    for card in cards:
        return_str += ("%s - %s %s/%s (`%s-%s`)\n" % (card.name, card.set.series,
                                                      card.number, card.set.printedTotal,
                                                      card.set.id, card.number))

    return (return_str, len(cards))


def embed_create(card, card_set):
    embed = None
    if card.supertype == "Pokémon":
        embed = pokemon_embed(card)
    elif card.supertype == "Trainer" or card.supertype == "Energy":
        embed = trainer_embed(card)

    # Image
    embed.set_image(url=card.images.large)

    # Set - legality - rarity
    text = "%s - %s/%s -- %s\n " % (card_set.name, card.number, card_set.printedTotal, card.rarity)

    if card_set.legalities.standard == 'Legal':
        text += "\u2705 (Standard) - "
    elif card_set.legalities.standard == 'Banned':
        text += "\u274C (Standard) - "
    if card_set.legalities.expanded == 'Legal':
        text += "\u2705 (Expanded) - "
    elif card_set.legalities.expanded == 'Banned':
        text += "\u274C (Expanded) - "
    if card_set.legalities.unlimited == 'Legal':
        text += "\u2705 (Legacy)"
    elif card_set.legalities.unlimited == 'Banned':
        text += "\u274C (Legacy)"

    embed.set_footer(text=text, icon_url=card_set.images.symbol)

    return embed


# Construct an Embed object from a Pokemon card and it's set
def pokemon_embed(card):

    # Name, type(s), HP
    title = card.name

    if card.hp is not None:
        title += " - HP%s" % (card.hp)

    title += " - " + " / ".join(list(map(lambda x : emoji[x], card.types)))

    # Subtype, evolution
    desc = "%s Pokémon" % card.subtypes[0]
    if card.evolvesFrom is not None and card.evolvesFrom != "":
        desc += " (Evolves from %s)" % card.evolvesFrom
    if len(card.subtypes) > 1:
        desc += "\n%s" % card.subtypes[1]

    embed = discord.Embed(title=title, color=colour[card.types[0]], description=desc)

    # Ancient Traits
    if card.ancientTrait is not None:
        name = "Ancient Trait: %s" % card.ancientTrait.name
        desc = "%s" % card.ancientTrait.text
        embed.add_field(name=name, value=desc or '\u200b')
    
    # Ability
    if card.abilities is not None:
        for ability in card.abilities:
            name = "%s: %s" % (ability.type, ability.name)
            desc = "%s" % ability.text
            embed.add_field(name=name, value=desc or '\u200b')

    # Attacks
    if card.attacks is not None:
        for attack in card.attacks:
            name = ""
            text = ""

            for cost in attack.cost:
                name += "%s" % emoji[cost]

            name += " %s" % attack.name

            if attack.damage != '':
                name += " - %s" % attack.damage

            if attack.text is not None and attack.text != "":
                text = attack.text
            else:
                text = '\u200b'

            embed.add_field(name=name, value=text, inline=False)

    # Weakness, resistance, retreat
    name = ""
    desc = ""
    
    if card.weaknesses is not None:
        name += "Weakness: "
        for weakness in card.weaknesses:
            name += "%s (%s)" % (emoji[weakness.type], weakness.value)

    if card.resistances is not None:
        name += " - Resistance: "

        for resistance in card.resistances:
            name += "%s (%s)" % (emoji[resistance.type], resistance.value)

    if card.retreatCost is not None:
        name += " - Retreat: "
        name += "%s" % emoji['Colorless'] * len(card.retreatCost)
    # Ruleboxes
    
    if card.rules is not None:
        for rule in card.rules:
            desc += "%s\n" % rule
    else:
        desc = '\u200b'

    embed.add_field(name=name, value=desc, inline=False)

    return embed


# Construct an Embed object from a Trainer or Energy card and it's set
def trainer_embed(card):
    desc = "%s - %s" % (card.supertype, card.subtypes)
    embed = discord.Embed(title=card.name, description=desc)

    for text in card.rules:
        embed.add_field(name='\u200b', value=text)

    return embed


# Get a card object from the passed name and set code
def parse_card(name, card_set):
    # If the card set includes a specific number, we can just use that to
    # get the card
    card = None
    if "-" in card_set:
        card = Card.find(card_set)
        if card is None:
            return "No results for card `%s`" % card_set
    else:
        # Search for the given card
        cards = Card.where(name = name, setCode=card_set)

        if len(cards) == 0:
            return "No results found for '%s' in set `%s`" % (name, card_set)

        if len(cards) > 1:
            return ("Too many results. Try specifying the card number too. "
                    "For example `[p]show %s %s-%s`" % (name, card_set, cards[0].number))

        card = cards[0]

    return card


# Given a card name and set code, get an embed for that card
@lru_cache(maxsize=1024)
def show(name, card_set_text):
    card = parse_card(name, card_set_text)

    if type(card) == str:
        return card

    card_set = Set.find(card.set.id)
    return embed_create(card, card_set)


# Given a card name and set code, return the card text as plain text
def text(name, card_set_text):
    card = parse_card(name, card_set_text)
    card_set = Set.find(card.set.id)

    # Create a string for the card text
    return_str = "```\n"

    # Pokemon are the most involved as they have a lot going on
    if card.supertype == "Pokémon":
        # Start with the Pokemon's name and type(s)
        return_str += "%s - %s" % (card.name, "/".join(card.types))

        # Some Pokemon have no HP (e.g. the second half of LEGEND cards),
        # so do only add it if it exists
        if card.hp is not None:
            return_str += " - HP%s\n" % (card.hp)
        else:
            return_str += "\n"

        return_str += "%s Pokemon" % card.subtypes
        if card.evolvesFrom is not None and card.evolvesFrom != "":
            return_str += " (Evolves from %s)" % card.evolvesFrom
        if len(card.subtypes) > 1:
            return_str += "%s" % card.subtypes[1]

        return_str += "\n\n"
        
        # Ancient Traits
        if card.ancientTrait is not None:
            return_str += "Ancient Trait: %s\n" % card.ancientTrait.name
            return_str += "%s\n" % card.ancientTrait.text
            return_str += "\n"

        # Add the ability if present
        if card.abilities is not None:
            for ability in card.abilities:
                return_str += "%s: %s\n" % (ability.type, ability.name)
                return_str += "%s\n" % ability.text
                return_str += "\n"

        # Add any attacks, including shorthand cost, text and damage
        if card.attacks is not None:
            for attack in card.attacks:
                for cost in attack.cost:
                    return_str += "%s" % short_energy[cost]

                return_str += " %s" % attack.name

                if attack.damage != '':
                    return_str += ": %s damage\n" % attack.damage
                else:
                    return_str += "\n"

                if attack.text is not None:
                    return_str += "%s\n" % attack.text

                return_str += "\n"

        # Add weakness, resistances and retreat if they exist
        if card.weaknesses is not None:
            for weakness in card.weaknesses:
                return_str += ("Weakness: %s (%s)\n" % (weakness.type, weakness.value))

        if card.resistances is not None:
            for resistance in card.resistances:
                return_str += ("Resistance: %s (%s)\n" % (resistance.type, resistance.value))

        if card.retreatCost is not None:
            return_str += "Retreat: %s" % len(card.retreatCost)
        
        # Ruleboxes
        if card.rules is not None:
            return_str += "\n\n"
            for rule in card.rules:
                return_str += "%s" % rule

    # Trainers and Energy are a lot easier
    elif card.supertype == "Trainer" or card.supertype == "Energy":
        return_str += "%s\n" % card.name
        return_str += "%s\n\n" % card.subtypes
        return_str += "%s\n" % "\n\n".join(card.rules)

    # Finally, get the set and legality info
    return_str += "\n\n%s - %s/%s" % (card_set.name, card.number, card_set.printedTotal)
    if card_set.legalities.standard == 'Legal':
        return_str += " \u2705 (Standard)"
    elif card_set.legalities.standard == 'Banned':
        return_str += " \u274C (Standard)"
    if card_set.legalities.expanded == 'Legal':
        return_str += " \u2705 (Expanded)"
    elif card_set.legalities.expanded == 'Banned':
        return_str += " \u274C (Expanded)"
    if card_set.legalities.unlimited == 'Legal':
        return_str += " \u2705 (Legacy)"
    elif card_set.legalities.unlimited == 'Banned':
        return_str += " \u274C (Legacy)"

    return_str += "```\n"
    return return_str


class PokemonTCGv2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.executor = ThreadPoolExecutor()

    def __unload(self):
        self.executor.shutdown(wait=True)

    async def _run_in_thread(self, *args):
        return await self.bot.loop.run_in_executor(self.executor, *args)

    async def _smart_send(self, destination, message):
        if isinstance(message, discord.Embed):
            await destination.send(embed=message)
        elif message:
            for page in pagify(message):
                await destination.send(page)

    @commands.command(pass_context=True)
    async def card(self, ctx, *, card_name: str):
        """
        Gives a list of all cards matching the search.
        Also displays the set code and name.
        Examples:
            !card ambipom
            !card ninja boy
            !card splash energy
        """
        (message, results) = await self._run_in_thread(search, card_name)

        if results > MAX_LINES:
            await ctx.send("Results list is too long, messaging instead")
            destination = ctx.message.author
        else:
            destination = ctx.message.channel

        await self._smart_send(destination, message)

    @commands.command(pass_context=True)
    async def show(self, ctx, set_text: str, *, name: str = None):
        """
        Displays the text and image of the given card from the given set.
        If you are unsure of the set code, find it using [p]card first.
        Examples:
            !show xy11-91
            !show xy11-103
            !show xy9-113
        """
        message = await self._run_in_thread(show, name, set_text)
        await self._smart_send(ctx.message.channel, message)

    @commands.command(pass_context=True)
    async def text(self, ctx, set_text: str, *, name: str = None):
        """
        Similar to [p]show, but gives just the card text in a copy-and-pastable format.
        Examples:
            !text xy11-91
            !text xy11-103
            !text xy9-113
        """
        message = await self._run_in_thread(text, name, set_text)
        await self._smart_send(ctx.message.channel, message)
