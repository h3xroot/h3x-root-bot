import os
import json
import discord

from discord.ext import commands
from discord.ui import View, Button
from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

if not TOKEN or not GUILD_ID:
    raise RuntimeError(
        "Set DISCORD_TOKEN and GUILD_ID in the environment variables."
    )


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()

# Required for member join/nickname functionality.
intents.members = True

# Required by discord.py configuration.
intents.message_content = True


# ============================================================
# BOT SETTINGS
# ============================================================

VERIFIED_ROLE = "✅ Verified"

VERIFY_CHANNEL = "🔐・verification"

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
# DATA STORAGE
# ============================================================

# FadeHost/container environments may not allow writing beside
# the application file. Keep persistent runtime data in a
# dedicated writable directory.

DATA_DIR = os.path.join(os.getcwd(), "data")

os.makedirs(DATA_DIR, exist_ok=True)

SEQUENCE_FILE = os.path.join(
    DATA_DIR,
    "server_name_sequence.json",
)


# ============================================================
# SEQUENTIAL SERVER NAMES
# ============================================================

def generate_all_names():
    """
    Creates:

    h3x-A01
    h3x-A02
    ...
    h3x-A99
    h3x-B01
    ...
    h3x-Z99

    Total:
    26 * 99 = 2574 names
    """

    names = []

    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        for number in range(1, 100):
            names.append(
                f"h3x-{letter}{number:02d}"
            )

    return names


ALL_SERVER_NAMES = generate_all_names()


