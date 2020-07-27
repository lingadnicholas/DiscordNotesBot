import discord
import random
from discord.ext import commands, tasks
from bot import client
import globals
from cryptography.fernet import Fernet

class Misc(commands.Cog): #inherits from commands.Cog 

    def __init(self, client):
        self.client = client

    # Events
    @commands.Cog.listener() 
    async def on_ready(self):
        await client.change_presence(status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.playing, name="n!help"))
        print('Bot is online')
        print(discord.__version__)

    # Commands 
    @commands.command() 
    async def ping(self, ctx):
        await ctx.send(f'Pong! {round(client.latency * 1000)}ms')
    
    @commands.command()
    async def encryptThis(self, ctx, *, message):
        print(message)
        key = open("cogs/key.key", "rb").read()
        encoded_message = message.encode()
        f = Fernet(key)
        encrypted_message = (f.encrypt(encoded_message)).decode()
        sqlstring = f"INSERT INTO notes (category, note_id, note, timestamp, user_id) VALUES ('potato', '3', '{encrypted_message}', 'timestamp', 'id')"
        print(sqlstring)

    @commands.command(aliases=['8ball'])
    async def _8ball(self, ctx, *, question): #* allows you to take in multiple arguments as one argument 
        responses = ['It is certain.',
                    'It is decidedly so.',
                    'Without a doubt.',
                    'Yes - definitely.',
                    'You may rely on it.',
                    'As I see it, yes.',
                    'Most likely.', 
                    'Outlook Good.',
                    'Yes.',
                    'Signs point to yes.',
                    'Reply hazy, try again.',
                    'Ask again later.',
                    'Better not tell you now.',
                    'Cannot predict now.',
                    'Concentrate and ask again.',
                    "Don't count on it.",
                    'My reply is no.',
                    'My sources say no.',
                    'Outlook not so good.',
                    'Very doubtful.',
                    "Shouldn't you be studying?"
                    ]
        await ctx.send(f'Question: {question}\nAnswer: {random.choice(responses)}')


def setup(client): 
    client.add_cog(Misc(client))