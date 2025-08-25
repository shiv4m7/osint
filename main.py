import logging
import requests
import asyncio
import time
import shelve
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler,
                          CallbackQueryHandler, ContextTypes, filters)

# Bot config
BOT_TOKEN = "Bot Token "
ADMIN_ID = 7072631107
FORCE_JOIN_CHANNEL = "testv3c"
DB_PATH = "user_data.db"
BOT_CREATED_DATE = "03.07.2025"

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_state = {}

TRIAL_MINUTES = 30
PREMIUM_DAYS = 30
BASE_URL = "Dm @zgodbro for api "

# --- DB Functions ---
def get_user(user_id):
    with shelve.open(DB_PATH) as db:
        return db.get(str(user_id), {})

def set_user(user_id, data):
    with shelve.open(DB_PATH) as db:
        db[str(user_id)] = data

def all_users():
    with shelve.open(DB_PATH) as db:
        return dict(db)

def set_maintenance(status: bool):
    with shelve.open(DB_PATH) as db:
        db["maintenance"] = status

def is_maintenance():
    with shelve.open(DB_PATH) as db:
        return db.get("maintenance", False)

# --- Access Control ---
def is_premium(user_id):
    user = get_user(user_id)
    if "premium_until" in user:
        return time.time() < user["premium_until"]
    return False

def is_trial_valid(user_id):
    user = get_user(user_id)
    if "start_time" not in user:
        user["start_time"] = time.time()
        set_user(user_id, user)
    return time.time() - user["start_time"] <= TRIAL_MINUTES * 60

