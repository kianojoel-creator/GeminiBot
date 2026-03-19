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
    return "Multi-Kulti-Bot: Aktiv!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 2. KI Setup - Gemini 2.5 Flash
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

# 3. Discord Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

auto_translate = True

@bot.event
async def on_ready():
    print(f'--- UNIVERSAL TRANSLATOR ONLINE ---')
    print(f'Eingeloggt als: {bot.user.name}')
    sys.stdout.flush()

@bot.event
async def on_message(message):
    global auto_translate
    if message.author == bot.user:
        return

    # BEFEHL: INFO / HELP (Erweitert um die Antwort-Funktion)
    if message.content.lower() in ["!info", "!help"]:
        info_text = (
            "**🌍 Universal Translator & AI Assistant**\n"
            "__________________________________________\n\n"
            "**DE:** Ich übersetze automatisch zwischen allen Sprachen!\n"
            "💡 **Tipp:** Nutze die **'Antworten'-Funktion** von Discord, wenn du jemandem in seiner Sprache antworten willst. Ich erkenne dann automatisch die Zielsprache!\n\n"
            "**FR:** Je traduis automatiquement entre toutes les langues !\n"
            "💡 **Astuce:** Utilisez la fonction **'Répondre'** de Discord pour répondre à quelqu'un dans sa langue. Je reconnaîtrai automatiquement la langue cible !\n\n"
            "**EN:** I translate automatically between all languages!\n"
            "💡 **Tip:** Use the Discord **'Reply' function** to answer someone in their language. I will automatically recognize the target language!\n\n"
            "**Commands:**\n"
            "• `!auto on/off` -> Automatik steuern / Contrôle auto.\n"
            "• `!gemini [Text]` -> Frag die KI / Demander à l'IA."
        )
        await message.reply(info_text)
        return

    # STATUS-BEFEHLE
    if message.content.lower() == "!auto on":
        auto_translate = True
        await message.reply("✅ **Aktiviert!** Ich übersetze jetzt wieder alle Sprachen.")
        return
    if message.content.lower() == "!auto off":
        auto_translate = False
        await message.reply("😴 **Deaktiviert.** Nur noch Befehle funktionieren.")
        return

    # DIREKTE KI-ANFRAGE
    if message.content.lower().startswith("!gemini"):
        query = message.content[7:].strip()
        async with message.channel.typing():
            try:
                response = model.generate_content(query)
                await message.reply(response.text)
            except Exception as e:
                await message.reply(f"Fehler: {e}")
        return

    # 4. SMART MULTI-KULTI ÜBERSETZUNG MIT ANTWORT-ERKENNUNG
    if auto_translate and len(message.content) > 2 and not message.content.startswith("!"):
        try:
            # PRÜFUNG: Kontext aus der Antwort-Funktion holen
            context_msg = ""
            if message.reference:
                # Wir versuchen die Nachricht abzurufen, auf die geantwortet wurde
                try:
                    referenced_msg = await message.channel.fetch_message(message.reference.message_id)
                    context_msg = f" (Der User antwortet auf diese Nachricht: '{referenced_msg.content}')"
                except:
                    context_msg = " (Antwort auf eine unbekannte Nachricht)"

            prompt = (
                f"Du bist ein diskreter Dolmetscher. Deine Regeln:\n"
                f"1. Text DE -> übersetze NUR ins FRANZÖSISCHE.\n"
                f"2. Text FR -> übersetze NUR ins DEUTSCHE.\n"
                f"3. Text ANDERE SPRACHE -> übersetze in DEUTSCHE & FRANZÖSISCHE.\n"
                f"4. Wenn die Nachricht eine ANTWORT auf eine andere Sprache ist (siehe Kontext), übersetze sie ZUSÄTZLICH in diese Sprache zurück.\n"
                f"ANTWORTE NUR MIT 'SKIP', wenn keine Übersetzung nötig ist.\n\n"
                f"Kontext: {context_msg}\n"
                f"Aktueller Text: {message.content}"
            )
            
            async with message.channel.typing():
                response = model.generate_content(prompt)
                if response.text and "SKIP" not in response.text.upper():
                    await message.reply(f"🌍 {response.text}")
        except Exception:
            pass

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
