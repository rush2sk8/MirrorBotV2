import os
import re
from pathlib import Path
import re

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from pystreamable import StreamableApi
import subprocess
import time
from urlextract import URLExtract

load_dotenv(dotenv_path=Path('.')/'.env')

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
S_USER = os.getenv('S_USER')
S_PASS = os.getenv('S_PASS')

bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())
streamable_api = StreamableApi(S_USER, S_PASS)

urls = []

@bot.event
async def on_ready():
    """Event when the bot logs in"""
    await bot.change_presence(activity=discord.Streaming(name="by rush2sk8", url='https://www.twitch.tv/rush2sk8'))
    print('We have logged in as {0.user}'.format(bot))


@tasks.loop(seconds=1)
async def run_upload():
    if len(urls) > 0:
        message, url = urls.pop(0)

        try:
            p = subprocess.check_output(
                ["twitch-dl", "download", "-q", "source", "--debug", "--no-color", url])
            output = p.decode('utf-8')

            title = ''
            file_name = ''

            for x in output.split("\n"):
                if "Found: " in x:
                    title = re.search(r"Found: (.*) by", x).group(1)
                elif "Downloaded: " in x:
                    file_name = x.split(" ")[-1]

            shortcode = streamable_api.upload_video(
                file_name, title)['shortcode']
            while streamable_api.get_info(shortcode)["percent"] != 100:
                time.sleep(0.5)

            await message.channel.send(f'https://streamable.com/{shortcode}')
            await message.delete()

            os.remove(file_name)
        except Exception:
            pass

@bot.event
async def on_message(message):
    if message.author.id == bot.user.id:
        return

    m = message.content

    if "clips" in message.channel.name:
        print(m)
        extractor = URLExtract()
        found = extractor.find_urls(m)

        if len(found) > 0 and ("twitch" in found[0]) and ("clip" in found[0]):
            urls.append((message, found[0]))

run_upload.start()
bot.run(DISCORD_TOKEN)