def load_sequence():
    """
    Load the next sequence position.

    Example:
    {
        "next_index": 0
    }
    """

    try:
        with open(
            SEQUENCE_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        index = int(data.get("next_index", 0))

        if index < 0:
            index = 0

        return index

    except (
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
        TypeError,
    ):
        return 0


def save_sequence(index):
    """
    Save the next available sequence index.
    """

    data = {
        "next_index": index
    }

    temporary_file = SEQUENCE_FILE + ".tmp"

    with open(
        temporary_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
        )

    os.replace(
        temporary_file,
        SEQUENCE_FILE,
    )


def name_is_used(guild, nickname):
    """
    Check whether the nickname is already being used
    by another member.
    """

    return discord.utils.get(
        guild.members,
        nick=nickname,
    ) is not None


def get_next_server_name(guild):
    """
    Get the next available sequential server name.

    Starts with h3x-A01 and eventually reaches h3x-Z99.
    """

    index = load_sequence()

    while index < len(ALL_SERVER_NAMES):

        nickname = ALL_SERVER_NAMES[index]

        index += 1

        # Save the next position immediately so the same
        # sequence number isn't intentionally reused.
        save_sequence(index)

        # Avoid duplicate nickname if it already exists.
        if not name_is_used(guild, nickname):
            return nickname

    # 2,574 names exhausted.
    return None


# ============================================================
# VERIFICATION VIEW
# ============================================================

class VerifyView(View):

    def __init__(self):
        # Persistent view.
        super().__init__(timeout=None)


    @discord.ui.button(
        label="I Agree & Verify",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="h3x_root_verify",
    )
    async def verify(
        self,
        interaction: discord.Interaction,
        button: Button,
    ):

        guild = interaction.guild
        member = interaction.user

        if guild is None:

            await interaction.response.send_message(
                "This button only works inside the h3x.root server.",
                ephemeral=True,
            )

            return


        role = discord.utils.get(
            guild.roles,
            name=VERIFIED_ROLE,
        )


        if role is None:

            await interaction.response.send_message(
                "Verification is temporarily unavailable. "
                "Please contact staff.",
                ephemeral=True,
            )

            return


        try:

            # ------------------------------------------------
            # VERIFIED ROLE
            # ------------------------------------------------

            if role not in member.roles:

                await member.add_roles(
                    role,
                    reason="h3x.root verification",
                )


            # ------------------------------------------------
            # SERVER NICKNAME
            # ------------------------------------------------

            nick = None


            if (
                member.nick
                and member.nick.startswith("h3x-")
            ):

                nick = member.nick

            else:

                nick = get_next_server_name(guild)


                if nick is not None:

                    try:

                        await member.edit(
                            nick=nick,
                            reason="h3x.root privacy nickname",
                        )

                    except discord.Forbidden:

                        nick = None


            # ------------------------------------------------
            # RESPONSE
            # ------------------------------------------------

            if nick:

                message = (
                    "✅ **Verification complete!**\n\n"
                    f"Your private server name is **`{nick}`**.\n\n"
                    "Your server name is separate from your "
                    "Discord account ID.\n\n"
                    "You can now access the h3x.root channels."
                )

            else:

                message = (
                    "✅ **Verification complete!**\n\n"
                    "Your Verified role has been assigned.\n\n"
                    "I couldn't change your server nickname. "
                    "Please ask staff to check the bot's "
                    "**Manage Nicknames** permission and role hierarchy."
                )


            await interaction.response.send_message(
                message,
                ephemeral=True,
            )


        except discord.Forbidden:

            if not interaction.response.is_done():

                await interaction.response.send_message(
                    "I don't have enough permissions to complete "
                    "verification. Please contact staff.",
                    ephemeral=True,
                )


        except discord.HTTPException as error:

            print(
                f"Verification HTTP error: {error}"
            )

            if not interaction.response.is_done():

                await interaction.response.send_message(
                    "Verification temporarily failed. "
                    "Please try again.",
                    ephemeral=True,
                )


        except Exception as error:

            print(
                f"Verification error: "
                f"{type(error).__name__}: {error}"
            )

            if not interaction.response.is_done():

                await interaction.response.send_message(
                    "An unexpected verification error occurred. "
                    "Please contact staff.",
                    ephemeral=True,
                )


# ============================================================
# BOT CLASS
# ============================================================

class H3xBot(commands.Bot):

    async def setup_hook(self):

        # Makes the verification button survive bot restarts.
        self.add_view(
            VerifyView()
        )


bot = H3xBot(
    command_prefix="!",
    intents=intents,
    help_command=None,
)


# ============================================================
# ROLE SETUP
# ============================================================

async def get_or_create_role(
    guild,
    name,
    colour=discord.Colour.default(),
):

    role = discord.utils.get(
        guild.roles,
        name=name,
    )

    if role:
        return role


    return await guild.create_role(
        name=name,
        colour=colour,
        reason="h3x.root verification setup",
    )


# ============================================================
# PERMISSIONS
# ============================================================

async def setup_permissions(guild):

    verified = discord.utils.get(
        guild.roles,
        name=VERIFIED_ROLE,
    )


    if verified is None:

        verified = await get_or_create_role(
            guild,
            VERIFIED_ROLE,
            discord.Colour.green(),
        )


    everyone = guild.default_role


    # --------------------------------------------------------
    # START HERE
    # --------------------------------------------------------

    start = discord.utils.get(
        guild.categories,
        name=START_CATEGORY,
    )


    if start:

        for channel in start.channels:

            await channel.set_permissions(
                everyone,
                view_channel=True,
                send_messages=False,
                read_message_history=True,
            )

            await channel.set_permissions(
                verified,
                view_channel=True,
                send_messages=False,
                read_message_history=True,
            )


    # --------------------------------------------------------
    # MAIN CONTENT
    # --------------------------------------------------------

    for category_name in CONTENT_CATEGORIES:

        category = discord.utils.get(
            guild.categories,
            name=category_name,
        )


        if not category:
            continue


        # Hide from unverified members.
        await category.set_permissions(
            everyone,
            view_channel=False,
        )


        # Verified members.
        await category.set_permissions(
            verified,
            view_channel=True,
            read_message_history=True,
            send_messages=True,
            create_public_threads=True,
            embed_links=True,
            attach_files=True,
            add_reactions=True,
        )


        # Staff.
        for role_name in STAFF_ROLES:

            role = discord.utils.get(
                guild.roles,
                name=role_name,
            )


            if role:

                await category.set_permissions(
                    role,
                    view_channel=True,
                    read_message_history=True,
                    send_messages=True,
                )


# ============================================================
# VERIFICATION CHANNEL
# ============================================================

async def setup_verification_channel(guild):

    start = discord.utils.get(
        guild.categories,
        name=START_CATEGORY,
    )


    if start is None:

        start = await guild.create_category(
            START_CATEGORY,
            reason="h3x.root verification setup",
        )


    channel = discord.utils.get(
        start.channels,
        name=VERIFY_CHANNEL,
    )


    if channel is None:

        channel = await guild.create_text_channel(
            VERIFY_CHANNEL,
            category=start,
            reason="h3x.root verification setup",
        )


    everyone = guild.default_role

    verified = discord.utils.get(
        guild.roles,
        name=VERIFIED_ROLE,
    )


    await channel.set_permissions(
        everyone,
        view_channel=True,
        send_messages=False,
        read_message_history=True,
        add_reactions=False,
    )


    if verified:

        await channel.set_permissions(
            verified,
            view_channel=True,
            send_messages=False,
            read_message_history=True,
        )


    # --------------------------------------------------------
    # Avoid duplicate verification panels.
    # --------------------------------------------------------

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

            "Server names are assigned sequentially and are "
            "independent of your Discord account ID.\n\n"

            "**Sequence:** `h3x-A01` → `h3x-A99` → "
            "`h3x-B01` → ... → `h3x-Z99`.",

            view=VerifyView(),
        )


# ============================================================
# READY EVENT
# ============================================================

@bot.event
async def on_ready():

    guild = bot.get_guild(
        GUILD_ID
    )


    if guild is None:

        print(
            "ERROR: Server not found. "
            "Check GUILD_ID."
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
            "Server-name sequence: "
            "h3x-A01 -> h3x-Z99"
        )


    except discord.Forbidden as error:

        print(
            "ERROR: Discord permissions are insufficient: "
            f"{error}"
        )


    except Exception as error:

        print(
            f"Setup error: "
            f"{type(error).__name__}: {error}"
        )


# ============================================================
# NEW MEMBER
# ============================================================

@bot.event
async def on_member_join(member):

    if member.guild.id != GUILD_ID:
        return


    try:

        # Give a server-only sequential nickname immediately.
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
                    reason="h3x.root privacy nickname",
                )

                print(
                    f"Assigned {nick} to member "
                    f"{member.id}"
                )

            else:

                print(
                    "WARNING: h3x.root has exhausted "
                    "all 2,574 server names."
                )


    except discord.Forbidden:

        print(
            "Could not assign join nickname. "
            "Check Manage Nicknames + role hierarchy."
        )


    except discord.HTTPException as error:

        print(
            f"Nickname assignment failed: {error}"
        )


# ============================================================
# START
# ============================================================

bot.run(TOKEN)
