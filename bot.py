import os
import json
import logging
from pathlib import Path
from urllib.parse import urlparse
from datetime import time
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters,
)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_USERNAMES = {
    x.strip().lstrip("@").lower()
    for x in os.getenv("ADMIN_USERNAMES", "RJteam1,Mdshahadot20,offlinoffline").split(",")
    if x.strip()
}
ADMIN_IDS = {
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}
TARGET_CHAT_IDS = [
    x.strip() for x in os.getenv("TARGET_CHAT_IDS", "").split(",") if x.strip()
]
DEFAULT_INTERVAL = max(1, int(os.getenv("POST_INTERVAL_MINUTES", "10")))
TZ = ZoneInfo(os.getenv("BOT_TIMEZONE", "Asia/Dhaka"))
DATA_FILE = Path("bot_data.json")

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("vip_linkbot")

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
        {"title": "Developer 1", "url": "https://wa.me/8801742967532"},
        {"title": "Developer 2", "url": "https://wa.me/8801783060751"},
        {"title": "Developer 3", "url": "https://wa.me/8801779962693"},
        {"title": "Developer 4", "url": "https://wa.me/8801740697112"},
    ],
    "apps": [
        {"title": "অ্যাপসের কাজ শিখতে বা কিনতে আমাদের সাথে থাকুন", "url": "https://t.me/RJteam1owners"},
    ],
    "other": [],
}


def load_data():
    defaults = {
        "links": DEFAULT_LINKS,
        "posts": [],
        "auto_enabled": False,
        "interval_minutes": DEFAULT_INTERVAL,
        "post_index": 0,
        "last_daily_sent": {},
        "users": {},
    }
    if DATA_FILE.exists():
        try:
            saved = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            for key, value in defaults.items():
                saved.setdefault(key, value)
            saved.setdefault("links", {})
            for key, value in DEFAULT_LINKS.items():
                saved["links"].setdefault(key, value)
            return saved
        except (OSError, json.JSONDecodeError):
            log.exception("Could not read bot_data.json; loading defaults.")
    return defaults


data = load_data()
user_states = {}


def save_data():
    temp = DATA_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(DATA_FILE)


def is_admin(update: Update) -> bool:
    user = update.effective_user
    if not user:
        return False
    username = (user.username or "").lower()
    return user.id in ADMIN_IDS or username in ADMIN_USERNAMES


async def deny(update: Update):
    if update.effective_message:
        await update.effective_message.reply_text(
            "⛔ এই কাজটি শুধু অনুমোদিত অ্যাডমিন করতে পারবেন।\n"
            "আপনার Numeric ID জানতে /myid দিন।"
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
    state = "🟢 Auto Post: ON" if data["auto_enabled"] else "🔴 Auto Post: OFF"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Link", callback_data="admin:add"),
         InlineKeyboardButton("✏️ Edit Link", callback_data="admin:edit")],
        [InlineKeyboardButton("🗑 Delete Link", callback_data="admin:delete"),
         InlineKeyboardButton("📋 Manage Posts", callback_data="admin:posts")],
        [InlineKeyboardButton("📢 Post Next Now", callback_data="admin:postnow"),
         InlineKeyboardButton(state, callback_data="admin:auto")],
        [InlineKeyboardButton("➕ Add Text/Photo/Video", callback_data="admin:newpost")],
        [InlineKeyboardButton("🕒 Schedule Daily Post", callback_data="admin:daily")],
        [InlineKeyboardButton("⏱ Set Interval", callback_data="admin:interval")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="home")],
    ])


def back_keyboard(destination="home"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=destination)]])


def all_link_choices(action):
    rows = []
    for category, title in CATEGORIES.items():
        for i, item in enumerate(data["links"].get(category, [])):
            rows.append([InlineKeyboardButton(
                f"{title}: {item['title'][:32]}",
                callback_data=f"{action}:{category}:{i}"
            )])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="admin")])
    return InlineKeyboardMarkup(rows)


def ordered_items():
    """Return the rotating queue: all links, then non-daily saved posts."""
    queue = []
    for category in CATEGORIES:
        for item in data["links"].get(category, []):
            queue.append({"kind": "link", "category": category, **item})
    for i, post in enumerate(data.get("posts", [])):
        if not post.get("daily_time"):
            queue.append({"kind": "post", "post_index": i, **post})
    return queue


