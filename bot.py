import os
import asyncio
import logging
import datetime
import random
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, 
    ConversationHandler, MessageHandler, filters
)
import db

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Conversation States
BANK, AMOUNT, DURATION, LOAN_TYPE, CONFIRM = range(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.full_name)
    await update.message.reply_text(
        f"ሰላም {user.full_name}! 👋\n"
        "Welcome to the Beder/Loan Application Bot.\n"
        "Use /apply to start a new loan application."
    )

async def apply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Let's start your loan application.\n\n"
        "1. What is the **Bank Name**? (e.g., አዋሽ, ዳሽን)",
        parse_mode='Markdown'
    )
    return BANK

async def get_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['bank'] = update.message.text
    await update.message.reply_text("2. What is the **Loan Amount** in Birr? (e.g., 5000000)", parse_mode='Markdown')
    return AMOUNT

async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.replace(',', ''))
        context.user_data['amount'] = amount
        await update.message.reply_text("3. What is the **Duration** in months? (e.g., 120)", parse_mode='Markdown')
        return DURATION
    except ValueError:
        await update.message.reply_text("⚠️ Please enter a valid number for the amount.")
        return AMOUNT

async def get_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        duration = int(update.message.text)
        context.user_data['duration'] = duration
        await update.message.reply_text("4. What is the **Loan Type**? (e.g., የዳይስፖራ ብድር)", parse_mode='Markdown')
        return LOAN_TYPE
    except ValueError:
        await update.message.reply_text("⚠️ Please enter a valid number for the duration.")
        return DURATION

async def get_loan_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['type'] = update.message.text
    await update.message.reply_text(
        "Great! Type /confirm to submit your application, or /cancel to stop."
    )
    return CONFIRM

async def confirm_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bank = context.user_data['bank']
    amount = context.user_data['amount']
    duration = context.user_data['duration']
    loan_type = context.user_data['type']
    
    # Calculate fees
    prep_fee = 5000.0 
    consultant_fee = amount * 0.05  # 5% consultant fee
    
    # Generate Application Number
    app_number = f"LR-{datetime.datetime.now().year}-{random.randint(100, 999)}"
    
    # Save to Database
    db.save_loan(user_id, app_number, bank, amount, prep_fee, consultant_fee, duration, loan_type)
    
    # Generate Report Format exactly like the image
    now_str = datetime.datetime.now().isoformat()
    
    report = f"""🆔 የማመልከቻ ቁጥር: <b>{app_number}</b>
🏦 ባንክ: <b>{bank}</b>
💰 የብድር መጠን: <b>{amount:,.0f} ብር</b>
💵 የሰነድ ማዘጋጀት እና ፍላትፎርም ክፍያ: <b>{prep_fee:,.0f} ብር</b>
📈 የአማካሪ ክፍያ: <b>{consultant_fee:,.2f} ብር</b>
⏳ ብድሩ የሚመለስበት ጊዜ: <b>{duration} ወራት</b>
📄 ዓይነት: <b>{loan_type}</b>
⚖️ ውሉን ተቀብሏል: <b>{now_str}</b>

────────────────────
📋 <b>የሰነድ ሁኔታ</b>
────────────────────
✅ Full name
✅ Phone
✅ Email
✅ National ID
✅ TIN
✅ Address
✅ Marital status
✅ Age
✅ Tax clearance (borrower)
✅ Pension contribution
✅ VAT registered
✅ Audited statements
✅ Bank statements
✅ Credit report
✅ Feasibility study
✅ Proforma invoices
✅ የስትራቴጂ (መኪና, ሕንፃ)
⚠️ Lien-free: የለም
✅ መድን: ተስማምቷል
📎 Attachments: 0"""

    await update.message.reply_text(report, parse_mode='HTML')
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Application cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    # Fix for Termux Python 3.14
    try:
        asyncio.set_event_loop(asyncio.new_event_loop())
    except Exception:
        pass

    db.init_db()
    
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        print("ERROR: BOT_TOKEN environment variable is missing!")
        return

    application = ApplicationBuilder().token(TOKEN).build()

    # Set up the step-by-step conversation
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('apply', apply_start)],
        states={
            BANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bank)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)],
            DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_duration)],
            LOAN_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_loan_type)],
            CONFIRM: [CommandHandler('confirm', confirm_application)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)

    print("Bot is starting... Polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
