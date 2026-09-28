import os
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
    raise RuntimeError("Set DISCORD_TOKEN and GUILD_ID in the environment variables.")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


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


def new_server_name(guild):
    """Generate a random server-only nickname unrelated to the Discord ID."""
    alphabet = string.ascii_lowercase + string.digits

    for _ in range(100):
        nickname = "h3x-" + "".join(
            secrets.choice(alphabet) for _ in range(6)
        )

        # Make sure another member isn't currently using it.
        if not discord.utils.get(guild.members, nick=nickname):
            return nickname

    # Extremely unlikely fallback.
    return "h3x-" + secrets.token_hex(4)


class VerifyView(View):
    def __init__(self):
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
            # Give the verified role.
            if role not in member.roles:
                await member.add_roles(
                    role,
                    reason="h3x.root verification",
                )

            nick = None

            # Give a private server nickname if they don't already have one.
            if not (
                member.nick
                and member.nick.startswith("h3x-")
            ):
                nick = new_server_name(guild)

                try:
                    await member.edit(
                        nick=nick,
                        reason="h3x.root privacy nickname",
                    )
                except discord.Forbidden:
                    nick = None

            else:
                nick = member.nick

            if nick:
                text = (
                    "✅ **Verification complete!**\n\n"
                    f"Your private server name is **`{nick}`**.\n\n"
                    "You can now access the h3x.root channels."
                )
            else:
                text = (
                    "✅ **Verification complete!**\n\n"
                    "Your Verified role has been assigned.\n\n"
                    "I couldn't change your server nickname. "
                    "Staff should check the bot's "
                    "**Manage Nicknames** permission and role hierarchy."
                )

            await interaction.response.send_message(
                text,
                ephemeral=True,
            )

        except discord.Forbidden:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "I don't have enough permissions to complete "
                    "verification. Please contact staff.",
                    ephemeral=True,
                )

        except discord.HTTPException as e:
            print(f"Verification HTTP error: {e}")

            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Verification temporarily failed. "
                    "Please try again.",
                    ephemeral=True,
                )

        except Exception as e:
            print(f"Verification error: {type(e).__name__}: {e}")

            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "An unexpected verification error occurred. "
                    "Please contact staff.",
                    ephemeral=True,
                )


class H3xBot(commands.Bot):
    async def setup_hook(self):
        # Persistent button works after bot restarts.
        self.add_view(VerifyView())


bot = H3xBot(
    command_prefix="!",
    intents=intents,
    help_command=None,
)


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

    # START HERE stays visible to everyone.
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

    # Hide content categories from unverified members.
    for category_name in CONTENT_CATEGORIES:
        category = discord.utils.get(
            guild.categories,
            name=category_name,
        )

        if not category:
            continue

        await category.set_permissions(
            everyone,
            view_channel=False,
        )

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

        # Staff retain access.
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

    # Don't create duplicate verification panels.
    found = False

    try:
        async for message in channel.history(limit=50):
            if (
                message.author.id == bot.user.id
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
            "and you will receive a unique server nickname such "
            "as `h3x-a7k2m9`.\n\n"
            "Your server nickname is not your Discord ID and is "
            "generated independently from your account ID.",
            view=VerifyView(),
        )


@bot.event
async def on_ready():
    guild = bot.get_guild(GUILD_ID)

    if guild is None:
        print("ERROR: Server not found. Check GUILD_ID.")
        return

    print(f"Connected to: {guild.name}")

    try:
        await setup_verification_channel(guild)
        await setup_permissions(guild)

        print("h3x.root verification system is ready.")

    except discord.Forbidden as e:
        print(
            "ERROR: Discord permissions are insufficient. "
            f"{e}"
        )

    except Exception as e:
        print(
            f"Setup error: {type(e).__name__}: {e}"
        )


@bot.event
async def on_member_join(member):
    """
    Give new members a random server nickname.

    The nickname is random and does not contain or derive
    the user's Discord ID.
    """

    if member.guild.id != GUILD_ID:
        return

    try:
        if not (
            member.nick
            and member.nick.startswith("h3x-")
        ):
            nick = new_server_name(member.guild)

            await member.edit(
                nick=nick,
                reason="h3x.root privacy nickname",
            )

            print(
                f"Assigned private server name {nick} "
                f"to member {member.id}"
            )

    except discord.Forbidden:
        print(
            "Could not assign join nickname. "
            "Check Manage Nicknames + role hierarchy."
        )

    except discord.HTTPException as e:
        print(
            f"Nickname assignment failed: {e}"
        )


bot.run(TOKEN)
