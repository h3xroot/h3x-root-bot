# h3x.root verification bot
# New members see only START HERE until verification.

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

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


VERIFIED_ROLE = "✅ Verified"

START_CATEGORY = "📌 START HERE"
VERIFY_CHANNEL = "🔐・verification"
WELCOME_CHANNEL = "👋・welcome"
RULES_CHANNEL = "📜・rules"

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


def generate_names():

    names = []

    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":

        for number in range(1, 100):

            names.append(
                f"h3x-{letter}{number:02d}"
            )

    return names


ALL_NAMES = generate_names()


def load_sequence():

    try:

        with open(
            SEQUENCE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return int(
            data.get("next_index", 0)
        )

    except (
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
        TypeError
    ):

        return 0


def save_sequence(index):

    temp_file = SEQUENCE_FILE + ".tmp"

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            {"next_index": index},
            file,
            indent=2
        )

    os.replace(
        temp_file,
        SEQUENCE_FILE
    )


def get_next_name(guild):

    index = load_sequence()

    while index < len(ALL_NAMES):

        nickname = ALL_NAMES[index]

        index += 1

        save_sequence(index)

        if not discord.utils.get(
            guild.members,
            nick=nickname
        ):

            return nickname

    return None


# ============================================================
# VERIFICATION VIEW
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
                "Verification is currently unavailable. Contact staff.",
                ephemeral=True
            )

            return


        try:

            # Give verified role.
            if role not in member.roles:

                await member.add_roles(
                    role,
                    reason="h3x.root verification"
                )


            # Give sequential private server nickname.
            nick = member.nick

            if not (
                nick
                and nick.startswith("h3x-")
            ):

                new_name = get_next_name(guild)

                if new_name:

                    try:

                        await member.edit(
                            nick=new_name,
                            reason="h3x.root privacy nickname"
                        )

                        nick = new_name

                    except discord.Forbidden:

                        pass


            if nick:

                message = (
                    "✅ **Verification complete!**\n\n"
                    f"Your private server name is **`{nick}`**.\n\n"
                    "Your server nickname is independent from "
                    "your Discord account ID.\n\n"
                    "The main h3x.root channels are now unlocked."
                )

            else:

                message = (
                    "✅ **Verification complete!**\n\n"
                    "Your Verified role was assigned, but I "
                    "couldn't change your nickname.\n\n"
                    "Please contact staff."
                )


            await interaction.response.send_message(
                message,
                ephemeral=True
            )


        except discord.Forbidden:

            if not interaction.response.is_done():

                await interaction.response.send_message(
                    "I don't have enough permissions to verify you.",
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
# ROLE
# ============================================================

async def get_or_create_role(
    guild,
    name
):

    role = discord.utils.get(
        guild.roles,
        name=name
    )

    if role:

        return role

    return await guild.create_role(
        name=name,
        colour=discord.Colour.green(),
        reason="h3x.root verification setup"
    )


# ============================================================
# SERVER PERMISSIONS
# ============================================================

async def setup_permissions(guild):

    everyone = guild.default_role

    verified = discord.utils.get(
        guild.roles,
        name=VERIFIED_ROLE
    )

    if verified is None:

        verified = await get_or_create_role(
            guild,
            VERIFIED_ROLE
        )


    # --------------------------------------------------------
    # START HERE
    # --------------------------------------------------------

    start = discord.utils.get(
        guild.categories,
        name=START_CATEGORY
    )

    if start is None:

        start = await guild.create_category(
            START_CATEGORY,
            reason="h3x.root verification setup"
        )


    # --------------------------------------------------------
    # ONLY START HERE IS VISIBLE TO @everyone
    # --------------------------------------------------------

    await start.set_permissions(
        everyone,
        view_channel=True,
        send_messages=False,
        read_message_history=True
    )

    await start.set_permissions(
        verified,
        view_channel=True,
        send_messages=False,
        read_message_history=True
    )


    # --------------------------------------------------------
    # ALL OTHER CATEGORIES ARE HIDDEN BEFORE VERIFICATION
    # --------------------------------------------------------

    for category_name in CONTENT_CATEGORIES:

        category = discord.utils.get(
            guild.categories,
            name=category_name
        )

        if not category:
            continue


        # Completely hide from unverified members.
        await category.set_permissions(
            everyone,
            view_channel=False,
            send_messages=False,
            read_message_history=False
        )


        # Verified members can access it.
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

            staff_role = discord.utils.get(
                guild.roles,
                name=role_name
            )

            if staff_role:

                await category.set_permissions(
                    staff_role,
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )


    print(
        "Private verification gate configured."
    )


# ============================================================
# START HERE CHANNELS
# ============================================================

async def setup_start_channels(guild):

    start = discord.utils.get(
        guild.categories,
        name=START_CATEGORY
    )

    if start is None:

        start = await guild.create_category(
            START_CATEGORY,
            reason="h3x.root setup"
        )


    everyone = guild.default_role

    verified = discord.utils.get(
        guild.roles,
        name=VERIFIED_ROLE
    )


    # --------------------------------------------------------
    # WELCOME
    # --------------------------------------------------------

    welcome = discord.utils.get(
        start.channels,
        name=WELCOME_CHANNEL
    )

    if welcome is None:

        welcome = await guild.create_text_channel(
            WELCOME_CHANNEL,
            category=start,
            reason="h3x.root welcome"
        )


    await welcome.set_permissions(
        everyone,
        view_channel=True,
        send_messages=False,
        read_message_history=True
    )

    if verified:

        await welcome.set_permissions(
            verified,
            view_channel=True,
            send_messages=False,
            read_message_history=True
        )


    # --------------------------------------------------------
    # RULES
    # --------------------------------------------------------

    rules = discord.utils.get(
        start.channels,
        name=RULES_CHANNEL
    )

    if rules is None:

        rules = await guild.create_text_channel(
            RULES_CHANNEL,
            category=start,
            reason="h3x.root rules"
        )


    await rules.set_permissions(
        everyone,
        view_channel=True,
        send_messages=False,
        read_message_history=True
    )

    if verified:

        await rules.set_permissions(
            verified,
            view_channel=True,
            send_messages=False,
            read_message_history=True
        )


    # --------------------------------------------------------
    # VERIFICATION
    # --------------------------------------------------------

    verification = discord.utils.get(
        start.channels,
        name=VERIFY_CHANNEL
    )

    if verification is None:

        verification = await guild.create_text_channel(
            VERIFY_CHANNEL,
            category=start,
            reason="h3x.root verification"
        )


    await verification.set_permissions(
        everyone,
        view_channel=True,
        send_messages=False,
        read_message_history=True
    )

    if verified:

        await verification.set_permissions(
            verified,
            view_channel=True,
            send_messages=False,
            read_message_history=True
        )


    # --------------------------------------------------------
    # SEND VERIFICATION PANEL
    # --------------------------------------------------------

    found = False

    try:

        async for message in verification.history(
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

        await verification.send(

            "🔐 **h3x.root verification**\n\n"

            "Welcome to **h3x.root**.\n\n"

            "Before entering the main server, please read "
            "**📜・rules** and agree to the community rules.\n\n"

            "Click **✅ I Agree & Verify** below.\n\n"

            "After verification, the main channels will unlock "
            "and you will receive a unique server nickname such as "
            "`h3x-A01`.\n\n"

            "Your server nickname is not your Discord ID and is "
            "generated independently from your Discord account.",

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

        await setup_start_channels(
            guild
        )

        await setup_permissions(
            guild
        )

        print(
            "h3x.root verification system is ready."
        )

        print(
            "Before verification: START HERE only."
        )

        print(
            "After verification: main server unlocked."
        )

    except Exception as error:

        print(
            f"Setup error: {type(error).__name__}: {error}"
        )


# ============================================================
# NEW MEMBER
# ============================================================

@bot.event
async def on_member_join(member):

    if member.guild.id != GUILD_ID:

        return


    try:

        # Assign private sequential name immediately.
        if not (
            member.nick
            and member.nick.startswith("h3x-")
        ):

            nick = get_next_name(
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
# RUN
# ============================================================

bot.run(TOKEN)
