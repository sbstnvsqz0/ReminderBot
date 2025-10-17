import os
import sqlite3
from datetime import datetime
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

# --- Load environment ---
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
DB_FILE = "reminders.db"

# --- Database ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            hour TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def add_reminder_db(description, hour):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO reminders (description, hour) VALUES (?, ?)", (description, hour))
    conn.commit()
    conn.close()

def delete_reminder_db(reminder_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM reminders WHERE id=?", (reminder_id,))
    conn.commit()
    conn.close()

def get_all_reminders():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, description, hour FROM reminders")
    rows = cur.fetchall()
    conn.close()
    return rows

# --- Bot commands ---
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        hour = context.args[0]
        description = " ".join(context.args[1:])
        datetime.strptime(hour, "%H:%M")  # validate time
        add_reminder_db(description, hour)
        await update.message.reply_text(f"✅ Reminder added: '{description}' at {hour}")
    except (IndexError, ValueError):
        await update.message.reply_text("❗ Usage: /add HH:MM Description")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        reminder_id = int(context.args[0])
        delete_reminder_db(reminder_id)
        await update.message.reply_text(f"🗑️ Reminder {reminder_id} deleted.")
    except (IndexError, ValueError):
        await update.message.reply_text("❗ Usage: /delete ID")

async def show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reminders = get_all_reminders()
    if not reminders:
        await update.message.reply_text("📭 No reminders yet.")
        return
    msg = "⏰ *Your reminders:*\n"
    for rid, desc, hour in reminders:
        msg += f"{rid}. {desc} — at {hour}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

# --- Reminder sender ---
async def send_reminders(app):
    now = datetime.now().strftime("%H:%M")
    reminders = get_all_reminders()
    for _, desc, hour in reminders:
        if hour == now:
            await app.bot.send_message(chat_id=CHAT_ID, text=f"🔔 Reminder: {desc}")

# --- Scheduler ---
def start_scheduler(app, loop):
    scheduler = AsyncIOScheduler(event_loop=loop)

    async def job():
        await send_reminders(app)

    scheduler.add_job(job, "cron", minute="*")
    scheduler.start()
    print("🕒 Scheduler started.")

# --- Main ---
def main():
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(CommandHandler("show", show))

    # Get the running loop
    loop = asyncio.get_event_loop()

    # Start scheduler
    start_scheduler(app, loop)
    print("✅ Bot and scheduler started!")

    print("🚀 Bot is running...")
    app.run_polling()  # synchronous; handles its own async loop

if __name__ == "__main__":
    main()
