import requests
import json
import discord
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify

# Maximum number of rulings before giving up on creating an embed.
MAX_RULINGS = 3

# Compendium Icon
COMPENDIUM_ICO = 'https://compendium.pokegym.net/wp-content/uploads/2021/08/cropped-cpdm_ball-32x32.png'

# Variables for making Compendium Requests
url = "https://compendium.pokegym.net/wp-json/relevanssi/v1/search?keyword="
ruletype = "&type=ruling"
headers = {"Authorization": "Basic Um90b21QaG9uZTpYc2xOIHBXa1YgTFVnciAxdHNGIHBkM08gTHNvMw==", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36"}
payload = {}

# Given string "searchtext", search the compendium for rulings.
def compsearch(text):
    embed = None
    if text == "":
        return ("", 0)
    
    # Convert strings to appropriate url strings
    urltext = text.replace(" ","+")

    # Create the request URL
    finalurl = f"https://compendium.pokegym.net/wp-json/relevanssi/v1/search?keyword={urltext}&type=ruling"

    response = requests.get(finalurl, headers=headers)

    r = json.loads(response.text)
    
    # Set some embed variabled
    title = text.title()

    # Validate response is not empty
    if response.status_code == 500:
        return ("No results were found! Please check the terms you're searching. If you feel there should be a ruling here, feel free to ask Team Compendium in the forums: https://pokegym.net/community/index.php?forums/ask-the-rules-team.25/", 0)
    elif len(r) > MAX_RULINGS:
        url = f'https://compendium.pokegym.net/?s={urltext}'
        embed = discord.Embed(title=title, url=url, description="Too many results to display! Top 3 hits listed below. Use the title to view the full list.\n\nIf you don't find an answer below, check/post in Ask the Rules Team forum.")
        
        for rule in r[:3]:
            question = rule['meta']['question']
            answer = rule['meta']['ruling'] + ' (' + rule['meta']['source'][0] + ')'

            if bool(question) is True:
                embed.add_field(name="Question", value=question, inline=False)
                
            embed.add_field(name="Ruling", value=answer, inline=False)
        
        embed.set_footer(text="Compendium Team", icon_url=COMPENDIUM_ICO)

        return (embed, len(r))
    
    # Let's create a Discord Embed!
    if len(r) == 1:
        url = r[0]['link']
        question = r[0]['meta']['question']
        answer = r[0]['meta']['ruling']
        source = r[0]['meta']['source'][0]

        embed = discord.Embed(title=title, url=url, description="If you don't find an answer below, check/post in Ask the Rules Team forum.")

        if bool(question) is True:
            embed.add_field(name="Question", value=question, inline=False)
            
        embed.add_field(name="Ruling", value=answer, inline=False)

        embed.set_footer(text=source, icon_url=COMPENDIUM_ICO)

        return (embed, len(r))
    
    elif len(r) > 1:
        url = f'https://compendium.pokegym.net/?s={urltext}'
        embed = discord.Embed(title=title, url=url, description="If you don't find an answer below, check/post in Ask the Rules Team forum.")
        
        for rule in r:
            question = rule['meta']['question']
            answer = rule['meta']['ruling'] + ' (' + rule['meta']['source'][0] + ')'

            if bool(question) is True:
                embed.add_field(name="Question", value=question, inline=False)
                
            embed.add_field(name="Ruling", value=answer, inline=False)
        
        embed.set_footer(text="Compendium Team", icon_url=COMPENDIUM_ICO)

        return (embed, len(r))


def rulefind(num):
    embed = None
    if num == "":
        return ("")
    
    try:
        int(num)
    except ValueError:
        return "That isn't a valid value! Please use a Ruling ID!"
    
    finalurl = f"https://compendium.pokegym.net/wp-json/wp/v2/ruling/{num}"
    
    response = requests.get(finalurl, headers=headers)
    
    r = json.loads(response.text)
    
    if response.status_code == 404:
        return "No results were found! Please check the ID again."
    
    question = r['meta']['question']
    answer = r['meta']['ruling']
    url = f"https://compendium.pokegym.net/ruling/{num}"
    source = r['meta']['source'][0]
    
    title = "Pokémon Rulings Compendium"
    
    embed = discord.Embed(title=title, url=url)
    
    if bool(question) is True:
        embed.add_field(name="Question", value=question, inline=False)
        
    embed.add_field(name="Answer", value=answer, inline=False)
    
    embed.set_footer(text=source, icon_url=COMPENDIUM_ICO)
    
    return embed


class Compendium(commands.Cog):
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
    async def compendium(self, ctx, *, searchtext: str):
        """
        Returns rulings related to the search terms.
        Usage:
            !compendium Abyssal Gate
            !compendium Recycle Energy Spectral Breach
        """
        (message, results) = await self._run_in_thread(compsearch, searchtext)

        await self._smart_send(ctx.message.channel, message)
        
    @commands.command(pass_context=True)
    async def ruling(self, ctx, *, rulingnum: str):
        """
        Returns the specifed ruling number.
        Usage:
            !ruling 40
        """
        message = await self._run_in_thread(rulefind, rulingnum)
        
        await self._smart_send(ctx.message.channel, message)

    @commands.command(pass_context=True)
    async def about(self, ctx):
        await self._smart_send(ctx.message.channel, "Use !compendium to search for rulings.\n\nAsk more questions and read more answers in the Ask the Rules Team forum: https://pokegym.net/community/index.php?forums/ask-the-rules-team.25/")
