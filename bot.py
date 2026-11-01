import os, json, datetime
from dotenv import load_dotenv
import telebot
from telebot import types

from db import init_db, save_application, load_application, list_pending
from crypto import encrypt_record, decrypt_record
from mailer import send_full_record_email
from i18n import Q_AM

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
OFFICER_ID = int(os.getenv("LOAN_OFFICER_CHAT_ID", "0"))
bot = telebot.TeleBot(TOKEN)
AUTHORIZED = {OFFICER_ID}

AM = {
    "collected": "ተሰብስቧል", "missing": "ይጎድላል",
    "pending": "በመጠባበቅ ላይ", "confirmed": "ተረጋግጧል",
    "yes": "አዎ", "no": "አይደለም",
    "pending_upload": "ሰነድ ይጠበቃል",
    "agreed": "ተስማምቷል", "years": "ዓመታት",
    "items_pending": "የሚጠበቁ እቃዎች", "status": "የሰነድ ሁኔታ",
    "collateral": "ዋስትና", "insurance": "መድን",
    "not_provided": "አልቀረበም",
}

QUESTIONS = [
    {"key":"loan_type","type":"choice","choices":["Agriculture", "Investment", "Vehicle Purchase", "Building Purchase", "Export Import", "Diaspora", "Other"]},
    {"key":"loan_purpose","type":"text"},
    {"key":"amount_etb","type":"number"},
    
    # Own Contribution only for specific types
    {"key":"own_contribution","type":"number", "skip_if_not_in": "loan_type", "values": ["Investment", "Vehicle Purchase", "Building Purchase"]},
    
    {"key":"tenure_months","type":"number"},
    {"key":"full_repayment_date","type":"text"},
    {"key":"repayment_source","type":"choice","choices":["Business Income", "Salary", "Remittance", "Project Revenue", "Other"]},
    {"key":"bank","type":"text"},
    
    # --- Updated with yn_variant ---
    {"key":"has_account","type":"yesno", "yn_variant":"exists"},
    {"key":"existing_loans","type":"yesno", "yn_variant":"exists"},
    {"key":"existing_loan_details","type":"text","skip_if_false":"existing_loans"},
    
    {"key":"had_npl","type":"yesno", "yn_variant":"standard"},
    {"key":"full_name","type":"text"},
    {"key":"age","type":"number"},
    {"key":"marital_status","type":"choice","choices":["Single","Married","Divorced","Widowed"]},
    {"key":"national_id","type":"text"},
    {"key":"tin","type":"text"},
    {"key":"phone","type":"text"},
    {"key":"email","type":"text"},
    {"key":"address","type":"text"},
    {"key":"role","type":"choice","choices":["Owner","Representative"]},
    
    {"key":"has_poa","type":"yesno", "yn_variant":"exists"},
    {"key":"business_name","type":"text"},
    {"key":"legal_form","type":"choice","choices":["Sole Proprietorship","PLC","Share Company","Cooperative","Other"]},
    {"key":"trade_license","type":"text"},
    {"key":"year_established","type":"number"},
    {"key":"sector","type":"text"},
    {"key":"employees","type":"number"},
    {"key":"sales_2018","type":"number"},
    {"key":"sales_2017","type":"number"},
    {"key":"sales_2016","type":"number"},
    {"key":"sales_2015","type":"number"},
    {"key":"sales_2014","type":"number"},
    {"key":"sales_current_projection","type":"number"},
    
    {"key":"tax_clearance","type":"yesno", "yn_variant":"standard"},
    {"key":"guarantor_tax_clearance","type":"yesno", "yn_variant":"exists"},
    {"key":"pension_paid","type":"yesno", "yn_variant":"exists"},
    {"key":"vat_registered","type":"yesno", "yn_variant":"standard"},
    {"key":"tax_disputes","type":"yesno", "yn_variant":"exists"},
    {"key":"has_collateral","type":"yesno", "yn_variant":"exists"},
    
    {"key":"collateral_type","type":"choice","choices":["Land","Building","Vehicle","Machinery","Inventory","Fixed deposit","Shares","Livestock","Other"],"skip_if_false":"has_collateral"},
    {"key":"collateral_value","type":"number","skip_if_false":"has_collateral"},
    
    {"key":"third_party","type":"yesno", "yn_variant":"is","skip_if_false":"has_collateral"},
    {"key":"third_party_name","type":"text","skip_if_false":"third_party"},
    {"key":"vehicle_year","type":"text","skip_if_false":"has_collateral"},
    {"key":"collateral_free","type":"yesno", "yn_variant":"is","skip_if_false":"has_collateral"},
    
    {"key":"feasibility_study","type":"yesno", "yn_variant":"exists"},
    {"key":"proforma_invoices","type":"yesno", "yn_variant":"exists"},
    {"key":"audited_statements","type":"yesno", "yn_variant":"exists"},
    {"key":"bank_statements","type":"yesno", "yn_variant":"exists"},
    {"key":"credit_report","type":"yesno", "yn_variant":"exists"},
    {"key":"will_insure","type":"yesno", "yn_variant":"standard"},
    {"key":"site_visitable","type":"yesno", "yn_variant":"is"},
    {"key":"legal_cases","type":"yesno", "yn_variant":"exists"},
    {"key":"consent_credit_check","type":"yesno", "yn_variant":"standard"},
]

