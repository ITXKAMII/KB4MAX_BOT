import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from flask import Flask, request, jsonify
import threading
import time

# ⚙️ Aap ki personal configurations yahan set ho gayi hain
BOT_TOKEN = "8541203020:AAFYHBm7u0JpXVye4LiZPDj_1jrIJIRn6jU"      
ADMIN_ID = 8722819202                      
CHANNEL_ID = -1004491994880                
CHANNEL_LINK = "https://t.me/+vTlm7id5gIw4MGZk" 

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Data Structure
STOCK = {"WhatsApp": {}, "Telegram": {}, "Facebook": {}}
DISABLED_COUNTRIES = {"WhatsApp": [], "Telegram": [], "Facebook": []}
LOCKED_NUMBERS = {}  # {number: {"user_id": id, "expire_at": t, "service": s, "country": c}}
ADMIN_STATES = {}    # Admin menu tracking ke liye

SERVICE_ICONS = {
    "WhatsApp": "🟢 WhatsApp",
    "Telegram": "🔹 Telegram",
    "Facebook": "🔵 Facebook"
}

# Bot Menu Commands Set karne ka function
def set_bot_commands():
    try:
        commands = [
            BotCommand("start", "🚀 Open Client Panel (Get Numbers)"),
            BotCommand("admin", "🛠️ Open Admin Panel (Stock & Settings)")
        ]
        bot.set_my_commands(commands)
        print("Bot Menu Commands set successfully!")
    except Exception as e:
        print(f"Error setting commands: {e}")

# 5 Minute ka Timeout Clock (Auto Release System)
def clean_expired_locks():
    while True:
        current_time = time.time()
        expired = [num for num, data in LOCKED_NUMBERS.items() if current_time > data["expire_at"]]
        for num in expired:
            data = LOCKED_NUMBERS[num]
            if data["country"] not in STOCK[data["service"]]:
                STOCK[data["service"]][data["country"]] = []
            STOCK[data["service"]][data["country"]].append(num)
            del LOCKED_NUMBERS[num]
        time.sleep(10)

# --- CLIENT INTERFACE ---

@bot.message_handler(commands=['start'])
def start_handler(message):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🟢 WhatsApp", callback_data="srv_WhatsApp"))
    markup.row(InlineKeyboardButton("🔹 Telegram", callback_data="srv_Telegram"))
    markup.row(InlineKeyboardButton("🔵 Facebook", callback_data="srv_Facebook"))
    
    bot.send_message(
        message.chat.id, 
        "🔥 **Welcome to KB4MAX SMS LIVE ACCESS** ⭐️\n\n💬 Please select the service you want below:", 
        parse_mode="Markdown", 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("srv_"))
def service_select(call):
    bot.answer_callback_query(call.id)
    service = call.data.split("_")[1]
    countries = list(STOCK.get(service, {}).keys())
    
    available_countries = [
        c for c in countries 
        if len(STOCK[service][c]) > 0 and c not in DISABLED_COUNTRIES[service]
    ]
    
    if not available_countries:
        bot.answer_callback_query(call.id, f"❌ Sorry, no active numbers available for {service} right now.", show_alert=True)
        return
        
    markup = InlineKeyboardMarkup()
    for country in available_countries:
        markup.add(InlineKeyboardButton(f"📍 {country}", callback_data=f"get_{service}_{country}"))
        
    bot.edit_message_text(
        f"📱 **Service Selected:** {SERVICE_ICONS[service]}\n\n🌐 Choose available country:",
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("get_"))
def get_number(call):
    bot.answer_callback_query(call.id)
    _, service, country = call.data.split("_")
    
    if country in DISABLED_COUNTRIES[service] or country not in STOCK[service] or not STOCK[service][country]:
        bot.answer_callback_query(call.id, "❌ This country is currently unavailable or out of stock.", show_alert=True)
        return
        
    assigned_number = STOCK[service][country].pop(0)
    
    LOCKED_NUMBERS[assigned_number] = {
        "user_id": call.from_user.id,
        "expire_at": time.time() + 300,
        "service": service,
        "country": country
    }
    
    msg_text = (
        f"⚡ **KB4MAX SMS — Number Assigned**\n\n"
        f"📦 **Service:** {SERVICE_ICONS[service]}\n"
        f"🌐 **Country:** `{country}`\n"
        f"📞 **Number:** `{assigned_number}`\n\n"
        f"⏳ Yeh number aapke liye **5 Minutes** ke liye reserved hai.\n"
        f"📢 Kripya abhi code request karein aur neeche diye gaye button par click karke hamare OTP Channel mein jayein!"
    )
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text=f"📋 Copy: {assigned_number}", callback_data=f"click_copy_{assigned_number}"))
    markup.add(InlineKeyboardButton(text="📢 GET OTP (Go to Channel) ↗️", url=CHANNEL_LINK))
    
    bot.edit_message_text(text=msg_text, chat_id=call.message.chat.id, message_id=call.message.id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("click_copy_"))
