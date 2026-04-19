from builtins import str

import discord
from discord import client, message
from discord.ext import commands
import logging
import json

from discord.ext.commands import Context
from dotenv import load_dotenv
import os

from data.foods import *
from data.foods import Food
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
    banned_pet_ids: set[int] = set()
    banned_food_ids: set[int] = set()
    thread: discord.TextChannel

    def __init__(self, host: discord.Member, channel: discord.TextChannel):
        self.host = host
        self.players = [host]
        self.banned = []
        self.thread = channel


    def ban(self, target: Pet | Food):
        if type(target) is Pet:
            print("Banning pet!")
            self.banned_pet_ids.add(target.id)
        elif type(target) is Food:
            self.banned_food_ids.add(target.id)
            print("Banning food!")
        else:
            print("Ban failed")

        self.banned.append(target)

    def is_pack_valid(self, pack: dict) -> str:
        if not "Minions" in pack:
            return "Invalid pack: No Minions"

        if not "Spells" in pack:
            return "Invalid pack: No Spells"

        pack_pets: list[int] = pack["Minions"]
        pack_foods: list[int] = pack["Spells"]

        banned_pet_ids_in_pack = list(filter(lambda pet: pet in self.banned_pet_ids, pack_pets))
        banned_foods_ids_in_pack = list(filter(lambda food: food in self.banned_food_ids, pack_foods))

        if len(banned_pet_ids_in_pack + banned_foods_ids_in_pack) == 0:
            return "Valid pack!"

        print(banned_pet_ids_in_pack) # list[petId] -> list[petName]

        print(list(filter(lambda pet: pet in self.banned_pet_ids, pack_pets)))
        print(list(map(lambda pet: pet.name, filter(lambda pet: pet in self.banned_pet_ids, pets))))

        banned_pets_in_pack: list[Pet] = list(map(lambda pet: pet.name, filter(lambda pet: pet in self.banned_pet_ids, pets)))
        banned_foods_in_pack: list[Food] = list(map(lambda food: food.name, filter(lambda food: food in self.banned_food_ids, foods)))

        return 'Banned pets detected: ' + ', '.join(banned_pets_in_pack + banned_foods_in_pack)



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
async def ban(ctx: Context, arg):
    # TODO: Determine game from active channel instead
    participating_games: list[Game] = list(filter(lambda g: ctx.author in g.players, active_games))

    if len(participating_games) == 0:
        await ctx.send("You're currently not participating in a game")
        return

    # TODO: Move to game
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

    current_game.ban(target=ban_item)
    await ctx.send(f"{arg.title()} has been banned")


@bot.command()
async def check_pack(ctx: Context, *, message: str):
    pack = json.loads(message)

    participating_games: list[Game] = list(filter(lambda g: ctx.author in g.players, active_games))
    current_game = participating_games[0]

    response = current_game.is_pack_valid(pack)
    await ctx.send(response)


def get_lobby_for_channel(channel: discord.TextChannel | discord.VoiceChannel | discord.StageChannel | discord.Thread | discord.DMChannel | discord.PartialMessageable | discord.GroupChannel):
    return next((game for game in active_games if game.thread == channel), None)


bot.run(token, log_handler=handler, log_level=logging.DEBUG)