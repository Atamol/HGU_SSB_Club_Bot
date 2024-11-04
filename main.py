import discord
from discord.ext import commands
from discord.ui import View
import config  # config.py

TOKEN = os.getenv("TOKEN")
channel_1_id = int(os.getenv("CHANNEL_1_ID"))
channel_2_id = int(os.getenv("CHANNEL_2_ID"))

# intentを有効にする
intents = discord.Intents.default()
intents.members = True               # memberの取得を許可
intents.message_content = True       # messageの取得を許可

# botのインスタンスを作成
bot = commands.Bot(command_prefix=';;', intents=intents)

# statusを保存する辞書
room_status = {
    "is_locked": True,
    "members": [],
    "switch_count": 1
}

# infoを保持する変数
info_message = None

# buttonの設定
class RoomManagementView(View):
    def __init__(self):
        super().__init__(timeout=None)

    # Unlock
    @discord.ui.button(label="Unlock", style=discord.ButtonStyle.green, row=0)
    async def unlock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if not room_status["is_locked"]:
            await interaction.followup.send("すでに解錠されています", ephemeral=True)
        else:
            room_status["is_locked"] = False
            room_status["members"].append(f"<@{interaction.user.id}>")
            await report_to_channel(channel_2_id, interaction, "🔓 部室を解錠しました", button.label)
            await update_info_message(interaction.channel)

    # Lock
    @discord.ui.button(label="Lock", style=discord.ButtonStyle.red, row=0)
    async def lock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if room_status["is_locked"]:
            await interaction.followup.send("すでに施錠されています", ephemeral=True)
        else:
            room_status["is_locked"] = True
            await report_to_channel(channel_2_id, interaction, "🔒 部室を施錠しました", button.label)
            
            # 利用者がいる場合、自動で全員削除（leaveに相当する処理）
            if room_status["members"]:
                room_status["members"].clear()

            await update_info_message(interaction.channel)

    # Join
    @discord.ui.button(label="Join", style=discord.ButtonStyle.blurple, row=0)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if room_status["is_locked"]:
            await interaction.followup.send("部室は施錠されています", ephemeral=True)  # lockedのときはjoinを無効にする
            return

        user_mention = f"<@{interaction.user.id}>"
        if user_mention in room_status["members"]:
            await interaction.followup.send("すでに入室しています", ephemeral=True)
        else:
            room_status["members"].append(user_mention)
            await update_info_message(interaction.channel)

    # Leave
    @discord.ui.button(label="Leave", style=discord.ButtonStyle.gray, row=0)
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        user_mention = f"<@{interaction.user.id}>"
        if user_mention not in room_status["members"]:
            await interaction.followup.send("入室していません", ephemeral=True)
        else:
            room_status["members"].remove(user_mention)
            if len(room_status["members"]) == 0:
                # 通常メッセージで警告を送信
                await send_warning_message(channel_2_id, user_mention)
            await update_info_message(interaction.channel)

    # Add Switch
    @discord.ui.button(label="Add Switch", style=discord.ButtonStyle.gray, row=1)
    async def add_switch_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        room_status["switch_count"] += 1
        await update_info_message(interaction.channel)

    # Bring back Switch
    @discord.ui.button(label="Bring back Switch", style=discord.ButtonStyle.gray, row=1)
    async def bring_back_switch_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if room_status["switch_count"] > 0:
            room_status["switch_count"] -= 1
            await update_info_message(interaction.channel)
        else:
            await interaction.followup.send("エラー: Switchがありません", ephemeral=True)

# infoを更新する関数
async def update_info_message(channel):
    global info_message

    if room_status["members"]:
        member_list = "\n".join(room_status["members"])
        member_count = len(room_status["members"])
        content = f"\n- 現在の利用者:\n{member_list}\n{member_count}名\n"
    else:
        content = "\n- 現在、部室に利用者はいません\n0名\n"

    content += "\n- 部室の開放状況:\n"
    content += "🔒**Locked**" if room_status["is_locked"] else "🔓**Unlocked: 参加可能**"
    content += f"\n\n- Switchの台数: {room_status['switch_count']}"

    if info_message:
        try:
            await info_message.edit(content=content)
        except discord.errors.NotFound:
            # メッセージが見つからなかった場合は再度作成する
            info_message = await channel.send(content)
    else:
        info_message = await channel.send(content)

# チャンネル2に報告を投稿する関数
async def report_to_channel(channel_id, interaction, action_message, button_label):
    channel = bot.get_channel(channel_id)
    if channel:
        embed = discord.Embed(
            description=action_message,
            color=discord.Color.blue()
        )
        embed.set_author(
            name=f"{interaction.user.display_name} used {button_label}",
            icon_url=interaction.user.avatar.url
        )
        await channel.send(embed=embed)

# 通常のメッセージで警告を送信する関数
async def send_warning_message(channel_id, user_mention):
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(f"⚠️: {user_mention} 部室を施錠してください！")

@bot.event
async def on_ready():
    global info_message

    print(f'Logged in as {bot.user}!')

    # チャンネル1を取得してbuttonとinfoを表示
    channel_1 = bot.get_channel(channel_1_id)

    if channel_1:
        # infoを表示
        info_message = await channel_1.send("infoを表示しています...")
        await update_info_message(channel_1)

        # buttonを表示
        view = RoomManagementView()
        await channel_1.send(view=view)

bot.run(TOKEN)
