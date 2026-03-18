import discord
from discord.ext import commands
import google.generativeai as genai
import os
from flask import Flask
import threading

# Webserver für Render
app = Flask(__name__)
@app.route('/')
def home(): return "Bot läuft!"

def run_flask():
    # Render braucht den Port aus der Umgebungsvariable
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# KI Setup
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-pro')

# Discord Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Eingeloggt als {bot.user.name}')

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    
    # Prefix Befehl
    if message.content.lower().startswith("!gemini"):
        query = message.content[7:].strip()
        if query:
            async with message.channel.typing():
                response = model.generate_content(query)
                await message.reply(response.text)
        return

    # Automatische Übersetzung
    async with message.channel.typing():
        try:
            prompt = f"Übersetze DE<->FR, sonst antworte NUR mit 'SKIP': {message.content}"
            response = model.generate_content(prompt)
            if "SKIP" not in response.text.upper():
                await message.reply(f"🌍 {response.text}")
        except: pass

# Start
threading.Thread(target=run_flask, daemon=True).start()
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
