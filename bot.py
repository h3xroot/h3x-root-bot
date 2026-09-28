import os
import json
import discord

from discord.ext import commands
from discord.ui import View, Button
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

if not TOKEN or not GUILD_ID:
    raise RuntimeError("Set DISCORD_TOKEN and GUILD_ID in the environment variables.")


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


# ============================================================
# SETTINGS
# ============================================================

VERIFIED_ROLE = "✅ Verified"

VERIFY_CHANNEL = "🔐・verification"
RULES_CHANNEL = "📜・rules"
MAIN_CHAT_CHANNEL = "💬 COMMUNITY・MAIN CHAT"

START_CATEGORY = "📌 START HERE"

STAFF_ROLES = {
    "👑 Owner",
    "🛡️ Admin",
    "🔧 Moderator",
    "🎓 Mentor",
    "🔬 Researcher",
}

CONTENT_CATEGORIES = {
    "💬 COMMUNITY",
    "📰 NEWS",
    "🔴 SECURITY",
    "🧪 LAB",
    "📚 RESOURCES",
    "🎤 EVENTS",
}


# ============================================================
# SEQUENTIAL SERVER NAMES
# ============================================================

DATA_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(DATA_DIR, exist_ok=True)

SEQUENCE_FILE = os.path.join(
    DATA_DIR,
    "server_name_sequence.json"
)


def generate_all_names():
    names = []

    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        for number in range(1, 100):
            names.append(
                f"h3x-{letter}{number:02d}"
            )

    return names


ALL_SERVER_NAMES = generate_all_names()


def load_sequence():

    try:
        with open(
            SEQUENCE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return max(
            0,
            int(data.get("next_index", 0))
        )

    except (
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
        TypeError
    ):

        return 0


def save_sequence(index):

    data = {
        "next_index": index
    }

    temp_file = SEQUENCE_FILE + ".tmp"

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=2
        )

    os.replace(
        temp_file,
        SEQUENCE_FILE
    )


def name_is_used(guild, nickname):

    return discord.utils.get(
        guild.members,
        nick=nickname
    ) is not None


def get_next_server_name(guild):

    index = load_sequence()

    while index < len(ALL_SERVER_NAMES):

        nickname = ALL_SERVER_NAMES[index]

        index += 1

        save_sequence(index)

        if not name_is_used(
            guild,
            nickname
        ):

            return nickname

    return None


# ============================================================
# VERIFICATION BUTTON
# ============================================================

