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
def home(): return "VHA Translator - Full Master Version"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# 2. KI Setup
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL_NAME = "llama-3.3-70b-versatile"

# Bot Setup mit deaktivierter Standard-Hilfe für die eigene Hilfe
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# STATUS & SPEICHER
translate_active = True
processed_messages = set()

def detect_language_manually(text):
    t = text.lower()
    if any(re.search(rf'\b{w}\b', t) for w in ["c'est", "oui", "je", "suis", "pas", "le", "la", "et", "que", "pour", "est"]):
        return "FR"
    if any(re.search(rf'\b{w}\b', t) for w in ["ist", "ja", "ich", "bin", "nicht", "das", "die", "und", "dass", "für", "mit", "auch"]):
        return "DE"
    return "UNKNOWN"

@bot.event
async def on_ready():
    print(f'--- {bot.user.name} VOLLSTÄNDIG BEREIT ---')

# --- DIE BEFEHLE (Waren weg, jetzt wieder da!) ---

@bot.command(name="help")
async def custom_help(ctx):
    embed = discord.Embed(title="🤖 VHA Translator Hilfe", color=discord.Color.blue())
    embed.add_field(name="!translate on", value="Aktiviert die automatische Übersetzung.", inline=True)
    embed.add_field(name="!translate off", value="Deaktiviert die Automatik (Schlafmodus).", inline=True)
    embed.add_field(name="!ai [Frage]", value="Direkte Frage an die KI stellen.", inline=False)
    embed.add_field(name="Features", value="Übersetzt DE/FR automatisch. Erkennt Japanisch & Co. Antworte auf eine Nachricht (Reply), um in deren Sprache zu übersetzen.", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="translate")
async def toggle_translate(ctx, status: str):
    global translate_active
    if status.lower() == "on":
        translate_active = True
        await ctx.send("✅ **Übersetzung aktiviert.**")
    elif status.lower() == "off":
        translate_active = False
        await ctx.send("😴 **Übersetzung deaktiviert.**")

# --- DIE LOGIK ---

@bot.event
async def on_message(message):
    global processed_messages, translate_active
    if message.author == bot.user or message.id in processed_messages:
        return

    # WICHTIG: Erst prüfen, ob es ein Befehl (!help, !translate) ist
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    # Wenn Automatik aus ist oder Text zu kurz, nichts tun
    text = message.content.strip()
    if not translate_active or len(text) <= 2:
        return

    # Ignoriere Standard-Smalltalk automatisch
    if text.lower() in ["haha", "lol", "ok", "merci", "danke", "top", "nice", "ja", "oui", "nein"]:
        return

    processed_messages.add(message.id)
    if len(processed_messages) > 150: processed_messages.clear()

    # Reply-Check (für Japaner & Co)
    is_reply = False
    replied_text = ""
    if message.reference and message.reference.message_id:
        try:
            replied_to = await message.channel.fetch_message(message.reference.message_id)
            replied_text = replied_to.content
            is_reply = True
        except: pass

    input_lang = detect_language_manually(text)
    
    # SYSTEM PROMPT (Der Maulkorb)
    if is_reply:
        sys_msg = (f"Übersetze in DE (🇩🇪), FR (🇫🇷) und die Sprache von '{replied_text}'. "
                   "Regel: NUR Übersetzungen. KEINE Erklärungen. KEINE Analysen.")
    elif input_lang == "FR":
        sys_msg = "Übersetze NUR ins Deutsche (🇩🇪). Keine Kommentare."
    elif input_lang == "DE":
        sys_msg = "Übersetze NUR ins Französische (🇫🇷). Kein Kommentar."
    else:
        sys_msg = "Übersetze in DE (🇩🇪) und FR (🇫🇷). NUR Ergebnisse."

    try:
        completion = client.chat.completions.create(
            messages=[{"role": "system", "content": "Du bist ein stummer Übersetzer. Gib nur Zieltexte aus."},
                      {"role": "user", "content": f"{sys_msg}\n\nText: {text}"}],
            model=MODEL_NAME, temperature=0.0
        )
        result = completion.choices[0].message.content.strip()
        
        # Profi-Filter gegen Professor-Sprüche
        lines = result.split('\n')
        final_lines = []
        for line in lines:
            l_low = line.lower()
            if any(x in l_low for x in ["sprache ist", "identisch", "bleibt gleich", "original"]):
                continue
            # Echo-Schutz: Nicht die eigene Sprache wiederholen
            clean = line.replace("🇩🇪", "").replace("🇫🇷", "").strip().lower()
            if clean != text.lower() and len(clean) > 0:
                final_lines.append(line)
        
        output = "\n".join(final_lines).strip()
        if output:
            await message.reply(output)
    except: pass

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(os.getenv("DISCORD_TOKEN"))
