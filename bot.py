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

# --- THE QUESTIONNAIRE ---
# Add the rest of your 51 questions here by copying this format!
QUESTIONS = [
    {"key": "loan_type", "text": "1️⃣ ምን ዓይነት ብድር ይፈልጋሉ?"},
    {"key": "purpose", "text": "2️⃣ ብድሩን ለምን ማዋል አስበዋል?"},
    {"key": "amount", "text": "3️⃣ ስንት የብድር መጠን ይፈልጋሉ? (በብር፣ ቁጥር ብቻ)"},
    {"key": "duration", "text": "5️⃣ ብድሩ የሚመለስበት ጊዜ (በወራት)?"},
    {"key": "payback_date", "text": "6️⃣ ብድሩን ሙሉ በሙሉ መቼ ይከፍላሉ? (ለምሳሌ ታህሳስ 2028)"},
    {"key": "payment_source", "text": "7️⃣ የመክፈያ ምንጭዎ ምን ነው?"},
    {"key": "bank_choice", "text": "8️⃣ የትኛውን ባንክ ታመልክታለሁ? (ወይም 'recommend' ብለው ይጻፉ)"},
    {"key": "has_account", "text": "🔟 በሚያመለክቱት ባንክ የባንክ አካውንት አለዎት?"},
    {"key": "has_other_loan", "text": "1️⃣1️⃣ በሌላ ባንክ ወይም በዚህ ባንክ ያለዎት ብድር አለ?"},
    {"key": "full_name", "text": "1️⃣3️⃣ ሙሉ ስም (በመታወቂያው ላይ እንዳለ):"},
    {"key": "age", "text": "1️⃣4️⃣ ዕድሜ:"},
    {"key": "marital_status", "text": "1️⃣5️⃣ የጋብቻ ሁኔታ:"},
    {"key": "national_id", "text": "1️⃣7️⃣ የብሔራዊ መታወቂያ / ፓስፖርት ቁጥር:"},
    {"key": "tin", "text": "1️⃣8️⃣ የቲን (TIN) ቁጥር:"},
    {"key": "phone", "text": "1️⃣9️⃣ ስልክ ቁጥር:"},
    {"key": "email", "text": "1️⃣9️⃣ለ) ኢሜል አድራሻ:"},
    {"key": "address", "text": "2️⃣0️⃣ የመኖሪያ አድራሻ:"},
    # --- ADD THE REST OF THE QUESTIONS HERE ---
]

ASKING = range(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.full_name)
    
    # Terms and Conditions
    terms = """⚖️ የአገልግሎት ውሎችና ሁኔታዎች (Terms & Conditions)

ወደ ቃላል ብድር (Qelal Beder) የብድር ማመልከቻ ቦት እንኳን ደህና መጡ። ማመልከቻውን ከመጀመርዎ በፊት እባክዎ የሚከተሉትን ውሎች በጥንቃቄ ያንብቡ፡

1️⃣ የመረጃ ትክክለኛነት፡- በዚህ ቦት ላይ የሚያስገቡት መረጃ ሁሉ እውነተኛ፣ ትክክለኛ እና ለጉዳዩ የማመለከተው አካል መሆን አለበት።
2️⃣ ሚስጥራዊነት፡- የሰጡት መረጃ ለባንክ ባለሙያዎች ብቻ የሚተላለፍ ሲሆን፤ በሚስጥር ይያዛል።
3️⃣ ማረጋገጫ፡- የሰጡት መረጃ ሐሰት ሆኖ ከተገኘ ባንክ የብድር አገልግሎት ላይ ገደብ ሊጣልበት እንደሚችል ይስማሙ።
4️⃣ መረጃ ማጋራት፡- የእርስዎን የክሬዲት መረጃ ባንኮች እንዲመረምሩ ተስማምተዋል።

👇 ለመቀጠል ከታች ያለውን ✅ ተስማማሁ (I Accept) የሚለውን ቁልፍ ይጫኑ::"""
    
    await update.message.reply_text(terms)

