import telebot
from keep_alive import keep_alive
from telebot import types
import json
import os
import threading  # Timer ke liye naya tool

# ==========================================
# 🛠️ TERA MAIN SETUP
# ==========================================
BOT_TOKEN = '8950867900:AAEc32AGBj4U6At3uvSSp379s1I8zix6YX0'  
GROUP_ID = -1003668562553  
INVITE_LINK = 'https://t.me/+NAYA_LINK_YAHAN_DAAL'
ADMIN_ID = 1927388197  

bot = telebot.TeleBot(BOT_TOKEN)
DB_FILE = 'bot_pro_db.json'
temp_state = {}

# Kitne minute me delete karna hai? (20 minutes = 20 * 60 seconds)
# Testing ke liye tu isko 60 rakh kar (1 minute) check kar sakta hai
DELETE_TIME = 60 

# ==========================================
# 💣 AUTO-DELETE SYSTEM (Background Timer)
# ==========================================
def delete_later(chat_id, message_id, delay):
    def do_delete():
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass # Agar user ne pehle hi khud delete kar di toh error na aaye
    
    # Background me timer chalu kar diya
    threading.Timer(delay, do_delete).start()

# ==========================================
# 💾 SMART DATABASE FUNCTIONS
# ==========================================
def load_db():
    if not os.path.exists(DB_FILE):
        return {"menus": {"🏠 Main Menu": []}, "messages": {}}
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def check_membership(user_id):
    try:
        member = bot.get_chat_member(GROUP_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

# ==========================================
# 👑 PRO ADMIN PANEL
# ==========================================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add Button", callback_data="admin_add"),
        types.InlineKeyboardButton("🗑️ Factory Reset", callback_data="admin_del")
    )
    bot.reply_to(message, "⚙️ **PRO Admin Panel**\nKya karna hai?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def handle_admin(call):
    db = load_db()
    if call.data == "admin_add":
        markup = types.InlineKeyboardMarkup(row_width=1)
        for menu_name in db["menus"].keys():
            markup.add(types.InlineKeyboardButton(f"📁 Add in: {menu_name}", callback_data=f"loc_{menu_name}"))
        bot.send_message(call.message.chat.id, "Naya button kahan lagana hai?", reply_markup=markup)
    elif call.data == "admin_del":
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        bot.send_message(call.message.chat.id, "🗑️ Sab kuch delete ho gaya! Wapas /start dabao.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('loc_'))
def ask_btn_name(call):
    parent_menu = call.data.replace('loc_', '')
    msg = bot.send_message(call.message.chat.id, f"✅ Location: **{parent_menu}**\n\nAb naye button ka NAAM likho:")
    bot.register_next_step_handler(msg, ask_btn_type, parent_menu)

def ask_btn_type(message, parent_menu):
    btn_name = message.text.strip()
    temp_state[message.chat.id] = {"parent": parent_menu, "btn": btn_name}
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📁 Sub-Menu (Folder)", callback_data="type_folder"),
        types.InlineKeyboardButton("📝 PDF / Photo / Msg", callback_data="type_msg")
    )
    bot.send_message(message.chat.id, f"Button **'{btn_name}'** me kya hoga?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ['type_folder', 'type_msg'])
def process_btn_type(call):
    chat_id = call.message.chat.id
    if chat_id not in temp_state: return bot.answer_callback_query(call.id, "Error! Wapas /admin dabao.")
        
    parent_menu = temp_state[chat_id]["parent"]
    btn_name = temp_state[chat_id]["btn"]
    db = load_db()
    
    if btn_name not in db["menus"][parent_menu]:
        db["menus"][parent_menu].append(btn_name)
        save_db(db)

    if call.data == "type_folder":
        if btn_name not in db["menus"]: db["menus"][btn_name] = []
        save_db(db)
        bot.edit_message_text(f"🎉 Folder **'{btn_name}'** ban gaya!", chat_id, call.message.message_id)
        del temp_state[chat_id]
    elif call.data == "type_msg":
        msg = bot.send_message(chat_id, f"📝 Ab tum **Text, Photo, ya PDF File** bhejo jo **'{btn_name}'** par jayegi:")
        bot.register_next_step_handler(msg, save_media_msg, btn_name)

def save_media_msg(message, btn_name):
    db = load_db()
    chat_id = message.chat.id
    if message.document:
        db["messages"][btn_name] = {"type": "document", "file_id": message.document.file_id, "caption": message.caption or ""}
    elif message.photo:
        db["messages"][btn_name] = {"type": "photo", "file_id": message.photo[-1].file_id, "caption": message.caption or ""}
    elif message.video:
        db["messages"][btn_name] = {"type": "video", "file_id": message.video.file_id, "caption": message.caption or ""}
    else:
        db["messages"][btn_name] = {"type": "text", "text": message.text or ""}
        
    save_db(db)
    if chat_id in temp_state: del temp_state[chat_id]
    bot.send_message(chat_id, f"🎉 Success! Data save ho gaya.")

# ==========================================
# 🚀 USER SYSTEM WTH TIMER
# ==========================================
def render_menu(chat_id, menu_name, text="Options select karein:"):
    db = load_db()
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [types.InlineKeyboardButton(btn, callback_data=f"nav_{btn}") for btn in db["menus"].get(menu_name, [])]
    if buttons: markup.add(*buttons)
    if menu_name != "🏠 Main Menu":
        markup.add(types.InlineKeyboardButton("🔙 Back to Main Menu", callback_data="nav_🏠 Main Menu"))
    markup.add(types.InlineKeyboardButton("💬 Main Group", url=INVITE_LINK))
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if check_membership(message.from_user.id):
        bot.reply_to(message, f"Welcome {message.from_user.first_name}! 🎉")
        render_menu(message.chat.id, "🏠 Main Menu")
    else:
        bot.reply_to(message, f"❌ Bhai, bot use karne ke liye group join karo!\n👉 Join Here: {INVITE_LINK}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('nav_'))
def handle_nav(call):
    btn_name = call.data.replace('nav_', '')
    db = load_db()
    
    if btn_name in db["menus"]:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        render_menu(call.message.chat.id, btn_name, f"📂 **{btn_name}** khul gaya:")
    
    elif btn_name in db["messages"]:
        bot.answer_callback_query(call.id)
        msg_data = db["messages"][btn_name]
        chat_id = call.message.chat.id
        
        sent_msg = None
        
        # FIle bhej rahe hain aur usko track kar rahe hain
        if isinstance(msg_data, dict):
            if msg_data["type"] == "document":
                sent_msg = bot.send_document(chat_id, msg_data["file_id"], caption=msg_data["caption"])
            elif msg_data["type"] == "photo":
                sent_msg = bot.send_photo(chat_id, msg_data["file_id"], caption=msg_data["caption"])
            elif msg_data["type"] == "video":
                sent_msg = bot.send_video(chat_id, msg_data["file_id"], caption=msg_data["caption"])
            else:
                sent_msg = bot.send_message(chat_id, msg_data["text"])
        
        # Agar message successfully gaya, toh Timer laga do
        if sent_msg:
            # Ek warning bhej rahe hain user ko
            warning_msg = bot.send_message(chat_id, "⏳ *Ye file 20 minute me auto-delete ho jayegi!*", parse_mode="Markdown")
            
            # Timer Set (File aur Warning message dono delete honge 20 min baad)
            delete_later(chat_id, sent_msg.message_id, DELETE_TIME)
            delete_later(chat_id, warning_msg.message_id, DELETE_TIME)

print("🚀 TIMER WALA BOT ZINDA HAI! ...")
keep_alive()
bot.infinity_polling()