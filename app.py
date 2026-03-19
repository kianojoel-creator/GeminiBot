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

@bot.event
async def on_ready():
    activity = discord.Game(name="VHA Universal Translator", type=3)
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print(f'--- {bot.user.name} (VHA) ONLINE ---')
    sys.stdout.flush()

@bot.event
async def on_message(message):
    global auto_translate
    if message.author == bot.user:
        return

    # BEFEHLE (DREISPRACHIG)
    if message.content.lower() in ["!info", "!help"]:
        help_text = (
            "**🌍 VHA Universal Assistant**\n\n"
            "🇩🇪 **DE:** Automatische Übersetzung für alle Sprachen.\n"
            "🇫🇷 **FR:** Traduction automatique pour toutes les langues.\n"
            "🇺🇸 **EN:** Automatic translation for all languages.\n\n"
            "`!ai [Text]` - AI Chat | `!auto on/off` - Toggle | `!status`"
        )
        await message.reply(help_text)
        return

    if message.content.lower() == "!status":
        s = "AKTIV ✅ / ACTIF ✅ / ACTIVE ✅" if auto_translate else "OFF 😴"
        await message.reply(f"🛰️ **System Status:** {s}")
        return

    if message.content.lower() == "!auto on":
        auto_translate = True
        await message.reply("✅ **Translator ON** (DE/FR/Global)")
        return
        
    if message.content.lower() == "!auto off":
        auto_translate = False
        await message.reply("😴 **Translator OFF**")
        return

    # KI ANFRAGE
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

    # 4. UNIVERSAL-ÜBERSETZUNG MIT REPLY-LOGIK
    if auto_translate and len(message.content) > 2 and not message.content.startswith("!"):
        try:
            # Check ob es eine Antwort auf eine andere Nachricht ist
            context_text = ""
            if message.reference and message.reference.message_id:
                ref_msg = await message.channel.fetch_message(message.reference.message_id)
                context_text = f" (Context of replied message: {ref_msg.content})"

            t_prompt = (
                f"You are a universal translator for the VHA Discord server. "
                f"Input Text: '{message.content}'{context_text}. "
                f"Rules: "
                f"1. If Input is German -> Translate to French (start with 🇫🇷). "
                f"2. If Input is French -> Translate to German (start with 🇩🇪). "
                f"3. If Input is ANY OTHER language (English, Spanish, etc.) -> Translate to BOTH German (🇩🇪) and French (🇫🇷). "
                f"4. If it's a reply, use the context to ensure the translation makes sense. "
                f"5. Answer ONLY with the translation(s). If it's just emojis or noise, answer 'SKIP'."
            )
            
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": t_prompt}],
                model=MODEL_NAME,
                temperature=0.1
            )
            result = completion.choices[0].message.content
            if result and "SKIP" not in result.upper():
                await message.reply(result)
        except Exception as e:
            print(f"Translation Error: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
