import discord
from discord.ext import commands
from discord.ui import View

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DISCORD_BUTTON_CHANNEL = int(os.getenv('DISCORD_BUTTON_CHANNEL_ID'))
DISCORD_LOG_CHANNEL = int(os.getenv('DISCORD_LOG_CHANNEL_ID'))

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix=';;', intents=intents)

button_channel = None
log_channel = None
info_message = None

room_status = {
    'is_locked': True,
    'members': [],
    'switch_count': 1
}

class RoomManagementView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Unlock', style=discord.ButtonStyle.green, row=0)
    async def unlock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if not room_status['is_locked']:
            await interaction.followup.send('すでに解錠されています', ephemeral=True)
        else:
            room_status['is_locked'] = False
            room_status['members'].append(f'<@{interaction.user.id}>')
            await report_to_log(interaction, '🔓 部室を解錠しました', button.label)
            await update_info_message()

    @discord.ui.button(label='Lock', style=discord.ButtonStyle.red, row=0)
    async def lock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if room_status['is_locked']:
            await interaction.followup.send('すでに施錠されています', ephemeral=True)
        else:
            room_status['is_locked'] = True
            room_status['members'].clear()
            await report_to_log(interaction, '🔒 部室を施錠しました', button.label)
            await update_info_message()

    @discord.ui.button(label='Join', style=discord.ButtonStyle.blurple, row=0)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if room_status['is_locked']:
            await interaction.followup.send('部室は施錠されています', ephemeral=True)
            return

        user_mention = f'<@{interaction.user.id}>'
        if user_mention in room_status['members']:
            await interaction.followup.send('すでに入室しています', ephemeral=True)
        else:
            room_status['members'].append(user_mention)
            await update_info_message()

    @discord.ui.button(label='Leave', style=discord.ButtonStyle.gray, row=0)
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        user_mention = f'<@{interaction.user.id}>'
        if user_mention not in room_status['members']:
            await interaction.followup.send('入室していません', ephemeral=True)
        else:
            room_status['members'].remove(user_mention)
            if len(room_status['members']) == 0:
                await send_warning_message(user_mention)
            await update_info_message()

    @discord.ui.button(label='Add Switch', style=discord.ButtonStyle.gray, row=1)
    async def add_switch_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        room_status['switch_count'] += 1
        await update_info_message()

    @discord.ui.button(label='Bring back Switch', style=discord.ButtonStyle.gray, row=1)
    async def bring_back_switch_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if room_status['switch_count'] > 0:
            room_status['switch_count'] -= 1
            await update_info_message()
        else:
            await interaction.followup.send('エラー: Switchがありません', ephemeral=True)


async def update_info_message():
    global info_message, button_channel

    if not button_channel:
        return

    if room_status['members']:
        member_list = '\n'.join(room_status['members'])
        member_count = len(room_status['members'])
        content = f'\n- 現在の利用者:\n{member_list}\n{member_count}名\n'
    else:
        content = '\n- 現在、部室に利用者はいません\n0名\n'

    content += '\n- 部室の開放状況:\n'
    content += '🔒**Locked**' if room_status['is_locked'] else '🔓**Unlocked: 参加可能**'
    content += f"\n\n- Switchの台数: {room_status['switch_count']}"

    if info_message:
        try:
            await info_message.edit(content=content)
        except discord.errors.NotFound:
            info_message = await button_channel.send(content)
    else:
        info_message = await button_channel.send(content)


async def report_to_log(interaction, action_message, button_label):
    if not log_channel:
        return

    embed = discord.Embed(
        description=action_message,
        color=discord.Color.blue()
    )
    embed.set_author(
        name=f'{interaction.user.display_name} used {button_label}',
        icon_url=interaction.user.avatar.url
    )
    await log_channel.send(embed=embed)


async def send_warning_message(user_mention):
    if log_channel:
        await log_channel.send(f'⚠️: {user_mention} 部室を施錠してください！')


@bot.event
async def on_ready():
    global button_channel, log_channel, info_message

    button_channel = bot.get_channel(DISCORD_BUTTON_CHANNEL)
    log_channel = bot.get_channel(DISCORD_LOG_CHANNEL)

    await bot.tree.sync()
    print(f'Logged in as {bot.user}!')

    if log_channel:
        await log_channel.send('デプロイテスト。再起動しました。')
    else:
        print('Error: Log Channel not found.')

    if button_channel:
        await delete_previous_messages(button_channel)
        info_message = await button_channel.send('infoを表示しています...')
        await update_info_message()
        view = RoomManagementView()
        await button_channel.send(view=view)


async def delete_previous_messages(button_channel):
    try:
        messages = []
        async for message in button_channel.history(limit=2):
            messages.append(message)
        for message in messages:
            await message.delete()
    except discord.errors.Forbidden:
        print('AUTHエラー: メッセージを削除する権限がありません。')
    except discord.errors.HTTPException as e:
        print(f'HTTPエラー: メッセージ削除中に問題が発生しました: {e}')

bot.run(BOT_TOKEN)