async def send_queue_item(app: Application, item):
    sent_any = False
    for chat_id in TARGET_CHAT_IDS:
        try:
            if item["kind"] == "link":
                caption = (
                    "✨ আপনাদের জন্য নতুন লিংক!\n\n"
                    f"📌 {item['title']}\n\n"
                    f"🔗 {item['url']}\n\n"
                    "💙 ভালো লাগলে বন্ধুদের সঙ্গে শেয়ার করুন!\n"
                    "#Bangla #SocialMedia"
                )
                await app.bot.send_message(chat_id=chat_id, text=caption, disable_web_page_preview=False)
            else:
                post = item
                ptype = post.get("type", "text")
                if ptype == "photo":
                    await app.bot.send_photo(chat_id, post["file_id"], caption=post.get("caption", "")[:1024])
                elif ptype == "video":
                    await app.bot.send_video(chat_id, post["file_id"], caption=post.get("caption", "")[:1024])
                else:
                    await app.bot.send_message(chat_id, post.get("text") or post.get("caption", ""))
            sent_any = True
        except Exception:
            log.exception("Failed posting to target chat %s", chat_id)
    return sent_any


async def post_next(app: Application, force=False):
    if not force and not data["auto_enabled"]:
        return
    if not TARGET_CHAT_IDS:
        log.warning("TARGET_CHAT_IDS is empty; add your group ID in Render Environment.")
        return
    queue = ordered_items()
    if not queue:
        log.info("No links or queued posts.")
        return
    index = data.get("post_index", 0) % len(queue)
    sent = await send_queue_item(app, queue[index])
    if sent:
        data["post_index"] = (index + 1) % len(queue)
        save_data()


async def scheduled_post(context: ContextTypes.DEFAULT_TYPE):
    await post_next(context.application)


async def daily_post(context: ContextTypes.DEFAULT_TYPE):
    post_id = str(context.job.data)
    if not data.get("auto_enabled"):
        return
    post = next((p for p in data.get("posts", []) if p.get("id") == post_id), None)
    if not post or not TARGET_CHAT_IDS:
        return
    from datetime import datetime
    day_key = datetime.now(TZ).strftime("%Y-%m-%d")
    if data.get("last_daily_sent", {}).get(post_id) == day_key:
        return
    item = {"kind": "post", **post}
    sent = await send_queue_item(context.application, item)
    if sent:
        data.setdefault("last_daily_sent", {})[post_id] = day_key
        save_data()


def schedule_daily_jobs(app: Application):
    for job in app.job_queue.get_jobs_by_name("daily_saved_post"):
        job.schedule_removal()
    for post in data.get("posts", []):
        daily_time = post.get("daily_time")
        if not daily_time or not post.get("id"):
            continue
        try:
            hour, minute = map(int, daily_time.split(":"))
            app.job_queue.run_daily(
                daily_post,
                time=time(hour=hour, minute=minute, tzinfo=TZ),
                data=post["id"],
                name="daily_saved_post",
            )
        except (ValueError, TypeError):
            log.warning("Invalid daily schedule for post %s", post.get("id"))


async def post_init(app: Application):
    app.job_queue.run_repeating(
        scheduled_post,
        interval=data["interval_minutes"] * 60,
        first=data["interval_minutes"] * 60,
        name="scheduled_post",
    )
    schedule_daily_jobs(app)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user:
        data.setdefault("users", {})[str(user.id)] = {
            "username": user.username or "",
            "first_name": user.first_name or "",
        }
        save_data()
    await update.effective_message.reply_text(
        "🌟 স্বাগতম!\n\nFacebook, TikTok, Telegram, YouTube ও অন্যান্য লিংক দেখুন।\n"
        "ব্যক্তিগত মেসেজ পেতে হলে আগে এই বটটি Start করতে হবে।",
        reply_markup=main_menu(),
    )


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.effective_message.reply_text(
        f"🆔 আপনার Telegram Numeric User ID: {user.id}\n"
        f"Username: @{user.username}" if user.username else
        f"🆔 আপনার Telegram Numeric User ID: {user.id}\nUsername নেই"
    )


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    await update.effective_message.reply_text("👑 VIP Admin Panel", reply_markup=admin_menu())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "📚 কমান্ড:\n/start - বট চালু\n/help - সাহায্য\n/myid - নিজের ID\n"
        "/admin - অ্যাডমিন প্যানেল\n/setinterval 10 - পোস্টের বিরতি\n"
        "/setdaily 21:30 - পরবর্তী মিডিয়া পোস্টের দৈনিক সময়\n"
        "/sendmsg @username আপনার মেসেজ - আগে বট Start করেছেন এমন ইউজারকে মেসেজ\n",
        reply_markup=main_menu(),
    )


