#!/usr/bin/env python3
"""
ربات Referral برای کانال مانتو شیک و پیک
@ShikopickVIPBot
"""

import logging
import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

# ─── تنظیمات ───────────────────────────────────────────────
TOKEN = "8978730869:AAEEe0Ut39XbBCWpsxMEjfmnUFHGP4s6fGs"
CHANNEL_USERNAME = "@Poshak_shikopick"
CHANNEL_ID = "@Poshak_shikopick"
ADMIN_USERNAME = "@shikopickAdmin"
BOT_USERNAME = "ShikopickVIPBot"

# جوایز بر اساس تعداد دعوت
REWARDS = {
    3:  "🎁 کد تخفیف ۱۰٪ — کد: SHIKO10",
    7:  "🎀 کد تخفیف ۲۰٪ — کد: SHIKO20",
    15: "👑 تخفیف ۳۰٪ + ارسال رایگان — کد: SHIKO30",
}

# ─── دیتابیس ───────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("shikopick.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            full_name   TEXT,
            referrer_id INTEGER,
            invite_count INTEGER DEFAULT 0,
            joined_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS claimed_rewards (
            user_id     INTEGER,
            reward_level INTEGER,
            PRIMARY KEY (user_id, reward_level)
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("shikopick.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def register_user(user_id, username, full_name, referrer_id=None):
    conn = sqlite3.connect("shikopick.db")
    c = conn.cursor()
    # اگر قبلاً ثبت نشده
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    exists = c.fetchone()
    if not exists:
        c.execute(
            "INSERT INTO users (user_id, username, full_name, referrer_id) VALUES (?,?,?,?)",
            (user_id, username, full_name, referrer_id)
        )
        # اضافه کردن به تعداد دعوت دعوت‌کننده
        if referrer_id and referrer_id != user_id:
            c.execute(
                "UPDATE users SET invite_count = invite_count + 1 WHERE user_id=?",
                (referrer_id,)
            )
        conn.commit()
        conn.close()
        return True  # کاربر جدید
    conn.close()
    return False  # قبلاً ثبت شده

def get_invite_count(user_id):
    conn = sqlite3.connect("shikopick.db")
    c = conn.cursor()
    c.execute("SELECT invite_count FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def get_claimed_rewards(user_id):
    conn = sqlite3.connect("shikopick.db")
    c = conn.cursor()
    c.execute("SELECT reward_level FROM claimed_rewards WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def claim_reward(user_id, level):
    conn = sqlite3.connect("shikopick.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO claimed_rewards (user_id, reward_level) VALUES (?,?)", (user_id, level))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def get_all_stats():
    conn = sqlite3.connect("shikopick.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    c.execute("SELECT full_name, invite_count FROM users ORDER BY invite_count DESC LIMIT 5")
    top = c.fetchall()
    conn.close()
    return total, top

# ─── بررسی عضویت در کانال ──────────────────────────────────
async def is_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ─── هندلرها ───────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referrer_id = int(args[0]) if args and args[0].isdigit() else None

    # ثبت کاربر
    is_new = register_user(
        user.id,
        user.username or "",
        user.full_name,
        referrer_id
    )

    # بررسی عضویت در کانال
    member = await is_member(user.id, context)

    if not member:
        keyboard = [[InlineKeyboardButton(
            "📢 عضو کانال شو", url=f"https://t.me/Poshak_shikopick"
        )], [InlineKeyboardButton(
            "✅ عضو شدم!", callback_data="check_member"
        )]]
        await update.message.reply_text(
            f"👗 *سلام {user.first_name} عزیز!*\n\n"
            f"به ربات VIP مانتو شیک و پیک خوش اومدی! 🎉\n\n"
            f"برای استفاده از ربات، اول باید عضو کانال ما بشی 👇",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    await show_main_menu(update, context, user, is_new)

async def show_main_menu(update, context, user, is_new=False):
    invite_count = get_invite_count(user.id)
    invite_link = f"https://t.me/{BOT_USERNAME}?start={user.id}"

    # محاسبه جایزه بعدی
    next_reward = None
    for level in sorted(REWARDS.keys()):
        if invite_count < level:
            next_reward = level
            break

    progress_text = ""
    if next_reward:
        remaining = next_reward - invite_count
        progress_text = f"\n📍 تا جایزه بعدی: *{remaining} دعوت* دیگه لازم داری"

    welcome = "🎊 *خوش اومدی!* " if is_new else ""
    text = (
        f"{welcome}👗 *مانتو شیک و پیک*\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 نام: {user.full_name}\n"
        f"🔗 دعوت‌های موفق: *{invite_count} نفر*"
        f"{progress_text}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"🔗 *لینک دعوت اختصاصی تو:*\n"
        f"`{invite_link}`\n\n"
        f"این لینک رو برای دوستات بفرست و جایزه بگیر! 🎁"
    )

    keyboard = [
        [InlineKeyboardButton("🎁 جوایز من", callback_data="my_rewards"),
         InlineKeyboardButton("📊 آمار من", callback_data="my_stats")],
        [InlineKeyboardButton("🏆 برترین‌ها", callback_data="leaderboard")],
        [InlineKeyboardButton("📢 اشتراک‌گذاری لینک", 
                              url=f"https://t.me/share/url?url={invite_link}&text=بیا+مانتوهای+شیک+و+پیک+ببین+🛍️")],
    ]

    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    data = query.data

    if data == "check_member":
        member = await is_member(user.id, context)
        if member:
            await show_main_menu(update, context, user, is_new=False)
        else:
            await query.answer("❌ هنوز عضو نشدی! اول کانال رو جوین کن.", show_alert=True)

    elif data == "my_stats":
        invite_count = get_invite_count(user.id)
        invite_link = f"https://t.me/{BOT_USERNAME}?start={user.id}"
        claimed = get_claimed_rewards(user.id)

        rewards_status = ""
        for level, reward in sorted(REWARDS.items()):
            if level in claimed:
                rewards_status += f"✅ {level} دعوت: دریافت شد\n"
            elif invite_count >= level:
                rewards_status += f"🔔 {level} دعوت: قابل دریافت!\n"
            else:
                rewards_status += f"🔒 {level} دعوت: {level - invite_count} دعوت دیگه\n"

        text = (
            f"📊 *آمار من*\n\n"
            f"👤 {user.full_name}\n"
            f"🔗 دعوت‌های موفق: *{invite_count} نفر*\n\n"
            f"🎁 *وضعیت جوایز:*\n{rewards_status}\n"
            f"🔗 لینک دعوت:\n`{invite_link}`"
        )
        keyboard = [[InlineKeyboardButton("🔙 برگشت", callback_data="back_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "my_rewards":
        invite_count = get_invite_count(user.id)
        claimed = get_claimed_rewards(user.id)

        text = f"🎁 *جوایز شما*\n\n"
        keyboard_rows = []

        for level, reward in sorted(REWARDS.items()):
            if level in claimed:
                text += f"✅ *{level} دعوت:* {reward}\n_(دریافت شده)_\n\n"
            elif invite_count >= level:
                text += f"🎊 *{level} دعوت:* {reward}\n_(آماده دریافت!)_\n\n"
                keyboard_rows.append([InlineKeyboardButton(
                    f"🎁 دریافت جایزه {level} دعوت", callback_data=f"claim_{level}"
                )])
            else:
                text += f"🔒 *{level} دعوت:* هنوز {level - invite_count} دعوت دیگه لازم داری\n\n"

        keyboard_rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="back_main")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard_rows), parse_mode="Markdown")

    elif data.startswith("claim_"):
        level = int(data.split("_")[1])
        invite_count = get_invite_count(user.id)
        claimed = get_claimed_rewards(user.id)

        if level in claimed:
            await query.answer("✅ این جایزه رو قبلاً گرفتی!", show_alert=True)
        elif invite_count < level:
            await query.answer(f"❌ هنوز {level - invite_count} دعوت دیگه لازم داری!", show_alert=True)
        else:
            claim_reward(user.id, level)
            reward_text = REWARDS[level]
            await query.edit_message_text(
                f"🎉 *تبریک!*\n\n"
                f"جایزه‌ات رو دریافت کردی:\n\n"
                f"*{reward_text}*\n\n"
                f"این کد رو موقع خرید به ادمین {ADMIN_USERNAME} بده 🛍️",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 برگشت", callback_data="back_main")
                ]])
            )

    elif data == "leaderboard":
        total, top_users = get_all_stats()
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        board = ""
        for i, (name, count) in enumerate(top_users):
            board += f"{medals[i]} {name}: *{count} دعوت*\n"

        text = (
            f"🏆 *برترین دعوت‌کنندگان*\n\n"
            f"{board}\n"
            f"👥 کل کاربران ربات: *{total} نفر*"
        )
        keyboard = [[InlineKeyboardButton("🔙 برگشت", callback_data="back_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "back_main":
        await show_main_menu(update, context, user)

# ─── دستور ادمین ───────────────────────────────────────────
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if f"@{user.username}" != ADMIN_USERNAME:
        return
    total, top_users = get_all_stats()
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    board = ""
    for i, (name, count) in enumerate(top_users):
        board += f"{medals[i]} {name}: {count} دعوت\n"
    await update.message.reply_text(
        f"📊 *آمار کلی ربات*\n\n"
        f"👥 کل کاربران: *{total} نفر*\n\n"
        f"🏆 برترین دعوت‌کنندگان:\n{board}",
        parse_mode="Markdown"
    )

# ─── اجرا ──────────────────────────────────────────────────
def main():
    init_db()
    logging.basicConfig(level=logging.INFO)

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("✅ ربات شیک و پیک در حال اجراست...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
