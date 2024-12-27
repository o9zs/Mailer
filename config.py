API_ID = 27806506
API_HASH = "c3b39a0ffbcc698afb63319c95e97b61"

invite_link = "https://t.me/+oLvXduZWm0dkMzI0"

responses = []

for emoji in ("🤗💰👾💎"):
	responses.append(f"**Весь ворк тут {emoji}**\nА также конкурсы, призы и многое другое ↙\n\n[https://t.me/t0rtuga_chat]({invite_link})")

messages = []

mail = True
auto_respond = True
forward_from_channel = True

channel_id = 2415085452

message_ids = [22, 23, 25, 31, 40, 42, 43, 44, 45, 52, 53, 54, 55, 56, 57, 58]
per_chat_ids = {}

excluded_chats = [2295959373, 2038629185, 2327726002]
hide_forward_chats = [2091490622, 2315505220]

interval = (300, 600)
read_after = (2, 5)
respond_after = (2, 5)
