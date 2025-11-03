from datetime import datetime

# Temporary in-memory chat storage (no files!)
chats = {}

def create_chat(title):
    chat_id = str(len(chats) + 1)
    chats[chat_id] = {"title": title, "messages": [], "created": datetime.now()}
    return chat_id

def add_message(chat_id, role, text):
    if chat_id in chats:
        chats[chat_id]["messages"].append({"role": role, "text": text})

def get_chat(chat_id):
    return chats.get(chat_id, {})

def delete_chat(chat_id):
    if chat_id in chats:
        del chats[chat_id]

def rename_chat(chat_id, new_title):
    if chat_id in chats:
        chats[chat_id]["title"] = new_title
