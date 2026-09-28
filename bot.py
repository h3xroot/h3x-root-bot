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
intents.members = True
intents.message_content = True


# ============================================================
# SERVER SETTINGS
# ============================================================

VERIFIED_ROLE = "✅ Verified"

START_CATEGORY = "📌 START HERE"

WELCOME_CHANNEL = "👋・welcome"
RULES_CHANNEL = "📜・rules"
VERIFY_CHANNEL = "🔐・verification"

LOG_CATEGORY = "📊 MEMBER LOGS"

JOIN_LOG_CHANNEL = "🟢・member-joined"
LEAVE_LOG_CHANNEL = "🔴・member-left"


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
# SEQUENTIAL PRIVATE SERVER NAMES
# h3x-A01 -> h3x-A99 -> h3x-B01 -> ... -> h3x-Z99
# ============================================================

DATA_DIR = os.path.join(
    os.getcwd(),
    "data"
)

os.makedirs(
    DATA_DIR,
    exist_ok=True
)

SEQUENCE_FILE = os.path.join(
    DATA_DIR,
    "server_name_sequence.json"
)


def generate_server_names():

    names = []

    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":

        for number in range(1, 100):

            names.append(
                f"h3x-{letter}{number:02d}"
            )

    return names


ALL_SERVER_NAMES = generate_server_names()


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
            int(
                data.get(
                    "next_index",
                    0
                )
            )
        )

    except (
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
        TypeError
    ):

        return 0


def save_sequence(index):

    temporary_file = SEQUENCE_FILE + ".tmp"

    with open(
        temporary_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            {
                "next_index": index
            },
            file,
            indent=2
        )

    os.replace(
        temporary_file,
        SEQUENCE_FILE
    )


