import discord
from discord import client, message
from discord.ext import commands
import logging

from discord.ext.commands import Context
from dotenv import load_dotenv
import os

from data.foods import *
from data.pets import *

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

class Game:
    host: discord.User | discord.Member
    players: list[discord.User | discord.Member] = []
    banned: list[Pet | Food] = []
    thread: discord.TextChannel

    def __init__(self, host: discord.Member, channel: discord.TextChannel):
        self.host = host
        self.players = [host]
        self.banned = []
        self.thread = channel


active_games: list[Game] = []


@bot.event
async def on_ready():
    print(f"Successfully started up {bot.user.name}!")


# TODO: Create dedicated thread for starting a game
# TODO: Track active game with banned critters / foods
# TODO: Track foods / critters that are banned w/ mapping to their IDs
# TODO: Allow users to select bans from a given tier
@bot.command()
async def create_lobby(ctx: Context):
    print(f"Starting a new lobby owned by {ctx.author.name}")
    new_channel = await ctx.message.guild.create_text_channel(f"{ctx.author.name} Lobby")

    new_game: Game = Game(host=ctx.author, channel=new_channel)
    active_games.append(new_game)

    await new_channel.send(f"New lobby created by {ctx.author.mention}")


@bot.command()
async def close_lobby(ctx: Context):
    associated_game = get_lobby_for_channel(ctx.channel)

    if associated_game is None:
        print("User attempted to close a non-lobby thread")
        return

    if associated_game.host != ctx.author:
        await ctx.send(f"You cannot close a lobby for {associated_game.host}")
        return

    await ctx.channel.delete(reason=f"Game closed by {ctx.author}")
    active_games.remove(associated_game)


@bot.command()
async def hello_world(ctx: Context):
    await ctx.send(f"Hello {ctx.author.mention}")


@bot.command()
async def ban(ctx: Context, arg):
    # TODO: Determine game from active channel instead
    participating_games: list[Game] = list(filter(lambda g: ctx.author in g.players, active_games))

    if len(participating_games) == 0:
        await ctx.send("You're currently not participating in a game")
        return

    ban_item: Pet | Food | None = next((item for item in (pets + foods) if item.name == arg.lower()), None)
    valid_request = ban_item is not None

    if not valid_request:
        await ctx.send(f"You cannot ban a {arg.title()}, it does not exist!")
        return

    ban_item: Pet | Food

    # TODO: Update to NOT assume you're in the first game
    current_game = participating_games[0]
    if ban_item in current_game.banned:
        await ctx.send(f"{arg.title()} has already been banned!")
        return

    current_game.banned.append(ban_item)
    await ctx.send(f"Banning {arg.title()}")


def get_lobby_for_channel(channel: discord.TextChannel | discord.VoiceChannel | discord.StageChannel | discord.Thread | discord.DMChannel | discord.PartialMessageable | discord.GroupChannel):
    return next((game for game in active_games if game.thread == channel), None)


bot.run(token, log_handler=handler, log_level=logging.DEBUG)