for q in QUESTIONS:
    q["q"] = Q_AM.get(q["key"], q["key"])

user_sessions = {}

def next_ref():
    year = datetime.datetime.now().year
    return f"LR-{year}-{int(datetime.datetime.now().timestamp())%100000:05d}"

def skip_question(q, data):
    if "skip_if_false" in q:
        return not data.get(q["skip_if_false"], False)
    if "skip_if_not_in" in q:
        previous_answer = data.get(q["skip_if_not_in"])
        return previous_answer not in q["values"]
    return False

def build_status_checklist(data):
    lines = []
    def mark(label, present, yes_text=None, no_text=None):
        yes_text = yes_text or AM["collected"]; no_text = no_text or AM["missing"]
        lines.append(f"{'✅' if present else '❌'} {label}: {yes_text if present else no_text}")

    mark("Full name",      bool(data.get("full_name")))
    mark("Phone",          bool(data.get("phone")))
    mark("Email",          bool(data.get("email")))
    mark("National ID",    bool(data.get("national_id")))
    mark("TIN",            bool(data.get("tin")))
    mark("Address",        bool(data.get("address")))
    mark("Marital status", bool(data.get("marital_status")), yes_text=AM["confirmed"])
    mark("Age",            bool(data.get("age")))
    mark("Business name",  bool(data.get("business_name")))
    mark("Trade license",  bool(data.get("trade_license")))

    fy = ["sales_2014","sales_2015","sales_2016","sales_2017","sales_2018"]
    n = sum(1 for k in fy if data.get(k) not in (None,"",0))
    lines.append(f"{'✅' if n>=3 else '⚠️'} Financial statements: {n}/5 {AM['years']}")

    b, g = bool(data.get("tax_clearance")), bool(data.get("guarantor_tax_clearance"))
    lines.append(f"{'✅' if b else '⏳'} Tax clearance (borrower): {AM['collected'] if b else AM['pending_upload']}")
    lines.append(f"{'✅' if g else '⏳'} Tax clearance (guarantor): {AM['collected'] if g else AM['pending_upload']}")

    mark("Pension contribution", bool(data.get("pension_paid")))
    mark("VAT registered",       bool(data.get("vat_registered")))
    mark("Audited statements",   bool(data.get("audited_statements")))
    mark("Bank statements",      bool(data.get("bank_statements")))
    mark("Credit report",        bool(data.get("credit_report")))
    mark("Feasibility study",    bool(data.get("feasibility_study")))
    mark("Proforma invoices",    bool(data.get("proforma_invoices")))

    if data.get("has_collateral"):
        lines.append(f"✅ {AM['collateral']}: {data.get('collateral_type','Provided')}")
        free = bool(data.get("collateral_free"))
        lines.append(f"{'✅' if free else '⚠️'} Lien-free: {AM['yes'] if free else AM['no']}")
        ins = bool(data.get("will_insure"))
        lines.append(f"{'✅' if ins else '⏳'} {AM['insurance']}: {AM['agreed'] if ins else AM['pending']}")
    else:
        lines.append(f"❌ {AM['collateral']}: {AM['not_provided']}")

    mark("Credit check consent", bool(data.get("consent_credit_check")))
    lines.append(f"📎 Attachments: {len(data.get('_files', []))}")

    pending = sum(1 for l in lines if l[0] in ("⏳","❌","⚠️"))
    return lines, pending

