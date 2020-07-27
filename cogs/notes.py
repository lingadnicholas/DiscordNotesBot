import discord
from discord.ext import commands
import mysql.connector as mysql
from bot import db, my_cursor, client
import globals
from datetime import datetime
import asyncio
from cryptography.fernet import Fernet

class Notes(commands.Cog): #inherits from commands.Cog 

    def __init__(self, client): 
        self.client = client


    
    #Commands 

    #Allows the user to create a new note in an already existing category.
    #Syntax: n!new [Category] [Note]
    #Example of use: n!new Chickens I think chickens are really cool
    #Category is 'Chickens' and note is 'I think chickens are really cool'
    @commands.command(name='new') 
    async def create_note(self, ctx, category, *, note):
        #Entire message after category is note.
        #If category DNE, error
        id = str(ctx.message.author.id)
        sqlstring = f"SELECT category FROM categories WHERE user_id = {id} AND category = '{category}'"
        if not self.__fetchResult(sqlstring):
            await ctx.send(f'{globals.ERROR}\nSorry {ctx.message.author.mention}, category [{category}] does not exist. Please try again.')
            return 
        
        #REACTION CONFIRMATION to store message
        msg = await ctx.send(f"{ctx.message.author.mention}, react with \U00002705 if you want to add note to category [{category}]")
        await msg.add_reaction("\U00002705")
        def check(reaction, user):
            return user == ctx.message.author and (str(reaction.emoji) == "\U00002705")

        try:
            reaction, user = await client.wait_for('reaction_add', timeout = 10.0, check=check) 
        except asyncio.TimeoutError:
            await msg.edit(content=f"{ctx.message.author.mention}, note was not stored because you took too long to react.")
            return 
        else: 
            #Need to store the note, datetime, update number of notes in category
            timestamp = str(ctx.message.created_at)[:19]

            #Update number of notes in category
            sqlstring = f"SELECT num_notes FROM categories WHERE user_id = {id} AND category = '{category}'"
            result = (self.__fetchResult(sqlstring))[0]
            num_notes = result[0]
            num_notes +=1
            sqlstring = f"UPDATE categories SET num_notes = {num_notes} WHERE user_id = {id} AND category = '{category}'"
            self.__commit(sqlstring)

            #Encrypt note
            key = open('cogs/key.key', 'rb').read()
            encoded_message = note.encode()
            f = Fernet(key) 
            encrypted_message = (f.encrypt(encoded_message)).decode()
            sqlstring = f"INSERT INTO notes (category, note_id, note, timestamp, user_id) VALUES ('{category}', {num_notes}, '{encrypted_message}', '{timestamp}', {id})"
            self.__commit(sqlstring)

            await msg.edit(content=f'{globals.SUCCESS}\n {ctx.message.author.mention}, your note was successfully stored in category [{category}] as note number {num_notes}')
            return

    #Allows the user to delete an existing note in an existing category
    #Syntax: n!new [Category] [Note_ID]
    #Note_ID is the # that note is in the category 
    #Example of use: n!delete Chickens 1
    #Category is 'Chickens' and the note_id of 'I think chickens are really cool' is 1
    @commands.command(name='delete')
    async def remove_note(self, ctx, category, note_id):
        id = str(ctx.message.author.id)

        #Check if note_id arg is an int
        if note_id.isnumeric() is False:
            await ctx.send(f'{globals.ERROR}\n{ctx.message.author.mention}, you must enter a number.')
            return

        #Check if category for specific user exists 
        #If category does not exist, return an error to the user
        sqlstring = f"SELECT category from categories WHERE user_id = {id} AND category = '{category}'"

        if not self.__fetchResult(sqlstring):
            await ctx.send(f'{globals.ERROR}\n{ctx.message.author.mention}, category [{category}] does not exist, so nothing was deleted.')
            return
        
        #Check if note within that category exists
        #If note does not exist, return an error to the user
        sqlstring = f"SELECT note from notes WHERE user_id = {id} AND category = '{category}' AND note_id = {note_id}"
        if not self.__fetchResult(sqlstring):
            await ctx.send(f'{globals.ERROR}\n{ctx.message.author.mention}, a note in category [{category}] with ID [{note_id}] does not exist.')
            return

        #REACTION CONFIRMATION if user wants to delete note
        msg = await ctx.send(f"{ctx.message.author.mention}, react with \U00002705 if you want to delete note {note_id} in category [{category}]")

        await msg.add_reaction("\U00002705")
        def check(reaction, user):
            return user == ctx.message.author and (str(reaction.emoji) == "\U00002705")

        try:
            reaction, user = await client.wait_for('reaction_add', timeout = 10.0, check=check) 
        except asyncio.TimeoutError:
            await msg.edit(content=f"{ctx.message.author.mention}, note was not deleted because you took too long to react.")
            return 
        else: 
            sqlstring = f"DELETE FROM notes WHERE user_id = {id} AND category = '{category}' AND note_id = {note_id}"
            self.__commit(sqlstring)

            #Update num_notes
            sqlstring = f"SELECT num_notes FROM categories WHERE user_id = {id} AND category = '{category}'"
            result = (self.__fetchResult(sqlstring))[0]
            num_notes = result[0]
            num_notes -=1
            sqlstring = f"UPDATE categories SET num_notes = {num_notes} WHERE user_id = {id} AND category = '{category}'"
            self.__commit(sqlstring)

            #All notes above note_id must have their note_id lowered by 1
            sqlstring = f"SELECT note_id FROM notes WHERE user_id = {id} AND category = '{category}'"
            result = self.__fetchResult(sqlstring)
            note_id_int = int(note_id)
            for row in result: 
                old_id = row[0]
                if old_id > note_id_int:
                    new_id = old_id - 1
                    sqlstring = f"UPDATE notes SET note_id = {new_id} WHERE user_id = {id} AND category = '{category}' AND note_id = {old_id}"
                    self.__commit(sqlstring)

            await msg.edit(content=f'{globals.SUCCESS}\n{ctx.message.author.mention}, your message was successfully deleted.')
            return

    #Allows the user to change the content of notes that already exist. 
    #NOTE: Also updates timestamp 
    #Syntax: n!edit [Category] [Note_ID] [Note]
    #Example: n!edit Chickens 1 I am changing the content of this note. 
    @commands.command(name='edit')
    async def edit_note(self, ctx, category, note_id, *, note): 
        id = str(ctx.message.author.id)
        #If category doesn't exist, error
        sqlstring = f"SELECT category FROM categories WHERE user_id = {id} AND category = '{category}'"
        if not self.__fetchResult(sqlstring): #Category doesn't exist
            print(f"ERROR - FAILED TO EDIT NOTE: Category {category} doesn't exist")
            await ctx.send(f"{globals.ERROR}\nSorry {ctx.message.author.mention}, Category [{category}] doesn't exist.")
            return

        #If note doesn't exist, error
        sqlstring = f"SELECT note_id FROM notes WHERE user_id = {id} AND category = '{category}' AND note_id = {note_id}"
        if not self.__fetchResult(sqlstring):
            print(f"ERROR - FAILED TO EDIT NOTE: Note #{note_id} in Category {category} doesn't exist.")
            await ctx.send(f"{globals.ERROR}\nSorry {ctx.message.author.mention}, Note #{note_id} in Category {category} doesn't exist.")
            return

        #REACTION CONFIRMATION if user wants to edit message
        msg = await ctx.send(f"{ctx.message.author.mention}, react with \U00002705 if you want to edit note {note_id} in category [{category}]")

        await msg.add_reaction("\U00002705")
        def check(reaction, user):
            return user == ctx.message.author and (str(reaction.emoji) == "\U00002705")

        try:
            reaction, user = await client.wait_for('reaction_add', timeout = 30.0, check=check) 
        except asyncio.TimeoutError:
            await msg.edit(content=f"{ctx.message.author.mention}, note was not edited because you took too long to react.")
            return 
        else: 
            #Need to store the note, datetime, update number of notes in category

            #Encrypt message
            key = open('cogs/key.key', 'rb').read()
            encoded_message = note.encode()
            f = Fernet(key) 
            encrypted_message = (f.encrypt(encoded_message)).decode()

            timestamp = str(ctx.message.created_at)[:19]
            sqlstring = f"UPDATE notes SET timestamp = '{timestamp}' WHERE user_id = {id} AND category = '{category}' AND note_id = {note_id}"
            self.__commit(sqlstring)
            sqlstring = f"UPDATE notes SET note = '{encrypted_message}' WHERE user_id = {id} AND category = '{category}' AND note_id = {note_id}"
            self.__commit(sqlstring)
            await msg.edit(content=f'{globals.SUCCESS}\n{ctx.message.author.mention}, you successfully edited note {note_id} in Category [{category}].')
            return

    #Allows the user to create a new category of notes. Categories cannot have a space.
    #Syntax: n!newCategory [Category]
    #Example of use: n!newCategory Chickens
    #WRONG example: n!newCategory Chick ens
    @commands.command(name='newCategory', ignore_extra = False)
    async def create_category(self, ctx, category): 
        id = str(ctx.message.author.id)
        name = str(ctx.message.author) 
        self.__addUser(ctx)

        #Check if category for specific user exists already
        sqlstring = f"SELECT category from categories WHERE user_id = {id} AND category = '{category}'"

        #If category exists, then respond to the user saying that category already exists, do nothing
        if self.__fetchResult(sqlstring): #Non empty string, already exists
            print(f'ERROR - FAILED TO CREATE CATEGORY: Category {category} for {name} already exists.')
            await ctx.send(f'{globals.ERROR}\nSorry {ctx.message.author.mention}, Category [{category}] already exists.')
            return
        #Else, create the category (insert into categories table) and respond to the user saying that the category was successfully created
        sqlstring = f"INSERT INTO categories (category, username, num_notes, user_id) VALUES ('{category}', '{name}', 0, {id})"
        self.__commit(sqlstring)


        await ctx.send(f'{globals.SUCCESS}\n{ctx.message.author.mention}, Category [{category}] was successfully created.')

    #Allows the user to delete an entire category and all notes that are stored in that category.
    #Syntax: n!deleteCategory [Category]
    #Example of use: n!deleteCategory Chickens
    @commands.command(name='deleteCategory')
    async def remove_category(self, ctx, category):
        id = str(ctx.message.author.id)
        name = str(ctx.message.author)

        #If category does not exist, return a message saying that the category was unable to be removed
        sqlstring = f"SELECT category from categories WHERE user_id = {id} AND category = '{category}'"
        if not self.__fetchResult(sqlstring): 
            await ctx.send(f'{globals.ERROR}\n{ctx.message.author.mention}, category [{category}] does not exist, and therefore was not deleted.')
            return 

        #REACTION CONFIRMATION if user wants to delete category
        msg = await ctx.send(f"{ctx.message.author.mention}, react with \U00002705 if you want to delete category [{category}]. This WILL **delete all notes** associated with it.")

        await msg.add_reaction("\U00002705")
        def check(reaction, user):
            return user == ctx.message.author and (str(reaction.emoji) == "\U00002705")

        try:
            reaction, user = await client.wait_for('reaction_add', timeout = 10.0, check=check) 
        except asyncio.TimeoutError:
            await msg.edit(content=f"{ctx.message.author.mention}, Category [{category}] was not deleted because you took too long to react.")
            return 
        else: 
            sqlstring = f"DELETE FROM categories WHERE user_id = {id} AND category = '{category}'"
            self.__commit(sqlstring)

            #Remove all notes associated with the category
            sqlstring = f"DELETE FROM notes WHERE user_id = {id} AND category = '{category}'"
            self.__commit(sqlstring)
            await msg.edit(content=f'{globals.SUCCESS}\n{ctx.message.author.mention}, Category [{category}] was successfully deleted.')

    #Allows the user to ask the bot for all categories that they have created.
    #Syntax: n!categories 
    @commands.command(name='categories')
    async def retrieve_categories(self, ctx):
        id = str(ctx.message.author.id)
        sqlstring = f"SELECT category, num_notes FROM categories WHERE user_id = {id}"
        result = (self.__fetchResult(sqlstring))
        print(result)
        if not result: 
            await ctx.send(f"{globals.ERROR}\n{ctx.message.author.mention}, you do not have any categories.")
            return

        cat_string = "Categories:\n"
        for row in result: 
            cat_string += f'{row[0]}\t\t {str(row[1])} Notes stored\n'
        await ctx.send(f'{ctx.message.author.mention}, sending categories to your DMs!')
        await ctx.message.author.send(cat_string)
        return


    #TODO: Need to decrpyt notes (once you encrypt them first, of course)
    #DMs user all notes from category, or a specific note
    #Syntax: n!get [Category] [Note_ID]
    #If note_id is left blank, the user gets DMed all notes from the category. 
    #Example of use: n!get Chickens 1   - Gets note #1 from Chickens
    #Example of use: n!get Chickens     - Gets all notes from Chickens
    @commands.command(name='get')
    async def retrieve_notes(self, ctx, category, note_id = None):
        #DM Format:
        #[Category]
        #\n Note [Note number],    [Timestamp] UTC
        #[Note content]
        #If more, start at Note[Note number]


        id = str(ctx.message.author.id)
        #If category does not exist, return a message saying that the category was unable to be found
        sqlstring = f"SELECT category from categories WHERE user_id = {id} AND category = '{category}'"
        if not self.__fetchResult(sqlstring): 
            await ctx.send(f'{globals.ERROR}\n{ctx.message.author.mention}, category [{category}] does not exist.')
            return 
        result = ''
        note = ''
        timestamp = ''
        msg = None
        cur_id = None
        if note_id is not None and note_id.isnumeric() is False:
            await ctx.send(f'{globals.ERROR}\n{ctx.message.author.mention}, you must enter a number or nothing.')
            return

        #Get num notes
        sqlstring = f"SELECT num_notes FROM categories WHERE user_id = {id} AND category = '{category}'"
        result = (self.__fetchResult(sqlstring))[0]
        num_notes = str(result[0])
        #RETRIEVE ALL NOTES
        if note_id is None:
            msg = await ctx.send(f'{ctx.message.author.mention}, we will DM you all notes in category [{category}]. This may take a while if you have a lot of notes.')

            #Retrieve all notes, timestamps
            sqlstring = f"SELECT note, timestamp, note_id FROM notes WHERE user_id = {id} AND category = '{category}' ORDER BY note_id ASC"
            result = (self.__fetchResult(sqlstring))
                
        #Retrieve specific note
        else:
            msg = await ctx.send(f'{ctx.message.author.mention}, sending note to your DMs!')
            sqlstring = f"SELECT note, timestamp, note_id FROM notes WHERE user_id = {id} AND category = '{category}' AND note_id = {note_id}"
            result = (self.__fetchResult(sqlstring))
            print(result)
            if not result:
                await ctx.send(f'{globals.ERROR}\n{ctx.message.author.mention}, there is no such note with ID [{note_id}]')
                return

        #Create embed to send
        for row in result: 
            note = row[0]
            timestamp = str(row[1])
            cur_id = str(row[2])
            #Decrypt message
            key = open("cogs/key.key", "rb").read()
            f = Fernet(key)
            decrypted_message = (f.decrypt(note.encode())).decode()

            #Create embed to be sent
            embed = discord.Embed(
                title=f"[{category}]Note #{cur_id}/{num_notes}", 
                description=decrypted_message,
                colour = discord.Colour.blue()
            )
            embed.set_footer(text=f"Last edited (UTC): {timestamp}")
            await ctx.message.author.send(embed=embed)
            
        if note_id is None: 
            await msg.edit(content=f"{globals.SUCCESS}\n{ctx.message.author.mention}, all notes were sent to your DMs!")
        else: 
            await msg.edit(content=f"{globals.SUCCESS}\n{ctx.message.author.mention}, the requested note was sent to your DMs!")
        return

    #Private helper methods

    #__addUser returns FALSE if it doesn't add a user (they already exist) 
    # and TRUE when it adds a user (they don't currently exist in the database)
    def __addUser(self,ctx): 
        id = str(ctx.message.author.id) #Search by this! 
        name = str(ctx.message.author) 

        sqlstring = f"INSERT INTO users (name, user_id) VALUES ('{name}', {id}) ON DUPLICATE KEY UPDATE name = '{name}'"
        self.__commit(sqlstring)
    
    #Does my whole print, execute, and commit to database so I don't forget the commit
    def __commit(self, sqlstring): 
        print(sqlstring)
        my_cursor.execute(sqlstring)
        db.commit()

    #Returns fetched results given a sqlstring
    def __fetchResult(self, sqlstring):
        my_cursor.execute(sqlstring)
        return my_cursor.fetchall()

    #Events - Error Handling
    @create_category.error
    @remove_category.error
    async def create_category_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f'{globals.ERROR}\n{ctx.message.author.mention}, you must specify a category name.')
        if isinstance(error, commands.TooManyArguments):
            await ctx.send(f'{globals.ERROR}\n{ctx.message.author.mention}, sorry! Categories cannot have spaces.')

    @remove_note.error
    @create_note.error
    async def remove_note_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f'{globals.ERROR}\n{ctx.message.author.mention}, you are missing a required argument.\nThe correct syntax for CREATING a note is\n `n!new [category] [note]`\n The correct syntax for DELETING a note is\n`n!delete [category] [note number]`')

    @retrieve_categories.error
    async def retrieve_categories_error(self, ctx, error):
        if isinstance(error, commands.TooManyArguments):
            await ctx.send(f'{globals.ERROR}\n{ctx.message.author.mention}, the command `n!categories` does not take any arguments.')

    @edit_note.error
    async def edit_note_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.TooManyArguments):
            await ctx.send(f'{globals.ERROR}\n{ctx.message.author.mention}, the correct syntax for editing an existing note is\n`n!edit [category] [note_id] [note]`')

def setup(client): 
    client.add_cog(Notes(client))