def copy_alert(call):
    bot.answer_callback_query(call.id, text="Number copied successfully!", show_alert=False)


# --- FULL ADMIN CONTROL PANEL ---

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        bot.reply_to(message, f"❌ Access denied! Your ID: {message.from_user.id} does not match Admin ID.")
        return
        
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📥 Add Bulk Stock", callback_data="adm_add_stock"))
    markup.row(InlineKeyboardButton("🌍 Manage Countries (On/Off)", callback_data="adm_manage_countries"))
    markup.row(InlineKeyboardButton("📊 Check Live Stock Status", callback_data="adm_check_status"))
    markup.row(InlineKeyboardButton("🧹 Clear All Stock", callback_data="adm_clear_stock"))
    
    bot.send_message(message.chat.id, "🛠️ **KB4MAX SMS — MAIN ADMIN CONTROL PANEL**\n\nWelcome back, Boss. What do you want to manage today?", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_actions(call):
    bot.answer_callback_query(call.id)
    action = call.data.split("_")[1]
    
    if action == "add_stock":
        markup = InlineKeyboardMarkup()
        for srv in SERVICE_ICONS:
            markup.add(InlineKeyboardButton(SERVICE_ICONS[srv], callback_data=f"asrv_{srv}"))
        bot.edit_message_text("📥 Select the **Service** for which you want to upload stock:", chat_id=call.message.chat.id, message_id=call.message.id, reply_markup=markup, parse_mode="Markdown")
        
    elif action == "manage_countries":
        markup = InlineKeyboardMarkup()
        for srv in SERVICE_ICONS:
            markup.add(InlineKeyboardButton(f"Manage {srv}", callback_data=f"mctry_{srv}"))
        bot.edit_message_text("🌍 Select the service to **Enable/Disable** its countries:", chat_id=call.message.chat.id, message_id=call.message.id, reply_markup=markup, parse_mode="Markdown")
        
    elif action == "check_status":
        status_text = "📊 **CURRENT LIVE STOCK STATUS:**\n\n"
        for srv in STOCK:
            status_text += f"🔹 **{srv}:**\n"
            if not STOCK[srv]:
                status_text += "  ↳ No countries added yet.\n"
            for ctry in STOCK[srv]:
                status = "🔴 DISABLED" if ctry in DISABLED_COUNTRIES[srv] else "🟢 ACTIVE"
                status_text += f"  ↳ 📍 {ctry}: `{len(STOCK[srv][ctry])}` numbers [{status}]\n"
        
        status_text += f"\n⏳ **Currently Locked Numbers (Waiting OTP):** `{len(LOCKED_NUMBERS)}`"
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Back to Admin Panel", callback_data="adm_back"))
        bot.edit_message_text(status_text, chat_id=call.message.chat.id, message_id=call.message.id, parse_mode="Markdown", reply_markup=markup)
        
    elif action == "clear_stock":
        for srv in STOCK: STOCK[srv].clear()
        LOCKED_NUMBERS.clear()
        bot.answer_callback_query(call.id, "⚠️ Entire stock database has been wiped clean!", show_alert=True)
        admin_panel(call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("asrv_"))
def admin_stock_service(call):
    bot.answer_callback_query(call.id)
    srv = call.data.split("_")[1]
    ADMIN_STATES[call.from_user.id] = {"action": "wait_country", "service": srv}
    bot.edit_message_text(f"Selected: **{SERVICE_ICONS[srv]}**\n\n✍️ Please Type the **Country Name** (e.g., Pakistan, Algeria) in chat now:", chat_id=call.message.chat.id, message_id=call.message.id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("mctry_"))
def admin_toggle_countries_list(call):
    bot.answer_callback_query(call.id)
    srv = call.data.split("_")[1]
    countries = list(STOCK[srv].keys())
    
    if not countries:
        bot.answer_callback_query(call.id, "No countries found in this service stock.", show_alert=True)
        return
        
    markup = InlineKeyboardMarkup()
    for c in countries:
        status_label = "❌ Off" if c in DISABLED_COUNTRIES[srv] else "✅ On"
        markup.add(InlineKeyboardButton(f"{c} ({status_label})", callback_data=f"tgl_{srv}_{c}"))
    markup.add(InlineKeyboardButton("⬅️ Back", callback_data="adm_back"))
    
    bot.edit_message_text(f"🌍 Toggle Countries for **{srv}**:\n*(Click a button to turn On/Off)*", chat_id=call.message.chat.id, message_id=call.message.id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("tgl_"))
def admin_toggle_country_execute(call):
    bot.answer_callback_query(call.id)
    _, srv, ctry = call.data.split("_")
    if ctry in DISABLED_COUNTRIES[srv]:
        DISABLED_COUNTRIES[srv].remove(ctry)
    else:
        DISABLED_COUNTRIES[srv].append(ctry)
    
    admin_toggle_countries_list(call)

@bot.callback_query_handler(func=lambda call: call.data == "adm_back")
def back_to_admin(call):
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.id)
    
    class FakeMessage:
        def __init__(self, chat_id, from_user):
            self.chat = chat_id
            self.from_user = from_user
    
    fake_msg = FakeMessage(call.message.chat, call.from_user)
    admin_panel(fake_msg)

