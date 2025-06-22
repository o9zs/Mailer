import asyncio
import os
import random
import re
import sqlite3
import sys
from datetime import datetime, timedelta

from rich.console import Console

from telethon import TelegramClient, functions, utils
from telethon.events import NewMessage
from telethon.errors import AuthKeyError, ChannelPrivateError, ChatGuestSendForbiddenError, ChatRestrictedError, ChatWriteForbiddenError, FloodWaitError, MsgIdInvalidError, RPCError, SlowModeWaitError, UserBannedInChannelError, UserDeactivatedBanError, UserDeactivatedError
from telethon.types import InputMessagesFilterPinned, PeerChannel, User

import config

if len(sys.argv) > 1:
	session = " ".join(sys.argv[1:]).strip()

	with open("session.txt", "w") as file:
		file.write(session)

	session = os.path.join(config.sessions, session)
else:
	with open("session.txt", "r") as file:
		session = file.read().strip()

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

		console.log(f"[cyan]Responded to [bold white]{sender.first_name}[/bold white][/cyan]")

	@client.on(NewMessage(outgoing=True, func=lambda e: e.chat.is_self))
	async def cache(event: NewMessage.Event):
		me = await client.get_me()

		if event.raw_text.startswith(".cache "):
			user = event.raw_text.split()[1]

			try:
				user_id = int(user)
			except ValueError:
				if user.startswith("@"):
					user = user[1:]
				elif user.startswith(("https://t.me/", "t.me/")):
					user = user.replace("https://t.me/", "").replace("t.me/", "")
				else:
					return await client.edit_message(event.chat, event.message, "❌ Unrecognized input")

				user = await client.get_entity(user)

				if not isinstance(user, User):
					return await client.edit_message(event.chat, event.message, "❌ Not a user")
				
				user_id = user.id

			if user_id in cached_ids:
					return await client.edit_message(event.chat, event.message, "❌ Already cached")

			cached_ids.append(user_id)

			text = f"✅ Successfully cached user {user_id}"
			
			if isinstance(user, User):
				text += " " + "("

				if user.username:
					text += f"@{user.username}"
				else:
					text += user.first_name

					if user.last_name:
						text += " " + user.last_name

				text += ")"

			return await client.edit_message(event.chat, event.message, text)

if config.comment_in_channels == True:
	@client.on(NewMessage(incoming=True, func=lambda e: e.is_channel and e.chat and e.chat.broadcast))
	async def comment(event: NewMessage.Event):
		try:
			if config.forward_from_channel == True:
				message = await client.get_messages(config.channel_id, ids=random.choice(config.message_ids))

				await client.send_message(
					event.chat,
					message.raw_text,
					comment_to=event.message.id,
					formatting_entities=message.entities
				)
			else:
				await client.send_message(
					event.chat,
					random.choice(config.messages),
					comment_to=event.message.id
				)
		except AuthKeyError as error:
			if error.message == "ALLOW_PAYMENT_REQUIRED":
				return
			else:
				raise
		except (ChatGuestSendForbiddenError, MsgIdInvalidError):
			return
		except RPCError as error:
			console.log(f"[red]❌ RPCError while commenting: {error}[/red]")

			return

		console.log(f"[cyan]🧻 Commented on post [bold white]#{event.message.id}[/bold white] in channel [bold white]{event.chat.title}[/bold white][/cyan]")
			
