# ════════════════════════════════════════════════
#  Timer-Cog  •  VHA Alliance
#  Separate Datei – wird von app.py geladen
#  Erlaubte Rollen: Administrator, R5, R4
# ════════════════════════════════════════════════

import discord
from discord.ext import commands, tasks
import json
import os
import asyncio
from datetime import datetime, timezone

DATA_FILE = "timer.json"
ALLOWED_ROLES = {"R5", "R4"}


# ────────────────────────────────────────────────
# Hilfsfunktionen
# ────────────────────────────────────────────────

def load_timers() -> list:
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("timers", [])


def save_timers(timers: list):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"timers": timers}, f, indent=2, ensure_ascii=False)


def has_permission(member: discord.Member) -> bool:
    # Administrator-Berechtigung ODER Rolle R5/R4
    if member.guild_permissions.administrator:
        return True
    # Rollenname exakt oder case-insensitive prüfen
    member_roles = {r.name.upper() for r in member.roles}
    allowed_upper = {r.upper() for r in ALLOWED_ROLES}
    return bool(member_roles & allowed_upper)


def parse_duration(duration_str: str) -> int:
    """
    Parst eine Zeitangabe wie '2h', '30m', '1h30m', '90m' in Sekunden.
    Gibt -1 zurück wenn das Format ungültig ist.
    """
    duration_str = duration_str.lower().strip()
    total_seconds = 0
    import re

    # Format: 1h30m, 2h, 45m, 90m, 3600s
    pattern = re.findall(r'(\d+)\s*([hms])', duration_str)
    if not pattern:
        # Nur Zahl → als Minuten interpretieren
        if duration_str.isdigit():
            return int(duration_str) * 60
        return -1

    for value, unit in pattern:
        value = int(value)
        if unit == 'h':
            total_seconds += value * 3600
        elif unit == 'm':
            total_seconds += value * 60
        elif unit == 's':
            total_seconds += value

    return total_seconds if total_seconds > 0 else -1


