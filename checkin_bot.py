import os
import json
import time
import threading
from io import BytesIO
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from fuzzywuzzy import process
from PIL import Image

# === Google Sheets Auth via GitHub Secret ===
GOOGLE_CREDS = json.loads(os.environ['WALKATHONPASSSYSTEM'])
SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDS, SCOPES)
gspread_client = gspread.authorize(creds)

# === Sheet & Telegram Settings ===
SHEET_URL = "https://docs.google.com/spreadsheets/d/1qKZSQPbLY9SlHGHx7dCm66kuYS4krtY6Mc01GjhbOQ/edit"
SHEET_NAME = "Walkathon 2025 Guests Lists For Bot"
CHAT_ID = "-1002649361802"
TOKEN = os.getenv("TELEGRAM_TOKEN")

sheet = gspread_client.open_by_url(SHEET_URL).worksheet(SHEET_NAME)

def get_guest_list():
    records = sheet.get_all_records()
    return {row['Registration ID']: row for row in records}, records

def mark_arrived(reg_id):
    cell = sheet.find(reg_id)
    row = cell.row
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.update_cell(row, sheet.find("Status").col, "Arrived")
    sheet.update_cell(row, sheet.find("Check-In Time").col, now)
    return row

def extract_registration_id_from_image(image_path):
    # Simulated for demo: extract registration ID from image filename
    return os.path.splitext(os.path.basename(image_path))[0].upper()

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await photo.get_file()
    img_bytes = await file.download_as_bytearray()
    img = Image.open(BytesIO(img_bytes))
    reg_id = extract_registration_id_from_image(file.file_path)  # simulate barcode read

    guests_by_id, _ = get_guest_list()
    if reg_id not in guests_by_id:
        await update.message.reply_text(f"⚠️ No guest found for Reg ID `{reg_id}`", parse_mode='Markdown')
        return

    guest = guests_by_id[reg_id]
    if guest['Status'].lower() == 'arrived':
        await update.message.reply_text(f"✅ {guest['Name']} already checked in.")
        return

    mark_arrived(reg_id)
    await context.bot.send_message(chat_id=CHAT_ID, text=f"🟢 {guest['Name']} ({guest['Guest Type']}) has arrived.")
    await update.message.reply_text(f"🎉 Welcome {guest['Name']}! Check-in confirmed.")

async def cmd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, guests = get_guest_list()
    ca = [g for g in guests if g['Guest Type'] == 'CA' and g['Status'].lower() == 'arrived']
    pa = [g for g in guests if g['Guest Type'] == 'PA' and g['Status'].lower() == 'arrived']

    msg = f"📊 Check-in Summary:\n\n✅ CA Guests: {len(ca)}\n✅ PA Guests: {len(pa)}\n\n"
    if ca:
        msg += "👥 CA Arrived:\n" + "\n".join([g['Name'] for g in ca]) + "\n\n"
    if pa:
        msg += "👥 PA Arrived:\n" + "\n".join([g['Name'] for g in pa])
    await update.message.reply_text(msg)

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /status <Registration ID>")
        return
    reg_id = args[0].upper()
    guests_by_id, _ = get_guest_list()
    if reg_id not in guests_by_id:
        await update.message.reply_text("❌ Registration ID not found")
        return
    guest = guests_by_id[reg_id]
    await update.message.reply_text(f"👤 {guest['Name']}\nStatus: {guest['Status']}\nCheck-in Time: {guest['Check-In Time']}")

async def cmd_b(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name_query = " ".join(context.args)
    if not name_query:
        await update.message.reply_text("Usage: /b <name>")
        return
    _, guests = get_guest_list()
    names = [g['Name'] for g in guests]
    best, _ = process.extractOne(name_query, names)
    guest = next(g for g in guests if g['Name'] == best)
    await update.message.reply_text(f"👤 {guest['Name']}\nStatus: {guest['Status']}\nCheck-in Time: {guest['Check-In Time']}")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Walkathon Check-in Bot Help:\n\n"
        "/summary – Show arrival stats\n"
        "/status <Reg ID> – Check one guest\n"
        "/b <name> – Search by name\n"
        "📸 Upload a parking pass photo to check-in."
    )

def run_self_destruct_timer():
    def shutdown():
        print("⏳ 2 hours reached. Shutting down...")
        time.sleep(7200)
        os._exit(0)
    threading.Thread(target=shutdown).start()

# === Run Bot ===
if __name__ == '__main__':
    run_self_destruct_timer()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("summary", cmd_summary))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("b", cmd_b))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("start", cmd_help))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("🚀 Walkathon Check-in Bot is now running...")
    app.run_polling()
