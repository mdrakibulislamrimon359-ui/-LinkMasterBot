Telegram Link & Auto Post Bot
Features
Separate Facebook, TikTok, Telegram, YouTube, Developer Contact, Apps Information, and Other Links categories\n- Starts with the social links and contact numbers supplied in the chat
Inline category buttons and direct link buttons
Admin-only add/edit/delete link actions
Save text/photo/video posts and send them manually with Admin > Post Now
Scheduled auto-posting at a configurable interval (default 20 minutes)
Persistent JSON storage
Setup
Install Python 3.10+.
Create a bot with @BotFather and copy its token.
Copy .env.example to .env and fill in BOT_TOKEN.
Add your bot to each target Telegram group/channel and grant posting permissions.
Set TARGET_CHAT_IDS in .env (comma-separated chat IDs).
Install and run:
pip install -r requirements.txt
python main.py
Open your bot and run /start, then /admin.
Add initial links
Use Admin > Add Link, then send: facebook | Facebook Page 1 | https://www.facebook.com/example
Valid categories: facebook, tiktok, telegram, youtube, contacts, apps, other
Admin security
The supplied usernames are used as an initial allowlist. Usernames can change or be impersonated over time, so for stronger security have each admin run /myid, then set the verified numeric IDs in ADMIN_IDS in .env. Keep .env private and never share your bot token.
Important notes
Auto-posting is only to Telegram chats/channels listed in TARGET_CHAT_IDS.
This bot does not automatically publish to Facebook, Instagram, or TikTok. Those require separate authorized platform APIs and permissions.
The current caption generator uses a simple template; it does not use an AI API yet.
Saved post media file IDs are Telegram-specific and should be created by sending the media to this bot.
Keep persistent disk storage enabled on hosting so bot_data.json is not lost on restart.
Test in a private group first. Only post content you own or are authorized to share.
