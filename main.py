import discord
from discord.ext import commands
from discord.ui import Select, View
import sqlite3, os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Bot setup
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Database setup
conn = sqlite3.connect("stats.db")
cursor = conn.cursor()

# Create tables
cursor.execute(
    """CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        attack INTEGER DEFAULT 0,
        speed INTEGER DEFAULT 0,
        defense INTEGER DEFAULT 0,
        has_action INTEGER DEFAULT 1
    )"""
)
conn.commit()

# Helper functions
def get_user_stats(user_id):
    cursor.execute("SELECT attack, speed, defense, has_action FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

def reset_user_actions():
    cursor.execute("UPDATE users SET has_action = 1")
    conn.commit()

# Custom Help Command
@bot.command(name="game-help")
async def game_help(ctx):
    embed = discord.Embed(
        title="Game Stats Bot Commands",
        description="Here are the available commands for interacting with the Game Stats Bot:",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="!train",
        value="Train your character's stats (Attack, Speed, or Defense).",
        inline=False
    )
    embed.add_field(
        name="!stats",
        value="View your current stats.",
        inline=False
    )
    embed.add_field(
        name="!reset-round",
        value="Admin-only command to reset the round and allow users to take actions again.",
        inline=False
    )
    embed.add_field(
        name="!set-stat `<member>` `<stat>` `<value>`",
        value="Admin-only command to set a specific stat (Attack, Speed, Defense) for a user.",
        inline=False
    )
    
    embed.add_field(
        name="**Stats:**",
        value="`str` - Strength (Attack)\n`sp` - Speed\n`def` - Defense",
        inline=False
    )
    
    embed.add_field(
        name="**Permissions:**",
        value="Admins can use `!reset-round` and `!set-stat`.",
        inline=False
    )

    await ctx.send(embed=embed)


# Commands
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command(name="train")
async def train(ctx):
    user_id = ctx.author.id
    cursor.execute("SELECT has_action FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        user = (1,)

    if user[0] == 0:
        await ctx.send("You have already used your action this round!")
        return

    # Create a dropdown menu for stat training
    select = Select(
        placeholder="Choose which stat to train...",
        options=[
            discord.SelectOption(label="Strength (STR)", value="str"),
            discord.SelectOption(label="Speed (SP)", value="sp"),
            discord.SelectOption(label="Defense (DEF)", value="def")
        ]
    )

    # Add the callback function for when the user selects an option
    async def select_callback(interaction):
        stat = select.values[0]
        if stat == "str":
            stat_column = "attack"
        elif stat == "sp":
            stat_column = "speed"
        else:
            stat_column = "defense"
        
        cursor.execute(f"UPDATE users SET {stat_column} = {stat_column} + 1, has_action = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        await interaction.response.send_message(f"You have trained your {stat_column.capitalize()}! It has increased by 1.", ephemeral=True)

    # Set the callback for the dropdown menu
    select.callback = select_callback

    # Create a view to display the dropdown menu
    view = View()
    view.add_item(select)

    # Send the message with the dropdown menu
    await ctx.send("Choose a stat to train:", view=view)

@bot.command(name="stats")
async def stats(ctx):
    user_id = ctx.author.id
    stats = get_user_stats(user_id)

    if not stats:
        await ctx.send("You have no stats yet! Use `!train` to get started.")
        return

    attack, speed, defense, has_action = stats
    embed = discord.Embed(title=f"{ctx.author.display_name}'s Stats", color=discord.Color.blue())
    embed.add_field(name="Attack", value=attack, inline=True)
    embed.add_field(name="Speed", value=speed, inline=True)
    embed.add_field(name="Defense", value=defense, inline=True)
    embed.add_field(name="Action Available", value="Yes" if has_action else "No", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="reset-round")
@commands.has_permissions(administrator=True)
async def reset_round(ctx):
    reset_user_actions()
    await ctx.send("The round has been reset. All users can now take one action!")

@bot.command(name="set-stat")
@commands.has_permissions(administrator=True)
async def set_stat(ctx, member: discord.Member, stat: str, value: int):
    valid_stats = {"str": "attack", "sp": "speed", "def": "defense"}
    if stat.lower() not in valid_stats:
        await ctx.send("Invalid stat! Use `str`, `sp`, or `def`.")
        return

    stat_column = valid_stats[stat.lower()]
    cursor.execute(f"UPDATE users SET {stat_column} = ? WHERE user_id = ?", (value, member.id))
    conn.commit()
    await ctx.send(f"{member.display_name}'s {stat_column.capitalize()} has been set to {value}.")

# Run the bot
bot.run(BOT_TOKEN)
