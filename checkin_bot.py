import os
import json
import logging
import pytz
from datetime import datetime
from io import BytesIO

import gspread
import pytesseract
from PIL import Image
from oauth2client.service_account import ServiceAccountCredentials
from fuzzywuzzy import fuzz

from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    CommandHandler,
    ContextTypes,
)

# === CONFIG ===
SHEET_NAME = "Walkathon 2025 Guests Lists For Bot"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1qKZSQPbLY9SlHGHxX7dCm66kuYS4krtY6Mc01GjhbOQ"
TIMEZONE = "America/Chicago"
TELEGRAM_GROUP_ID = "-1002649361802"

# === GOOGLE CREDS (from GitHub secret) ===
google_creds_str = os.environ.get("WALKATHONPASSSYSTEM")
if not google_creds_str:
    raise EnvironmentError("Missing WALKATHONPASSSYSTEM env variable.")
google_creds = json.loads(google_creds_str)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
gspread_client = gspread.authorize(creds)
sheet = gspread_client.open_by_url(SHEET_URL).worksheet(SHEET_NAME)

# === SETUP LOGGER ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === HELPER FUNCTIONS ===

def get_current_time():
    return datetime.now(pytz.timezone(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")

def find_guest_by_text(text):
    text = text.strip().upper()
    guests = sheet.get_all_records()
    for i, guest in enumerate(guests):
        if guest['Registration ID'].strip().upper() == text:
            return i + 2, guest  # offset by 2 for header + 1-index
    return None, None

def fuzzy_find_by_name(name):
    name = name.strip().lower()
    guests = sheet.get_all_records()
    best_score, best_index, best_guest = 0, None, None
    for i, guest in enumerate(guests):
        score = fuzz.partial_ratio(name, guest['Name'].lower())
        if score > best_score:
            best_score = score
            best_index = i + 2
            best_guest = guest
    return (best_index, best_guest) if best_score >= 70 else (None, None)

def mark_arrival(row_index):
    sheet.update_cell(row_index, 6, "Arrived")  # Status
    sheet.update_cell(row_index, 7, get_current_time())  # Check-In Time

# === TELEGRAM BOT HANDLERS ===

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = await update.message.photo[-1].get_file()
    image_bytes = BytesIO()
    await photo.download_to_memory(out=image_bytes)
    image_bytes.seek(0)
    text = pytesseract.image_to_string(Image.open(image_bytes)).strip()

    row_index, guest = find_guest_by_text(text)
    if not guest:
        await update.message.reply_text(f"❌ Could not identify guest from: {text}")
        return

    mark_arrival(row_index)
    message = f"✅ Guest *{guest['Name']}* ({guest['Guest Type']}) has arrived!\n🕒 {get_current_time()}"
    await context.bot.send_message(chat_id=TELEGRAM_GROUP_ID, text=message, parse_mode="Markdown")

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /status <Registration ID>")
        return
    reg_id = " ".join(context.args).strip()
    _, guest = find_guest_by_text(reg_id)
    if not guest:
        await update.message.reply_text("❌ Guest not found.")
        return
    await update.message.reply_text(f"Guest: {guest['Name']} ({guest['Guest Type']})\nStatus: {guest['Status']}")

async def cmd_b(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /b <guest name>")
        return
    name_query = " ".join(context.args).strip()
    _, guest = fuzzy_find_by_name(name_query)
    if not guest:
        await update.message.reply_text("❌ No matching guest found.")
        return
    status = guest["Status"]
    checkin = guest.get("Check-In Time", "N/A")
    msg = (
        f"Guest: {guest['Name']} ({guest['Guest Type']})\n"
        f"Status: {status}"
    )
    if status.lower() == "arrived":
        msg += f"\n🕒 Arrived at: {checkin}"
    await update.message.reply_text(msg)

async def cmd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    guests = sheet.get_all_records()

    ca_guests = [g for g in guests if g["Guest Type"] == "CA"]
    pa_guests = [g for g in guests if g["Guest Type"] == "PA"]

    ca_arrived = [g for g in ca_guests if g["Status"].lower() == "arrived"]
    pa_arrived = [g for g in pa_guests if g["Status"].lower() == "arrived"]

    ca_names = "\n".join([f"• {g['Name']} ({g.get('Check-In Time', 'Time Unknown')})" for g in ca_arrived])
    pa_names = "\n".join([f"• {g['Name']} ({g.get('Check-In Time', 'Time Unknown')})" for g in pa_arrived])

    msg = (
        f"📊 *Arrival Summary*\n\n"
        f"👥 *CA Guests*: {len(ca_arrived)}/{len(ca_guests)} arrived\n"
        f"{ca_names or '_None yet_'}\n\n"
        f"👔 *PA Guests*: {len(pa_arrived)}/{len(pa_guests)} arrived\n"
        f"{pa_names or '_None yet_'}"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")


# === BOT STARTUP ===

def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise EnvironmentError("TELEGRAM_TOKEN not set.")
    
    app = ApplicationBuilder().token(token).build()
    
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("b", cmd_b))
    app.add_handler(CommandHandler("summary", cmd_summary))

    logger.info("🚀 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
