import asyncio
import python_socks
import random

from rich.console import Console

from telethon import TelegramClient, utils
from telethon.events import NewMessage

import config

if config.proxy:
	proxy = config.proxy

	auth = proxy.split("@")[0]
	host = proxy.split("@")[1]

	username = auth.split(":")[0]
	password = auth.split(":")[1]

	ip = host.split(":")[0]
	port = host.split(":")[1]

	proxy = {
		"proxy_type": python_socks.ProxyType.SOCKS5,
		"addr": ip,
		"port": int(port),
		"username": username,
		"password": password
	}
else:
	proxy = None

client = TelegramClient("telethon", config.API_ID, config.API_HASH, system_version="5.10.3", proxy=proxy)

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
	async for dialog in client.iter_dialogs():
		if dialog.is_group:
			dialog_id, _ = utils.resolve_id(dialog.id)

			if dialog_id in config.excluded_chats: continue

			try:
				if config.forward_from_channel == True:
					if dialog_id in config.per_chat_ids:
						message_ids = config.per_chat_ids[dialog_id]
					else:
						message_ids = config.message_ids

					await client.forward_messages(
						entity=dialog,
						messages=random.choice(message_ids),
						from_peer=2415085452,
						drop_author=dialog_id in config.hide_forward_chats
					)
				else:
					await client.send_message(dialog, random.choice(config.messages))

				console.log(f"[chartreuse2]✓ {dialog.name}[/chartreuse2]")
			except Exception as exception:
				if type(exception) == ValueError:
					exception_name = "ValueError... Did you join the channel you're forwarding from? Try sending a message there"
				else:
					exception_name = exception.__class__.__name__
					console.log(f"[red]✗ {dialog.name} [gray50]({exception_name})[/gray50][/red]")

				continue
				
			await asyncio.sleep(2)

async def mail():
	if config.mail == True:
		while True:
			await send_to_chats()

			await asyncio.sleep(get_random(config.interval))

with client:
    client.loop.create_task(mail())
    client.loop.run_forever()
