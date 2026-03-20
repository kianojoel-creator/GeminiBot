import discord
from discord.ext import commands
import os
import re
import threading
from collections import deque
from flask import Flask
from groq import Groq

# ────────────────────────────────────────────────
# KONFIGURATION
# ────────────────────────────────────────────────

LOGO_URL = (
    "https://cdn.discordapp.com/attachments/1484252260614537247/"
    "1484253018533662740/Picsart_26-03-18_13-55-24-994.png"
    "?ex=69bd8dd7&is=69bc3c57&hm=de6fea399dd30f97d2a14e1515c9e7f91d81d0d9ea111f13e0757d42eb12a0e5&"
)

GROQ_MODEL = "llama-3.3-70b-versatile"

# ────────────────────────────────────────────────
# GLOBALS & FLASK
# ────────────────────────────────────────────────

app = Flask(__name__)

# FIX 3: Gleitendes Fenster statt hartem clear()
# Speichert max. 500 Message-IDs, älteste fliegt automatisch raus
processed_messages = deque(maxlen=500)
processed_messages_set = set()

translate_active = True

# Groq-Client einmal global erstellen
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# FIX 2: Einfacher User-Cooldown für die Übersetzung (Timestamp pro User)
import time
user_last_translation: dict[int, float] = {}
TRANSLATION_COOLDOWN = 3.0  # Sekunden zwischen zwei Übersetzungen pro User


def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


@app.route("/")
def home():
    return "VHA Translator • Online"


# ────────────────────────────────────────────────
# SPRACHE ERKENNEN via Groq LLM
# ────────────────────────────────────────────────

async def detect_language_llm(text: str) -> str:
    """
    Gibt 'DE', 'FR' oder 'OTHER' zurück.
    OTHER = neutral (ok, gg, lol, Emojis ...) → wird nicht übersetzt.
    """
    try:
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=0.0,
            max_tokens=5,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You detect the language of a text. "
                        "Reply with exactly one word: DE, FR, or OTHER. "
                        "DE = German, FR = French. "
                        "If the text is neutral/universal (e.g. 'ok', 'lol', 'gg', 'nice', "
                        "emojis only, numbers only) reply OTHER. "
                        "No explanation, no punctuation. Just the single word."
                    )
                },
                {"role": "user", "content": text}
            ]
        )
        result = resp.choices[0].message.content.strip().upper()
        if result in ("DE", "FR", "OTHER"):
            return result
        if "DE" in result:
            return "DE"
        if "FR" in result:
            return "FR"
        return "OTHER"
    except Exception as e:
        print(f"Spracherkennungs-Fehler: {e}")
        return "OTHER"


# ────────────────────────────────────────────────
# BOT SETUP
# ────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,
    case_insensitive=True
)


@bot.event
async def on_ready():
    print(f"→ {bot.user}  •  ONLINE  •  {discord.utils.utcnow():%Y-%m-%d %H:%M UTC}")


# ────────────────────────────────────────────────
# BEFEHLE
# ────────────────────────────────────────────────

@bot.command(name="help")
async def cmd_help(ctx):
    embed = discord.Embed(
        title="VHA Translator – Hilfe",
        color=discord.Color.blue()
    )
    embed.set_author(name="VHA ALLIANCE", icon_url=LOGO_URL)
    embed.add_field(
        name="🇩🇪 Deutsch",
        value=(
            "`!translate on` – Automatik einschalten\n"
            "`!translate off` – Automatik ausschalten\n"
            "`!translate status` – Status anzeigen\n"
            "`!ai [Frage]` – KI direkt fragen"
        ),
        inline=False
    )
    embed.add_field(
        name="🇫🇷 Français",
        value=(
            "`!translate on` – Activer la traduction\n"
            "`!translate off` – Désactiver la traduction\n"
            "`!translate status` – Voir le statut\n"
            "`!ai [Question]` – Poser une question à l'IA"
        ),
        inline=False
    )
    embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text="VHA - Powering Communication", icon_url=LOGO_URL)
    await ctx.send(embed=embed)


# FIX 1: !translate on/off/status Befehl implementiert
@bot.command(name="translate")
@commands.has_permissions(manage_messages=True)
async def cmd_translate(ctx, action: str = None):
    global translate_active

    if action is None:
        await ctx.send(
            "❓ Benutzung: `!translate on` / `!translate off` / `!translate status`\n"
            "Usage: `!translate on` / `!translate off` / `!translate status`"
        )
        return

    action = action.lower()

    if action == "on":
        translate_active = True
        embed = discord.Embed(
            title="VHA System • Übersetzung",
            color=0x57F287
        )
        embed.add_field(name="Deutsch ↔ Français", value="Aktiviert / Activée", inline=False)
        await ctx.send(embed=embed)

    elif action == "off":
        translate_active = False
        embed = discord.Embed(
            title="VHA System • Übersetzung",
            color=0xED4245
        )
        embed.add_field(name="Deutsch ↔ Français", value="Deaktiviert / Désactivée", inline=False)
        await ctx.send(embed=embed)

    elif action == "status":
        if translate_active:
            embed = discord.Embed(title="VHA System • Übersetzung", color=0x57F287)
            embed.add_field(name="Deutsch ↔ Français", value="Aktiviert / Activée", inline=False)
        else:
            embed = discord.Embed(title="VHA System • Übersetzung", color=0xED4245)
            embed.add_field(name="Deutsch ↔ Français", value="Deaktiviert / Désactivée", inline=False)
        await ctx.send(embed=embed)

    else:
        await ctx.send(
            "❓ Unbekannte Option. Benutze: `!translate on` / `!translate off` / `!translate status`\n"
            "Option inconnue. Utilise: `!translate on` / `!translate off` / `!translate status`"
        )


