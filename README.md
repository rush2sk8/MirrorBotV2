# Rewrite of MirrorBot

A discord bot that will mirror twitch clips and vreddit links. A rewrite of the original MirrorBot. 

## Installation
`pip install -r requirements.txt`

## Necessary files

* `.env` with the following fields
  - `DISCORD_TOKEN` Discord api token
  - `S_USER` Streamable user name
  - `S_PASS` Streamable password

## Launching the bot
Launch with [`pm2`](https://www.npmjs.com/package/pm2)

`pm2 start bot.py --interpreter python3 --name mirrorbot`