# Admin Text Input Handler
@bot.message_handler(func=lambda message: message.from_user.id in ADMIN_STATES)
def handle_admin_inputs(message):
    state = ADMIN_STATES[message.from_user.id]
    
    if state["action"] == "wait_country":
        country_name = message.text.strip()
        ADMIN_STATES[message.from_user.id] = {"action": "wait_numbers", "service": state["service"], "country": country_name}
        bot.reply_to(message, f"📍 Country Set to: **{country_name}**\n\n📥 Now send the **Numbers List**.\nFormat: Paste numbers here directly (one number per line) or upload a txt file.")
        
    elif state["action"] == "wait_numbers":
        srv = state["service"]
        ctry = state["country"]
        
        numbers = message.text.strip().splitlines()
        if ctry not in STOCK[srv]:
            STOCK[srv][ctry] = []
            
        added = 0
        for num in numbers:
            num = num.strip()
            if num and num not in STOCK[srv][ctry]:
                STOCK[srv][ctry].append(num)
                added += 1
                
        del ADMIN_STATES[message.from_user.id]
        bot.reply_to(message, f"✅ Done Boss! Successfully added `{added}` new numbers to **{srv} -> {ctry}**.")

# Admin File Input Handler
@bot.message_handler(content_types=['document'], func=lambda message: message.from_user.id in ADMIN_STATES)
def handle_admin_file_input(message):
    state = ADMIN_STATES[message.from_user.id]
    if state["action"] != "wait_numbers": return
    
    srv = state["service"]
    ctry = state["country"]
    
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    lines = downloaded_file.decode("utf-8").splitlines()
    
    if ctry not in STOCK[srv]:
        STOCK[srv][ctry] = []
        
    added = 0
    for num in lines:
        num = num.strip()
        if num and num not in STOCK[srv][ctry]:
            STOCK[srv][ctry].append(num)
            added += 1
            
    del ADMIN_STATES[message.from_user.id]
    bot.reply_to(message, f"✅ File Processed! Successfully added `{added}` new numbers to **{srv} -> {ctry}**.")


# --- FLASK WEBHOOK (TAMPERMONKEY SYNC ROUTE) ---

@app.route('/webhook/otp', methods=['POST'])
def incoming_otp():
    data = request.json
    num = data.get("number")
    otp = data.get("otp")
    full_sms = data.get("full_sms", "")
    
    if num in LOCKED_NUMBERS:
        lock_data = LOCKED_NUMBERS[num]
        service_title = SERVICE_ICONS.get(lock_data['service'], lock_data['service'])
        
        channel_msg = (
            f"⚡ **KB4MAX SMS** ⭐️\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"🆕 **New {service_title} OTP!**\n\n"
            f"📱 **Number:** `{num}`\n"
            f"🔑 **OTP:** `{otp}`\n\n"
            f"💬 **SMS:** `{full_sms}`\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"*BE ACTIVE FOR MORE OTPS* 💖"
        )
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text="📋 COPY CODE", callback_data="click_copy_otp"))
        
        bot.send_message(CHANNEL_ID, channel_msg, parse_mode="Markdown", reply_markup=markup)
        
        del LOCKED_NUMBERS[num]
        return jsonify({"status": "success"}), 200
        
    return jsonify({"status": "ignored"}), 200

def run_flask():
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    set_bot_commands() 
    threading.Thread(target=run_flask).start()
    threading.Thread(target=clean_expired_locks, daemon=True).start()
    print("KB4MAX Premium Bot started...")
    bot.infinity_polling()