def get_next_server_name(guild):

    index = load_sequence()

    while index < len(ALL_SERVER_NAMES):

        nickname = ALL_SERVER_NAMES[index]

        index += 1

        save_sequence(index)

        # Don't give the same nickname to somebody
        # who is currently using it.
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


        verified_role = discord.utils.get(
            guild.roles,
            name=VERIFIED_ROLE
        )


        if verified_role is None:

            await interaction.response.send_message(
                "Verification is temporarily unavailable. "
                "Please contact staff.",
                ephemeral=True
            )

            return


        try:

            # ------------------------------------------------
            # GIVE VERIFIED ROLE
            # ------------------------------------------------

            if verified_role not in member.roles:

                await member.add_roles(
                    verified_role,
                    reason="h3x.root verification"
                )


            # ------------------------------------------------
            # ASSIGN PRIVATE SERVER NAME
            # ------------------------------------------------

            nickname = member.nick


            if not (
                nickname
                and nickname.startswith("h3x-")
            ):

                new_name = get_next_server_name(
                    guild
                )

                if new_name:

                    try:

                        await member.edit(
                            nick=new_name,
                            reason="h3x.root privacy nickname"
                        )

                        nickname = new_name

                    except discord.Forbidden:

                        nickname = None


            # ------------------------------------------------
            # RESPONSE
            # ------------------------------------------------

            if nickname:

                message = (
                    "✅ **Verification complete!**\n\n"
                    f"Your private server name is **`{nickname}`**.\n\n"
                    "Your server nickname is independent from "
                    "your Discord account ID.\n\n"
                    "The main h3x.root channels are now unlocked."
                )

            else:

                message = (
                    "✅ **Verification complete!**\n\n"
                    "Your Verified role has been assigned.\n\n"
                    "I couldn't change your server nickname. "
                    "Please contact staff."
                )


            await interaction.response.send_message(
                message,
                ephemeral=True
            )


        except discord.Forbidden:

            if not interaction.response.is_done():

                await interaction.response.send_message(
                    "I don't have enough permissions to complete "
                    "verification. Please contact staff.",
                    ephemeral=True
                )


        except Exception as error:

            print(
                f"Verification error: "
                f"{type(error).__name__}: {error}"
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

        # Persistent verification button.
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

async def get_or_create_verified_role(guild):

    role = discord.utils.get(
        guild.roles,
        name=VERIFIED_ROLE
    )

    if role:

        return role


    return await guild.create_role(
        name=VERIFIED_ROLE,
        colour=discord.Colour.green(),
        reason="h3x.root verification setup"
    )


# ============================================================
# STAFF CHECK
# ============================================================

def member_is_staff(member):

    if member.guild_permissions.administrator:

        return True

    return any(
        role.name in STAFF_ROLES
        for role in member.roles
    )


# ============================================================
# START HERE SETUP
# ============================================================

async def setup_start_here(guild):

    everyone = guild.default_role

    verified_role = discord.utils.get(
        guild.roles,
        name=VERIFIED_ROLE
    )


    # --------------------------------------------------------
    # CATEGORY
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


    # New/unverified members can see this category.
    await start.set_permissions(
        everyone,
        view_channel=True,
        send_messages=False,
        read_message_history=True
    )


    if verified_role:

        await start.set_permissions(
            verified_role,
            view_channel=True,
            send_messages=False,
            read_message_history=True
        )


    # --------------------------------------------------------
    # WELCOME
    # --------------------------------------------------------

    welcome = discord.utils.get(
        start.text_channels,
        name=WELCOME_CHANNEL
    )


    if welcome is None:

        welcome = await guild.create_text_channel(
            WELCOME_CHANNEL,
            category=start,
            reason="h3x.root welcome channel"
        )


    await welcome.set_permissions(
        everyone,
        view_channel=True,
        send_messages=False,
        read_message_history=True
    )


    # --------------------------------------------------------
    # RULES
    # --------------------------------------------------------

    rules = discord.utils.get(
        start.text_channels,
        name=RULES_CHANNEL
    )


    if rules is None:

        rules = await guild.create_text_channel(
            RULES_CHANNEL,
            category=start,
            reason="h3x.root rules channel"
        )


    await rules.set_permissions(
        everyone,
        view_channel=True,
        send_messages=False,
        read_message_history=True
    )


    # --------------------------------------------------------
    # VERIFICATION
    # --------------------------------------------------------

    verification = discord.utils.get(
        start.text_channels,
        name=VERIFY_CHANNEL
    )


    if verification is None:

        verification = await guild.create_text_channel(
            VERIFY_CHANNEL,
            category=start,
            reason="h3x.root verification channel"
        )


    await verification.set_permissions(
        everyone,
        view_channel=True,
        send_messages=False,
        read_message_history=True
    )


    if verified_role:

        await verification.set_permissions(
            verified_role,
            view_channel=True,
            send_messages=False,
            read_message_history=True
        )


    # --------------------------------------------------------
    # VERIFICATION PANEL
    # --------------------------------------------------------

    panel_exists = False


    try:

        async for message in verification.history(
            limit=50
        ):

            if (
                bot.user
                and message.author.id == bot.user.id
                and "h3x.root verification" in message.content
            ):

                panel_exists = True

                break

    except discord.Forbidden:

        pass


    if not panel_exists:

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
# MAIN SERVER PERMISSIONS
# ============================================================

async def setup_main_server_permissions(guild):

    everyone = guild.default_role

    verified_role = discord.utils.get(
        guild.roles,
        name=VERIFIED_ROLE
    )


    if verified_role is None:

        verified_role = await get_or_create_verified_role(
            guild
        )


    # --------------------------------------------------------
    # HIDE ALL MAIN CATEGORIES FROM UNVERIFIED USERS
    # --------------------------------------------------------

    for category_name in CONTENT_CATEGORIES:

        category = discord.utils.get(
            guild.categories,
            name=category_name
        )


        if category is None:

            continue


        # Unverified members:
        # completely hidden.
        await category.set_permissions(
            everyone,
            view_channel=False,
            send_messages=False,
            read_message_history=False
        )


        # Verified members:
        # normal access.
        await category.set_permissions(
            verified_role,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            create_public_threads=True,
            embed_links=True,
            attach_files=True,
            add_reactions=True
        )


        # Staff:
        # keep access even when unverified.
        for staff_role_name in STAFF_ROLES:

            staff_role = discord.utils.get(
                guild.roles,
                name=staff_role_name
            )


            if staff_role:

                await category.set_permissions(
                    staff_role,
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )


    print(
        "Main server categories locked until verification."
    )


# ============================================================
# MEMBER LOG SETUP
# ============================================================

async def setup_member_logs(guild):

    everyone = guild.default_role

    verified_role = discord.utils.get(
        guild.roles,
        name=VERIFIED_ROLE
    )


    # --------------------------------------------------------
    # LOG CATEGORY
    # --------------------------------------------------------

    log_category = discord.utils.get(
        guild.categories,
        name=LOG_CATEGORY
    )


    if log_category is None:

        log_category = await guild.create_category(
            LOG_CATEGORY,
            reason="h3x.root member logs"
        )


    # --------------------------------------------------------
    # HIDE CATEGORY FROM EVERYONE
    # --------------------------------------------------------

    await log_category.set_permissions(
        everyone,
        view_channel=False,
        send_messages=False,
        read_message_history=False
    )


    # --------------------------------------------------------
    # STAFF ACCESS
    # --------------------------------------------------------

    for role_name in STAFF_ROLES:

        role = discord.utils.get(
            guild.roles,
            name=role_name
        )

        if role:

            await log_category.set_permissions(
                role,
                view_channel=True,
                send_messages=False,
                read_message_history=True
            )


    # --------------------------------------------------------
    # JOIN LOG
    # --------------------------------------------------------

    join_channel = discord.utils.get(
        log_category.text_channels,
        name=JOIN_LOG_CHANNEL
    )


    if join_channel is None:

        join_channel = await guild.create_text_channel(
            JOIN_LOG_CHANNEL,
            category=log_category,
            reason="h3x.root join logs"
        )


    await join_channel.set_permissions(
        everyone,
        view_channel=False,
        send_messages=False,
        read_message_history=False
    )


    # --------------------------------------------------------
    # LEAVE LOG
    # --------------------------------------------------------

    leave_channel = discord.utils.get(
        log_category.text_channels,
        name=LEAVE_LOG_CHANNEL
    )


    if leave_channel is None:

        leave_channel = await guild.create_text_channel(
            LEAVE_LOG_CHANNEL,
            category=log_category,
            reason="h3x.root leave logs"
        )


    await leave_channel.set_permissions(
        everyone,
        view_channel=False,
        send_messages=False,
        read_message_history=False
    )


    print(
        "Member logs configured."
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
            "ERROR: Server not found. "
            "Check GUILD_ID."
        )

        return


    print(
        f"Connected to: {guild.name}"
    )


    try:

        await get_or_create_verified_role(
            guild
        )

        await setup_start_here(
            guild
        )

        await setup_main_server_permissions(
            guild
        )

        await setup_member_logs(
            guild
        )


        print(
            "=========================================="
        )

        print(
            "h3x.root verification system is ready."
        )

        print(
            "New members see START HERE only."
        )

        print(
            "Verification unlocks the main server."
        )

        print(
            "Sequential names: h3x-A01 -> h3x-Z99"
        )

        print(
            "Member join/leave logging enabled."
        )

        print(
            "=========================================="
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


    guild = member.guild


    # --------------------------------------------------------
    # PRIVATE SERVER NICKNAME
    # --------------------------------------------------------

    try:

        if not (
            member.nick
            and member.nick.startswith("h3x-")
        ):

            nickname = get_next_server_name(
                guild
            )


            if nickname:

                await member.edit(
                    nick=nickname,
                    reason="h3x.root privacy nickname"
                )

                print(
                    f"Assigned {nickname} to member "
                    f"{member.id}"
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


    # --------------------------------------------------------
    # JOIN LOG
    # --------------------------------------------------------

    try:

        log_category = discord.utils.get(
            guild.categories,
            name=LOG_CATEGORY
        )


        if log_category is None:

            return


        channel = discord.utils.get(
            log_category.text_channels,
            name=JOIN_LOG_CHANNEL
        )


        if channel is None:

            return


        embed = discord.Embed(
            title="🟢 Member Joined",
            description=(
                f"**Server name:** "
                f"`{member.nick or 'Not assigned'}`\n\n"
                f"**Account created:** "
                f"<t:{int(member.created_at.timestamp())}:F>\n\n"
                f"**Member count:** "
                f"`{guild.member_count}`"
            ),
            colour=discord.Colour.green(),
            timestamp=discord.utils.utcnow()
        )


        embed.set_footer(
            text="h3x.root member logs"
        )


        await channel.send(
            embed=embed
        )


    except Exception as error:

        print(
            f"Join log error: "
            f"{type(error).__name__}: {error}"
        )


# ============================================================
# MEMBER LEAVE
# ============================================================

@bot.event
async def on_member_remove(member):

    if member.guild.id != GUILD_ID:

        return


    guild = member.guild


    try:

        log_category = discord.utils.get(
            guild.categories,
            name=LOG_CATEGORY
        )


        if log_category is None:

            return


        channel = discord.utils.get(
            log_category.text_channels,
            name=LEAVE_LOG_CHANNEL
        )


        if channel is None:

            return


        embed = discord.Embed(
            title="🔴 Member Left",
            description=(
                f"**Server name:** "
                f"`{member.nick or 'Not assigned'}`\n\n"
                f"**Joined Discord:** "
                f"<t:{int(member.created_at.timestamp())}:F>\n\n"
                f"**Member count:** "
                f"`{guild.member_count}`"
            ),
            colour=discord.Colour.red(),
            timestamp=discord.utils.utcnow()
        )


        embed.set_footer(
            text="h3x.root member logs"
        )


        await channel.send(
            embed=embed
        )


    except Exception as error:

        print(
            f"Leave log error: "
            f"{type(error).__name__}: {error}"
        )


# ============================================================
# RUN
# ============================================================

bot.run(TOKEN)
