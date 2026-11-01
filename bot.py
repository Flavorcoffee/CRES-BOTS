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

# --- THE QUESTIONNAIRE (ALL 51 QUESTIONS) ---
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
    {"key": "past_default", "text": "1️⃣2️⃣ ቀድሞ ብሎ ብድርዎ ተሰርዞ ወይም እንደ ችግር ያለበት ተመድቦ ያውቃል?"},
    {"key": "full_name", "text": "1️⃣3️⃣ ሙሉ ስም (በመታወቂያው ላይ እንዳለ):"},
    {"key": "age", "text": "1️⃣4️⃣ ዕድሜ:"},
    {"key": "marital_status", "text": "1️⃣5️⃣ የጋብቻ ሁኔታ:"},
    {"key": "national_id", "text": "1️⃣7️⃣ የብሔራዊ መታወቂያ / ፓስፖርት ቁጥር:"},
    {"key": "tin", "text": "1️⃣8️⃣ የቲን (TIN) ቁጥር:"},
    {"key": "phone", "text": "1️⃣9️⃣ ስልክ ቁጥር:"},
    {"key": "email", "text": "1️⃣9️⃣ለ) ኢሜል አድራሻ:"},
    {"key": "address", "text": "2️⃣0️⃣ የመኖሪያ አድራሻ (ክልል፣ ከተማ፣ ክ/ከተማ ወይም ዞን፣ ወረዳ፣ ቀበሌ)፡ የሌለ ከሆነ ___ ይጻፉ:"},
    {"key": "owner_or_agent", "text": "2️⃣1️⃣ የንግዱ ባለቤት ነዎት ወይስ ወኪል?"},
    {"key": "business_name", "text": "2️⃣3️⃣ የንግድ ስም:"},
    {"key": "business_legal", "text": "23ለ) የንግድ ሕጋዊ ቅርጽ:"},
    {"key": "trade_license", "text": "2️⃣4️⃣ የንግድ ፈቃድ ቁጥር:"},
    {"key": "business_est", "text": "2️⃣5️⃣ ንግዱ የተመሠረተበት ዓመት (በእንትጅ ሀመን አቆጣጠር):"},
    {"key": "industry", "text": "2️⃣6️⃣ የሥራ ዘርፍ / ኢንዱስትሪ:"},
    {"key": "employees", "text": "2️⃣7️⃣ የሥራተኛ ብዛት:"},
    {"key": "sales_2018", "text": "2️⃣8️⃣ የሽያጭ መጠን — 2018 ዓ.ም (በብር)፣ ካልኖረ 'ዝልል' ይጻፉ:"},
    {"key": "sales_2017", "text": "2️⃣9️⃣ የሽያጭ መጠን — 2017 ዓ.ም (በብር)፣ ካልኖረ 'ዝልል' ይጻፉ:"},
    {"key": "sales_2016", "text": "3️⃣0️⃣ የሽያጭ መጠን — 2016 ዓ.ም (በብር)፣ ካልኖረ 'ዝልል' ይጻፉ:"},
    {"key": "sales_2015", "text": "3️⃣1️⃣ የሽያጭ መጠን — 2015 ዓ.ም (በብር)፣ ካልኖረ 'ዝልል' ይጻፉ:"},
    {"key": "sales_2014", "text": "3️⃣2️⃣ የሽያጭ መጠን — 2014 ዓ.ም (በብር)፣ ካልኖረ 'ዝልል' ይጻፉ:"},
    {"key": "sales_2019_exp", "text": "3️⃣3️⃣ ለያዘነው ዓመት (2019 ዓ.ም) የሚጠበቀው ሽያጭ:"},
    {"key": "tax_clearance", "text": "3️⃣4️⃣ እርስዎ (ተበዳሪው) የታክስ ክሊራንስ አግኝተዋል?"},
    {"key": "tax_clearance_g", "text": "34ለ) ወስትና ሰጪው የታክስ ክሊራንስ አለው?"},
    {"key": "pension", "text": "3️⃣5️⃣ የሠራተኞችዎን የጡረታ መዋጮ ክሊራንስ አለ?"},
    {"key": "vat", "text": "3️⃣6️⃣ በተጨማሪ እሴት ታክስ (VAT) ተመዝግበዋል?"},
    {"key": "disputes", "text": "3️⃣7️⃣ በባንክ ላይ ክርክር ወይም ያልተከፈለ እዳ አለ?"},
    {"key": "collateral", "text": "3️⃣8️⃣ ለብድር መያዣ ዋስትና አለዎት?"},
    {"key": "marriage_cert", "text": "38ለ) አለኝ ካሉ አስያዥ የጋብቻ የምስክር ወረቀት ማቅረብ ይችላሉ? (ያላገባ ከሆነ በስድስት ወር ውስጥ ታድሏል?)"},
    {"key": "collateral_type", "text": "3️⃣9️⃣ የዋስትናዎቹን ዓይነት ይምረጡ (ብዙ ማመልከት ይችላሉ):-"},
    {"key": "collateral_value", "text": "4️⃣0️⃣ የዋስትናዎቹ ጠቅላላ ግምታዊ ገንዘብ ዋጋ (በብር):"},
    {"key": "collateral_3rd", "text": "4️⃣1️⃣ ዋስትናው በሶስተኛ ወገን የቀረበ ነው?"},
    {"key": "collateral_year", "text": "4️⃣2️⃣ የተከራዩ የተመረተበት ዓመት:"},
    {"key": "collateral_car_type", "text": "42ለ) የተከራዩ ዓይነት:"},
    {"key": "collateral_car_price", "text": "42ሐ) የተከራዩ የገበያ ዋጋ (በብር):"},
    {"key": "collateral_lien", "text": "4️⃣3️⃣ ዋስትናው ከቀድሞ ብድር/እዳ ነጻ ነው?"},
    {"key": "collateral_insurance", "text": "4️⃣5️⃣ የዚቢሌት ጥብን / የባንክስ ፕላን አለዎት?"},
    {"key": "proforma", "text": "4️⃣6️⃣ ከአቅራቢዎች የፕሮፎርማ ደረሰኝ አለ?"},
    {"key": "audited_stmt", "text": "4️⃣7️⃣ የአዴት የሂሳብ መግለጫ (3 ዓመት) አለዎት?"},
    {"key": "bank_stmt", "text": "4️⃣8️⃣ ያለፉት 6-12 ወራት የባንክ ስቴትመንት አለዎት?"},
    {"key": "credit_history", "text": "4️⃣9️⃣ የክሬዲት ታሪክዎ ከብሔራዊ ባንክ ባለሙያዎች ብቻ የሚተላለፍ ሲሆን፤ በሚስጥር ይያዛል።"},
    {"key": "insurance_agree", "text": "5️⃣0️⃣ ለሚቀርበው ዋስትና ኢንሹራንስ መግባት ይችላሉ?"},
    {"key": "accessible", "text": "5️⃣1️⃣ ንግዱ/ዋስትናው ባንኩ ለመስማማት ተደራሽ ነው?"}
]

