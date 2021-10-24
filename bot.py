import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from shutil import which
from urllib.parse import urlsplit, urlunsplit
import pickledb

import discord
import requests
import spaw
from discord.ext import commands, tasks
from dotenv import load_dotenv
from pystreamable import StreamableApi
from urlextract import URLExtract

load_dotenv(dotenv_path=Path('.')/'.env')

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
S_USER = os.getenv('S_USER')
S_PASS = os.getenv('S_PASS')

spaw_obj = spaw.SPAW()
bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())
streamable_api = StreamableApi(S_USER, S_PASS)
spaw_obj.auth(S_USER, S_PASS)

db = pickledb.load("urls.db", True)

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
    db_query = db.get(url)
    if db_query == False:
        try:
            return_code = spaw_obj.videoImport(url)

            shortcode = return_code["shortcode"]
            while streamable_api.get_info(shortcode)["percent"] != 100:
                time.sleep(0.5)

            db.set(url, shortcode)
            await message.channel.send(f'https://streamable.com/{shortcode}')
        except Exception as e:
            print(e)
            pass
    else:
        await message.channel.send(f'https://streamable.com/{db_query}')

async def reddit(message, url):
    url = f'{urlunsplit(urlsplit(url)._replace(query="", fragment=""))[:-1]}.json'
    db_query = db.get(url)
    if db_query == False:
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

            try:
                os.rename(final_video_name, f'{video_title}.mp4')
            except Exception as e:
                print(e)

            upload_status = spaw_obj.videoUpload(f'{video_title}.mp4')
            shortcode = upload_status["shortcode"]

            while streamable_api.get_info(shortcode)["percent"] != 100:
                time.sleep(1)

            db.set(url, shortcode)
            await message.channel.send(f'https://streamable.com/{shortcode} from: {message.author.mention}')

            try:
                os.remove(f'{video_title}.mp4')
                os.remove("video.mp4")
                os.remove("output.mp4")
            except Exception as e:
                print(e)

        except Exception:
            pass
    else:
        await message.channel.send(f'https://streamable.com/{db_query}')

@bot.event
async def on_message(message):
    if message.author.id == bot.user.id or message.channel.is_nsfw():
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