async def setinterval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    if not context.args or not context.args[0].isdigit():
        return await update.effective_message.reply_text("ব্যবহার: /setinterval 10")
    minutes = int(context.args[0])
    if not 1 <= minutes <= 1440:
        return await update.effective_message.reply_text("বিরতি ১ থেকে ১৪৪০ মিনিটের মধ্যে দিন।")
    data["interval_minutes"] = minutes
    save_data()
    for job in context.application.job_queue.get_jobs_by_name("scheduled_post"):
        job.schedule_removal()
    context.application.job_queue.run_repeating(
        scheduled_post, interval=minutes * 60, first=minutes * 60, name="scheduled_post"
    )
    await update.effective_message.reply_text(f"✅ অটো পোস্টের বিরতি {minutes} মিনিট করা হয়েছে।")


async def setdaily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    if not context.args or len(context.args[0]) != 5 or context.args[0][2] != ":":
        return await update.effective_message.reply_text(
            "ব্যবহার: /setdaily 21:30\nসময় ২৪-ঘণ্টার ফরম্যাটে দিন।"
        )
    try:
        hour, minute = map(int, context.args[0].split(":"))
        time(hour=hour, minute=minute)
    except ValueError:
        return await update.effective_message.reply_text("সময় সঠিক নয়। উদাহরণ: /setdaily 21:30")
    user_states[update.effective_user.id] = {"action": "newpost", "daily_time": f"{hour:02d}:{minute:02d}"}
    await update.effective_message.reply_text(
        f"🕒 প্রতিদিন {hour:02d}:{minute:02d} (বাংলাদেশ সময়) পোস্ট হবে।\n"
        "এখন যে টেক্সট, ছবি বা ভিডিও পোস্ট করতে চান সেটি পাঠান।"
    )


async def sendmsg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    if len(context.args) < 2:
        return await update.effective_message.reply_text(
            "ব্যবহার: /sendmsg @username আপনার মেসেজ\n"
            "প্রাপককে আগে বট Start করতে হবে।"
        )
    username = context.args[0].lstrip("@").lower()
    message_text = " ".join(context.args[1:])
    found_id = next(
        (uid for uid, info in data.get("users", {}).items()
         if (info.get("username") or "").lower() == username),
        None,
    )
    if not found_id:
        return await update.effective_message.reply_text(
            "❌ ইউজার পাওয়া যায়নি। ওই ব্যক্তিকে আগে বট Start করতে বলুন, তারপর আবার চেষ্টা করুন।"
        )
    try:
        await context.bot.send_message(chat_id=int(found_id), text=message_text)
        await update.effective_message.reply_text(f"✅ @{username}-কে মেসেজ পাঠানো হয়েছে।")
    except Exception:
        log.exception("Could not DM user %s", username)
        await update.effective_message.reply_text(
            "❌ মেসেজ পাঠানো যায়নি। ওই ব্যক্তি বট Block করে থাকলে বা Start না করলে সম্ভব নয়।"
        )


