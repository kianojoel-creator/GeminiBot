import discord
from discord.ext import commands
import google.generativeai as genai
import os
from flask import Flask
import threading
import sys
import asyncio # Neu für die kleine Pause

# 1. Webserver für Render
app = Flask(__name__)
@app.route('/')
def home(): 
    return "Multi-Kulti-Bot LITE: Aktiv!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 2. KI Setup - Wechsel auf das LITE Modell für mehr Power/Limit
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
# Wir nutzen 2.0-flash-lite-preview-02-05 (Das 'Lite' mit dem höchsten Limit)
model = genai.GenerativeModel('gemini-2.0-flash-lite-preview-02-05')

# 3. Discord Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

auto_translate = True

@bot.event
async def on_ready():
    print(f'--- LITE TRANSLATOR ONLINE ---')
    print(f'Eingeloggt als: {bot.user.name}')
    sys.stdout.flush()

@bot.event
async def on_message(message):
    global auto_translate
    if message.author == bot.user:
        return

    # BEFEHLE
    if message.content.lower() in ["!info", "!help"]:
        await message.reply("**🚀 Lite-Bot Aktiv**\nHöheres Limit, schnellere Antworten.\n`!auto on/off` | `!gemini [Text]`")
        return

    if message.content.lower() == "!auto on":
        auto_translate = True
        await message.reply("✅ Aktiviert!")
        return
    if message.content.lower() == "!auto off":
        auto_translate = False
        await message.reply("😴 Deaktiviert.")
        return

    # KI-FRAGE (!gemini)
    if message.content.lower().startswith("!gemini"):
        query = message.content[7:].strip()
        async with message.channel.typing():
            try:
                response = model.generate_content(query)
                await message.reply(response.text)
            except Exception as e:
                if "429" in str(e):
                    await message.reply("⏳ **Limit kurz erreicht.** Ich mache 10 Sek. Pause.")
                    await asyncio.sleep(10)
                else:
                    print(f"Fehler: {e}")
        return

    # 4. ÜBERSETZUNG (Lite-Version)
    if auto_translate and len(message.content) > 3 and not message.content.startswith("!"):
        try:
            context_msg = ""
            if message.reference:
                try:
                    referenced_msg = await message.channel.fetch_message(message.reference.message_id)
                    context_msg = f" (Antwort auf: '{referenced_msg.content}')"
                except: pass

            prompt = (
                f"Übersetze kurz:\n1. DE -> FR\n2. FR -> DE\n3. Andere -> DE & FR\n"
                f"Antworte NUR mit 'SKIP', wenn keine Übersetzung nötig ist.\n\n"
                f"Kontext: {context_msg}\nText: {message.content}"
            )
            
            # Kein typing() bei Auto-Übersetzung spart Zeit/Ressourcen
            response = model.generate_content(prompt)
            if response.text and "SKIP" not in response.text.upper():
                await message.reply(f"🌍 {response.text}")

        except Exception as e:
            if "429" in str(e):
                print("LITE-Limit erreicht - Schweige kurz.")
                await asyncio.sleep(5) # Kurze interne Pause
            else:
                print(f"Fehler: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
