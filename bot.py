import os

import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
client = discord.Client(intents=intents)

server_active = {}
users_active = {}
EMOJI_LIST = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

def check_roles(user_roles: list) -> bool:
    for role in user_roles:
        if role.name == 'Movie Watcher':
            return True
    return False

def filter_user_with_movie_watcher_role(user_list, mention_person):
    users = []
    for user in user_list:
        if user == mention_person:
            continue
        for role in user.roles:
            if role.name == 'Movie Watcher':
                users.append(user)
    return users

async def pm_all_user(user_list):
    for user in user_list:
        movie_score = await user.send("How's the movie? Gimme score from 1 to 10")
        for EMOJI in EMOJI_LIST:
            await movie_score.add_reaction(EMOJI)

def add_members_to_active_state(user_list, guild_id, users_active):
    for user in user_list:
        if users_active.get(user.id, None) is not None:
            users_active[user.id]['server_active_count'] += 1
            users_active[user.id]['server_active_list'].append(guild_id)
        else:
            users_active[user.id] = {
                'server_active_count': 1,
                'server_active_list': [guild_id]
            }

def delete_active_state(guild_id):
    users = server_active[guild_id]['user_list']
    for user in users:
        try:
            del users_active[user.id]
        except KeyError:
            pass
    del server_active[guild_id]

def get_user_with_movie_king_role(user_list):
    for user in user_list:
        for role in user.roles:
            if role.name == 'Movie King / Queen':
                return user
    return None

def get_intro_text(mention_user, movie_king_user):
    if mention_user == movie_king_user:
        return "Bisakah <@%s> mempertahankan Tahta Movie King / Queen?" % mention_user.id
    elif movie_king_user == None:
        return "Bisakah <@%s> mendapatkan tahta Movie King / Queen?" % mention_user.id
    else:
        return "Bisakah <@%s> mencuri tahta Movie King / Queen dari <@%s>?" % (mention_user.id, movie_king_user.id)

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
    content = message.content
    
    if content.startswith('!friday vote'):
        mentions = message.mentions

        if len(mentions) == 0:
            await message.channel.send("You didn't mention anyone yet!, Please mention someone")
            return
        elif len(mentions) > 1:
            await message.channel.send("Please mention 1 person only!")
            return
        guild_id = message.guild.id
        if server_active.get(guild_id, None) is not None:
            await message.channel.send("There's active voting on this server")
            return

        mention_person = mentions[0]
        user_roles = mention_person.roles
        
        if not check_roles(user_roles):
            await message.channel.send("This person doesn't have \"Movie Watcher\" role")
            return

        user_movie_watcher = filter_user_with_movie_watcher_role(message.guild.members, mention_person)
        
        
        channel_id = message.channel.id
        server_active[guild_id] = {
            'total_points': 0,
            'total_voters': 0,
            'channel_id': channel_id,
            'user_list': user_movie_watcher,
            'mention_person': mention_person
        }
        add_members_to_active_state(user_movie_watcher, guild_id, users_active)
        await message.channel.send("Attention Movie Watcher, please check your personal messages")
        await pm_all_user(user_movie_watcher)
    
    if content == '!friday close':
        guild_id = message.guild.id
        if server_active.get(guild_id, None) is None:
            await message.channel.send("There's no active voting")
            return
        await message.channel.send("Calculating point...")
        voting_stats = server_active[guild_id]
        try:
            final_point = voting_stats['total_points'] / voting_stats['total_voters']
        except ZeroDivisionError:
            await message.channel.send("Eh?")
            await message.channel.send("Nobody voted yet?")
            final_point = 0
        
        movie_king_user = get_user_with_movie_king_role(message.guild.members)
        mention_user = server_active[guild_id]['mention_person']
        await message.channel.send(get_intro_text(mention_user, movie_king_user))
        await message.channel.send("%s Points!!!" % final_point)
        role = discord.utils.get(message.guild.roles, name='Movie King / Queen')
        if final_point > 7.5:
            if movie_king_user != None and movie_king_user != mention_user:
                await movie_king_user.remove_roles(role)
            await mention_user.add_roles(role)

            await message.channel.send("Congratulation!")
        else:
            await message.channel.send("Better luck next time :(")
            if movie_king_user == mention_user:
                await movie_king_user.remove_roles(role)
        delete_active_state(guild_id)

def reaction_to_int(reaction) -> int:
    return EMOJI_LIST.index(str(reaction)) + 1

@client.event
async def on_reaction_add(reaction, user):
    if client.user != user:
        message = reaction.message
        if not isinstance(message.channel, discord.channel.DMChannel):
            return
        if users_active.get(user.id, None) is None:
            try:
                await user.send("Sorry, you already voted / the voting has ended")
            except Exception as e:
                print(e)
            return
        if str(reaction) not in EMOJI_LIST:
            try:
                await user.send("You put the wrong value! Please use the number value")
            except Exception as e:
                print(e)
            return

        server_active_list = users_active[user.id]['server_active_list']
        server_id = server_active_list[0]
        channel_id = server_active[server_id]['channel_id']
        channel = client.get_channel(channel_id)
        server_active[server_id]['total_voters'] += 1
        server_active[server_id]['total_points'] += reaction_to_int(reaction)
        
        server_voting_dict = server_active[server_id]
        server_active_list.pop(0)
        if len(server_active_list) == 0:
            users_active.pop(user.id)
        try:
            await user.send("Thank you for voting")
        except Exception as e:
            print(e)
        await channel.send("%s has voted" % (user.name))
client.run(TOKEN)