async def show_link_list(query, category):
    items = data["links"].get(category, [])
    title = CATEGORIES.get(category, category)
    if not items:
        return await query.edit_message_text(
            f"{title}\n\nএখনও কোনো লিংক যোগ করা হয়নি।", reply_markup=back_keyboard("home")
        )
    rows = [[InlineKeyboardButton(item["title"], url=item["url"])] for item in items]
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="home")])
    await query.edit_message_text(f"{title}\n\nলিংকে চাপ দিলে সেটি খুলবে:", reply_markup=InlineKeyboardMarkup(rows))


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    payload = query.data or ""
    user = query.from_user

    if payload == "home":
        return await query.edit_message_text("📂 ক্যাটাগরি নির্বাচন করুন:", reply_markup=main_menu())
    if payload.startswith("cat:"):
        return await show_link_list(query, payload.split(":", 1)[1])
    if payload == "about":
        return await query.edit_message_text(
            "📌 সোশ্যাল লিংক ও অ্যাডমিন পরিচালিত পোস্ট বট।\n"
            "অটো পোস্ট চালু থাকলে লিংক/সাধারণ পোস্ট নির্ধারিত বিরতিতে যাবে।",
            reply_markup=back_keyboard("home"),
        )
    if payload == "admin":
        if not is_admin(update):
            return await query.edit_message_text("⛔ অনুমতি নেই।")
        return await query.edit_message_text("👑 VIP Admin Panel", reply_markup=admin_menu())
    if not is_admin(update):
        return await query.edit_message_text("⛔ এই অপশন শুধু অ্যাডমিনদের জন্য।")

    if payload == "admin:add":
        user_states[user.id] = {"action": "add"}
        return await query.edit_message_text(
            "এই ফরম্যাটে পাঠান:\ncategory | নাম | https://example.com\n\n"
            "category: facebook, tiktok, telegram, youtube, contacts, apps, other",
            reply_markup=back_keyboard("admin"),
        )
    if payload == "admin:edit":
        return await query.edit_message_text("যে লিংকটি এডিট করবেন বেছে নিন:", reply_markup=all_link_choices("edit"))
    if payload == "admin:delete":
        return await query.edit_message_text("যে লিংকটি ডিলিট করবেন বেছে নিন:", reply_markup=all_link_choices("delete"))
    if payload == "admin:auto":
        data["auto_enabled"] = not data["auto_enabled"]
        save_data()
        state = "চালু 🟢" if data["auto_enabled"] else "বন্ধ 🔴"
        return await query.edit_message_text(
            f"অটো পোস্ট এখন {state}।\nবিরতি: {data['interval_minutes']} মিনিট\n"
            "চালু থাকলে পোস্ট যাবে, বন্ধ থাকলে অটো পোস্ট বন্ধ থাকবে।",
            reply_markup=admin_menu(),
        )
    if payload == "admin:interval":
        return await query.edit_message_text(
            "অটো পোস্টের বিরতি বদলাতে ব্যক্তিগত চ্যাটে লিখুন:\n/setinterval 10",
            reply_markup=back_keyboard("admin"),
        )
    if payload == "admin:daily":
        return await query.edit_message_text(
            "প্রতিদিন নির্দিষ্ট সময়ে টেক্সট/ছবি/ভিডিও পোস্ট করতে:\n"
            "/setdaily 21:30\n\nএরপর পোস্টটি পাঠান। সময় বাংলাদেশ সময় (Asia/Dhaka)।",
            reply_markup=back_keyboard("admin"),
        )
    if payload == "admin:postnow":
        await query.edit_message_text("📢 পরবর্তী লিংক/সাধারণ পোস্ট পাঠানো হচ্ছে…", reply_markup=back_keyboard("admin"))
        await post_next(context.application, force=True)
        return
    if payload == "admin:posts":
        posts = data.get("posts", [])
        lines = []
        for i, post in enumerate(posts, 1):
            label = post.get("caption") or post.get("text") or post.get("type", "post")
            suffix = f" | প্রতিদিন {post['daily_time']}" if post.get("daily_time") else " | ১০-মিনিটের কিউ"
            lines.append(f"{i}. {label[:65]}{suffix}")
        return await query.edit_message_text(
            "📋 সেভ করা পোস্ট:\n\n" + ("\n".join(lines) if lines else "এখনও কোনো পোস্ট নেই।"),
            reply_markup=back_keyboard("admin"),
        )
    if payload == "admin:newpost":
        user_states[user.id] = {"action": "newpost"}
        return await query.edit_message_text(
            "এখন টেক্সট, ছবি বা ভিডিও পাঠান। ক্যাপশনও দিতে পারবেন।\n"
            "এটি ১০-মিনিটের অটো-পোস্ট কিউতে যোগ হবে।\n"
            "প্রতিদিন নির্দিষ্ট সময়ে দিতে চাইলে আগে /setdaily 21:30 দিন।",
            reply_markup=back_keyboard("admin"),
        )
    if payload.startswith("delete:"):
        _, category, index = payload.split(":")
        index = int(index)
        if index < len(data["links"].get(category, [])):
            removed = data["links"][category].pop(index)
            save_data()
            return await query.edit_message_text(f"🗑 ডিলিট হয়েছে: {removed['title']}", reply_markup=back_keyboard("admin"))
        return await query.edit_message_text("লিংকটি আর পাওয়া যাচ্ছে না।", reply_markup=back_keyboard("admin"))
    if payload.startswith("edit:"):
        _, category, index = payload.split(":")
        index = int(index)
        if index < len(data["links"].get(category, [])):
            user_states[user.id] = {"action": "edit", "category": category, "index": index}
            item = data["links"][category][index]
            return await query.edit_message_text(
                f"বর্তমান: {item['title']} | {item['url']}\n\nনতুন তথ্য পাঠান:\nনাম | https://example.com",
                reply_markup=back_keyboard("admin"),
            )


