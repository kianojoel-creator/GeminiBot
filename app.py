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
    return "Groq Assistant Online"

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
    # Setzt den Status in Discord
    activity = discord.Game(name="Llama-3.3 AI", type=3)
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print(f'--- {bot.user.name} IST ONLINE ---')
    sys.stdout.flush()

@bot.event
async def on_message(message):
    global auto_translate
    if message.author == bot.user:
        return

    # HILFE / INFO
    if message.content.lower() in ["!info", "!help"]:
        help_text = (
            "**🚀 Groq Assistant ist bereit!**\n"
            "Modell: `Llama-3.3-70B` (High Speed)\n\n"
            "**Befehle:**\n"
            "`!ai [Frage]` - Frag mich alles\n"
            "`!prompt [Thema]` - Erstellt Flux-Prompts für dich\n"
            "`!auto on/off` - Automatische Übersetzung DE<->FR\n"
            "`!status` - Zeigt meinen aktuellen Zustand"
        )
        await message.reply(help_text)
        return

    # STATUS & STEUERUNG
    if message.content.lower() == "!status":
        state = "AKTIV ✅" if auto_translate else "PAUSIERT 😴"
        await message.reply(f"Bot läuft flüssig. Übersetzung ist: {state}")
        return

    if message.content.lower() == "!auto on":
        auto_translate = True
        await message.reply("✅ Übersetzung aktiviert!")
        return
        
    if message.content.lower() == "!auto off":
        auto_translate = False
        await message.reply("😴 Übersetzung deaktiviert.")
        return

    # FLUX PROMPT GENERATOR
    if message.content.lower().startswith("!prompt "):
        topic = message.content[8:].strip()
        async with message.channel.typing():
            try:
                p_prompt = (
                    f"Erstelle einen hochdetaillierten Bild-Prompt für die KI 'Flux.1'. "
                    f"Thema: {topic}. Nutze Fachbegriffe wie 'photorealistic, 8k, highly detailed, "
                    f"cinematic lighting'. Antworte NUR mit dem englischen Prompt."
                )
                completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": p_prompt}],
                    model=MODEL_NAME,
                    temperature=0.7
                )
                await message.reply(f"🎨 **Flux-Prompt:**\n```{completion.choices[0].message.content}```")
            except Exception as e:
                await message.reply("❌ Fehler beim Prompt-Design.")
        return

    # ALLGEMEINE KI ANFRAGE
    if message.content.lower().startswith("!ai "):
        query = message.content[4:].strip()
        async with message.channel.typing():
            try:
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "system", "content": "Antworte präzise und hilfreich auf Deutsch."},
                              {"role": "user", "content": query}],
                    model=MODEL_NAME,
                    temperature=0.6
                )
                await message.reply(chat_completion.choices[0].message.content)
            except Exception as e:
                print(f"Fehler: {e}")
                await message.reply("❌ Groq-API Error.")
        return

    # 4. AUTOMATISCHE ÜBERSETZUNG (Mit Flaggen)
    if auto_translate and len(message.content) > 3 and not message.content.startswith("!"):
        try:
            t_prompt = (
                f"Übersetze kurz: Wenn Text Französisch -> Deutsch. Wenn Text Deutsch -> Französisch. "
                f"Antworte NUR mit der Übersetzung und beginne IMMER mit der passenden Flagge (🇩🇪 oder 🇫🇷). "
                f"Antworte NUR mit 'SKIP', wenn keine Übersetzung nötig ist. "
                f"Text: {message.content}"
            )
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": t_prompt}],
                model=MODEL_NAME,
                temperature=0.1
            )
            result = completion.choices[0].message.content
            if result and "SKIP" not in result.upper():
                await message.reply(result)
        except:
            pass

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