def finish(chat_id):
    session = user_sessions[chat_id]
    ref, data = session["ref"], session["data"]
    record = {"ref": ref, "submitted_at": datetime.datetime.now().isoformat(), "chat_id": chat_id, **data}

    status_lines, pending = build_status_checklist(data)
    summary = {
        "bank": data.get("bank"),
        "loan_type": data.get("loan_type"),
        "amount_etb": data.get("amount_etb"),
        "tenure_months": data.get("tenure_months"),
    }

    blob = encrypt_record(record)
    save_application(ref, chat_id, summary, blob, status_lines, pending)

    officer_msg = (
        f"📥 *New Loan Application — {ref}*\n\n"
        f"🆔 *App ID:* `{ref}`\n"
        f"🏦 {summary['bank']}\n"
        f"💰 {summary['amount_etb']:,.0f} ETB\n"
        f"⏳ {summary['tenure_months']} months — {summary['loan_type']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n📋 *{AM['status']}*\n━━━━━━━━━━━━━━━━━━━━\n"
        + "\n".join(status_lines)
        + f"\n\n⚠️ {pending} {AM['items_pending']}\n\n"
        f"`/lookup {ref}` — full record + email"
    )
    try:
        bot.send_message(OFFICER_ID, officer_msg, parse_mode="Markdown")
    except Exception as e:
        print("Officer notify error:", e)

    bot.send_message(chat_id,
        f"✅ *Application received!*\n\nReference: `{ref}`\n\n"
        f"Please save this App ID.\nOfficer will contact you within 2 working days.",
        parse_mode="Markdown")
    del user_sessions[chat_id]

def ask_question(chat_id):
    s = user_sessions[chat_id]
    while s["index"] < len(QUESTIONS) and skip_question(QUESTIONS[s["index"]], s["data"]):
        s["index"] += 1
    if s["index"] >= len(QUESTIONS):
        return finish(chat_id)
    q = QUESTIONS[s["index"]]
    
    if q["type"] == "yesno":
        kb = types.InlineKeyboardMarkup()
        variant = q.get("yn_variant", "standard")
        
        # Change the Yes/No text based on the question type
        if variant == "exists":
            yes_txt, no_txt = "✅ አለ", "❌ የለም"
        elif variant == "is":
            yes_txt, no_txt = "✅ ነው", "❌ አይደለም"
        else:
            yes_txt, no_txt = "✅ አዎ", "❌ አይደለም"
            
        kb.add(types.InlineKeyboardButton(yes_txt, callback_data="yes"),
               types.InlineKeyboardButton(no_txt, callback_data="no"))
        bot.send_message(chat_id, q["q"], reply_markup=kb)
        
    elif q["type"] == "choice":
        kb = types.InlineKeyboardMarkup()
        buttons = [types.InlineKeyboardButton(c, callback_data=c) for c in q["choices"]]
        for i in range(0, len(buttons), 2):
            kb.row(*buttons[i:i+2])
        bot.send_message(chat_id, q["q"], reply_markup=kb)
        
    else:
        bot.send_message(chat_id, q["q"])

def save_answer(chat_id, value):
    s = user_sessions[chat_id]
    s["data"][QUESTIONS[s["index"]]["key"]] = value
    s["index"] += 1
    ask_question(chat_id)

# ---------- HANDLERS ----------
@bot.message_handler(commands=["start"])
def start(m):
    cid = m.chat.id
    user_sessions[cid] = {"index": 0, "data": {}, "ref": next_ref()}
    bot.send_message(cid,
        "👋 እንኳን ወደ የብድር ጥያቄ ቦት በደህና መጡ!\n\n"
        "ጥያቄዎችን በቅደም ተከተል እጠይቅዎታለሁ። /cancel ብለው ማቆም ይችላሉ።",
        parse_mode="Markdown")
    ask_question(cid)