async def receive_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return
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
            return await msg.reply_text("ফরম্যাট: category | নাম | https://example.com")
        category, title, url = parts
        parsed = urlparse(url)
        if category not in CATEGORIES or not title or parsed.scheme not in ("http", "https") or not parsed.netloc:
            return await msg.reply_text("ক্যাটাগরি বা URL সঠিক নয়। আবার চেষ্টা করুন।")
        if any(x["url"] == url for x in data["links"][category]):
            return await msg.reply_text("এই লিংকটি আগেই আছে।")
        data["links"][category].append({"title": title, "url": url})
        save_data()
        user_states.pop(user.id, None)
        return await msg.reply_text(f"✅ {CATEGORIES[category]}-তে “{title}” যোগ হয়েছে।", reply_markup=admin_menu())

    if action == "edit":
        raw = (msg.text or "").strip()
        parts = [x.strip() for x in raw.split("|", 1)]
        if len(parts) != 2:
            return await msg.reply_text("ফরম্যাট: নতুন নাম | https://example.com")
        title, url = parts
        parsed = urlparse(url)
        if not title or parsed.scheme not in ("http", "https") or not parsed.netloc:
            return await msg.reply_text("নাম বা URL সঠিক নয়।")
        category, index = state["category"], state["index"]
        if index >= len(data["links"].get(category, [])):
            user_states.pop(user.id, None)
            return await msg.reply_text("লিংকটি আর পাওয়া যাচ্ছে না।")
        data["links"][category][index] = {"title": title, "url": url}
        save_data()
        user_states.pop(user.id, None)
        return await msg.reply_text("✅ লিংক আপডেট হয়েছে।", reply_markup=admin_menu())

    if action == "newpost":
        post = {
            "id": f"{user.id}-{len(data.get('posts', []))}-{int(__import__('time').time())}",
            "caption": msg.caption or msg.text or "",
        }
        if msg.photo:
            post.update({"type": "photo", "file_id": msg.photo[-1].file_id})
        elif msg.video:
            post.update({"type": "video", "file_id": msg.video.file_id})
        elif msg.text:
            post.update({"type": "text", "text": msg.text})
        else:
            return await msg.reply_text("টেক্সট, ছবি বা ভিডিও পাঠান।")
        if state.get("daily_time"):
            post["daily_time"] = state["daily_time"]
        data.setdefault("posts", []).append(post)
        save_data()
        user_states.pop(user.id, None)
        if post.get("daily_time"):
            schedule_daily_jobs(context.application)
            answer = f"✅ পোস্ট সেভ হয়েছে। প্রতিদিন {post['daily_time']} (বাংলাদেশ সময়) পোস্ট হবে। Auto Post ON রাখুন।"
        else:
            answer = "✅ পোস্ট সেভ হয়েছে। অটো পোস্ট ON থাকলে লিংকের সঙ্গে কিউ অনুযায়ী পোস্ট হবে।"
        return await msg.reply_text(answer, reply_markup=admin_menu())


async def main_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.exception("Unhandled bot error", exc_info=context.error)


def main():
    if not TOKEN:
        raise RuntimeError("Render Environment-এ BOT_TOKEN সেট করুন।")
    if not ADMIN_USERNAMES and not ADMIN_IDS:
        raise RuntimeError("Render Environment-এ ADMIN_USERNAMES অথবা ADMIN_IDS সেট করুন।")
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("setinterval", setinterval))
    app.add_handler(CommandHandler("setdaily", setdaily))
    app.add_handler(CommandHandler("sendmsg", sendmsg))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.VIDEO) & ~filters.COMMAND,
        receive_admin_message,
    ))
    app.add_error_handler(main_error)
    print("VIP Telegram Link Bot is running.")
    app.run_polling()


if __name__ == "__main__":
    main()
