import asyncio
import nest_asyncio
from threading import Timer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
import re
nest_asyncio.apply()

BOT_TOKEN = "7576453328:AAHntURmxMHnsxKYeVRPgO1Q2Fl3kdNXyQ8"
ADMIN_USER_ID = 1675462613  # Replace with the actual admin user ID
INACTIVITY_TIMEOUT = 600  # Timeout duration (e.g., 10 minutes)

waiting_users = set()
active_chats = {}
warning_counts = {}
blocked_users = set()
user_reports = {}
user_inactivity = {}
user_friends = {}

inappropriate_words = {"nude", "sex", "porn", "nsfw"}

async def start(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    await update.message.reply_text("Welcome to Anonymous Chat! Use /find to match with a stranger.")

async def report(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    if len(context.args) == 0:
        await update.message.reply_text("⚠️ Please provide a reason for the report.")
        return
    
    report_reason = " ".join(context.args)
    user_reports[user_id] = report_reason
    await update.message.reply_text("✅ Your report has been submitted.")

async def help(update: Update, context: CallbackContext):
    help_text = """
🛠️ **Help - Anonymous Chat Bot**

**Commands:**
- `/start` - Start the bot and get a welcome message.
- `/find` - Find an anonymous chat partner and start chatting.
- `/stop` - Leave your current chat or stop waiting for a partner.
- `/help` - Show this help message.
- `/report [reason]` - Report inappropriate behavior or content to the bot admin.

**Usage:**
- When you use `/find`, you'll be matched with a random user.
- If you want to leave the chat, simply type `/stop`.
- You can also provide feedback using the thumbs-up or thumbs-down buttons after stopping a chat.

Please follow the community guidelines and keep the chat respectful!

⚠️ **Note**: If you use inappropriate language, you may be warned or blocked.
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def find(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    
    if user_id in blocked_users:
        await update.message.reply_text("🚫 You have been blocked for inappropriate behavior.")
        return
    
    if user_id in active_chats:
        await update.message.reply_text("You're already in a chat! Use /stop to leave your current chat.")
        return
    
    available_users = [uid for uid in waiting_users if uid != user_id]
    
    if available_users:
        partner_id = available_users.pop(0)
        waiting_users.remove(partner_id)
        
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        
        await context.bot.send_message(chat_id=user_id, text="🔗 Connected! Start chatting anonymously.")
        await context.bot.send_message(chat_id=partner_id, text="🔗 Connected! Start chatting anonymously.")
    else:
        waiting_users.add(user_id)
        await update.message.reply_text("⏳ Waiting for a partner...")

async def handle_feedback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id

    if query.data.startswith("accept_"):
        requester_id = int(query.data.split("_")[1])
        await query.answer("✅ Friend request accepted!")

        # Exchange usernames
        await context.bot.send_message(
            chat_id=requester_id,
            text=f"Your friend request has been accepted! You can now exchange IDs."
        )
        await query.edit_message_text(text="You are now friends. Feel free to exchange your IDs!")
    elif query.data.startswith("reject_"):
        requester_id = int(query.data.split("_")[1])
        await query.answer("❌ Friend request rejected!")

        await context.bot.send_message(
            chat_id=requester_id,
            text="Your friend request has been rejected."
        )
        await query.edit_message_text(text="Your friend request has been rejected.")

async def stop(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        del active_chats[partner_id]
        
        keyboard = [
            [InlineKeyboardButton("👍 Like", callback_data="like"),
             InlineKeyboardButton("👎 Dislike", callback_data="dislike")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=partner_id,
            text="❌ Your chat partner has left. If you wish, leave your feedback about your partner.",
            reply_markup=reply_markup
        )
        await update.message.reply_text("❌ You have left the chat.")
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        await update.message.reply_text("✅ You have left the queue.")
    else:
        await update.message.reply_text("You're not in a chat or queue.")

async def handle_message(update: Update, context: CallbackContext):
    if update.message is None:
        return
    
    user_id = update.message.chat_id
    text = update.message.text.lower() if update.message.text else ""
    
    if user_id in blocked_users:
        await update.message.reply_text("🚫 You are blocked and cannot send messages.")
        return
    
    if any(word in text for word in inappropriate_words):
        if user_id in warning_counts:
            warning_counts[user_id] += 1
        else:
            warning_counts[user_id] = 1
        
        if warning_counts[user_id] >= 3:
            blocked_users.add(user_id)
            await update.message.reply_text("🚫 You have been blocked for inappropriate behavior.")
        else:
            await update.message.reply_text("⚠️ Please refrain from using inappropriate language.")
    
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        if update.message.text:
            await context.bot.send_message(chat_id=partner_id, text=update.message.text)
        elif update.message.photo:
            await context.bot.send_photo(chat_id=partner_id, photo=update.message.photo[-1].file_id, caption=update.message.caption, has_spoiler=True)
            await context.bot.send_message(chat_id=partner_id, text="📷 Image received (hidden with spoiler). Tap to view.")
        elif update.message.video:
            await context.bot.send_video(chat_id=partner_id, video=update.message.video.file_id, caption=update.message.caption, has_spoiler=True)
            await context.bot.send_message(chat_id=partner_id, text="🎥 Video received (hidden with spoiler). Tap to view.")
        elif update.message.sticker:
            await context.bot.send_sticker(chat_id=partner_id, sticker=update.message.sticker.file_id)
        elif update.message.voice:
            await context.bot.send_voice(chat_id=partner_id, voice=update.message.voice.file_id)
        elif update.message.animation:
            await context.bot.send_animation(chat_id=partner_id, animation=update.message.animation.file_id)
        elif update.message.document:
            await context.bot.send_document(chat_id=partner_id, document=update.message.document.file_id, caption=update.message.caption)
    else:
        await update.message.reply_text("You're not in a chat. Use /find to start one.")

def reset_inactivity_timer(user_id):
    if user_id in user_inactivity:
        user_inactivity[user_id].cancel()

    timer = Timer(INACTIVITY_TIMEOUT, stop_inactive_user, [user_id])
    timer.start()
    user_inactivity[user_id] = timer

async def stop_inactive_user(user_id, context: CallbackContext):
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        del active_chats[partner_id]
        
        asyncio.run(context.bot.send_message(
            chat_id=partner_id,
            text="❌ Your chat partner has been removed due to inactivity."
        ))
        asyncio.run(context.bot.send_message(
            chat_id=user_id,
            text="❌ You have been removed from the chat due to inactivity."
        ))

# Handle the callback from the user accepting or rejecting the friend request
async def send_profile_link(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    
    # Check if the user is in an active chat
    if user_id not in active_chats:
        await update.message.reply_text("⚠️ You are not in a chat to share your profile link.")
        return
    
    # Get the username of the user
    user_username = update.message.from_user.username
    
    if not user_username:
        await update.message.reply_text("⚠️ You don't have a username set. Please set one in Telegram to share your profile link.")
        return
    
    # Create the link to the user's profile
    profile_link = user_username
    
    # Get the partner's ID
    partner_id = active_chats[user_id]
    
    # Send the profile link to the partner
    await context.bot.send_message(
        chat_id=partner_id,
        text=f"🔗 The link to your partner's profile: {profile_link}"
    )
    
    # Notify the user that the link has been sent
    await update.message.reply_text("The link to your profile has been sent to your partner.")

async def view_active_chats(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("🚫 You are not authorized to view active chats.")
        return
    
    active_users = list(active_chats.keys())
    if active_users:
        chat_list = "\n".join([f"User {uid}" for uid in active_users])
        await update.message.reply_text(f"🟢 Active Chats:\n{chat_list}")
    else:
        await update.message.reply_text("🔴 No active chats at the moment.")

async def kick_user(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("🚫 You are not authorized to perform this action.")
        return
    
    try:
        target_user_id = int(context.args[0])  # Get the user ID from the command arguments
        if target_user_id in active_chats:
            partner_id = active_chats.pop(target_user_id)
            del active_chats[partner_id]
            await context.bot.send_message(chat_id=partner_id, text="❌ You have been kicked out of the chat.")
        blocked_users.add(target_user_id)
        await context.bot.send_message(chat_id=target_user_id, text="🚫 You have been blocked for inappropriate behavior.")
        await update.message.reply_text(f"✅ User {target_user_id} has been blocked.")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Please provide a valid user ID.")

async def view_reports(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("🚫 You are not authorized to view reports.")
        return
    
    if user_reports:
        reports_text = "\n".join([f"User {uid}: {reason}" for uid, reason in user_reports.items()])
        await update.message.reply_text(f"📝 User Reports:\n{reports_text}")
    else:
        await update.message.reply_text("🔴 No reports received.")

async def bot_stats(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("🚫 You are not authorized to view bot stats.")
        return
    
    active_user_count = len(active_chats)
    reported_users_count = len(user_reports)
    
    stats_message = f"""
    📊 **Bot Stats:**
    - Active Users: {active_user_count}
    - Reported Users: {reported_users_count}
    """
    await update.message.reply_text(stats_message)

async def main():
    application = Application.builder().token(BOT_TOKEN).build()


    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("find", find))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("report", report))
    application.add_handler(CommandHandler("link", send_profile_link))
    application.add_handler(CommandHandler("view_active_chats", view_active_chats))
    application.add_handler(CommandHandler("kick_user", kick_user))
    application.add_handler(CommandHandler("view_reports", view_reports))
    application.add_handler(CommandHandler("bot_stats", bot_stats))
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    application.add_handler(CallbackQueryHandler(handle_feedback))
    application.run_polling()

if __name__ == "__main__":
    import asyncio
    print("Bot started successfully!")
    asyncio.run(main())  # This line can be removed if you're already running in an event loop