import os
import asyncio
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import yt_dlp
import aiohttp

BOT_TOKEN = "8386912250:AAHWppIHrXHpG8lQuZ7l3xkO4AjMUkIkhZg"  # <-- Replace with your token
adult_confirmed_users = set()

# -----------------------------
# Async download/stream function
# -----------------------------
async def download_and_send(url: str, chat_id, context):
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, "%(title)s.%(ext)s")

    ydl_opts = {
        'outtmpl': output_path,
        'format': 'best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
    }

    try:
        # Adult site detection
        adult_sites = ["pornhub.com", "xvideos.com", "xhamster.com", "xnxx.com"]
        if any(site in url for site in adult_sites) and chat_id not in adult_confirmed_users:
            keyboard = [[InlineKeyboardButton("✅ Confirm 18+", callback_data="confirm_adult")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id=chat_id,
                                           text="⚠️ Adult content detected. Confirm you are 18+ to download.",
                                           reply_markup=reply_markup)
            return

        # Use yt-dlp to extract info
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            size = info.get('filesize') or info.get('filesize_approx') or 0
            title = info.get('title', 'video')

            if size > 500 * 1024 * 1024:  # 500 MB limit
                await context.bot.send_message(chat_id=chat_id,
                                               text=f"Video too large. Download directly: {info.get('webpage_url', url)}")
                return

            # Download file
            ydl.download([url])
            files = os.listdir(temp_dir)
            if files:
                video_file = os.path.join(temp_dir, files[0])
                await context.bot.send_chat_action(chat_id=chat_id, action="upload_video")
                await context.bot.send_video(chat_id=chat_id, video=open(video_file, 'rb'))
                return

        await context.bot.send_message(chat_id=chat_id, text=f"❌ Cannot download video from this URL: {url}")

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Failed: {e}")

    finally:
        # Cleanup
        for f in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, f))
        os.rmdir(temp_dir)

# -----------------------------
# Handlers
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me any video link (YouTube, TeraBox, Telegram, direct mp4/webm, or adult links).\n"
        "Adult content requires confirmation."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    await update.message.reply_text("⏳ Processing your video...")
    asyncio.create_task(download_and_send(url, update.effective_chat.id, context))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "confirm_adult":
        adult_confirmed_users.add(query.from_user.id)
        await query.edit_message_text("✅ You are now confirmed for adult content. Send the link again to download.")

# -----------------------------
# Main
# -----------------------------
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
app.add_handler(CallbackQueryHandler(button_handler))

print("Bot is running...")
app.run_polling()
