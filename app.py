import discord
from discord.ext import commands
import os
from flask import Flask
import threading
import sys
from groq import Groq

# 1. Webserver für Render (Uptime)
app = Flask(__name__)
@app.route('/')
def home(): 
    return "VHA Universal Assistant Online"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 2. Groq KI Setup
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL_NAME = "llama-3.3-70b-versatile"

# 3. Discord Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

auto_translate = True
last_processed_msg = None

@bot.event
async def on_ready():
    activity = discord.Game(name="VHA Guard | !info", type=3)
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print(f'--- {bot.user.name} ONLINE ---')
    sys.stdout.flush()

@bot.event
async def on_message(message):
    global auto_translate, last_processed_msg
    
    # Grund-Sperren (Ignoriere Bots & Doppelnachrichten)
    if message.author == bot.user:
        return
    
    current_msg_fingerprint = f"{message.author.id}_{message.content}"
    if last_processed_msg == current_msg_fingerprint:
        return
    last_processed_msg = current_msg_fingerprint

    # BEFEHLE (DREISPRACHIG)
    if message.content.lower() in ["!info", "!help"]:
        help_text = (
            "**🌍 VHA Universal Assistant**\n\n"
            "🇩🇪 **DE:** Automatische Übersetzung für alle Sprachen.\n"
            "🇫🇷 **FR:** Traduction automatique pour toutes les langues.\n"
            "🇺🇸 **EN:** Automatic translation for all languages.\n\n"
            "**Commands:** `!ai [Text]` | `!auto on/off` | `!status`"
        )
        await message.reply(help_text)
        return

    if message.content.lower() == "!status":
        s = "AKTIV ✅ / ACTIF ✅" if auto_translate else "OFF 😴"
        await message.reply(f"🛰️ **System Status:** {s}")
        return

    if message.content.lower() == "!auto on":
        auto_translate = True
        await message.reply("✅ **Universal Translator ON**")
        return
        
    if message.content.lower() == "!auto off":
        auto_translate = False
        await message.reply("😴 **Universal Translator OFF**")
        return

    # KI CHAT (!ai)
    if message.content.lower().startswith("!ai "):
        query = message.content[4:].strip()
        async with message.channel.typing():
            try:
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "system", "content": "You are the VHA Assistant. Answer in the user's language."},
                              {"role": "user", "content": query}],
                    model=MODEL_NAME,
                    temperature=0.6
                )
                await message.reply(chat_completion.choices[0].message.content)
            except:
                await message.reply("❌ Error.")
        return

    # 4. UNIVERSAL-ÜBERSETZUNG (NUR WENN KEIN BEFEHL & AKTIV)
    if auto_translate and len(message.content) > 3 and not message.content.startswith("!"):
        
        # FILTER: Ignoriere Lacher und kurze Reaktionen (Blacklist)
        low_msg = message.content.lower().strip()
        blacklist = ["haha", "lol", "xd", "hi", "hey", "ok", "danke", "merci", "thanks", "gut", "bien", "nice"]
        if any(word == low_msg for word in blacklist):
            return

        try:
            context_info = ""
            if message.reference and message.reference.message_id:
                try:
                    ref_msg = await message.channel.fetch_message(message.reference.message_id)
                    context_info = f"\n(Context: Reply to: '{ref_msg.content}')"
                except:
                    pass

            # *** NEUER SYSTEM-PROMPT MIT FRECHEN ANTWORTEN ***
            t_prompt = (
                f"Task: Smart Translation for VHA.\n"
                f"Input: '{message.content}'{context_info}\n\n"
                f"Rules:\n"
                f"1. Check if Input is a silly/impossible request (e.g., make coffee, play music like Alexa, do homework).\n"
                f"2. IF silly: Answer precisely but with a small, witty, and charming joke in all three languages (DE, FR, EN) with flags. Do NOT provide a translation of the actual request. Use emojis. 🤖\n"
                f"3. IF NOT silly: Translate normally. German -> French (🇩🇪->🇫🇷), French -> German (🇫🇷->🇩🇪), Others -> Both (🇩🇪+🇫🇷).\n"
                f"4. ONLY output translation or witty answer with flags. No spam."
            )
            
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": t_prompt}],
                model=MODEL_NAME,
                temperature=0.2 # Etwas höher für mehr "Kreativität"
            )
            result = completion.choices[0].message.content
            if result and "SKIP" not in result.upper() and len(result) > 2:
                await message.reply(result)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