ASKING = range(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.full_name)
    
    terms = """⚖️ የአገልግሎት ውሎችና ሁኔታዎች (Terms & Conditions)

ወደ ቃላል ብድር (Qelal Beder) የብድር ማመልከቻ ቦት እንኳን ደህና መጡ። ማመልከቻውን ከመጀመርዎ በፊት እባክዎ የሚከተሉትን ውሎች በጥንቃቄ ያንብቡ፡

1️⃣ የመረጃ ትክክለኛነት፡- በዚህ ቦት ላይ የሚያስገቡት መረጃ ሁሉ እውነተኛ፣ ትክክለኛ እና ለጉዳዩ የማመለከተው አካል መሆን አለበት።
2️⃣ ሚስጥራዊነት፡- የሰጡት መረጃ ለባንክ ባለሙያዎች ብቻ የሚተላለፍ ሲሆን፤ በሚስጥር ይያዛል።
3️⃣ ማረጋገጫ፡- የሰጡት መረጃ ሐሰት ሆኖ ከተገኘ ባንክ የብድር አገልግሎት ላይ ገደብ ሊጣልበት እንደሚችል ይስማሙ።
4️⃣ መረጃ ማጋራት፡- የእርስዎን የክሬዲት መረጃ ባንኮች እንዲመረምሩ ተስማምተዋል።

👇 ለመቀጠል /apply ብለው ይጻፉ::"""
    
    await update.message.reply_text(terms)

async def apply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['answers'] = {}
    context.user_data['q_index'] = 0
    
    await update.message.reply_text("✅ ውሉን ተቀብለዋል።\n\n👋 የብድር ጥያቄ መቀበያ ቦት እንኳን ደህና መጡ።\n\n⚠️ ማንኛውንም ጊዜ ለማቋረጥ /cancel ብለው ይጻፉ::")
    
    return await ask_next_question(update, context)

async def ask_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data['q_index']
    
    if idx >= len(QUESTIONS):
        return await finish_application(update, context)
        
    q = QUESTIONS[idx]
    
    if q['key'] == 'duration':
        await update.message.reply_text("💡 የአገልግሎት ክፍያ መረጃ (Fee Info):\nብድር የማዘጋጀት ክፍያ: 5,000 ብር\nብድር ሲለቀቅ የሚከፈል ኮሚሽን: 75,000.00 ብር\n\n(ይህ መረጃ ለእርስዎ ግልጽነት የተሰጠ ነው)")
        
    await update.message.reply_text(q['text'])
    return ASKING

async def receive_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data['q_index']
    current_q = QUESTIONS[idx]
    
    context.user_data['answers'][current_q['key']] = update.message.text
    context.user_data['q_index'] += 1
    
    return await ask_next_question(update, context)

async def finish_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    answers = context.user_data['answers']
    
    app_number = f"LR-{datetime.datetime.now().year}-{random.randint(100, 999)}"
    
    db.save_full_loan(user_id, app_number, answers)
    
    now_str = datetime.datetime.now().isoformat()
    
    try:
        amount = float(answers.get('amount', '0').replace(',', ''))
        consultant_fee = amount * 0.0075
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

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('apply', apply_start)],
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
