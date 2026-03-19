import discord
from discord.ext import commands
import google.generativeai as genai
import os
from flask import Flask
import threading
import sys

# 1. Webserver für Render
app = Flask(__name__)
@app.route('/')
def home(): 
    return "Bot Herzschlag: Aktiv!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 2. KI Setup - Gemini 2.5 Flash (Stand 2026)
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

# 3. Discord Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Status-Variable für die Automatik
auto_translate = True

@bot.event
async def on_ready():
    print(f'--- BOT 2.5 FLASH ONLINE ---')
    print(f'Eingeloggt als: {bot.user.name}')
    sys.stdout.flush()

@bot.event
async def on_message(message):
    global auto_translate
    if message.author == bot.user:
        return

    # BEFEHLE FÜR STATUS
    if message.content.lower() == "!auto on":
        auto_translate = True
        await message.reply("✅ **Übersetzung AKTIVIERT.** Ich helfe euch wieder beim Chatten (DE <-> FR).")
        return

    if message.content.lower() == "!auto off":
        auto_translate = False
        await message.reply("😴 **Übersetzung DEAKTIVIERT.** Ich antworte jetzt nur noch auf `!gemini`.")
        return

    # 4. DIREKTE KI-ANFRAGE
    if message.content.lower().startswith("!gemini"):
        query = message.content[7:].strip()
        if not query:
            await message.reply("Frag mich etwas!")
            return

        async with message.channel.typing():
            try:
                response = model.generate_content(query)
                if response and response.text:
                    await message.reply(response.text)
            except Exception as e:
                await message.reply(f"KI Fehler: {e}")
        return

    # 5. AUTO-ÜBERSETZUNG (Zwei-Wege)
    # Nur aktiv, wenn auto_translate True ist und kein Befehl genutzt wurde
    if auto_translate and len(message.content) > 2 and not message.content.startswith("!"):
        try:
            prompt = (
                f"Übersetze Deutsch nach Französisch oder Französisch nach Deutsch. "
                f"Antworte NUR mit dem Wort 'SKIP', wenn der Text bereits verständlich ist, "
                f"eine Mischung beider Sprachen ist oder keine Übersetzung braucht. "
                f"Text: {message.content}"
            )
            async with message.channel.typing():
                response = model.generate_content(prompt)
                if response.text and "SKIP" not in response.text.upper():
                    await message.reply(f"🔄 {response.text}")
        except:
            pass

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
