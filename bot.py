import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import youtube_dl
import instaloader
import requests
import os

# --- Telegram Bot Token from Replit Secrets ---
BOT_TOKEN = os.environ['BOT_TOKEN']
bot = telebot.TeleBot(BOT_TOKEN)

# Ensure downloads folder exists
if not os.path.exists("downloads"):
    os.makedirs("downloads")

# Store user platform selection
user_platform = {}

# --- /start command ---
@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("YouTube", callback_data="yt"))
    markup.add(InlineKeyboardButton("Instagram", callback_data="ig"))
    markup.add(InlineKeyboardButton("TeraBox / WhatsApp", callback_data="tb"))
    bot.send_message(message.chat.id, "👋 Hi! Choose platform to download:", reply_markup=markup)

# --- Button callback ---
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    user_platform[call.from_user.id] = call.data
    bot.send_message(call.message.chat.id, f"✅ You selected: {call.data.upper()}\nNow send me the link.")

# --- Handle incoming messages (links) ---
@bot.message_handler(func=lambda message: True)
def handle_link(message):
    user_id = message.from_user.id
    platform = user_platform.get(user_id)
    if not platform:
        bot.reply_to(message, "⚠️ Please select a platform first using /start.")
        return

    url = message.text.strip()
    bot.reply_to(message, "⏳ Downloading, please wait...")

    try:
        if platform == "yt":
            ydl_opts = {"outtmpl": "downloads/%(title)s.%(ext)s"}
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url)
                filename = ydl.prepare_filename(info)
            bot.send_video(message.chat.id, open(filename, 'rb'))
            os.remove(filename)

        elif platform == "ig":
            L = instaloader.Instaloader(download_videos=True, download_comments=False)
            shortcode = url.split("/")[-2]
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            L.download_post(post, target="downloads")
            video_files = [f for f in os.listdir("downloads") if f.endswith(".mp4")]
            if video_files:
                bot.send_video(message.chat.id, open(f"downloads/{video_files[0]}", 'rb'))
                os.remove(f"downloads/{video_files[0]}")

        elif platform == "tb":
            r = requests.get(url)
            filename = url.split("/")[-1]
            path = f"downloads/{filename}"
            with open(path, "wb") as f:
                f.write(r.content)
            bot.send_document(message.chat.id, open(path, 'rb'))
            os.remove(path)

        else:
            bot.reply_to(message, "❌ Unknown platform selected!")

    except Exception as e:
        bot.reply_to(message, f"❌ Download failed: {e}")

    user_platform.pop(user_id, None)

# --- Run the bot forever ---
bot.infinity_polling()