def format_duration(seconds: int) -> str:
    """Formatiert Sekunden als lesbare Zeit z.B. '1h 30m'."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    if s and not h:
        parts.append(f"{s}s")
    return " ".join(parts) if parts else "0m"


# ────────────────────────────────────────────────
# Cog
# ────────────────────────────────────────────────

class TimerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_timers.start()

    def cog_unload(self):
        self.check_timers.cancel()

    # ── Hintergrund-Task: prüft jede Minute ob Timer abgelaufen ──
    @tasks.loop(seconds=30)
    async def check_timers(self):
        timers = load_timers()
        now = datetime.now(timezone.utc).timestamp()
        remaining = []
        fired = []

        for t in timers:
            if now >= t["end_timestamp"]:
                fired.append(t)
            else:
                remaining.append(t)

        if fired:
            save_timers(remaining)

        for t in fired:
            try:
                channel = self.bot.get_channel(t["channel_id"])
                if channel:
                    embed = discord.Embed(
                        title=f"⏰ Erinnerung / Rappel • {t['event']}",
                        color=0xF39C12
                    )
                    embed.add_field(
                        name="🇩🇪 Deutsch",
                        value=f"**{t['event']}** beginnt jetzt! ⚔️",
                        inline=False
                    )
                    embed.add_field(
                        name="🇫🇷 Français",
                        value=f"**{t['event']}** commence maintenant ! ⚔️",
                        inline=False
                    )
                    embed.set_footer(text=f"Timer gesetzt von / Minuteur défini par {t['author']}")

                    # @everyone ping damit alle es sehen
                    await channel.send("@everyone", embed=embed)
            except Exception as e:
                print(f"Timer-Fehler beim Senden: {e}")

    @check_timers.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    # ── !timer ───────────────────────────────────
    @commands.group(name="timer", aliases=["rappel", "erinnerung", "reminder"], invoke_without_command=True)
    async def timer(self, ctx, duration: str = None, *, event: str = None):
        """
        Setzt einen Timer für ein Event.
        Nutzung: !timer DAUER EVENTNAME
        Beispiel: !timer 2h Kriegsstart
                  !timer 30m Allianz-Meeting
                  !timer 1h30m Angriff Zone 5
        """
        if duration is None or event is None:
            await ctx.send(
                "❓ Nutzung: `!timer DAUER EVENT`\n"
                "Exemple: `!timer 2h Kriegsstart` / `!timer 30m Meeting`\n"
                "Zeitformate / Formats: `30m`, `2h`, `1h30m`"
            )
            return

        if not has_permission(ctx.author):
            embed = discord.Embed(
                title="❌ Keine Berechtigung / Pas d'autorisation",
                description=(
                    "Nur **Administrator**, **R5** und **R4** dürfen Timer setzen.\n"
                    "Seuls les **Administrateur**, **R5** et **R4** peuvent définir des minuteurs."
                ),
                color=0xED4245
            )
            await ctx.send(embed=embed)
            return

        seconds = parse_duration(duration)
        if seconds <= 0:
            await ctx.send(
                "❌ Ungültiges Zeitformat. Beispiele: `30m`, `2h`, `1h30m`\n"
                "Format invalide. Exemples: `30m`, `2h`, `1h30m`"
            )
            return

        end_timestamp = datetime.now(timezone.utc).timestamp() + seconds

        timers = load_timers()
        timers.append({
            "event": event,
            "duration_seconds": seconds,
            "end_timestamp": end_timestamp,
            "channel_id": ctx.channel.id,
            "author": ctx.author.display_name
        })
        save_timers(timers)

        embed = discord.Embed(
            title=f"⏱️ Timer gesetzt / Minuteur défini • {event}",
            color=0x57F287
        )
        embed.add_field(
            name="🇩🇪 Erinnerung in",
            value=f"**{format_duration(seconds)}**",
            inline=True
        )
        embed.add_field(
            name="🇫🇷 Rappel dans",
            value=f"**{format_duration(seconds)}**",
            inline=True
        )
        embed.add_field(
            name="📍 Event",
            value=event,
            inline=False
        )
        embed.set_footer(text=f"Gesetzt von / Défini par {ctx.author.display_name}")
        await ctx.send(embed=embed)

    # ── !timer list ──────────────────────────────
    @timer.command(name="list", aliases=["liste", "all", "alle"])
    async def timer_list(self, ctx):
        """Zeigt alle aktiven Timer an."""
        timers = load_timers()
        now = datetime.now(timezone.utc).timestamp()

        # Abgelaufene rausfiltern
        active = [t for t in timers if now < t["end_timestamp"]]
        if len(active) != len(timers):
            save_timers(active)
            timers = active

        if not timers:
            await ctx.send(
                "📭 Keine aktiven Timer.\n"
                "Aucun minuteur actif."
            )
            return

        embed = discord.Embed(
            title="⏱️ Aktive Timer / Minuteurs actifs",
            color=0x3498DB
        )

        for t in timers:
            remaining = int(t["end_timestamp"] - now)
            embed.add_field(
                name=f"📍 {t['event']}",
                value=(
                    f"⏳ Noch / Reste: **{format_duration(remaining)}**\n"
                    f"👤 {t['author']}"
                ),
                inline=False
            )

        embed.set_footer(text=f"Gesamt / Total: {len(timers)} Timer")
        await ctx.send(embed=embed)

    # ── !timer delete ────────────────────────────
    @timer.command(name="delete", aliases=["löschen", "supprimer", "del", "remove", "cancel", "abbrechen", "annuler"])
    async def timer_delete(self, ctx, *, event: str):
        """Löscht einen Timer manuell."""
        if not has_permission(ctx.author):
            embed = discord.Embed(
                title="❌ Keine Berechtigung / Pas d'autorisation",
                description=(
                    "Nur **Administrator**, **R5** und **R4** dürfen Timer löschen.\n"
                    "Seuls les **Administrateur**, **R5** et **R4** peuvent supprimer des minuteurs."
                ),
                color=0xED4245
            )
            await ctx.send(embed=embed)
            return

        timers = load_timers()
        original_len = len(timers)
        timers = [t for t in timers if t["event"].lower() != event.lower()]

        if len(timers) == original_len:
            await ctx.send(
                f"⚠️ Kein Timer mit dem Namen `{event}` gefunden.\n"
                f"Aucun minuteur nommé `{event}` trouvé."
            )
            return

        save_timers(timers)
        embed = discord.Embed(
            title=f"🗑️ Timer gelöscht / Minuteur supprimé • {event}",
            color=0xED4245
        )
        embed.set_footer(text=f"Gelöscht von / Supprimé par {ctx.author.display_name}")
        await ctx.send(embed=embed)

    # ── !timer help ──────────────────────────────
    @timer.command(name="help", aliases=["hilfe", "aide"])
    async def timer_help(self, ctx):
        embed = discord.Embed(
            title="⏱️ Timer – Hilfe / Aide",
            color=0x3498DB
        )
        embed.add_field(
            name="🇩🇪 Befehle",
            value=(
                "`!timer DAUER EVENT` – Timer setzen\n"
                "`!timer list` – Alle aktiven Timer anzeigen\n"
                "`!timer delete EVENTNAME` – Timer löschen\n\n"
                "**Zeitformate:** `30m` `2h` `1h30m`\n"
                "**Beispiel:** `!timer 2h Kriegsstart`"
            ),
            inline=False
        )
        embed.add_field(
            name="🇫🇷 Commandes",
            value=(
                "`!rappel DURÉE EVENT` – Définir un minuteur\n"
                "`!rappel list` – Voir tous les minuteurs\n"
                "`!rappel supprimer EVENTNAME` – Supprimer\n\n"
                "**Formats:** `30m` `2h` `1h30m`\n"
                "**Exemple:** `!rappel 2h Kriegsstart`"
            ),
            inline=False
        )
        embed.add_field(
            name="🔐 Berechtigung / Permission",
            value="Administrator, R5, R4",
            inline=False
        )
        await ctx.send(embed=embed)


# ────────────────────────────────────────────────
# Setup
# ────────────────────────────────────────────────

async def setup(bot):
    await bot.add_cog(TimerCog(bot))