@cmd_translate.error
async def translate_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "❌ Du hast keine Berechtigung dafür. / Tu n'as pas la permission."
        )


@bot.command(name="ai")
@commands.cooldown(1, 12, commands.BucketType.user)
async def cmd_ai(ctx, *, question: str = None):
    if not question or not question.strip():
        await ctx.send(
            "Beispiel: `!ai Qui est la VHA ?`  oder  `!ai Was ist die VHA?`"
        )
        return

    thinking = await ctx.send("**Denke nach …** 🧠")

    lang = await detect_language_llm(question)
    lang_map = {
        "DE": ("Deutsch",     "auf Deutsch",     "Antwort auf Deutsch"),
        "FR": ("Französisch", "auf Französisch", "Réponse en français"),
    }
    _, prompt_lang, footer = lang_map.get(
        lang, ("Deutsch", "auf Deutsch", "Antwort auf Deutsch")
    )

    system = (
        f"Du bist ein freundlicher VHA-Alliance Assistent. "
        f"Antworte **ausschließlich** {prompt_lang}. "
        f"Keine Sprachhinweise. Natürlich und direkt."
    )

    try:
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=0.7,
            max_tokens=1400,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": question.strip()}
            ]
        )
        answer = resp.choices[0].message.content.strip()
        color = 0x5865F2
    except Exception as e:
        answer = f"Fehler: {str(e)}"
        color = 0xFF0000
        footer = "Fehler"

    embed = discord.Embed(title="VHA KI • Antwort", description=answer, color=color)
    embed.set_author(name="VHA ALLIANCE", icon_url=LOGO_URL)
    embed.add_field(name="→ Deine Frage", value=question[:900], inline=False)
    embed.set_footer(
        text=f"VHA • Groq • {GROQ_MODEL} • {footer}", icon_url=LOGO_URL
    )
    await thinking.edit(embed=embed)


# ────────────────────────────────────────────────
# AUTOMATISCHE ÜBERSETZUNG
# ────────────────────────────────────────────────

@bot.event
async def on_message(message: discord.Message):
    global processed_messages, processed_messages_set, translate_active

    if message.author.bot:
        return

    # FIX 3: Gleitendes Fenster – deque wirft älteste ID automatisch raus
    if message.id in processed_messages_set:
        return
    if len(processed_messages) == processed_messages.maxlen:
        oldest = processed_messages[0]
        processed_messages_set.discard(oldest)
    processed_messages.append(message.id)
    processed_messages_set.add(message.id)

    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return

    if not translate_active:
        return

    content = message.content.strip()

    # Nur wirklich leere oder reine Links überspringen
    if len(content) < 2:
        return
    if re.match(r'^https?://', content):
        return

    # FIX 2: Cooldown pro User – max. 1 Übersetzung alle 3 Sekunden
    now = time.time()
    last = user_last_translation.get(message.author.id, 0)
    if now - last < TRANSLATION_COOLDOWN:
        return
    user_last_translation[message.author.id] = now

    # Sprache per LLM erkennen
    lang = await detect_language_llm(content)

    if lang == "DE":
        flag = "🇫🇷"
        system_prompt = (
            "Du bist ein sehr natürlicher, umgangssprachlicher Übersetzer. "
            "Übersetze den folgenden deutschen Text **locker, jugendlich und idiomatisch** ins Französische. "
            "Gib **ausschließlich** die französische Übersetzung aus – "
            "KEINEN einleitenden Satz, KEIN 'Voici la traduction:', nur den reinen französischen Text."
        )
    elif lang == "FR":
        flag = "🇩🇪"
        system_prompt = (
            "Du bist ein sehr natürlicher, umgangssprachlicher Übersetzer. "
            "Übersetze den folgenden französischen Text **locker, jugendlich und idiomatisch** ins Deutsche. "
            "Gib **ausschließlich** die deutsche Übersetzung aus – "
            "KEINEN einleitenden Satz, KEIN 'Auf Deutsch:', nur den reinen deutschen Text."
        )
    else:
        # OTHER = neutral → nicht übersetzen
        return

    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=0.15,
            max_tokens=700,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": content}
            ]
        )

        translation = completion.choices[0].message.content.strip()

        if not translation or len(translation) < 2:
            return

        # Nur blocken wenn Übersetzung exakt gleich dem Original ist
        if content.lower().strip() == translation.lower().strip():
            return

        await message.reply(f"{flag} {translation}", mention_author=False)

    except Exception as e:
        print(f"Übersetzungsfehler: {type(e).__name__} - {str(e)}")
        # FIX 5: User bekommt ein sichtbares Signal wenn die Übersetzung fehlschlägt
        try:
            await message.add_reaction("⚠️")
        except Exception:
            pass  # Falls auch die Reaktion fehlschlägt, still ignorieren


# ────────────────────────────────────────────────
# START
# ────────────────────────────────────────────────

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True, name="Flask-KeepAlive").start()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("DISCORD_TOKEN fehlt!")
        exit(1)

    bot.run(token)