async def accept_terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['answers'] = {}
    context.user_data['q_index'] = 0
    
    await update.message.reply_text("✅ ውሉን ተቀብለዋል።\n\n👋 የብድር ጥያቄ መቀበያ ቦት እንኳን ደህና መጡ። ቃላል ብድር እንደስማችን ሄደተን ቃላል በማድረግ ብድርዎን በአጭር ጊዜ ውስጥ ለማግኘት በሚችሉበት መንገድ አብረን እንሰራለን።\n\n⚠️ ማንኛውንም ጊዜ ለማቋረጥ /cancel ብለው ይጻፉ::")
    
    # Ask the first question
    return await ask_next_question(update, context)

async def ask_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data['q_index']
    
    if idx >= len(QUESTIONS):
        return await finish_application(update, context)
        
    q = QUESTIONS[idx]
    # Special fee message before duration question
    if q['key'] == 'duration':
        await update.message.reply_text("💡 የአገልግሎት ክፍያ መረጃ (Fee Info):\nብድር የማዘጋጀት ክፍያ: 5,000 ብር\nብድር ሲለቀቅ የሚከፈል ኮሚሽን: 75,000.00 ብር\n\n(ይህ መረጃ ለእርስዎ ግልጽነት የተሰጠ ነው)")
        await update.message.reply_text(q['text'])
    else:
        await update.message.reply_text(q['text'])
        
    return ASKING

async def receive_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data['q_index']
    current_q = QUESTIONS[idx]
    
    # Save the answer
    context.user_data['answers'][current_q['key']] = update.message.text
    
    # Move to next question
    context.user_data['q_index'] += 1
    
    return await ask_next_question(update, context)

async def finish_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    answers = context.user_data['answers']
    
    # Generate Application Number
    app_number = f"LR-{datetime.datetime.now().year}-{random.randint(100, 999)}"
    
    # Save to Database
    db.save_full_loan(user_id, app_number, answers)
    
    # Generate Report
    now_str = datetime.datetime.now().isoformat()
    
    try:
        amount = float(answers.get('amount', '0').replace(',', ''))
        consultant_fee = amount * 0.0075 # Example: 0.75%
    except:
        amount = 0
        consultant_fee = 0

    report = f"""📥 አዲስ የብድር ማመልከቻ — {app_number}

🆔 የማመልከቻ ቁጥር: {app_number}
🏦 ባንክ: {answers.get('bank_choice', 'N/A')}
💰 የብድር መጠን: {amount:,.0f} ብር
💵 የማዘጋጀት ክፍያ: 5,000 ብር
📈 ብድር ሲለቀቅ የሚከፈል ኮሚሽን: {consultant_fee:,.2f} ብር
⏳ ብድሩ የሚመለስበት ጊዜ: {answers.get('duration', 'N/A')} ወራት
📄 ዓይነት: {answers.get('loan_type', 'N/A')}
⚖️ ውሉን ተቀብሏል: {now_str}

────────────────────
📋 የሰነድ ሁኔታ
────────────────────
✅ Full name: {answers.get('full_name', 'N/A')}
✅ Phone: {answers.get('phone', 'N/A')}
✅ Email: {answers.get('email', 'N/A')}
✅ National ID: {answers.get('national_id', 'N/A')}
✅ TIN: {answers.get('tin', 'N/A')}
✅ Address: {answers.get('address', 'N/A')}
✅ Marital status: {answers.get('marital_status', 'N/A')}
✅ Age: {answers.get('age', 'N/A')}
⚠️ Lien-free: የለም
✅ መድን: ተስማምቷል
📎 Attachments: 0"""

    await update.message.reply_text(report)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Application cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    try:
        asyncio.set_event_loop(asyncio.new_event_loop())
    except Exception:
        pass

    db.init_db()
    
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        return

    application = ApplicationBuilder().token(TOKEN).build()

    # Main conversational flow
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('apply', accept_terms) # For now, skipping the T&C button to keep it simple
        ],
        states={
            ASKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_answer)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)

    print("Bot is starting... Polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