class VerifyView(View):

    def __init__(self):

        super().__init__(
            timeout=None
        )


    @discord.ui.button(
        label="I Agree & Verify",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="h3x_root_verify"
    )
    async def verify(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        guild = interaction.guild
        member = interaction.user

        if guild is None:

            await interaction.response.send_message(
                "This button only works inside h3x.root.",
                ephemeral=True
            )

            return


        role = discord.utils.get(
            guild.roles,
            name=VERIFIED_ROLE
        )


        if role is None:

            await interaction.response.send_message(
                "Verification is temporarily unavailable. Please contact staff.",
                ephemeral=True
            )

            return


        try:

            if role not in member.roles:

                await member.add_roles(
                    role,
                    reason="h3x.root verification"
                )


            nick = None


            if (
                member.nick
                and member.nick.startswith("h3x-")
            ):

                nick = member.nick

            else:

                nick = get_next_server_name(
                    guild
                )

                if nick:

                    try:

                        await member.edit(
                            nick=nick,
                            reason="h3x.root privacy nickname"
                        )

                    except discord.Forbidden:

                        nick = None


            if nick:

                text = (
                    "✅ **Verification complete!**\n\n"
                    f"Your private server name is **`{nick}`**.\n\n"
                    "Your server name is separate from your Discord account ID.\n\n"
                    "You can now access the h3x.root channels."
                )

            else:

                text = (
                    "✅ **Verification complete!**\n\n"
                    "Your Verified role has been assigned.\n\n"
                    "I couldn't change your server nickname. "
                    "Please ask staff to check **Manage Nicknames** "
                    "and role hierarchy."
                )


            await interaction.response.send_message(
                text,
                ephemeral=True
            )


        except discord.Forbidden:

            if not interaction.response.is_done():

                await interaction.response.send_message(
                    "I don't have enough permissions to complete verification.",
                    ephemeral=True
                )


        except Exception as error:

            print(
                f"Verification error: {type(error).__name__}: {error}"
            )

            if not interaction.response.is_done():

                await interaction.response.send_message(
                    "Verification failed. Please contact staff.",
                    ephemeral=True
                )


# ============================================================
# BOT
# ============================================================

class H3xBot(commands.Bot):

    async def setup_hook(self):

        self.add_view(
            VerifyView()
        )


bot = H3xBot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# ============================================================
# ROLE CREATION
# ============================================================

async def get_or_create_role(
    guild,
    name,
    colour=discord.Colour.default()
):

    role = discord.utils.get(
        guild.roles,
        name=name
    )

    if role:

        return role


    return await guild.create_role(
        name=name,
        colour=colour,
        reason="h3x.root verification setup"
    )


# ============================================================
# PERMISSIONS
# ============================================================

async def setup_permissions(guild):

    verified = discord.utils.get(
        guild.roles,
        name=VERIFIED_ROLE
    )


    if verified is None:

        verified = await get_or_create_role(
            guild,
            VERIFIED_ROLE,
            discord.Colour.green()
        )


    everyone = guild.default_role


    # --------------------------------------------------------
    # START HERE
    # --------------------------------------------------------

    start = discord.utils.get(
        guild.categories,
        name=START_CATEGORY
    )


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


    # --------------------------------------------------------
    # MAIN COMMUNITY CHAT
    # --------------------------------------------------------

    main_chat = discord.utils.get(
        guild.text_channels,
        name=MAIN_CHAT_CHANNEL
    )


    if main_chat:

        # Everyone can see the main chat.
        # Unverified members can send messages ONLY here.
        await main_chat.set_permissions(
            everyone,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            add_reactions=True
        )

        # Verified members get normal chat access.
        await main_chat.set_permissions(
            verified,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            add_reactions=True,
            embed_links=True,
            attach_files=True,
            create_public_threads=True
        )


    # --------------------------------------------------------
    # CONTENT CATEGORIES
    # --------------------------------------------------------

    for category_name in CONTENT_CATEGORIES:

        category = discord.utils.get(
            guild.categories,
            name=category_name
        )


        if not category:
            continue


        # Allow unverified members to SEE the channels,
        # but they cannot send messages.
        await category.set_permissions(
            everyone,
            view_channel=True,
            send_messages=False,
            read_message_history=True
        )


        # Verified members get full community access.
        await category.set_permissions(
            verified,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            create_public_threads=True,
            embed_links=True,
            attach_files=True,
            add_reactions=True
        )


        # Staff access.
        for role_name in STAFF_ROLES:

            role = discord.utils.get(
                guild.roles,
                name=role_name
            )

            if role:

                await category.set_permissions(
                    role,
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )


    print(
        "Permissions configured: "
        "unverified members can chat only in the main community chat."
    )


# ============================================================
# VERIFICATION CHANNEL
# ============================================================

async def setup_verification_channel(guild):

    start = discord.utils.get(
        guild.categories,
        name=START_CATEGORY
    )


    if start is None:

        start = await guild.create_category(
            START_CATEGORY,
            reason="h3x.root verification setup"
        )


    channel = discord.utils.get(
        start.channels,
        name=VERIFY_CHANNEL
    )


    if channel is None:

        channel = await guild.create_text_channel(
            VERIFY_CHANNEL,
            category=start,
            reason="h3x.root verification setup"
        )


    everyone = guild.default_role

    verified = discord.utils.get(
        guild.roles,
        name=VERIFIED_ROLE
    )


    await channel.set_permissions(
        everyone,
        view_channel=True,
        send_messages=False,
        read_message_history=True
    )


    if verified:

        await channel.set_permissions(
            verified,
            view_channel=True,
            send_messages=False,
            read_message_history=True
        )


    found = False


    try:

        async for message in channel.history(
            limit=50
        ):

            if (
                bot.user
                and message.author.id == bot.user.id
                and "h3x.root verification" in message.content
            ):

                found = True
                break


    except discord.Forbidden:

        pass


    if not found:

        await channel.send(

            "🔐 **h3x.root verification**\n\n"

            "Welcome to **h3x.root**.\n\n"

            "Before entering the main server, please read "
            "**📜・rules** and agree to the community rules.\n\n"

            "Click **✅ I Agree & Verify** below.\n\n"

            "After verification, the main channels will unlock "
            "and you will receive a unique server nickname "
            "such as `h3x-A01`.\n\n"

            "Your server nickname is independent from your "
            "Discord account ID.",

            view=VerifyView()
        )


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    guild = bot.get_guild(
        GUILD_ID
    )


    if guild is None:

        print(
            "ERROR: Server not found. Check GUILD_ID."
        )

        return


    print(
        f"Connected to: {guild.name}"
    )


    try:

        await setup_verification_channel(
            guild
        )

        await setup_permissions(
            guild
        )

        print(
            "h3x.root verification system is ready."
        )

        print(
            "Server-name sequence: h3x-A01 -> h3x-Z99"
        )


    except discord.Forbidden as error:

        print(
            f"Discord permission error: {error}"
        )


    except Exception as error:

        print(
            f"Setup error: {type(error).__name__}: {error}"
        )


# ============================================================
# MEMBER JOIN
# ============================================================

@bot.event
async def on_member_join(member):

    if member.guild.id != GUILD_ID:

        return


    try:

        if not (
            member.nick
            and member.nick.startswith("h3x-")
        ):

            nick = get_next_server_name(
                member.guild
            )


            if nick:

                await member.edit(
                    nick=nick,
                    reason="h3x.root privacy nickname"
                )

                print(
                    f"Assigned {nick} to member {member.id}"
                )

            else:

                print(
                    "WARNING: All 2,574 server names are used."
                )


    except discord.Forbidden:

        print(
            "Could not assign nickname. "
            "Check Manage Nicknames and role hierarchy."
        )


    except discord.HTTPException as error:

        print(
            f"Nickname assignment failed: {error}"
        )


# ============================================================
# START
# ============================================================

bot.run(TOKEN)
