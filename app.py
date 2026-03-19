import discord
from discord.ext import commands
import os
from flask import Flask
import threading
from groq import Groq

# 1. Webserver für Render
app = Flask(__name__)
@app.route('/')
def home(): return "VHA Universal Translator - Clean Reset"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# 2. KI Setup
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL_NAME = "llama-3.3-70b-versatile"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Speicher gegen Doppel-Antworten
processed_messages = set()

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="Übersetzer aktiv 🌍"))
    print(f'--- {bot.user.name} RESET ERFOLGREICH ---')

@bot.event
async def on_message(message):
    global processed_messages
    
    # 1. Sicherheits-Checks
    if message.author == bot.user or message.id in processed_messages:
        return
    
    # ID speichern gegen Echo-Effekt
    processed_messages.add(message.id)
    if len(processed_messages) > 100: processed_messages.clear()

    # 2. KI-BEFEHL (!ai) -> Hier darf er (bei Bedarf) witzig sein
    if message.content.lower().startswith("!ai "):
        query = message.content[4:].strip()
        async with message.channel.typing():
            try:
                chat_res = client.chat.completions.create(
                    messages=[{
                        "role": "system", 
                        "content": (
                            "Du bist der VHA Assistent. "
                            "Regel 1: Wenn die Frage ernst ist, antworte hilfreich in der Sprache des Users. "
                            "Regel 2: Wenn die Frage offensichtlich Quatsch ist (Kaffee kochen, Alexa-Sprüche), "
                            "antworte kurz und witzig in DE, FR und EN mit Flaggen."
                        )},
                        {"role": "user", "content": query}
                    ],
                    model=MODEL_NAME, temperature=0.7
                )
                await message.reply(chat_res.choices[0].message.content)
            except: pass
        return

    # 3. AUTOMATISCHE ÜBERSETZUNG -> Streng, Sauber, Seriös
    if not message.content.startswith("!") and len(message.content) > 3:
        # Filter für Spam
        low_msg = message.content.lower().strip()
        if low_msg in ["haha", "lol", "xd", "ok", "merci", "danke"]:
            return

        try:
            t_prompt = (
                "Du bist ein 1:1 Übersetzer. Gib NUR die Übersetzung aus.\n"
                "Format: [Flagge] [Text]\n"
                "Regeln:\n"
                "- Deutsch -> Französisch (🇫🇷)\n"
                "- Französisch -> Deutsch (🇩🇪)\n"
                "- Andere -> Beides (🇩🇪 & 🇫🇷)\n"
                "- KEINE Kommentare, KEINE Einleitung (wie 'DE:'), KEIN Labern.\n"
                f"Text zum Übersetzen: {message.content}"
            )
            
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": t_prompt}],
                model=MODEL_NAME, 
                temperature=0.0 # Maximale Sachlichkeit
            )
            result = completion.choices[0].message.content
            
            if result and "SKIP" not in result.upper():
                await message.reply(result)
        except: pass

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(os.getenv("DISCORD_TOKEN"))
