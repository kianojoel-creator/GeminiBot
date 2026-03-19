import discord
from discord.ext import commands
import os
from flask import Flask
import threading
from groq import Groq
import re

# 1. Webserver für Render
app = Flask(__name__)
@app.route('/')
def home(): return "VHA Translator - Reply Logic 2026"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# 2. KI Setup
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL_NAME = "llama-3.3-70b-versatile"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

processed_messages = set()

def detect_language_manually(text):
    """Prüft auf typische Wörter für DE/FR"""
    t = text.lower()
    if any(re.search(rf'\b{w}\b', t) for w in ["c'est", "oui", "je", "suis", "pas", "le", "la", "et", "que", "pour"]):
        return "FR"
    if any(re.search(rf'\b{w}\b', t) for w in ["ist", "ja", "ich", "bin", "nicht", "das", "die", "und", "dass", "für"]):
        return "DE"
    return "UNKNOWN"

@bot.event
async def on_ready():
    print(f'--- {bot.user.name} MIT REPLY-LOGIK ONLINE ---')

@bot.event
async def on_message(message):
    global processed_messages
    if message.author == bot.user or message.id in processed_messages:
        return
    processed_messages.add(message.id)
    if len(processed_messages) > 150: processed_messages.clear()

    # !ai Befehl
    if message.content.lower().startswith("!ai "):
        query = message.content[4:].strip()
        async with message.channel.typing():
            try:
                res = client.chat.completions.create(
                    messages=[{"role": "system", "content": "Antworte kurz und witzig."},
                              {"role": "user", "content": query}],
                    model=MODEL_NAME, temperature=0.7
                )
                await message.reply(res.choices[0].message.content)
            except: pass
        return

    # ÜBERSETZUNG MIT REPLY-CHECK
    text = message.content.strip()
    if not text.startswith("!") and len(text) > 2:
        if text.lower() in ["haha", "lol", "ok", "merci", "danke"]: return

        # Prüfe, ob es eine Antwort auf eine andere Sprache ist
        extra_info = ""
        if message.reference and message.reference.message_id:
            try:
                replied_to = await message.channel.fetch_message(message.reference.message_id)
                orig_lang = detect_language_manually(replied_to.content)
                if orig_lang == "UNKNOWN":
                    extra_info = f"Zusätzlich: Übersetze auch zurück in die Sprache der Nachricht, auf die geantwortet wurde: '{replied_to.content[:50]}...'"
            except: pass

        input_lang = detect_language_manually(text)
        
        # System-Anweisung zusammenbauen
        if extra_info:
            sys_msg = f"Du bist ein All-in-One Übersetzer. {extra_info}. Gib IMMER auch DE (🇩🇪) und FR (🇫🇷) aus. Gib NUR die Übersetzungen mit Flaggen aus."
        elif input_lang == "FR":
            sys_msg = "Übersetze NUR in Deutsch (🇩🇪). Gib nur Text + Flagge aus."
        elif input_lang == "DE":
            sys_msg = "Übersetze NUR in Französisch (🇫🇷). Gib nur Text + Flagge aus."
        else:
            sys_msg = "Übersetze in Deutsch (🇩🇪) UND Französisch (🇫🇷). Gib nur die Übersetzungen aus."

        try:
            completion = client.chat.completions.create(
                messages=[{"role": "system", "content": sys_msg},
                          {"role": "user", "content": text}],
                model=MODEL_NAME, temperature=0.0
            )
            result = completion.choices[0].message.content.strip()
            
            # Filter gegen Nachplappern
            if text.lower() in result.lower() and len(result) > len(text) + 5:
                result = result.replace(text, "").replace(text.lower(), "").strip()
            
            if result:
                await message.reply(result)
        except: pass

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(os.getenv("DISCORD_TOKEN"))
