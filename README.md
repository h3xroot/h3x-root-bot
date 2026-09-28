# h3x.root verification bot

This version adds:
- A private verification channel with an **I Agree & Verify** button.
- Verified role assignment.
- Main content categories hidden until verification.
- Random server nicknames such as `h3x-a7k2m9`.
- Nicknames are generated independently and are not based on Discord user IDs.
- Persistent button after bot restarts.

## Discord Developer Portal
Enable **Server Members Intent** under Bot > Privileged Gateway Intents.

The bot needs:
- Manage Roles
- Manage Channels
- Manage Nicknames
- View Channels
- Send Messages
- Read Message History

The bot's role must be above the `Member`/`Verified` roles and above members whose nicknames it needs to change.

## Run
```powershell
py -m pip install -r requirements.txt
py bot.py
```

Important: a server nickname does not make a Discord account anonymous. Server members may still see the account profile/username when interacting with it, and Discord/bots/staff can have access to account identifiers. The nickname only provides a server-specific display name.