async def send_to_chats():
	last_check = 0
	last_messages = await client.get_messages("SpamBot", 1)

	if last_messages:
		last_check = last_messages[0].date

		if type(last_check) != datetime: last_check = None

	if last_check and datetime.now(last_check.tzinfo) - last_check >= timedelta(minutes=15):
		async with client.conversation("@SpamBot") as conversation:
			await conversation.send_message("/start")

			response = await conversation.get_response()
			await conversation.mark_read()

		if "Ограничения будут автоматически сняты" in response.text:
			spamblock = "до " + re.search(
				r"Ограничения будут автоматически сняты (.*?) \(по московскому времени — на три часа позже\)",
				response.text
			).group(1)
		elif "Your account will be automatically released" in response.text:
			spamblock = "до " + re.search(
				r"Your account will be automatically released on (.*?)\. Please note that if you repeat what got you limited and users report you again",
				response.text
			).group(1)
		elif "К сожалению, иногда наша антиспам-система излишне сурово реагирует на некоторые действия" in response.text or "Unfortunately, some actions can trigger a harsh response from our anti-spam systems" in response.text:
			spamblock = "вечный"
		elif "Ваш аккаунт свободен" in response.text or "You’re free as a bird" in response.text:
			spamblock = "отсутствует"

		connection = sqlite3.connect(os.path.join(config.sessions, "cache.db"))
		cursor = connection.cursor()

		cursor.execute("UPDATE cache SET spamblock = ? WHERE session = ?", (spamblock, os.path.basename(session)))

		connection.commit()
		connection.close()

		console.log(f"🛢️ Cached spamblock status: {spamblock}")

	me = await client.get_me()

	async for dialog in client.iter_dialogs():
		if dialog.is_group:
			dialog_id, _ = utils.resolve_id(dialog.id)

			if dialog_id in config.excluded_chats: continue

			if dialog_id not in config.non_discussion_groups:
				pinned_messages = await client.get_messages(dialog_id, limit=3, filter=InputMessagesFilterPinned)

				if any([isinstance(pinned_message.from_id, PeerChannel) for pinned_message in pinned_messages]):
					config.excluded_chats.append(dialog_id)

					continue
				else:
					config.non_discussion_groups.append(dialog_id)
			
			try:
				await client(functions.channels.GetForumTopicsRequest(
					dialog_id,
					0, 0, 0, 1
				))
			except:
				pass
			else:
				console.log(f"[yellow]📜 {dialog.name} [gray50](чат содержит темы)[/gray50][/yellow]")

				continue

			reply_to = None

			if config.random_reply:
				try:
					async for message in client.iter_messages(dialog, 3):
						sender = await message.get_sender()

						try:
							if sender and not sender.bot:
								reply_to = message
						except AttributeError:
							continue
				except RPCError as error:
					console.log(f"[red]❌ RPCError while randomly replying: {error}[/red]")

			try:
				if config.forward_from_channel == True:
					if dialog_id in config.per_chat_ids:
						message_ids = config.per_chat_ids[dialog_id]
					else:
						message_ids = config.message_ids

					if dialog_id in config.hide_forward_chats or config.force_hide_forward or me.premium:
						message = await client.get_messages(config.channel_id, ids=random.choice(message_ids))

						await client.send_message(
							dialog,
							message.raw_text,
							formatting_entities=message.entities,
							reply_to=reply_to
						)
					else:
						await client.forward_messages(
							entity=dialog,
							messages=random.choice(message_ids),
							from_peer=config.channel_id
						)
				else:
					await client.send_message(
						dialog,
						random.choice(config.messages),
						reply_to=reply_to
					)

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
	if config.comment_in_channels == True:
		async for dialog in client.iter_dialogs():
			if dialog.is_channel and dialog.entity.broadcast:
				me = await client.get_me()
				
				try:
					async for message in client.iter_messages(dialog, reply_to=dialog.message.id, reverse=True):
						sender = await message.get_sender()

						if sender == None:
							continue

						if sender.id == me.id:
							break
					else:
						try:
							if config.forward_from_channel == True:
								message = await client.get_messages(config.channel_id, ids=random.choice(config.message_ids))

								await client.send_message(
									dialog,
									message.raw_text,
									comment_to=dialog.message.id,
									formatting_entities=dialog.message.entities
								)
							else:
								await client.send_message(
									dialog,
									random.choice(config.messages),
									comment_to=dialog.message.id
								)
						except AuthKeyError as error:
							if error.message == "ALLOW_PAYMENT_REQUIRED":
								continue
							else:
								raise
						except ChatGuestSendForbiddenError:
							continue
						except RPCError as error:
							console.log(f"[red]❌ RPCError while commenting: {error} [gray50](post-fire)[/gray50][/red]")

							continue

						console.log(f"[cyan]🧻 Commented on post [bold white]#{dialog.message.id}[/bold white] in channel [bold white]{dialog.name}[/bold white][/cyan] [gray50](post-fire)[/gray50]")
				except MsgIdInvalidError:
					pass

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
	console.log(f"Running on [bold]{session}[/bold]")
	
	client.loop.create_task(mail())
	client.run_until_disconnected()
