import asyncio
import os
import random
import sqlite3
import sys

from rich.console import Console

from telethon import TelegramClient, functions, utils
from telethon.events import NewMessage
from telethon.errors import ChannelForumMissingError, ChatRestrictedError, ChatWriteForbiddenError, FloodWaitError, SlowModeWaitError, UserBannedInChannelError, UserDeactivatedBanError, UserDeactivatedError

import config

if len(sys.argv) > 1:
	session = " ".join(sys.argv[1:])

	with open("session.txt", "w") as file:
		file.write(session)

	session = os.path.join(config.sessions, session)
else:
	with open("session.txt", "r") as file:
		session = file.read()

	session = os.path.join(config.sessions, session)

client = TelegramClient(session, config.API_ID, config.API_HASH, system_version="5.9")

console = Console(highlight=False)

def get_random(value):
	if type(value) is tuple:
		value = random.randint(value[0], value[1])

	return value

if config.auto_respond == True:
	cached_ids = []

	@client.on(NewMessage(incoming=True, func=lambda e: e.is_private))
	async def respond(event: NewMessage.Event):
		me = await client.get_me()
		sender = await event.get_sender()

		if sender.bot or sender.id == me.id or sender.id == 777000: return

		if sender.id in cached_ids: return
		cached_ids.append(sender.id)

		await asyncio.sleep(get_random(config.read_after))
		await client.send_read_acknowledge(sender)

		async with client.action(sender, 'typing'):
			await asyncio.sleep(get_random(config.respond_after))
			await client.send_message(sender, random.choice(config.responses), parse_mode="markdown")

		await client.send_read_acknowledge(sender)

		console.log(f"[cyan]Responded to {sender.first_name}[/cyan]")
			
async def send_to_chats():
	me = await client.get_me()

	async for dialog in client.iter_dialogs():
		if dialog.is_group:
			dialog_id, _ = utils.resolve_id(dialog.id)

			if dialog_id in config.excluded_chats: continue
			
			try:
				await client(functions.channels.GetForumTopicsRequest(
					dialog_id,
					0, 0, 0, 1
				))
			except ChannelForumMissingError: pass
			else:
				console.log(f"[yellow]📜 {dialog.name} [gray50](чат содержит темы)[/gray50][/yellow]")

				continue

			try:
				if config.forward_from_channel == True:
					if dialog_id in config.per_chat_ids:
						message_ids = config.per_chat_ids[dialog_id]
					else:
						message_ids = config.message_ids

					await client.forward_messages(
						entity=dialog,
						messages=random.choice(message_ids),
						from_peer=config.channel_id,
						drop_author=dialog_id in config.hide_forward_chats or me.premium
					)
				else:
					await client.send_message(dialog, random.choice(config.messages))

				console.log(f"[chartreuse2]✓ {dialog.name}[/chartreuse2]")
			except ChatRestrictedError:
				await dialog.delete()
			except ChatWriteForbiddenError:
				console.log(f"[yellow]🔇 {dialog.name} [gray50](обеззвучен)[/gray50][/yellow]")
			except FloodWaitError as error:
				console.log(f"[yellow]🌊 {dialog.name} [gray50](флуд, ожидание {error.seconds} секунд)[/gray50][/yellow]")

				await asyncio.sleep(error.seconds)
			except SlowModeWaitError as error:
				console.log(f"[yellow]⏳ {dialog.name} [gray50](слоумоуд, осталось {error.seconds} секунд)[/gray50][/yellow]")
			except UserBannedInChannelError:
				console.log(f"[yellow]🚫 {dialog.name} [gray50](вам запрещено состоять в публичных группах)[/gray50][/yellow]")
			except (UserDeactivatedBanError, UserDeactivatedError) as error:
				console.log(f"[red]✗ Вы забанены![/red]")
			except Exception as exception:
				console.log(f"[red]✗ {dialog.name} [gray50]({exception})[/gray50][/red]")
				
			await asyncio.sleep(get_random(config.message_interval))

async def mail():
	if config.mail == True:
		while True:
			await send_to_chats()

			await asyncio.sleep(get_random(config.loop_interval))

connection = sqlite3.connect(os.path.join(config.sessions, "cache.db"))
cursor = connection.cursor()

cursor.execute("UPDATE cache SET task = ? WHERE session = ?", (config.task, os.path.basename(session)))

connection.commit()
connection.close()

with client:
    client.loop.create_task(mail())
    client.run_until_disconnected()
