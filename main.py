import telebot
import os
import json
import subprocess
from datetime import datetime, timedelta
from telebot import types
from flask import Flask
from threading import Thread

# --- কনফিগারেশন ---
API_TOKEN = '8991224456:AAGGs571JdZy07FiHfJvaLql8tTLDnnayng'
ADMIN_ID = 8760779092 
DATA_FILE = "tamim_db.json"
HOST_DIR = "user_bots"

if not os.path.exists(HOST_DIR):
    os.makedirs(HOST_DIR)

bot = telebot.TeleBot(API_TOKEN)

# রেন্ডারের Web Service টিকিয়ে রাখার জন্য ফ্লাস্ক সার্ভার
app = Flask('')

@app.route('/')
def home():
    return "Tamim Hosting Bot is Alive!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f: return json.load(f)
    return {}

def save_db(db):
    with open(DATA_FILE, 'w') as f: json.dump(db, f, indent=4)

@bot.message_handler(commands=['start'])
def welcome(message):
    uid = str(message.from_user.id)
    db = load_db()
    
    args = message.text.split()
    if uid not in db:
        db[uid] = {"coins": 5, "active_bots": [], "last_bonus": "", "referred_by": None}
        if len(args) > 1:
            ref_id = args[1]
            if ref_id in db and ref_id != uid:
                db[uid]["referred_by"] = ref_id
                db[ref_id]["coins"] += 3 
                try:
                    bot.send_message(ref_id, "🎉 অভিনন্দন! আপনার রেফারল লিংকের মাধ্যমে একজন নতুন ইউজার যুক্ত হয়েছে এবং আপনি ৩ কয়েন বোনাস পেয়েছেন।")
                except:
                    pass
        save_db(db)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📤 বট আপলোড (হোস্ট)", callback_data="upload_info"),
        types.InlineKeyboardButton("📊 আমার বট ম্যানেজ", callback_data="my_bots"),
        types.InlineKeyboardButton("💎 আমার কয়েন ও প্রফাইল", callback_data="my_coins"),
        types.InlineKeyboardButton("🎁 ডেইলি বোনাস", callback_data="daily_bonus"),
        types.InlineKeyboardButton("🔗 রেফারেল লিংক", callback_data="ref_link"),
        types.InlineKeyboardButton("ℹ️ নির্দেশিকা ও সাহায্য", callback_data="help_info")
    )
    
    welcome_text = (
        f"🔥 **স্বাগতম {message.from_user.first_name} Tamim Hosting প্যানেলে!** 🔥\n\n"
        "এখানে আপনি খুব সহজেই আপনার পাইথন টেলিগ্রাম বট ২৪/৭ ক্লাউডে ফ্রিতে হোস্ট করতে পারবেন। "
        "নিচের অপشنগুলো থেকে আপনার প্রয়োজনীয় কাজ সিলেক্ট করুন:"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = str(call.from_user.id)
    db = load_db()
    
    if call.data == "my_coins":
        coins = db.get(uid, {}).get("coins", 0)
        bots_count = len(db.get(uid, {}).get("active_bots", []))
        text = (
            f"👤 **আপনার প্রফাইল ইনফো:**\n\n"
            f"🆔 ইউজার আইডি: `{uid}`\n"
            f"💰 বর্তমান কয়েন: **{coins}** 💎\n"
            f"🤖 রানিং বট সংখ্যা: **{bots_count}** টি"
        )
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        
    elif call.data == "upload_info":
        bot.send_message(call.message.chat.id, "📁 দয়া করে আপনার পাইথন (`.py`) ফাইলটি সরাসরি এই চ্যাটে সেন্ড করুন। প্রতি বটের জন্য ৩ কয়েন কাটা হবে এবং বট ২৪/৭ সচল থাকবে।")
        
    elif call.data == "my_bots":
        user_bots = db.get(uid, {}).get("active_bots", [])
        if not user_bots:
            bot.answer_callback_query(call.id, "আপনার কোনো রানিং বট নেই!", show_alert=True)
            return
        
        text = "🤖 **আপনার রানিং বটগুলোর তালিকা ও ম্যানেজমেন্ট:**\n\n"
        markup = types.InlineKeyboardMarkup(row_width=2)
        for b in user_bots:
            markup.add(
                types.InlineKeyboardButton(f"🔄 রিস্টার্ট: {b.split('_')[-1]}", callback_data=f"restart_{b}"),
                types.InlineKeyboardButton(f"❌ বন্ধ করুন: {b.split('_')[-1]}", callback_data=f"stop_{b}")
            )
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)
        
    elif call.data.startswith("stop_"):
        bot_name = call.data.replace("stop_", "")
        try:
            subprocess.run(["pm2", "stop", bot_name], stderr=subprocess.DEVNULL)
            subprocess.run(["pm2", "delete", bot_name], stderr=subprocess.DEVNULL)
            if bot_name in db[uid]["active_bots"]:
                db[uid]["active_bots"].remove(bot_name)
                save_db(db)
            bot.answer_callback_query(call.id, "বট সফলভাবে বন্ধ ও ডিলিট করা হয়েছে!", show_alert=True)
            bot.edit_message_text("✅ এই বটটি বন্ধ এবং সার্ভার থেকে রিমুভ করা হয়েছে।", call.message.chat.id, call.message.message_id)
        except Exception as e:
            bot.answer_callback_query(call.id, f"এরর: {str(e)}", show_alert=True)

    elif call.data.startswith("restart_"):
        bot_name = call.data.replace("restart_", "")
        try:
            subprocess.run(["pm2", "restart", bot_name], stderr=subprocess.DEVNULL)
            bot.answer_callback_query(call.id, "সফলভাবে বট রিস্টার্ট করা হয়েছে!", show_alert=True)
        except Exception as e:
            bot.answer_callback_query(call.id, f"রিস্টার্ট করতে সমস্যা হয়েছে!", show_alert=True)
            
    elif call.data == "daily_bonus":
        today = str(datetime.now().date())
        if db[uid].get("last_bonus") == today:
            bot.answer_callback_query(call.id, "❌ আপনি আজ ইতিমধ্যে ডেইলি বোনাস নিয়ে নিয়েছেন! আগামিকাল আবার চেষ্টা করুন।", show_alert=True)
        else:
            db[uid]["coins"] += 2
            db[uid]["last_bonus"] = today
            save_db(db)
            bot.answer_callback_query(call.id, "🎁 অভিনন্দন! আপনি ডেইলি বোনাস হিসেবে ২ কয়েন পেয়েছেন।", show_alert=True)

    elif call.data == "ref_link":
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={uid}"
        text = (
            f"🔗 **আপনার রেফারেল লিংক:**\n\n"
            f"`{ref_link}`\n\n"
            "এই লিংকটি আপনার বন্ধুদের শেয়ার করুন। কেউ এই লিংকে ক্লিক করে বট স্টার্ট করলে আপনি **৩ কয়েন** ফ্রি পাবেন!"
        )
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

    elif call.data == "help_info":
        help_text = (
            "📖 **সহায়িকা ও নিয়মাবলী:**\n\n"
            "১. শুধুমাত্র পাইথন (`.py`) ফাইল আপলোড করতে পারবেন।\n"
            "২. প্রতিবার ফাইল হোস্ট করতে ৩ কয়েন কাটবে।\n"
            "৩. ডেইলি বোনাস থেকে প্রতিদিন ২ কয়েন ফ্রিতে নিতে পারবেন।\n"
            "৪. বন্ধুদের রেফার করে কয়েন ইনকাম করতে পারবেন।\n"
            "৫. কোনো সমস্যা হলে অ্যাডমিনের সাথে যোগাযোগ করুন।"
        )
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(content_types=['document'])
def handle_file(message):
    uid = str(message.from_user.id)
    db = load_db()
    
    if uid not in db:
        db[uid] = {"coins": 5, "active_bots": [], "last_bonus": ""}
        
    user_coins = db[uid].get("coins", 0)
    if user_coins < 3:
        bot.reply_to(message, "❌ আপনার পর্যাপ্ত কয়েন নেই! হোস্টিংয়ের জন্য অন্তত ৩ কয়েন লাগবে। ডেইলি বোনাস নিন অথবা রেফার করুন।")
        return

    if not message.document.file_name.endswith('.py'):
        bot.reply_to(message, "⚠️ শুধুমাত্র পাইথন (.py) ফাইল সাপোর্ট করে। অন্য কোনো ফাইল পাঠানো যাবে না।")
        return

    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_name = f"{uid}_{message.document.file_name}"
        file_path = os.path.join(HOST_DIR, file_name)
        
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        
        process_name = f"bot_{uid}_{message.document.file_name}"
        
        subprocess.run(["pm2", "delete", process_name], stderr=subprocess.DEVNULL)
        subprocess.run(["pm2", "start", file_path, "--name", process_name, "--interpreter", "python3"])
        
        db[uid]["coins"] -= 3
        if "active_bots" not in db[uid]: db[uid]["active_bots"] = []
        if process_name not in db[uid]["active_bots"]:
            db[uid]["active_bots"].append(process_name)
        save_db(db)
        
        bot.reply_to(message, f"✅ **{message.document.file_name}** সফলভাবে ক্লাউডে হোস্ট হয়েছে!\n💸 ৩ কয়েন কাটা হয়েছে।\n📊 বট ম্যানেজ করতে /start মেনু ব্যবহার করুন।", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ এরর দেখা দিয়েছে: {str(e)}")

@bot.message_handler(commands=['add'])
def add_coins(message):
    if message.from_user.id == ADMIN_ID:
        try:
            _, tid, amt = message.text.split()
            db = load_db()
            if tid not in db: db[tid] = {"coins": 0, "active_bots": [], "last_bonus": ""}
            db[tid]["coins"] += int(amt)
            save_db(db)
            bot.reply_to(message, f"✅ ইউজার `{tid}` কে সফলভাবে `{amt}` কয়েন দেওয়া হয়েছে।", parse_mode="Markdown")
            try:
                bot.send_message(tid, f"🎉 অ্যাডমিন আপনাকে `{amt}` কয়েন উপহার দিয়েছেন!")
            except:
                pass
        except:
            bot.reply_to(message, "ভুল নিয়ম! ব্যবহার করুন: `/add ID Amount`", parse_mode="Markdown")

if __name__ == '__main__':
    # ফ্লাস্ক সার্ভার ব্যাকগ্রাউন্ডে রান করা
    t = Thread(target=run_flask)
    t.start()
    # টেলিগ্রাম বট পোলিং শুরু করা
    bot.infinity_polling()
