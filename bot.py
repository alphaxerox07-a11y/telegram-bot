import telebot
from telebot import types
import threading
import time
from datetime import datetime
from pymongo import MongoClient
from keep_alive import keep_alive

# ==========================================
# 🔑 TUMHARI KEYS AUR IDs
# ==========================================
BOT_TOKEN = '8950867900:AAEc32AGBj4U6At3uvSSp379s1I8zix6YX0'
GROUP_ID = -1003668562553  # Yahan apne group ka ID daalo
INVITE_LINK = 'https://t.me/+l4NpDNT_cdUyZDNl'
ADMIN_ID = 1927388197

# 🗄️ MONGODB CONNECTION
MONGO_URL = "mongodb+srv://alphaxerox07_db_user:7053610990@cluster0.2nbabsq.mongodb.net/?appName=Cluster0"

bot = telebot.TeleBot(BOT_TOKEN)

# MongoDB Setup
client = MongoClient(MONGO_URL)
db = client['jee_bot_db']
menus_col = db['menus']
msgs_col = db['messages']
users_col = db['users']

# Agar Main Menu nahi hai toh bana do
if not menus_col.find_one({"_id": "🏠 Main Menu"}):
  menus_col.insert_one({"_id": "🏠 Main Menu", "buttons": []})

temp_state = {}
user_spam_dict = {}
SPAM_COOLDOWN = 4
DELETE_TIME = 20 * 60

# ==========================================
# 🧹 AUTO-DELETE GROUP JOIN/SERVICE MESSAGES
# ==========================================


@bot.message_handler(
    content_types=[
        'new_chat_members',
        'left_chat_member',
        'new_chat_title',
        'new_chat_photo',
        'delete_chat_photo',
    ]
)
def delete_system_messages(message):
  try:
    bot.delete_message(message.chat.id, message.message_id)
  except Exception:
    pass


def delete_later(chat_id, message_id, delay):

  def do_delete():
    try:
      bot.delete_message(chat_id, message_id)
    except Exception:
      pass

  threading.Timer(delay, do_delete).start()


def check_membership(user_id):
  try:
    member = bot.get_chat_member(GROUP_ID, user_id)
    return member.status in ['member', 'administrator', 'creator']
  except Exception:
    return False


# ==========================================
# 👑 PRO ADMIN PANEL & MANAGEMENT
# ==========================================


@bot.message_handler(commands=['totalusers'])
def count_users(message):
  if message.from_user.id != ADMIN_ID:
    return
  total = users_col.count_documents({})
  bot.reply_to(
      message,
      f"📊 **Bot Analytics:**\nTotal {total} students ne bot start kiya hai!",
      parse_mode="Markdown",
  )


@bot.message_handler(commands=['admin'])
def admin_panel(message):
  if message.from_user.id != ADMIN_ID:
    return
  markup = types.InlineKeyboardMarkup(row_width=2)
  markup.add(
      types.InlineKeyboardButton("➕ Add Button", callback_data="admin_add"),
      types.InlineKeyboardButton("➖ Delete Button", callback_data="admin_del_btn"),
      types.InlineKeyboardButton("🗑️ Factory Reset", callback_data="admin_del"),
  )
  bot.reply_to(
      message,
      "⚙️ **PRO Admin Panel**\nKya manage karna hai?",
      reply_markup=markup,
      parse_mode="Markdown",
  )


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def handle_admin(call):
  chat_id = call.message.chat.id
  if call.data == "admin_add":
    markup = types.InlineKeyboardMarkup(row_width=1)
    for menu in menus_col.find():
      markup.add(
          types.InlineKeyboardButton(
              f"📁 Add in: {menu['_id']}", callback_data=f"loc_{menu['_id']}"
          )
      )
    bot.send_message(
        chat_id, "Naya button kahan lagana hai?", reply_markup=markup
    )

  elif call.data == "admin_del_btn":
    markup = types.InlineKeyboardMarkup(row_width=1)
    for menu in menus_col.find():
      if menu["buttons"]:  #jisme buttons hon
        markup.add(
           types.InlineKeyboardButton(
                f"📁 Menu: {menu['_id']}",
                callback_data=f"delmenu_{menu['_id']}",
            )
        )
    bot.send_message(
        chat_id,
        "🗑️ Kis menu me se button delete karna hai select karo:",
        reply_markup=markup,
    )

  elif call.data == "admin_del":
    menus_col.delete_many({})
    msgs_col.delete_many({})
    menus_col.insert_one({"_id": "🏠 Main Menu", "buttons": []})
    bot.send_message(
        chat_id, "🗑️ Sab kuch delete ho gaya! Wapas /start dabao."
    )


# Single Button Deletion Selectors
@bot.callback_query_handler(func=lambda call: call.data.startswith('delmenu_'))
def select_btn_to_delete(call):
  menu_name = call.data.replace('delmenu_', '')
  menu_doc = menus_col.find_one({"_id": menu_name})
  markup = types.InlineKeyboardMarkup(row_width=1)
  if menu_doc and menu_doc.get("buttons"):
    for btn in menu_doc["buttons"]:
      markup.add(
          types.InlineKeyboardButton(
              f"❌ Delete: {btn}", callback_data=f"rmbtn_{menu_name}_{btn}"
          )
      )
    bot.edit_message_text(
        f"🗑️ Menu **{menu_name}** ke kis button ko udana hai?",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode="Markdown",
    )
  else:
    bot.answer_callback_query(call.id, "Is menu me koi button nahi hai!")


