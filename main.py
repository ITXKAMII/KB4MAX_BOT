import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request, jsonify
import threading
import time

# ⚙️ Aap ki personal configurations (Naya Token Updated)
BOT_TOKEN = "8810988814:AAHO3XR7oXC7MaW2EzClTc_AVwSDnEowKS8"      
ADMIN_ID = 8722819202                      
CHANNEL_ID = -1004491994880                
CHANNEL_LINK = "https://t.me/+vTlm7id5gIw4MGZk" 

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Data Structure
STOCK = {"WhatsApp": {}, "Telegram": {}, "Facebook": {}}
LOCKED_NUMBERS = {}  # {number: {"user_id": id, "expire_at": t, "service": s, "country": c}}

SERVICE_ICONS = {
    "WhatsApp": "🟢 WhatsApp",
    "Telegram": "🔹 Telegram",
    "Facebook": "🔵 Facebook"
}

# 5 Minute Auto Release System
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
    
    available_countries = [c for c in countries if len(STOCK[service][c]) > 0]
    
    if not available_countries:
        bot.answer_callback_query(call.id, f"❌ Sorry, no numbers available for {service} right now.", show_alert=True)
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
    
    if country not in STOCK[service] or not STOCK[service][country]:
        bot.answer_callback_query(call.id, "❌ Out of stock.", show_alert=True)
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
    bot.answer_callback_query(call.id, text="Number copied!", show_alert=False)


# --- EASY ADMIN COMMANDS ---

@bot.message_handler(commands=['addstock'])
def add_stock_command(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Access Denied.")
        return
    
    try:
        parts = message.text.split(maxsplit=3)
        if len(parts) < 4:
            bot.reply_to(message, "💡 **Format:** `/addstock <Service> <Country> <Number>`\nExample: `/addstock WhatsApp Pakistan +923001234567`", parse_mode="Markdown")
            return
            
        service = parts[1].strip()
        country = parts[2].strip()
        number = parts[3].strip()
        
        if service not in STOCK:
            bot.reply_to(message, "❌ Invalid Service. Choose: WhatsApp, Telegram, or Facebook.")
            return
            
        if country not in STOCK[service]:
            STOCK[service][country] = []
            
        STOCK[service][country].append(number)
        bot.reply_to(message, f"✅ Added successfully to **{service} ({country})**: `{number}`", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

@bot.message_handler(commands=['checkstock'])
def check_stock_command(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Access Denied.")
        return
        
    status = "📊 **CURRENT LIVE STOCK:**\n\n"
    for srv in STOCK:
        status += f"🔹 **{srv}:**\n"
        if not STOCK[srv]:
            status += "  ↳ Empty\n"
        for ctry in STOCK[srv]:
            status += f"  ↳ 📍 {ctry}: `{len(STOCK[srv][ctry])}` numbers\n"
    bot.reply_to(message, status, parse_mode="Markdown")


# --- FLASK WEBHOOK (TAMPERMONKEY RECEIVER) ---

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
        
        bot.send_message(CHANNEL_ID, channel_msg, parse_mode="Markdown")
        del LOCKED_NUMBERS[num]
        return jsonify({"status": "success"}), 200
        
    return jsonify({"status": "ignored"}), 200

def run_flask():
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    threading.Thread(target=clean_expired_locks, daemon=True).start()
    print("KB4MAX Safe Admin Bot started...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
