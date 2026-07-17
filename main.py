import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request, jsonify
import threading
import time

BOT_TOKEN = "8541203020:AAFYHBm7u0JpXVye4LiZPDj_1jrIJIRn6jU"  # ⚠️ Apna Bot Token yahan dalein
ADMIN_ID = 8722819202                # ⚠️ Apni Telegram User ID yahan dalein
CHANNEL_ID = -1004491994880            # ⚠️ Apne Channel ki ID yahan dalein

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# System Data Storage
# Format: {"WhatsApp": {"Pakistan": ["+923001234567"]}}
STOCK = {"WhatsApp": {}, "Telegram": {}, "Facebook": {}}
LOCKED_NUMBERS = {}  # Tracking: {number: {"user_id": id, "expire_at": timestamp, "service": s, "country": c}}

SERVICE_ICONS = {
    "WhatsApp": "🟢 WhatsApp",
    "Telegram": "🔹 Telegram",
    "Facebook": "🔵 Facebook"
}

# Helper: Clean Expired Numbers
def clean_expired_locks():
    while True:
        current_time = time.time()
        expired = [num for num, data in LOCKED_NUMBERS.items() if current_time > data["expire_at"]]
        for num in expired:
            data = LOCKED_NUMBERS[num]
            # Put back to stock
            if data["country"] not in STOCK[data["service"]]:
                STOCK[data["service"]][data["country"]] = []
            STOCK[data["service"]][data["country"]].append(num)
            del LOCKED_NUMBERS[num]
        time.sleep(10)

# --- TELEGRAM BOT LOGIC ---

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
    service = call.data.split("_")[1]
    countries = list(STOCK.get(service, {}).keys())
    
    # Only show countries that have active numbers in stock
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
    _, service, country = call.data.split("_")
    
    if country not in STOCK[service] or not STOCK[service][country]:
        bot.answer_callback_query(call.id, "❌ Stock just ran out! Try another country.", show_alert=True)
        return
        
    # Get 1 number and remove from available stock
    assigned_number = STOCK[service][country].pop(0)
    
    # Lock for 5 minutes (300 seconds)
    LOCKED_NUMBERS[assigned_number] = {
        "user_id": call.from_user.id,
        "expire_at": time.time() + 300,
        "service": service,
        "country": country
    }
    
    msg_text = (
        f"⚡ **KB4MAX SMS — Assigned Number**\n\n"
        f"📦 **Service:** {SERVICE_ICONS[service]}\n"
        f"📞 **Number:** `{assigned_number}`\n\n"
        f"⏳ This number is reserved for you for **5 Minutes**.\n"
        f"📢 Please request OTP now! Check our channel for updates."
    )
    
    # Direct click to copy number structure
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text=f"📋 Copy: {assigned_number}", callback_data=f"click_copy_{assigned_number}"))
    markup.add(InlineKeyboardButton(text="📱 Go to OTP Channel ↗️", url="https://t.me/your_channel_username"))
    
    bot.edit_message_text(text=msg_text, chat_id=call.message.chat.id, message_id=call.message.id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("click_copy_"))
def copy_alert(call):
    bot.answer_callback_query(call.id, text="Number copied to clipboard successfully!", show_alert=False)

# Admin Bulk Upload File Handler
@bot.message_handler(content_types=['document'])
def handle_stock_file(message):
    if message.from_user.id != ADMIN_ID: return
    
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    # File content processing line by line
    lines = downloaded_file.decode("utf-8").splitlines()
    count = 0
    
    for line in lines:
        if ',' in line:
            try:
                srv, cntry, num = [x.strip() for x in line.split(',')]
                if srv in STOCK:
                    if cntry not in STOCK[srv]:
                        STOCK[srv][cntry] = []
                    if num not in STOCK[srv][cntry]:
                        STOCK[srv][cntry].append(num)
                        count += 1
            except:
                continue
                
    bot.reply_to(message, f"✅ Successfully added {count} numbers to the stock system!")

# --- FLASK WEBHOOK ROUTE FOR TAMPERMONKEY ---

@app.route('/webhook/otp', methods=['POST'])
def incoming_otp():
    data = request.json
    num = data.get("number")
    otp = data.get("otp")
    full_sms = data.get("full_sms", "")
    
    if num in LOCKED_NUMBERS:
        lock_data = LOCKED_NUMBERS[num]
        service_title = SERVICE_ICONS.get(lock_data['service'], lock_data['service'])
        
        # Exact Short Format Layout
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
        
        # Remove from active lock completely so it cannot be reused
        del LOCKED_NUMBERS[num]
        return jsonify({"status": "success"}), 200
        
    return jsonify({"status": "ignored", "reason": "Number not locked or expired"}), 200

def run_flask():
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    threading.Thread(target=clean_expired_locks, daemon=True).start()
    print("Bot is polling...")
    bot.infinity_polling()
