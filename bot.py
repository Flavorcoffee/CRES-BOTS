import os
import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import db

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.full_name)
    
    await update.message.reply_text(
        f"ሰላም {user.full_name}! 👋\n"
        "Welcome to the Beder/Loan Application Bot.\n"
        "Use /apply to start a new loan application."
    )

async def apply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Loan application process will start here soon.")

def main():
    # FIX FOR PYTHON 3.14 ON TERMUX: Create a new event loop
    try:
        asyncio.set_event_loop(asyncio.new_event_loop())
    except Exception as e:
        print(f"Event loop setup note: {e}")

    # 1. Initialize Database
    db.init_db()
    
    # 2. Get Token securely
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        print("ERROR: BOT_TOKEN environment variable is missing!")
        return

    # 3. Build Bot
    application = ApplicationBuilder().token(TOKEN).build()

    # 4. Add Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("apply", apply))

    # 5. Run 24/7
    print("Bot is starting... Polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