@bot.callback_query_handler(func=lambda call: call.data.startswith('rmbtn_'))
def execute_btn_deletion(call):
  data = call.data.replace('rmbtn_', '')
  # Menu name aur button name alag karna (pehla underscore ke baad menu, baaki button)
  parts = data.split('_', 1)
  menu_name = parts[0]
  btn_name = parts[1]

  # Database se button hatao
  menus_col.update_one(
      {"_id": menu_name}, {"$pull": {"buttons": btn_name}}
  )
  msgs_col.delete_one({"_id": btn_name})
  # Agar yeh khud ek sub-menu folder tha toh use bhi uda do
  menus_col.delete_one({"_id": btn_name})

  bot.edit_message_text(
      f"✅ Success! Button **'{btn_name}'** ko hamesha ke liye uda diya gaya hai.",
      call.message.chat.id,
      call.message.message_id,
      parse_mode="Markdown",
  )


@bot.callback_query_handler(func=lambda call: call.data.startswith('loc_'))
def ask_btn_name(call):
  parent_menu = call.data.replace('loc_', '')
  msg = bot.send_message(
      call.message.chat.id,
      f"✅ Location: **{parent_menu}**\n\nAb naye button ka NAAM likho:",
      parse_mode="Markdown",
  )
  bot.register_next_step_handler(msg, ask_btn_type, parent_menu)


def ask_btn_type(message, parent_menu):
  btn_name = message.text.strip()
  temp_state[message.chat.id] = {"parent": parent_menu, "btn": btn_name}
  markup = types.InlineKeyboardMarkup(row_width=2)
  markup.add(
      types.InlineKeyboardButton(
          "📁 Sub-Menu (Folder)", callback_data="type_folder"
      ),
      types.InlineKeyboardButton("📝 PDF / Photo / Msg", callback_data="type_msg"),
  )
  bot.send_message(
      message.chat.id,
      f"Button **'{btn_name}'** me kya hoga?",
      reply_markup=markup,
      parse_mode="Markdown",
  )


