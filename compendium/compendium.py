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

    # Validate response is not empty
    if response.status_code == 500:
        return ("", 0)
    elif len(r) > MAX_RULINGS:
        return ("", len(r))

    # Set some embed variabled
    title = text.title()
    
    # Let's create a Discord Embed!
    if len(r) == 1:
        url = r[0]['link']
        question = r[0]['meta']['question']
        answer = r[0]['meta']['ruling']
        source = r[0]['meta']['source'][0]

        embed = discord.Embed(title=title, url=url, description="If you don't find an answer below, check/post in Ask the Rules Team forum.")

        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=answer, inline=False)

        embed.set_footer(text=source, icon_url=COMPENDIUM_ICO)

        return (embed, len(r))
    
    elif len(r) > 1:
        url = f'https://compendium.pokegym.net/?s={urltext}'
        embed = discord.Embed(title=title, url=url, description="If you don't find an answer below, check/post in Ask the Rules Team forum.")
        
        for rule in r:
            question = rule['meta']['question']
            answer = rule['meta']['ruling'] + ' (' + rule['meta']['source'][0] + ')'

            embed.add_field(name="Question", value=question, inline=False)
            embed.add_field(name="Answer", value=answer, inline=False)
        
        embed.set_footer(text="Compendium Team", icon_url=COMPENDIUM_ICO)

        return (embed, len(r))



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

        if results > MAX_RULINGS:
            await self._smart_send(ctx.message.channel, "Results list is too long, try using more terms.")
        elif results == 0:
            await self._smart_send(ctx.message.channel, "No results were found, check the terms you're searching. If you feel there should be a ruling here, feel free to ask Team Compendium in the forums: https://pokegym.net/community/index.php?forums/ask-the-rules-team.25/")
        else:
            await self._smart_send(ctx.message.channel, message)

    @commands.command(pass_context=True)
    async def about(self, ctx):
        await self._smart_send(ctx.message.channel, "Use !compendium to search for rulings.\n\nAsk more questions and read more answers in the Ask the Rules Team forum: https://pokegym.net/community/index.php?forums/ask-the-rules-team.25/")