@bot.message_handler(commands=["cancel"])
def cancel(m):
    user_sessions.pop(m.chat.id, None)
    bot.reply_to(m, "❌ ጥያቄው ተሰርዟል። /start ብለው እንደገና ይጀምሩ።")

@bot.message_handler(commands=["lookup"])
def lookup(m):
    if m.chat.id not in AUTHORIZED:
        return bot.reply_to(m, "⛔ Unauthorized.")
    parts = m.text.split()
    if len(parts) != 2:
        return bot.reply_to(m, "Usage: /lookup LR-2026-042")
    ref = parts[1].upper()
    row = load_application(ref)
    if not row:
        return bot.reply_to(m, f"❌ No record for {ref}")

    record = decrypt_record(row["encrypted_blob"])
    lines = [f"*{ref}* — full record", ""]
    for k, v in record.items():
        if k in ("ref", "chat_id"):
            continue
        if k == "_files":
            lines.append(f"*{k}:* {len(v)} file(s)")
        else:
            lines.append(f"*{k}:* {v}")
    bot.send_message(m.chat.id, "\n".join(lines), parse_mode="Markdown")

    try:
        send_full_record_email(ref, record)
        bot.send_message(m.chat.id, f"📧 Full record emailed to {os.getenv('OFFICER_EMAIL')}")
    except Exception as e:
        bot.send_message(m.chat.id, f"⚠️ Email failed: {e}")

@bot.message_handler(commands=["pending"])
def pending(m):
    if m.chat.id not in AUTHORIZED:
        return bot.reply_to(m, "⛔ Unauthorized.")
    rows = list_pending()
    if not rows:
        return bot.reply_to(m, "✅ No pending applications.")
    lines = ["⏳ *Pending Applications*", ""]
    for r in rows:
        lines.append(f"• `{r['ref']}` — {r['pending_count']} {AM['items_pending']} — {r['bank'] or '?'} — {r['amount_etb'] or 0:,.0f} ETB")
    bot.send_message(m.chat.id, "\n".join(lines), parse_mode="Markdown")

@bot.message_handler(content_types=["document", "photo"])
def handle_file(m):
    cid = m.chat.id
    if cid not in user_sessions:
        return bot.reply_to(m, "/start ብለው ይጀምሩ።")
    fid = m.document.file_id if m.document else m.photo[-1].file_id
    user_sessions[cid]["data"].setdefault("_files", []).append({
        "type": m.content_type, "file_id": fid,
        "time": datetime.datetime.now().isoformat(),
    })
    bot.reply_to(m, "📎 ፋይል ተያዘ። ቀጥለው ይመልሱ።")

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(m):
    cid = m.chat.id
    if cid not in user_sessions:
        return bot.send_message(cid, "/start ብለው ይጀምሩ።")
    s = user_sessions[cid]
    q = QUESTIONS[s["index"]]
    txt = m.text.strip()
    if q["type"] == "number":
        try:
            v = float(txt.replace(",", ""))
        except ValueError:
            return bot.send_message(cid, "⚠️ እባክዎ ትክክለኛ ቁጥር ይላኩ።")
        save_answer(cid, v)
    else:
        save_answer(cid, txt)

@bot.callback_query_handler(func=lambda c: True)
def cb(call):
    cid = call.message.chat.id
    if cid not in user_sessions:
        return bot.answer_callback_query(call.id, "Session expired. /start")
    q = QUESTIONS[user_sessions[cid]["index"]]
    val = call.data
    
    if q["type"] == "yesno":
        is_yes = (val == "yes")
        val = is_yes
        
        # Show the correct text based on the variant
        variant = q.get("yn_variant", "standard")
        if variant == "exists":
            display_text = "አለ" if is_yes else "የለም"
        elif variant == "is":
            display_text = "ነው" if is_yes else "አይደለም"
        else:
            display_text = "አዎ" if is_yes else "አይደለም"
    else:
        display_text = call.data
        
    bot.answer_callback_query(call.id)
    bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
    bot.send_message(cid, f"➡️ {display_text}")
    
    save_answer(cid, val)

if __name__ == "__main__":
    init_db()
    print("🚀 Loan Bot running...")
    bot.infinity_polling()
