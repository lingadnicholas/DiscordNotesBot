import discord
import random
import os
import mysql.connector as mysql
from discord.ext import commands, tasks
import globals
import connect

client = commands.Bot(command_prefix = 'n!')

#Database

db = connect.connectDb()

#Create cursor instance
my_cursor = db.cursor() 

my_cursor.execute("CREATE DATABASE IF NOT EXISTS notesdb") 
my_cursor.execute("CREATE TABLE IF NOT EXISTS users (name VARCHAR(255), user_id BIGINT PRIMARY KEY)")
my_cursor.execute("CREATE TABLE IF NOT EXISTS categories (category VARCHAR(255), username VARCHAR(255), num_notes INT, user_id BIGINT, uniqueID INTEGER AUTO_INCREMENT PRIMARY KEY)")
my_cursor.execute("CREATE TABLE IF NOT EXISTS notes (category VARCHAR(255), note_id INT, note LONGTEXT, timestamp DATETIME, user_id BIGINT, uniqueID INTEGER AUTO_INCREMENT PRIMARY KEY)")


#Load cogs
for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        client.load_extension(f'cogs.{filename[:-3]}')

#Event Errors
@client.event
async def on_command_error(ctx,error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"{globals.ERROR}\n{ctx.message.author.mention}, use a valid command.")

client.run('NzI4MzU0MzY1OTMyNDM3NTk0.XwnyzA.BMtPWqzuALN-qi7AHzp8aig_6Fs') 
