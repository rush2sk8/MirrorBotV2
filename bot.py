import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from shutil import which
from urllib.parse import urlsplit, urlunsplit

import discord
import requests
from discord.ext import commands, tasks
from dotenv import load_dotenv
from pystreamable import StreamableApi
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
        message, url, site = urls.pop(0)

        if(site == "twitch"):
            await twitch(message, url)
        elif(site == "reddit"):
            await reddit(message, url)

async def twitch(message, url):
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
                file_name = x.split(" ")[-1].strip().rstrip('\n').rstrip('\r')

        shortcode = streamable_api.upload_video(
            file_name, title)['shortcode']
        while streamable_api.get_info(shortcode)["percent"] != 100:
            time.sleep(0.5)

        await message.channel.send(f'https://streamable.com/{shortcode}')
        await message.delete()

        os.remove(file_name)
    except Exception as e:
        print(e)
        pass


async def reddit(message, url):
    url = f'{urlunsplit(urlsplit(url)._replace(query="", fragment=""))[:-1]}.json'
    try:
        json = requests.get(
            url, headers={'User-agent': 'reddit-discordbot'}).json()
        video_url = json[0]["data"]["children"][0]["data"]["secure_media"]["reddit_video"]["fallback_url"]

        video_title = json[0]["data"]["children"][0]["data"]["title"]

        l = video_url.split("DASH")[0]
        r = video_url.split("?")[-1]

        audio_url = f'{l}DASH_audio.mp4?{r}'

        final_video_name = "video.mp4"

        urllib.request.urlretrieve(
            video_url, filename=final_video_name)

        try:
            urllib.request.urlretrieve(audio_url, filename="audio.mp4")

            subprocess.call(
                "ffmpeg -y -hide_banner -loglevel error -i video.mp4 -i audio.mp4 -c:v copy -c:a aac output.mp4",
                shell=True
            )

            final_video_name = "output.mp4"
            os.remove("audio.mp4")

        except Exception:
            pass

        shortcode = streamable_api.upload_video(
            final_video_name, video_title)['shortcode']

        while streamable_api.get_info(shortcode)["percent"] != 100:
            time.sleep(1)

        await message.channel.send(f'https://streamable.com/{shortcode} from: {message.author.mention}')
        await message.delete()

        os.remove(final_video_name)
        os.remove("video.mp4")
    except Exception:
        pass

@bot.event
async def on_message(message):
    if message.author.id == bot.user.id:
        return

    m = message.content
    extractor = URLExtract()
    found = extractor.find_urls(m)

    if len(found) > 0:

        if "clips" in message.channel.name and \
            ("twitch" in found[0]) and \
                ("clip" in found[0]):
            urls.append((message, found[0], "twitch"))

        elif ("reddit" in found[0]):
            urls.append((message, found[0], "reddit"))

if which("ffmpeg") is not None:
    run_upload.start()
    bot.run(DISCORD_TOKEN)
else:
    sys.exit("Bro install ffmpeg")
