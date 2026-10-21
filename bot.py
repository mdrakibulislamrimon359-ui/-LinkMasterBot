import os
import json
import logging
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters,
)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_USERNAMES = {
    x.strip().lstrip("@").lower()
    for x in os.getenv("ADMIN_USERNAMES", "RJteam1,Mdshahadot20,offlinoffline").split(",")
    if x.strip()
}
# Optional stronger security: add verified numeric Telegram user IDs here.
ADMIN_IDS = {
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}
TARGET_CHAT_IDS = [
    x.strip() for x in os.getenv("TARGET_CHAT_IDS", "").split(",") if x.strip()
]
INTERVAL_MINUTES = max(1, int(os.getenv("POST_INTERVAL_MINUTES", "20")))
DATA_FILE = Path("bot_data.json")

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("linkbot")

CATEGORIES = {
    "facebook": "📘 Facebook",
    "tiktok": "🎵 TikTok",
    "telegram": "✈️ Telegram",
    "youtube": "▶️ YouTube",
    "contacts": "☎️ Developer Contact",
    "apps": "📱 Apps Information",
    "other": "🔗 Other Links",
}


DEFAULT_LINKS = {
    "facebook": [
        {"title": "Facebook Link 1", "url": "https://www.facebook.com/share/19dBFje8oX/"},
        {"title": "Facebook Profile", "url": "https://www.facebook.com/profile.php?id=61595073882633"},
        {"title": "Facebook Link 3", "url": "https://www.facebook.com/share/1DtEmf47f1/"},
        {"title": "Facebook Link 4", "url": "https://www.facebook.com/share/1DogLWMp9Z/"},
    ],
    "tiktok": [
        {"title": "TikTok lyrics.song333", "url": "https://www.tiktok.com/@lyrics.song333"},
        {"title": "TikTok lyris.rakib0.1", "url": "https://www.tiktok.com/@lyris.rakib0.1"},
    ],
    "telegram": [
        {"title": "@RJteam1owners", "url": "https://t.me/RJteam1owners"},
        {"title": "@offlinoffline", "url": "https://t.me/offlinoffline"},
        {"title": "@Mdshahadot20", "url": "https://t.me/Mdshahadot20"},
        {"title": "@Otoupdaterenderbot", "url": "https://t.me/Otoupdaterenderbot"},
        {"title": "iPhone LLC", "url": "https://t.me/iphonellc"},
        {"title": "RJteam123890", "url": "https://t.me/RJteam123890"},
    ],
    "youtube": [
        {"title": "YouTube @rakib22", "url": "https://youtube.com/@rakib22?si=6nr4bhuCX0OfaNz0"},
        {"title": "YouTube Channel 2", "url": "https://www.youtube.com/channel/UCB-rtEqdI_B3SOoMg901tyQ"},
    ],
    "contacts": [
        {"title": "Developer 1 — 01742967532", "url": "https://wa.me/8801742967532"},
        {"title": "Developer 2 — 01783060751", "url": "https://wa.me/8801783060751"},
        {"title": "Developer 3 — 01779962693", "url": "https://wa.me/8801779962693"},
        {"title": "Developer 4 — +8801740697112", "url": "https://wa.me/8801740697112"},
    ],
    "apps": [
        {"title": "অ্যাপসের কাজ শিখতে বা কিনতে আমাদের সাথে থাকুন", "url": "https://t.me/RJteam1owners"},
    ],
    "other": [],
}


def load_data():
    default = {
        "links": DEFAULT_LINKS,
        "auto_enabled": False,
        "interval_minutes": INTERVAL_MINUTES,
        "post_index": 0,
        "posts": [],
    }
    if DATA_FILE.exists():
        try:
            saved = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            for key, value in default.items():
                if key not in saved:
                    saved[key] = value
            for key in CATEGORIES:
                saved.setdefault("links", {}).setdefault(key, [])
            return saved
        except (OSError, json.JSONDecodeError):
            log.exception("Could not read data file; starting with defaults.")
    return default


data = load_data()
user_states = {}


def save_data():
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DATA_FILE)


def is_admin(update: Update) -> bool:
    user = update.effective_user
    if not user:
        return False
    username = (user.username or "").lower()
    return user.id in ADMIN_IDS or username in ADMIN_USERNAMES


async def deny(update: Update):
    message = update.effective_message
    if message:
        await message.reply_text(
            "⛔ এই কাজটি শুধু অনুমোদিত অ্যাডমিন করতে পারবেন।\n"
            "আপনার numeric ID জানতে /myid দিন।"
        )


