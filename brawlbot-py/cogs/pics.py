from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks

import db
from config import PIC_ADMIN_ID, PIC_STORAGE_CHANNEL_ID, PIC_CHANNEL_ID
from views import PicLibraryView


EST = ZoneInfo("America/New_York")


class PicsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_posted_date: str | None = None

    async def cog_load(self):
        self.daily_pic_check.start()

    async def cog_unload(self):
        self.daily_pic_check.cancel()

    # ── Permission check ──

    async def _check_pic_perm(self, interaction: discord.Interaction) -> bool:
        uid = str(interaction.user.id)
        if uid == PIC_ADMIN_ID:
            return True
        return await db.is_allowed_user(uid)

    # ── Autocomplete helpers ──

    async def _pic_name_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        names = await db.get_all_pic_names()
        filtered = [n["name"] for n in names if current.lower() in n["name"]][:25]
        return [app_commands.Choice(name=n, value=n) for n in filtered]

    async def _pic_name_and_alias_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        real_names = [n["name"] for n in await db.get_all_pic_names()]
        aliases = await db.get_all_aliases()
        all_names = list(set(real_names + aliases))
        filtered = [n for n in all_names if current.lower() in n][:25]
        return [app_commands.Choice(name=n, value=n) for n in filtered]

    # ── /pic (named "chink" in original) ──

    @app_commands.command(name="pic", description="Post a random picture by name")
    @app_commands.describe(name="The name to look up")
    @app_commands.autocomplete(name=_pic_name_autocomplete)
    async def pic(self, interaction: discord.Interaction, name: str):
        if not await self._check_pic_perm(interaction):
            await interaction.response.send_message(
                "\u274c You do not have permission to use this command.", ephemeral=True
            )
            return

        await interaction.response.defer()
        pic = await db.get_random_pic_by_name(name)

        if not pic:
            await interaction.followup.send(f"\u274c No pictures found for **{name}**.")
            return

        embed = discord.Embed(color=0xF5A623, title=pic["name"])
        embed.set_image(url=pic["image_url"])
        await interaction.followup.send(embed=embed)

    # ── /picadd (named "chinkadd" in original) ──

    @app_commands.command(name="picadd", description="Add pictures to the library (up to 5 at once)")
    @app_commands.describe(
        name="The name/category for these pictures",
        image1="Image 1", image2="Image 2", image3="Image 3",
        image4="Image 4", image5="Image 5",
    )
    @app_commands.autocomplete(name=_pic_name_autocomplete)
    async def picadd(
        self,
        interaction: discord.Interaction,
        name: str,
        image1: discord.Attachment,
        image2: discord.Attachment | None = None,
        image3: discord.Attachment | None = None,
        image4: discord.Attachment | None = None,
        image5: discord.Attachment | None = None,
    ):
        await interaction.response.defer(ephemeral=True)

        if not await self._check_pic_perm(interaction):
            await interaction.followup.send("\u274c You do not have permission to use this command.", ephemeral=True)
            return

        attachments = [a for a in [image1, image2, image3, image4, image5] if a is not None]

        # Validate all are images
        non_images = [a for a in attachments if not a.content_type or not a.content_type.startswith("image/")]
        if non_images:
            await interaction.followup.send("\u274c All files must be images (png, jpg, gif, etc.).", ephemeral=True)
            return

        if not PIC_STORAGE_CHANNEL_ID:
            await interaction.followup.send("\u274c PIC_STORAGE_CHANNEL_ID is not configured.", ephemeral=True)
            return

        storage_channel = self.bot.get_channel(int(PIC_STORAGE_CHANNEL_ID))
        if not storage_channel:
            try:
                storage_channel = await self.bot.fetch_channel(int(PIC_STORAGE_CHANNEL_ID))
            except Exception:
                await interaction.followup.send("\u274c Could not access the storage channel.", ephemeral=True)
                return

        try:
            added = 0
            for attachment in attachments:
                # Download and re-upload to storage channel for permanent URL
                file_bytes = await attachment.read()
                file_name = attachment.filename or "image.png"

                storage_msg = await storage_channel.send(
                    file=discord.File(fp=__import__("io").BytesIO(file_bytes), filename=file_name)
                )
                permanent_url = storage_msg.attachments[0].url
                await db.add_pic(name, permanent_url, str(interaction.user.id))
                added += 1

            pics = await db.get_pics_by_name(name)
            count = len(pics)

            embed = discord.Embed(
                color=0x57F287,
                title=f"\u2705 {added} Picture{'s' if added > 1 else ''} Added",
                description=f"Added to **{name}** ({count} total)",
            )
            embed.set_footer(text=f"Added by {interaction.user.name}")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"Error in /picadd: {e}")
            await interaction.followup.send("\u274c Failed to upload images. Try again.", ephemeral=True)

    # ── /piclibrary ──

    @app_commands.command(name="piclibrary", description="Browse or manage the picture library")
    @app_commands.describe(name="Filter to a specific name (omit to see all names)")
    @app_commands.autocomplete(name=_pic_name_autocomplete)
    async def piclibrary(self, interaction: discord.Interaction, name: str | None = None):
        await interaction.response.defer(ephemeral=True)

        if not await self._check_pic_perm(interaction):
            await interaction.followup.send("\u274c You do not have permission to use this command.", ephemeral=True)
            return

        if not name:
            # Summary view
            names = await db.get_all_pic_names()
            if not names:
                await interaction.followup.send(
                    "The library is empty. Use `/picadd` to add pictures.", ephemeral=True
                )
                return

            lines = [f"**{n['name']}** \u2014 {n['count']} pic{'s' if n['count'] != 1 else ''}" for n in names]
            embed = discord.Embed(color=0x00C8FF, title="Picture Library", description="\n".join(lines))
            embed.set_footer(text="Use /piclibrary name:<name> to browse a specific set")
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            # Detail view with pagination
            pics = list(await db.get_pics_by_name(name))
            if not pics:
                await interaction.followup.send(f"No pictures found for **{name}**.", ephemeral=True)
                return

            view = PicLibraryView(pics, name, interaction.user.id)
            await interaction.followup.send(embed=view.build_embed(), view=view, ephemeral=True)

    # ── /cotd ──

    @app_commands.command(name="cotd", description="Show today's Pic of the Day")
    async def cotd(self, interaction: discord.Interaction):
        await interaction.response.defer()

        today = datetime.now(EST).strftime("%Y-%m-%d")
        daily = await db.get_daily_pic(today)

        if not daily:
            pic = await db.get_random_pic()
            if not pic:
                await interaction.followup.send("The picture library is empty. No Pic of the Day yet.")
                return
            await db.set_daily_pic(today, pic["id"])
            daily = await db.get_daily_pic(today)

        embed = discord.Embed(color=0xF5A623, title="Pic of the Day")
        embed.description = f"**{daily['name']}**"
        embed.set_image(url=daily["image_url"])
        embed.set_footer(text=today)
        await interaction.followup.send(embed=embed)

    # ── /merge ──

    @app_commands.command(name="merge", description="Add an alias so another name points to an existing library")
    @app_commands.describe(alias="The new name (alias)", target="The existing library name to point to")
    @app_commands.autocomplete(target=_pic_name_autocomplete)
    async def merge(self, interaction: discord.Interaction, alias: str, target: str):
        await interaction.response.defer(ephemeral=True)

        if not await self._check_pic_perm(interaction):
            await interaction.followup.send("\u274c You do not have permission to use this command.", ephemeral=True)
            return

        alias_lower = alias.lower()
        target_lower = target.lower()

        if alias_lower == target_lower:
            await interaction.followup.send("\u274c Alias and target cannot be the same.", ephemeral=True)
            return

        count = await db.count_pics_by_name(target_lower)
        if count == 0:
            await interaction.followup.send(f"\u274c No library found for **{target}**.", ephemeral=True)
            return

        await db.add_alias(alias_lower, target_lower)

        embed = discord.Embed(
            color=0x57F287,
            title="\u2705 Alias Created",
            description=f"**{alias_lower}** now points to **{target_lower}**'s library ({count} pics)",
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /remove ──

    @app_commands.command(name="remove", description="Remove an alias or delete all pics under a name")
    @app_commands.describe(name="The alias or library name to remove")
    @app_commands.autocomplete(name=_pic_name_and_alias_autocomplete)
    async def remove(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)

        if not await self._check_pic_perm(interaction):
            await interaction.followup.send("\u274c You do not have permission to use this command.", ephemeral=True)
            return

        name_lower = name.lower()

        # Check if it's an alias
        alias_row = await db.get_alias(name_lower)
        if alias_row:
            await db.delete_alias(name_lower)
            embed = discord.Embed(
                color=0xED4245,
                title="\U0001f5d1\ufe0f Alias Removed",
                description=f"**{name_lower}** no longer points to **{alias_row['target']}**.",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Otherwise check if it's a real library
        count = await db.count_pics_by_name(name_lower)
        if count == 0:
            await interaction.followup.send(f"\u274c No library or alias found for **{name_lower}**.", ephemeral=True)
            return

        deleted = await db.delete_pics_by_name(name_lower)
        await db.delete_aliases_for_target(name_lower)

        embed = discord.Embed(
            color=0xED4245,
            title="\U0001f5d1\ufe0f Library Deleted",
            description=f"Deleted **{deleted}** picture{'s' if deleted != 1 else ''} from **{name_lower}**.",
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /picuser (named "chinkuser" in original) ──

    @app_commands.command(name="picuser", description="Manage allowed users for pic commands")
    @app_commands.describe(action="What to do", user="The user to add or remove")
    @app_commands.choices(action=[
        app_commands.Choice(name="add", value="add"),
        app_commands.Choice(name="remove", value="remove"),
        app_commands.Choice(name="list", value="list"),
    ])
    async def picuser(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        user: discord.User | None = None,
    ):
        await interaction.response.defer(ephemeral=True)

        if str(interaction.user.id) != PIC_ADMIN_ID:
            await interaction.followup.send("\u274c Only the bot owner can manage pic users.", ephemeral=True)
            return

        if action.value == "list":
            users = await db.get_all_allowed_users()
            if not users:
                await interaction.followup.send("No allowed users. Only the admin has access.", ephemeral=True)
                return

            user_list = "\n".join(f"<@{u['user_id']}>" for u in users)
            embed = discord.Embed(color=0x00C8FF, title="Allowed Pic Users", description=user_list)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if not user:
            await interaction.followup.send("\u274c You must specify a user to add or remove.", ephemeral=True)
            return

        if action.value == "add":
            await db.add_allowed_user(str(user.id), str(interaction.user.id))
            await interaction.followup.send(f"\u2705 <@{user.id}> can now use pic commands.", ephemeral=True)
        elif action.value == "remove":
            await db.remove_allowed_user(str(user.id))
            await interaction.followup.send(f"\u2705 <@{user.id}> has been removed from pic access.", ephemeral=True)

    # ── Daily Pic Task ──

    @tasks.loop(seconds=60)
    async def daily_pic_check(self):
        try:
            now = datetime.now(EST)
            today = now.strftime("%Y-%m-%d")

            if self._last_posted_date == today:
                return

            existing = await db.get_daily_pic(today)
            if existing:
                self._last_posted_date = today
                return

            if now.hour != 0:
                return

            pic = await db.get_random_pic()
            if not pic:
                return

            await db.set_daily_pic(today, pic["id"])
            self._last_posted_date = today

            if not PIC_CHANNEL_ID:
                return

            channel = self.bot.get_channel(int(PIC_CHANNEL_ID))
            if not channel:
                try:
                    channel = await self.bot.fetch_channel(int(PIC_CHANNEL_ID))
                except Exception:
                    return

            embed = discord.Embed(color=0xF5A623, title="Pic of the Day")
            embed.description = f"**{pic['name']}**"
            embed.set_image(url=pic["image_url"])
            embed.set_footer(text=today)
            embed.timestamp = datetime.now(EST)

            await channel.send(embed=embed)
            print(f"\U0001f5bc\ufe0f Daily pic posted: {pic['name']} (id {pic['id']})")
        except Exception as e:
            print(f"Error in daily pic check: {e}")

    @daily_pic_check.before_loop
    async def before_daily_pic(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(PicsCog(bot))
