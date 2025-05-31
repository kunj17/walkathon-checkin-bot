import os
import json
import time
import threading
import numpy as np
from io import BytesIO
from datetime import datetime
from pyzbar.pyzbar import decode

import gspread
import cv2
from PIL import Image
from pyzbar.pyzbar import decode
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
)
from fuzzywuzzy import process

# === Environment Config ===
GOOGLE_CREDS = {
  "type": "service_account",
  "project_id": "walkathon-pass-system",
  "private_key_id": "b25ea2ef9fbda7c759205d1cb45fb8fe7b9e4108",
  "private_key": """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCNXLhC7xK6nlOz
7olIZBWRA/kufLQ4KSaJkVLRi6FXJRQ1O30F+JVFV2S38W48/f4cwYj7yKFy7quw
k6qfyBTZGHLmhF7QBa9lEABLouojdLAzGVrdWUjMs+aDT/bQBP/0x+vMlY+bThhY
tlAeKXy3evfTOw2kpankY78QSVOt5HE+dQqZS8Ac4s/9BckiWrlRLpikMRlKbW5Y
Ln22pxEZuHsWfxS9WSVd7sydzYqzqIAbfErXYenAQGh1/ahVokBb64/xXWIQqUyk
c34elR6ITZuQ9aBjGoIq6kfBvD6SA1a/gyqR67lzuRLfiFVp/qiFP/etCrzOxKHX
qMtFHLc3AgMBAAECggEADMDBCgWepbtdR2EaFxYzlxUwSInAVt8cUB9BXqolvUJ/
fWkg5FMCx6V7IdhKeH72V9ditkq2Is12K8RTb+ReQFLWVGy76P4HG5HDLqlDgKNc
UGyiWxz2iZEi49UCkGdP3nnSw6HFuasX9mWsLXk5fFjZo4xmTksSKQqR1OeCM+PC
6MYfQCUDcy0F866FfYhhCtZZs0Ke3FAMde2pvp1W9N87O1BhWI6CDuhGGLDe4FqQ
I7VTy+9a8WgbW1oiB9E6uxPtz0PjUYJxFjYwG9SsEIVND1lHeomd1zQQyYaXpR5Y
J//geT1LaxaIwAF8Aa35oONkvSBGK7ist9RFLzuzcQKBgQDFjws5XXr3YD6DfGPr
go05yN+TRxCDAH8Le+uLsO7LLl86v5rR5a9dF9r5X/cbl3Trdx0fG56K+RW1SiNX
zqgi64sheuAwhEEhIA0Santbprpfarw8t3TTFE1mHL7dC5XQubfCVNrEHGegnT5j
SVMtYdNmee0aZNyQe7j41g6HPQKBgQC3LfUH2RDDQXZNIU1quV88BSyVccr9G+0A
c6na2qax7p0oHtPq407qLRIrxZkkQQwNrTFzjgqr3m71LqDxwcYzstZ6Rmfh8Hjk
ZGhdK+9v1ZU10R5eo3E5WWsWksd3bfSukfFZ4l+3aD3LsOGYWD+/tCLw0M0GbycB
WfRH/FO/gwKBgH40FQ1+ZDFncEf6zLIEYkeJxRmGikvFo2MotJ42VzXA1+DlyfdQ
bShhNueboHYl2PEa1KWstSk+WdnIFK/hOpOkOOsYXeNgeWK54N/k2g0Ag4q02q9G
2wCEtbUHo/39iqUeHv+ryV0CcEiwasxuaQ5SsgOC3C7CRAygnNeJlxpZAoGBAIks
RCLVXSUqv2Fw/91c5cE3irR622yBXhCJjPfT5yK1skBaHY33HKBmkgXvWgf5IgKX
4MFM7BbaYjL+8Q05c6hBUzWLxb0/a/h0bGbhQNN5mNwNNnXeZSpyGKx1zCNWVvXn
WlpaGB1rVWNUmQuRgmOXjNbTNcWMtSPg7fp+LWTrAoGAXQBRsQSkbPkNKudYCSIZ
vJf0hLaUtYrhj1TwYXvIDoKe+Qc8Xw4YWB5wtkMSlveqnXeDUAAAT5bd1UlmSFPP
U1tGXohQQpjArFjgwFnajBVBqxepihTpYxuwAcfXNt7YTtsjMJeIlIdLTz8qj6u8
E1np64V3P3hOEb/8jqHCLpg=
-----END PRIVATE KEY-----""",
  "client_email": "walkathon-pass-bot@walkathon-pass-system.iam.gserviceaccount.com",
  "client_id": "104023892724561366194",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/walkathon-pass-bot@walkathon-pass-system.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = "-1002649361802"

SHEET_URL = "https://docs.google.com/spreadsheets/d/1qKZSQPbLY9SlHGHxX7dCm66kuYS4krtY6Mc01GjhbOQ"
SHEET_NAME = "Walkathon 2025 Guests Lists For Bot"

# === Google Sheets Auth ===
SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDS, SCOPES)
gspread_client = gspread.authorize(creds)
sheet = gspread_client.open_by_url(SHEET_URL).worksheet(SHEET_NAME)

# === Bot Utility Functions ===

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

def extract_registration_id_from_bytes(img_bytes):
    try:
        # Save for manual debugging (always!)
        with open("debug_telegram_image.jpg", "wb") as f:
            f.write(img_bytes)

        # Decode image
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            print("❌ Could not decode image.")
            return None

        height, width, _ = img.shape
        print(f"📐 Image dimensions: {width}x{height}")

        # Try full image first
        decoded_full = decode(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
        if decoded_full:
            reg_id = decoded_full[0].data.decode('utf-8').strip().upper()
            print(f"✅ QR (full image): {reg_id}")
            return reg_id

        # Try bottom crop if full fails (where QR likely is)
        crop = img[int(height * 0.55):, :]
        decoded_crop = decode(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY))
        if decoded_crop:
            reg_id = decoded_crop[0].data.decode('utf-8').strip().upper()
            print(f"✅ QR (cropped): {reg_id}")
            return reg_id

        print("❌ QR decode failed.")
        return None

    except Exception as e:
        print(f"🔥 Exception during QR decode: {e}")
        return None




# === Telegram Handlers ===

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Force Telegram to give you the highest-resolution version
    photo = update.message.photo
    largest = max(photo, key=lambda p: p.file_size)
    file = await largest.get_file()
    img_bytes = await file.download_as_bytearray()
    reg_id = extract_registration_id_from_bytes(img_bytes)


    if not reg_id:
        await update.message.reply_text("❌ Could not read QR code from image.")
        return

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
        "🤖 *Walkathon Check-in Bot Help:*\n\n"
        "/summary – Show arrival stats\n"
        "/status <Reg ID> – Check guest status\n"
        "/b <name> – Search by name\n"
        "📸 Upload a parking pass photo with QR code to check-in.",
        parse_mode='Markdown'
    )

def run_self_destruct_timer():
    def shutdown():
        print("⏳ 2 hours reached. Shutting down...")
        time.sleep(7200)
        os._exit(0)
    threading.Thread(target=shutdown, daemon=True).start()

# === Main Bot Startup ===

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