def main_menu():
    rows = [
        [InlineKeyboardButton("📘 Facebook", callback_data="cat:facebook"),
         InlineKeyboardButton("🎵 TikTok", callback_data="cat:tiktok")],
        [InlineKeyboardButton("✈️ Telegram", callback_data="cat:telegram"),
         InlineKeyboardButton("▶️ YouTube", callback_data="cat:youtube")],
        [InlineKeyboardButton("☎️ Developer Contact", callback_data="cat:contacts")],
        [InlineKeyboardButton("📱 Apps Information", callback_data="cat:apps"),
         InlineKeyboardButton("🔗 Other Links", callback_data="cat:other")],
        [InlineKeyboardButton("ℹ️ About / Help", callback_data="about")],
    ]
    return InlineKeyboardMarkup(rows)


def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Link", callback_data="admin:add"),
         InlineKeyboardButton("✏️ Edit Link", callback_data="admin:edit")],
        [InlineKeyboardButton("🗑 Delete Link", callback_data="admin:delete"),
         InlineKeyboardButton("📋 Manage Posts", callback_data="admin:posts")],
        [InlineKeyboardButton("📢 Post Now", callback_data="admin:postnow"),
         InlineKeyboardButton("⏱ Auto Post Settings", callback_data="admin:auto")],
        [InlineKeyboardButton("➕ Add Photo/Video Post", callback_data="admin:newpost")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="home")],
    ])


def back_keyboard(destination="home"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=destination)]])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "🌟 স্বাগতম!\n\n"
        "এখানে Facebook, TikTok, Telegram, YouTube ও অন্যান্য দরকারি লিংক পাবেন।\n"
        "নিচের ক্যাটাগরি থেকে বেছে নিন।",
        reply_markup=main_menu(),
    )


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.effective_message.reply_text(
        f"আপনার Telegram numeric user ID: {user.id}\n"
        f"Username: @{user.username}" if user.username else
        f"আপনার Telegram numeric user ID: {user.id}\nUsername নেই"
    )


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    await update.effective_message.reply_text("🛠 Admin Panel", reply_markup=admin_menu())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ব্যবহার:\n/start — মূল মেনু\n/admin — অ্যাডমিন প্যানেল\n"
        "/myid — আপনার numeric Telegram ID\n\n"
        "অ্যাডমিন প্যানেল থেকে লিংক Add/Edit/Delete, পোস্ট পরিচালনা এবং "
        "অটো পোস্ট চালু/বন্ধ করতে পারবেন।"
    )
    await update.effective_message.reply_text(text, reply_markup=main_menu())


def category_keyboard(category):
    items = data["links"].get(category, [])
    rows = []
    for i, item in enumerate(items):
        # Each link opens directly in Telegram's browser.
        rows.append([InlineKeyboardButton(item["title"], url=item["url"])])
    rows.append([InlineKeyboardButton("⬅️ Back to Categories", callback_data="home")])
    return InlineKeyboardMarkup(rows)


def all_link_choices(action):
    rows = []
    for category, title in CATEGORIES.items():
        for i, item in enumerate(data["links"].get(category, [])):
            rows.append([InlineKeyboardButton(
                f"{title}: {item['title'][:35]}",
                callback_data=f"{action}:{category}:{i}"
            )])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="admin")])
    return InlineKeyboardMarkup(rows)


