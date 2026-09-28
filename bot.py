import os
import json
import secrets
import string
import discord
from discord.ext import commands
from discord.ui import View, Button
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

if not TOKEN or not GUILD_ID:
    raise RuntimeError("Set DISCORD_TOKEN and GUILD_ID in .env")

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

VERIFIED_ROLE = "✅ Verified"
VERIFY_CHANNEL = "🔐・verification"
START_CATEGORY = "📌 START HERE"
STAFF_ROLES = {"👑 Owner", "🛡️ Admin", "🔧 Moderator", "🎓 Mentor", "🔬 Researcher"}

CONTENT_CATEGORIES = {
    "💬 COMMUNITY", "📰 NEWS", "🔴 SECURITY", "🧪 LAB",
    "📚 RESOURCES", "🎤 EVENTS"
}

NICK_FILE = "server_nicknames.json"

def load_names():
    try:
        with open(NICK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"used": []}

def save_names(data):
    with open(NICK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def new_server_name(guild):
    data = load_names()
    used = set(data.get("used", []))
    alphabet = string.ascii_lowercase + string.digits

    while True:
        nickname = "h3x-" + "".join(secrets.choice(alphabet) for _ in range(6))
        if nickname not in used and not discord.utils.get(guild.members, nick=nickname):
            used.add(nickname)
            data["used"] = sorted(used)
            save_names(data)
            return nickname

class VerifyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="I Agree & Verify",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="h3x_root_verify"
    )
    async def verify(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        member = interaction.user

        if guild is None:
            await interaction.response.send_message(
                "This button only works inside the h3x.root server.",
                ephemeral=True
            )
            return

        role = discord.utils.get(guild.roles, name=VERIFIED_ROLE)
        if role is None:
            await interaction.response.send_message(
                "Verification is temporarily unavailable. Please contact staff.",
                ephemeral=True
            )
            return

        try:
            if role not in member.roles:
                await member.add_roles(role, reason="h3x.root verification")

            # Server nickname: random and unrelated to Discord ID.
            # Only change if the member doesn't already have an h3x nickname.
            if not (member.nick and member.nick.startswith("h3x-")):
                nick = new_server_name(guild)
                try:
                    await member.edit(nick=nick, reason="h3x.root privacy nickname")
                except discord.Forbidden:
                    # Verification still succeeds if nickname permission is missing.
                    nick = None

            if nick:
                text = (
                    f"✅ **Verification complete.**\n"
                    f"Your private server name is **`{nick}`**.\n\n"
                    "You can now access the h3x.root channels."
                )
            else:
                text = (
                    "✅ **Verification complete.**\n"
                    "Your Verified role has been assigned.\n\n"
                    "I couldn't change your server nickname. Staff should check "
                    "the bot's **Manage Nicknames** permission and role hierarchy."
                )

            await interaction.response.send_message(text, ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have enough permissions to complete verification. "
                "Please contact staff.",
                ephemeral=True
            )

class H3xBot(commands.Bot):
    async def setup_hook(self):
        self.add_view(VerifyView())

bot = H3xBot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

async def get_or_create_role(guild, name, colour=discord.Colour.default()):
    role = discord.utils.get(guild.roles, name=name)
    if role:
        return role
    return await guild.create_role(
        name=name,
        colour=colour,
        reason="h3x.root verification setup"
    )

async def setup_permissions(guild):
    verified = discord.utils.get(guild.roles, name=VERIFIED_ROLE)
    if verified is None:
        verified = await get_or_create_role(
            guild, VERIFIED_ROLE, discord.Colour.green()
        )

    everyone = guild.default_role

    # Verification/start-here category remains visible to everyone.
    start = discord.utils.get(guild.categories, name=START_CATEGORY)
    if start:
        for channel in start.channels:
            await channel.set_permissions(
                everyone,
                view_channel=True,
                send_messages=False,
                read_message_history=True
            )
            await channel.set_permissions(
                verified,
                view_channel=True,
                send_messages=False,
                read_message_history=True
            )

    # Content categories are hidden from unverified members.
    for category_name in CONTENT_CATEGORIES:
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            continue

        await category.set_permissions(everyone, view_channel=False)

        await category.set_permissions(
            verified,
            view_channel=True,
            read_message_history=True,
            send_messages=True,
            create_public_threads=True,
            embed_links=True,
            attach_files=True,
            add_reactions=True
        )

        # Staff retain access even before verification.
        for role_name in STAFF_ROLES:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                await category.set_permissions(
                    role,
                    view_channel=True,
                    read_message_history=True,
                    send_messages=True
                )

async def setup_verification_channel(guild):
    start = discord.utils.get(guild.categories, name=START_CATEGORY)
    if start is None:
        start = await guild.create_category(
            START_CATEGORY,
            reason="h3x.root verification setup"
        )

    channel = discord.utils.get(start.channels, name=VERIFY_CHANNEL)
    if channel is None:
        channel = await guild.create_text_channel(
            VERIFY_CHANNEL,
            category=start,
            reason="h3x.root verification setup"
        )

    everyone = guild.default_role
    verified = discord.utils.get(guild.roles, name=VERIFIED_ROLE)

    await channel.set_permissions(
        everyone,
        view_channel=True,
        send_messages=False,
        read_message_history=True,
        add_reactions=False
    )
    if verified:
        await channel.set_permissions(
            verified,
            view_channel=True,
            send_messages=False,
            read_message_history=True
        )

    # Don't duplicate the verification panel.
    found = False
    try:
        async for message in channel.history(limit=50):
            if message.author.id == bot.user.id and "h3x.root verification" in message.content:
                found = True
                break
    except discord.Forbidden:
        pass

    if not found:
        await channel.send(
            "🔐 **h3x.root verification**\n\n"
            "Welcome to **h3x.root**.\n\n"
            "Before entering the main server, please read **📜・rules** "
            "and agree to the community rules.\n\n"
            "Click **✅ I Agree & Verify** below.\n\n"
            "After verification, the main channels will unlock and you will "
            "receive a unique server nickname such as `h3x-a7k2m9`.\n\n"
            "Your server nickname is not your Discord ID and is generated "
            "independently from your account ID.",
            view=VerifyView()
        )

@bot.event
async def on_ready():
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        print("ERROR: Server not found. Check GUILD_ID.")
        return

    print(f"Connected to: {guild.name}")
    await setup_verification_channel(guild)
    await setup_permissions(guild)
    print("h3x.root verification system is ready.")

@bot.event
async def on_member_join(member):
    # Give every new member a private server nickname immediately.
    # This does not expose or derive the Discord ID.
    if member.guild.id != GUILD_ID:
        return

    try:
        if not (member.nick and member.nick.startswith("h3x-")):
            nick = new_server_name(member.guild)
            await member.edit(nick=nick, reason="h3x.root privacy nickname")
            print(f"Assigned {nick} to {member}")
    except discord.Forbidden:
        print("Could not assign join nickname. Check Manage Nicknames + role hierarchy.")
    except discord.HTTPException as e:
        print(f"Nickname assignment failed: {e}")

bot.run(TOKEN)
