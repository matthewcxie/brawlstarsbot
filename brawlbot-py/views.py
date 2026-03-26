import discord

import db


class PicLibraryView(discord.ui.View):
    def __init__(self, pics: list, name: str, user_id: int):
        super().__init__(timeout=120)
        self.pics = pics
        self.name = name
        self.page = 0
        self.user_id = user_id
        self._update_buttons()

    def _update_buttons(self):
        self.prev_btn.disabled = self.page == 0
        self.next_btn.disabled = self.page >= len(self.pics) - 1

    def build_embed(self) -> discord.Embed:
        pic = self.pics[self.page]
        embed = discord.Embed(
            color=0xF5A623,
            title=f"{self.name} \u2014 #{self.page + 1} of {len(self.pics)}",
        )
        embed.set_image(url=pic["image_url"])
        embed.set_footer(text=f"ID: {pic['id']}")
        return embed

    @discord.ui.button(label="\u25c0 Prev", style=discord.ButtonStyle.secondary, custom_id="pic_prev")
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
        self.page = max(0, self.page - 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next \u25b6", style=discord.ButtonStyle.secondary, custom_id="pic_next")
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
        self.page = min(len(self.pics) - 1, self.page + 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, custom_id="pic_delete")
    async def delete_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return

        deleted = self.pics[self.page]
        await db.remove_pic(deleted["id"])
        self.pics = list(await db.get_pics_by_name(self.name))

        if not self.pics:
            embed = discord.Embed(
                color=0xED4245,
                description=f"Deleted the last picture for **{self.name}**.",
            )
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
            return

        self.page = min(self.page, len(self.pics) - 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