async def is_channel_joined(user_id, context):
    try:
        member: ChatMember = await context.bot.get_chat_member(FORCE_JOIN_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_maintenance():
        await update.message.reply_text(
            "⚙️ *Bot is under maintenance!*\n\n"
            "We are adding next-level features like:\n"
            "🔥 Instagram ID Ban/Unban\n"
            "💥 Facebook & WhatsApp Freeze Methods\n"
            "📞 Full Phone & SIM Cloning Tools\n"
            "💳 Bank Info + Carding Tricks\n"
            "📡 Adhaar/Account Lookup Systems\n"
            "🧠 Secret Money-Making Tricks\n\n"
            "_Stay tuned… Something big is coming 😎_",
            parse_mode="Markdown"
        )
        return

    user_id = update.effective_user.id

    if not await is_channel_joined(user_id, context):
        await update.message.reply_text(
            f"🔒 Please join our channel to use this bot: [Join {FORCE_JOIN_CHANNEL}](https://t.me/astenxworld)",
            parse_mode="Markdown"
        )
        return

    keyboard = [
        [InlineKeyboardButton("🚘 Vehicle Details", callback_data="vehicle")],
        [InlineKeyboardButton("📸 Insta ID Details", callback_data="insta")],
        [InlineKeyboardButton("📞 Number Details", callback_data="number")]
    ]
    await update.message.reply_text(
        "🔍 Please select a lookup type:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_state[query.from_user.id] = query.data
    prompts = {
        "vehicle": "🚘 Send RC number:",
        "insta": "📸 Send Instagram username:",
        "number": "📞 Send phone number with country code (e.g., +919876543210):"
    }
    await query.message.reply_text(prompts[query.data])

def get_json(url, retries=2):
    try:
        return requests.get(url, timeout=10).json()
    except:
        if retries > 0:
            return get_json(url, retries - 1)
        return {}

def fetch_data(number):
    data = {
        "facebook": "N/A",
        "name": "N/A",
        "photo": "N/A",
        "location": "N/A",
        "operator": "N/A",
        "caller_name": "N/A"
    }
    try:
        fb = requests.get(f"{BASE_URL}/lookup?number={number}", timeout=10).json()
        data["facebook"] = fb.get("facebook", "N/A")
        data["name"] = fb.get("name_info", "N/A")
        data["photo"] = fb.get("photo_url", "N/A")
    except Exception as e:
        logger.error(f"Facebook API error: {e}")
    try:
        loc = requests.get(f"{BASE_URL}/scrap?number={number}", timeout=10).json()
        data["location"] = loc.get("location", "N/A")
        data["operator"] = loc.get("operator", "N/A")
    except Exception as e:
        logger.error(f"Location API error: {e}")
    try:
        spam = requests.get(f"{BASE_URL}/callerapi?number={number}", timeout=10).json()
        if isinstance(spam, list) and spam:
            data["caller_name"] = spam[0].get("name", "N/A")
    except Exception as e:
        logger.error(f"Spam API error: {e}")
    return data

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_maintenance():
        await update.message.reply_text(
            "⚙️ *Bot is under maintenance!*\n\n"
            "_Stay tuned... we'll be back shortly!_",
            parse_mode="Markdown"
        )
        return

    user_id = update.message.from_user.id

    if not await is_channel_joined(user_id, context):
        await update.message.reply_text(
            f"🔒 Please join our channel to use this bot: [Join {FORCE_JOIN_CHANNEL}](https://t.me/astenxworld)",
            parse_mode="Markdown")
        return

    if not is_premium(user_id) and not is_trial_valid(user_id):
        await update.message.reply_text(
            "🚫 Your free access has expired. Contact @zgodbro to upgrade to premium."
        )
        return

    mode = user_state.get(user_id)
    if not mode:
        await update.message.reply_text("❗ Use /start and choose an option.")
        return

    input_value = update.message.text.strip()
    await update.message.reply_text(f"⏳ *Please Wait...*\nProcessing `{input_value}`", parse_mode="Markdown")

    try:
        if mode == "vehicle":
            url = " Dm @zgodbro for api "{input_value}"
            r = get_json(url)
            def safe(v): return v if v else "NA"
            msg = (
                "*🚘 Vehicle RC Info:*\n\n"
                f"🔢 *RC Number:* `{safe(r.get('rc_number'))}`\n"
                f"👤 *Owner:* `{safe(r.get('owner_name'))}`\n"
                f"👪 *Father's Name:* `{safe(r.get('father_name'))}`\n"
                f"🔁 *Owner Serial:* `{safe(r.get('owner_serial_no'))}`\n"
                f"🏍️ *Model:* `{safe(r.get('model_name'))}`\n"
                f"🧩 *Variant:* `{safe(r.get('maker_model'))}`\n"
                f"🚦 *Class:* `{safe(r.get('vehicle_class'))}`\n"
                f"⛽ *Fuel:* `{safe(r.get('fuel_type'))}`\n"
                f"♻️ *Norms:* `{safe(r.get('fuel_norms'))}`\n"
                f"🗓️ *Reg Date:* `{safe(r.get('registration_date'))}`\n"
                f"🛡️ *Insurance:* `{safe(r.get('insurance_company'))}` till `{safe(r.get('insurance_expiry') or r.get('insurance_upto'))}`\n"
                f"🏋️ *Fitness:* `{safe(r.get('fitness_upto'))}`\n"
                f"📄 *PUC:* `{safe(r.get('puc_upto'))}`\n"
                f"💸 *Tax Paid Till:* `{safe(r.get('tax_upto'))}`\n"
                f"📍 *RTO:* `{safe(r.get('rto'))}`\n"
                f"🏙️ *City:* `{safe(r.get('city'))}`\n"
                f"🏠 *Address:* `{safe(r.get('address'))}`\n"
                f"📞 *Phone:* `{safe(r.get('phone'))}`\n"
                "👨‍💻 *Powered by:* AstenX OSINT"
            )
            await update.message.reply_text(msg, parse_mode="Markdown")

        elif mode == "number":
            number = input_value.strip().replace("+", "")
            await asyncio.sleep(1.2)
            data = fetch_data(number)

            msg = f"📞 *Number:* `{number}`\n"
            if data['caller_name'] != "N/A":
                msg += f"👤 *Caller Name:* {data['caller_name']}\n"
            if data['name'] != "N/A":
                msg += f"📘 *Facebook Name:* {data['name']}\n"
            if data['location'] != "N/A":
                msg += f"📍 *Location:* {data['location']}\n"
            if data['operator'] != "N/A":
                msg += f"📶 *Operator:* {data['operator']}\n"
            if data['facebook'] != "N/A":
                msg += f"🔗 *Facebook:* [Link]({data['facebook']})\n"
            if data['photo'] != "N/A":
                msg += f"🖼️ *Photo:* [Click Here]({data['photo']})"
            await update.message.reply_markdown(msg)

        elif mode == "insta":
            res = requests.get(f"https://api-ig-info-eternal.vercel.app/?username={input_value}")
            if res.status_code != 200:
                await update.message.reply_text(f"❌ Error: API returned status {res.status_code}")
                return
            r = res.json()
            u = r.get("user")
            if not u or not u.get("profile_pic_url"):
                await update.message.reply_text("❌ Error: User info not found or incomplete.")
                return
            p = r.get("last_post", {})
            post_info = (
                f"\n\n*🕸️ Last Post Info:*\n🆔 *Post ID:* `{p.get('id', 'NA')}`\n"
                f"🔗 *Shortcode:* `{p.get('shortcode', 'NA')}`\n"
                f"❤️ *Likes:* `{p.get('likes', 'NA')}`\n"
                f"💬 *Comments:* `{p.get('comments', 'NA')}`\n"
                f"👁️ *Views:* `{p.get('views', 0)}`"
            ) if p else "\n\n*🕸️ Last Post Info:*\n_No posts available_"

            caption = (
                f"*📸 Instagram Profile Info:*\n\n"
                f"👤 *Username:* `{u.get('username', 'NA')}`\n"
                f"📛 *Full Name:* `{u.get('full_name', 'NA')}`\n"
                f"👥 *Followers:* `{u.get('followers', 'NA')}`\n"
                f"➡️ *Following:* `{u.get('following', 'NA')}`\n"
                f"📝 *Posts:* `{u.get('posts', 'NA')}`\n"
                f"🔵 *Verified:* `{'✅' if u.get('verified') else '❌'}`\n"
                f"🔐 *Private:* `{'✅' if u.get('private') else '❌'}`\n"
                f"🏢 *Business:* `{'✅' if u.get('business_account') else '❌'}`\n"
                f"🧬 *Bio:* `{u.get('bio', 'NA')}`{post_info}"
            )
            await update.message.reply_photo(
                photo=u.get("profile_pic_url"),
                caption=caption,
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(str(e))
        await update.message.reply_text(f"❌ Error: {str(e)}")

# Admin Commands
async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("❗ Usage: /premium <user_id>")
        return
    try:
        user_id = str(context.args[0])
        user = get_user(user_id)
        user["premium_until"] = time.time() + PREMIUM_DAYS * 86400
        set_user(user_id, user)
        await update.message.reply_text(f"✅ Premium activated for user {user_id} for {PREMIUM_DAYS} days.")
    except:
        await update.message.reply_text("❌ Invalid user ID or failed to set premium.")

async def statics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    db = all_users()
    total = len(db)
    deleted = sum(1 for u in db.values() if not u)
    active = total - deleted
    await update.message.reply_text(
        f"📊 BOT STATISTICS\n\n"
        f"▪️Created: {BOT_CREATED_DATE}\n"
        f"▪️Users: {total}\n"
        f"▫️Active: {active}\n"
        f"▫️Deleted: {deleted}"
    )

async def closed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    set_maintenance(True)
    await update.message.reply_text("🚧 Bot is now in *Maintenance Mode*!", parse_mode="Markdown")

async def asten(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    set_maintenance(False)
    await update.message.reply_text("✅ Bot is now *Active* again!", parse_mode="Markdown")

# Main
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("premium", premium))
    app.add_handler(CommandHandler("statics", statics))
    app.add_handler(CommandHandler("closed", closed))
    app.add_handler(CommandHandler("asten", asten))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot is running...")
    app.run_polling()