@bot.callback_query_handler(func=lambda call: call.data in ['type_folder', 'type_msg'])
def process_btn_type(call):
  chat_id = call.message.chat.id
  if chat_id not in temp_state:
    return bot.answer_callback_query(call.id, "Error! Wapas /admin dabao.")

  parent_menu = temp_state[chat_id]["parent"]
  btn_name = temp_state[chat_id]["btn"]

  menus_col.update_one({"_id": parent_menu}, {"$addToSet": {"buttons": btn_name}})

  if call.data == "type_folder":
    if not menus_col.find_one({"_id": btn_name}):
      menus_col.insert_one({"_id": btn_name, "buttons": []})
    bot.edit_message_text(
        f"🎉 Folder **'{btn_name}'** MongoDB me ban gaya!",
        chat_id,
        call.message.message_id,
        parse_mode="Markdown",
    )
    del temp_state[chat_id]
  elif call.data == "type_msg":
    msg = bot.send_message(
        chat_id,
        f"📝 Ab tum **Text, Photo, ya PDF File** bhejo jo **'{btn_name}'** par"
        " jayegi:",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(msg, save_media_msg, btn_name)


def save_media_msg(message, btn_name):
  chat_id = message.chat.id
  msg_data = {"_id": btn_name}
  if message.document:
    msg_data.update({
        "type": "document",
        "file_id": message.document.file_id,
        "caption": message.caption or "",
    })
  elif message.photo:
    msg_data.update({
        "type": "photo",
        "file_id": message.photo[-1].file_id,
        "caption": message.caption or "",
    })
  elif message.video:
    msg_data.update({
        "type": "video",
        "file_id": message.video.file_id,
        "caption": message.caption or "",
    })
  else:
    msg_data.update({"type": "text", "text": message.text or ""})

  msgs_col.update_one({"_id": btn_name}, {"$set": msg_data}, upsert=True)
  if chat_id in temp_state:
    del temp_state[chat_id]

  bot.send_message(
      chat_id, f"🎉 Success! Data MongoDB me save ho gaya.", parse_mode="Markdown"
  )

  # 🚀 BROADCAST SYSTEM: Sabhi users ko DM me update bhejna
  markup = types.InlineKeyboardMarkup()
  markup.add(
      types.InlineKeyboardButton(
          "🚀 Bot Kholo & Padho", url=f"https://t.me/{bot.get_me().username}"
      )
  )

  all_users = users_col.find({})
  success_count = 0
  for user in all_users:
    try:
      bot.send_message(
          user["_id"],
          f"🔔 **NEW CHAPTER ADDED!**\n\n📚 Naya material **'{btn_name}'** upload"
          " kar diya gaya hai study vault me. Jaldi se jaakar check karo!",
          reply_markup=markup,
          parse_mode="Markdown",
      )
      success_count += 1
      time.sleep(0.1)  # Telegram API flood limit se bachne ke liye chota pause
    except Exception:
      pass

  bot.send_message(
      chat_id,
      f"📢 Broadcast Complete! Total {success_count} students ko DM update"
      " bhej diya gaya hai.",
      parse_mode="Markdown",
  )


# ==========================================
# 🚀 USER SYSTEM (Classic UI & Timestamp)
# ==========================================
def get_menu_markup(menu_name):
  markup = types.InlineKeyboardMarkup(row_width=2)
  menu_doc = menus_col.find_one({"_id": menu_name})
  buttons = menu_doc.get("buttons", []) if menu_doc else []

  btns = [
      types.InlineKeyboardButton(btn, callback_data=f"nav_{btn}")
      for btn in buttons
  ]
  markup.add(*btns)

  if menu_name != "🏠 Main Menu":
    markup.add(
        types.InlineKeyboardButton(
            "🔙 Back", callback_data="nav_🏠 Main Menu"
        )
    )
  markup.add(types.InlineKeyboardButton("💬 Join Discussion Group", url=INVITE_LINK))
  return markup


def get_menu_text(menu_name):
  return f"📚 **JEE 2027 STUDY VAULT**\n➖➖➖➖➖➖➖➖➖➖\n📂 **Location:** {menu_name}\n\n👇 *Neeche se option select karein:*"


@bot.message_handler(commands=['start'])
def send_welcome(message):
  user = message.from_user
  user_id = user.id
  chat_id = message.chat.id

  first_name = user.first_name if user.first_name else "No Name"
  username = f"@{user.username}" if user.username else "No Username"
  current_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

  # MongoDB me Naam, Username aur Exact Date/Time save karna
  users_col.update_one(
      {"_id": user_id},
      {
          "$setOnInsert": {"joined_date": current_time},
          "$set": {
              "joined": True,
              "name": first_name,
              "username": username,
          },
      },
      upsert=True,
  )

  if check_membership(user_id):
    bot.send_message(
        chat_id,
        get_menu_text("🏠 Main Menu"),
        reply_markup=get_menu_markup("🏠 Main Menu"),
        parse_mode="Markdown",
    )
  else:
    warn_msg = bot.reply_to(
        message,
        f"❌ Bot use karne ke liye group join karo!\n👉 Join Here:"
        f" {INVITE_LINK}\n\n*(⏳ Ye message 1 minute me auto-delete ho jayega)*",
        parse_mode="Markdown",
    )
    delete_later(chat_id, warn_msg.message_id, 60)
    delete_later(chat_id, message.message_id, 60)


@bot.callback_query_handler(func=lambda call: call.data.startswith('nav_'))
def handle_nav(call):
  user_id = call.from_user.id
  current_time = time.time()
  if user_id in user_spam_dict:
    if (current_time - user_spam_dict[user_id]) < SPAM_COOLDOWN:
      bot.answer_callback_query(
          call.id, "⚠️ Bhai aaram se! 4 second wait karo.", show_alert=True
      )
      return
  user_spam_dict[user_id] = current_time

  btn_name = call.data.replace('nav_', '')

  if menus_col.find_one({"_id": btn_name}):
    try:
      bot.edit_message_text(
          get_menu_text(btn_name),
          call.message.chat.id,
          call.message.message_id,
          reply_markup=get_menu_markup(btn_name),
          parse_mode="Markdown",
      )
    except Exception:
      bot.answer_callback_query(call.id, "Pehle se yahi menu khula hai!")
  else:
    msg_data = msgs_col.find_one({"_id": btn_name})
    if msg_data:
      bot.answer_callback_query(call.id, "⏳ File aa rahi hai...")
      chat_id = call.message.chat.id
      sent_msg = None

      if msg_data["type"] == "document":
        sent_msg = bot.send_document(
            chat_id, msg_data["file_id"], caption=msg_data["caption"]
        )
      elif msg_data["type"] == "photo":
        sent_msg = bot.send_photo(
            chat_id, msg_data["file_id"], caption=msg_data["caption"]
        )
      elif msg_data["type"] == "video":
        sent_msg = bot.send_video(
            chat_id, msg_data["file_id"], caption=msg_data["caption"]
        )
      else:
        sent_msg = bot.send_message(chat_id, msg_data["text"])

      if sent_msg:
        warning_msg = bot.send_message(
            chat_id,
            "⏳ *Ye file 20 minute me auto-delete ho jayegi! Forward kar"
            " lo.*",
            parse_mode="Markdown",
        )
        delete_later(chat_id, sent_msg.message_id, DELETE_TIME)
        delete_later(chat_id, warning_msg.message_id, DELETE_TIME)
    else:
      bot.answer_callback_query(call.id, "⚠️ File abhi upload nahi hui hai!")


print("🚀 MONGO-DB WALA PRO MAX BOT ZINDA HAI! ...")
keep_alive()
bot.infinity_polling()