async def show_link_list(query, category):
    items = data["links"].get(category, [])
    title = CATEGORIES.get(category, category)
    if not items:
        await query.edit_message_text(
            f"{title}\n\nএখনও কোনো লিংক যোগ করা হয়নি।",
            reply_markup=back_keyboard("home"),
        )
        return
    text = f"{title}\n\nলিংকে টাচ করলে সেটি খুলবে:"
    await query.edit_message_text(text, reply_markup=category_keyboard(category))


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    payload = query.data or ""

    if payload == "home":
        await query.edit_message_text("📂 ক্যাটাগরি নির্বাচন করুন:", reply_markup=main_menu())
        return
    if payload.startswith("cat:"):
        category = payload.split(":", 1)[1]
        await show_link_list(query, category)
        return
    if payload == "about":
        await query.edit_message_text(
            "📌 অ্যাপস ও সোশ্যাল লিংক এক জায়গায়।\n"
            "অ্যাডমিন যোগাযোগের জন্য Developer Contact দেখুন।",
            reply_markup=back_keyboard("home"),
        )
        return

    if payload == "admin":
        if not is_admin(update):
            return await query.edit_message_text("⛔ অনুমতি নেই।")
        await query.edit_message_text("🛠 Admin Panel", reply_markup=admin_menu())
        return

    if not is_admin(update):
        return await query.edit_message_text("⛔ এই অপশন শুধু অ্যাডমিনদের জন্য।")

    if payload == "admin:add":
        user_states[user.id] = {"action": "add"}
        await query.edit_message_text(
            "লিংক যোগ করতে এই ফরম্যাটে একটি মেসেজ পাঠান:\n\n"
            "category | নাম | https://example.com\n\n"
            "category: facebook, tiktok, telegram, youtube, contacts, apps, other",
            reply_markup=back_keyboard("admin"),
        )
    elif payload == "admin:edit":
        await query.edit_message_text(
            "যে লিংকটি এডিট করবেন সেটি বেছে নিন:",
            reply_markup=all_link_choices("edit"),
        )
    elif payload == "admin:delete":
        await query.edit_message_text(
            "যে লিংকটি ডিলিট করবেন সেটি বেছে নিন:",
            reply_markup=all_link_choices("delete"),
        )
    elif payload.startswith("delete:"):
        _, category, index = payload.split(":")
        index = int(index)
        if index < len(data["links"].get(category, [])):
            removed = data["links"][category].pop(index)
            save_data()
            await query.edit_message_text(
                f"🗑 ডিলিট হয়েছে: {removed['title']}",
                reply_markup=back_keyboard("admin"),
            )
        else:
            await query.edit_message_text("লিংকটি আর পাওয়া যাচ্ছে না।", reply_markup=back_keyboard("admin"))
    elif payload.startswith("edit:"):
        _, category, index = payload.split(":")
        index = int(index)
        if index < len(data["links"].get(category, [])):
            user_states[user.id] = {"action": "edit", "category": category, "index": index}
            item = data["links"][category][index]
            await query.edit_message_text(
                f"বর্তমান: {item['title']} | {item['url']}\n\n"
                "নতুন তথ্য পাঠান:\nনাম | https://example.com",
                reply_markup=back_keyboard("admin"),
            )
    elif payload == "admin:auto":
        data["auto_enabled"] = not data["auto_enabled"]
        save_data()
        state = "চালু" if data["auto_enabled"] else "বন্ধ"
        await query.edit_message_text(
            f"অটো পোস্ট এখন {state}।\n"
            f"বর্তমান বিরতি: {data['interval_minutes']} মিনিট\n\n"
            "বিরতি বদলাতে /setinterval 30-এর মতো কমান্ড দিন।",
            reply_markup=back_keyboard("admin"),
        )
    elif payload == "admin:postnow":
        await query.edit_message_text("এখন পোস্ট পাঠানো হচ্ছে…", reply_markup=back_keyboard("admin"))
        await post_next(context.application, force=True)
    elif payload == "admin:posts":
        posts = data.get("posts", [])
        text = "📋 সেভ করা পোস্ট:\n\n" + (
            "\n".join(f"{i+1}. {p.get('caption','(ক্যাপশন নেই)')[:70]}" for i, p in enumerate(posts))
            if posts else "এখনও কোনো পোস্ট সেভ করা নেই।"
        )
        await query.edit_message_text(text[:4000], reply_markup=back_keyboard("admin"))
    elif payload == "admin:newpost":
        user_states[user.id] = {"action": "newpost"}
        await query.edit_message_text(
            "এখন একটি টেক্সট, ছবি বা ভিডিও পাঠান। ক্যাপশনও দিতে পারবেন।\n"
            "এটি পোস্ট হিসেবে সেভ হবে। পরে /admin থেকে Post Now দিয়ে পাঠাতে পারবেন।",
            reply_markup=back_keyboard("admin"),
        )


async def receive_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    state = user_states.get(user.id)
    if not state:
        return
    if not is_admin(update):
        user_states.pop(user.id, None)
        return await deny(update)

    msg = update.effective_message
    action = state.get("action")

    if action == "add":
        raw = (msg.text or "").strip()
        parts = [x.strip() for x in raw.split("|", 2)]
        if len(parts) != 3:
            await msg.reply_text("ফরম্যাট ঠিক হয়নি। আবার পাঠান:\ncategory | নাম | https://example.com")
            return
        category, title, url = parts
        parsed = urlparse(url)
        if category not in CATEGORIES or not title or parsed.scheme not in ("http", "https") or not parsed.netloc:
            await msg.reply_text("ক্যাটাগরি বা URL সঠিক নয়। আবার চেষ্টা করুন।")
            return
        if any(x["url"] == url for x in data["links"][category]):
            await msg.reply_text("এই ক্যাটাগরিতে লিংকটি আগেই আছে।")
            return
        data["links"][category].append({"title": title, "url": url})
        save_data()
        user_states.pop(user.id, None)
        await msg.reply_text(f"✅ {CATEGORIES[category]}-তে “{title}” যোগ হয়েছে।", reply_markup=admin_menu())

    elif action == "edit":
        raw = (msg.text or "").strip()
        parts = [x.strip() for x in raw.split("|", 1)]
        if len(parts) != 2:
            await msg.reply_text("ফরম্যাট দিন: নতুন নাম | https://example.com")
            return
        title, url = parts
        parsed = urlparse(url)
        if not title or parsed.scheme not in ("http", "https") or not parsed.netloc:
            await msg.reply_text("নাম বা URL সঠিক নয়। আবার চেষ্টা করুন।")
            return
        category, index = state["category"], state["index"]
        if index >= len(data["links"].get(category, [])):
            user_states.pop(user.id, None)
            await msg.reply_text("লিংকটি আর পাওয়া যাচ্ছে না।")
            return
        data["links"][category][index] = {"title": title, "url": url}
        save_data()
        user_states.pop(user.id, None)
        await msg.reply_text("✅ লিংক আপডেট হয়েছে।", reply_markup=admin_menu())

    elif action == "newpost":
        post = {"caption": msg.caption or msg.text or ""}
        if msg.photo:
            post.update({"type": "photo", "file_id": msg.photo[-1].file_id})
        elif msg.video:
            post.update({"type": "video", "file_id": msg.video.file_id})
        elif msg.text:
            post.update({"type": "text", "text": msg.text})
        else:
            await msg.reply_text("টেক্সট, ছবি বা ভিডিও পাঠান।")
            return
        data.setdefault("posts", []).append(post)
        save_data()
        user_states.pop(user.id, None)
        await msg.reply_text("✅ পোস্ট সেভ হয়েছে। /admin → Post Now থেকে পাঠাতে পারবেন।", reply_markup=admin_menu())


