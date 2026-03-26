import asyncio
import discord
from discord.ext import commands

from config import DISCORD_TOKEN, GUILD_ID
import db


class BrawlBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await db.init_db()
        await self.load_extension("cogs.tracker")
        await self.load_extension("cogs.pics")

        # Sync slash commands (guild-scoped for faster updates during dev)
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")


async def main():
    bot = BrawlBot()
    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