async def post_next(app: Application, force=False):
    if not force and not data["auto_enabled"]:
        return
    if not TARGET_CHAT_IDS:
        log.warning("TARGET_CHAT_IDS is empty.")
        return
    posts = data.get("posts", [])
    links = [
        item for category in CATEGORIES
        for item in data["links"].get(category, [])
    ]
    if posts:
        post = posts[data["post_index"] % len(posts)]
        sent = False
        for chat_id in TARGET_CHAT_IDS:
            try:
                if post["type"] == "photo":
                    await app.bot.send_photo(chat_id, post["file_id"], caption=post.get("caption", "")[:1024])
                elif post["type"] == "video":
                    await app.bot.send_video(chat_id, post["file_id"], caption=post.get("caption", "")[:1024])
                else:
                    await app.bot.send_message(chat_id, post.get("text") or post.get("caption", ""))
                sent = True
            except Exception:
                log.exception("Failed to send saved post to %s", chat_id)
        if sent:
            data["post_index"] += 1
            save_data()
        return

    if not links:
        log.warning("No links or saved posts to publish.")
        return
    item = links[data["post_index"] % len(links)]
    caption = (
        f"✨ আপনাদের জন্য নতুন লিংক!\n\n"
        f"📌 {item['title']}\n\n"
        f"🔗 {item['url']}\n\n"
        f"💙 ভালো লাগলে বন্ধুদের সঙ্গে শেয়ার করুন!\n"
        f"#Bangla #SocialMedia"
    )
    sent = False
    for chat_id in TARGET_CHAT_IDS:
        try:
            await app.bot.send_message(chat_id=chat_id, text=caption, disable_web_page_preview=False)
            sent = True
        except Exception:
            log.exception("Failed to post to %s", chat_id)
    if sent:
        data["post_index"] += 1
        save_data()


async def scheduled_post(context: ContextTypes.DEFAULT_TYPE):
    await post_next(context.application)


async def setinterval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    if not context.args or not context.args[0].isdigit():
        await update.effective_message.reply_text("ব্যবহার: /setinterval 30")
        return
    minutes = int(context.args[0])
    if not 5 <= minutes <= 1440:
        await update.effective_message.reply_text("বিরতি ৫ থেকে ১৪৪০ মিনিটের মধ্যে দিন।")
        return
    data["interval_minutes"] = minutes
    save_data()
    job = context.application.job_queue.get_jobs_by_name("scheduled_post")
    for item in job:
        item.schedule_removal()
    context.application.job_queue.run_repeating(
        scheduled_post, interval=minutes * 60, first=minutes * 60, name="scheduled_post"
    )
    await update.effective_message.reply_text(f"✅ পোস্টের বিরতি {minutes} মিনিট করা হয়েছে।")


async def post_init(app: Application):
    app.job_queue.run_repeating(
        scheduled_post,
        interval=data["interval_minutes"] * 60,
        first=data["interval_minutes"] * 60,
        name="scheduled_post",
    )


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN .env ফাইলে সেট করুন।")
    if not ADMIN_USERNAMES and not ADMIN_IDS:
        raise RuntimeError("ADMIN_USERNAMES বা ADMIN_IDS সেট করুন।")

    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("setinterval", setinterval))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.VIDEO) & ~filters.COMMAND,
        receive_admin_message,
    ))
    print("Telegram Link Bot is running.")
    app.run_polling()


if __name__ == "__main__":
    main()
