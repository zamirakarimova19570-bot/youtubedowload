#!/usr/bin/env python3
"""
YouTube Video Downloader Telegram Bot
Developer: Isoqov Mironshoh
Token faqat BIR joyda: BOT_TOKEN o'zgaruvchisida
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import Optional
import subprocess
import tempfile
import shutil

# ========== FAQAT BIR JOYDA TOKEN ==========
# Tokenni faqat BOT_TOKEN environment variable'dan olamiz
BOT_TOKEN = os.environ.get('7879907267:AAE6zgRgFm9tC35V0MHZte1B5IVBsh8J5DE')

if not BOT_TOKEN:
    print("=" * 60)
    print("❌ XATOLIK: BOT_TOKEN environment variable topilmadi!")
    print("=" * 60)
    print("📋 Qanday qo'shish kerak:")
    print("")
    print("1️⃣ GitHub Actions uchun:")
    print("   Settings → Secrets and variables → Actions")
    print("   Name: BOT_TOKEN, Value: bot_token_here")
    print("")
    print("2️⃣ Lokal test uchun:")
    print("   export BOT_TOKEN='your_bot_token'")
    print("   python bot.py")
    print("")
    print("3️⃣ .env fayli uchun (agar dotenv o'rnatilgan bo'lsa):")
    print("   BOT_TOKEN=your_bot_token")
    print("=" * 60)
    print("👤 Developer: Isoqov Mironshoh")
    print("=" * 60)
    
    # Debug: mavjud environment variables
    if 'GITHUB_ACTIONS' in os.environ:
        print("\n🔍 Available environment variables:")
        env_vars = [k for k in os.environ.keys() if 'BOT' in k or 'TOKEN' in k]
        if env_vars:
            for var in env_vars:
                val = os.environ[var]
                masked = val[:5] + '...' + val[-3:] if len(val) > 8 else '[HIDDEN]'
                print(f"   {var}: {masked}")
        else:
            print("   No BOT/TOKEN variables found!")
    
    sys.exit(1)

# Tokenni tekshirish
print("=" * 50)
print("✅ BOT TOKENI TOPILDI!")
print(f"   Uzunligi: {len(BOT_TOKEN)} belgi")
if len(BOT_TOKEN) > 10:
    print(f"   Boshi: {BOT_TOKEN[:10]}...")
print("👤 Developer: Isoqov Mironshoh")
print("=" * 50)

# ========== KUTUBXONALARNI IMPORT QILISH ==========
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ========== LOGGING ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s\n👤 Isoqov Mironshoh',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

logger.info("🤖 Bot ishga tushmoqda...")
logger.info(f"📦 Maksimal video hajmi: 40MB")
logger.info(f"⏳ Yuklash kutish vaqti: 5 soniya")
logger.info(f"🔐 Token uzunligi: {len(BOT_TOKEN)}")

# ========== GLOBAL O'ZGARUVCHILAR ==========
user_stats = {}

class VideoDownloader:
    """YouTube video yuklovchi"""
    
    def __init__(self):
        self.max_size_mb = 40
        self.temp_dir = tempfile.mkdtemp(prefix="yt_dl_")
        logger.info(f"📁 Vaqtinchalik papka: {self.temp_dir}")
    
    async def download_video(self, url: str, user_id: int) -> Optional[dict]:
        """YouTube videoni yuklash"""
        try:
            # Statistikani yangilash
            if user_id not in user_stats:
                user_stats[user_id] = {'downloads': 0, 'total_size': 0}
            
            # 5 soniya kutish
            await asyncio.sleep(5)
            
            # Yuklovchi dasturni tanlash
            try:
                subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
                downloader = 'yt-dlp'
            except:
                downloader = 'youtube-dl'
            
            logger.info(f"📥 Yuklanmoqda: {url[:50]}...")
            logger.info(f"👤 User ID: {user_id}")
            
            # Fayl nomi
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.temp_dir, f"{user_id}_{timestamp}_%(title)s.%(ext)s")
            
            # Yuklash komandasi
            cmd = [
                downloader,
                url,
                '-f', 'best[filesize<40M]',
                '--max-filesize', '40M',
                '-o', output_path,
                '--quiet',
                '--no-warnings'
            ]
            
            # Yuklash
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Yuklangan faylni topish
                for file in os.listdir(self.temp_dir):
                    if file.startswith(f"{user_id}_{timestamp}"):
                        file_path = os.path.join(self.temp_dir, file)
                        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                        
                        if file_size_mb <= self.max_size_mb:
                            user_stats[user_id]['downloads'] += 1
                            user_stats[user_id]['total_size'] += file_size_mb
                            
                            return {
                                'success': True,
                                'file_path': file_path,
                                'file_size': round(file_size_mb, 2),
                                'file_name': file
                            }
                        else:
                            os.remove(file_path)
                            return {'success': False, 'error': f'Fayl {file_size_mb:.1f}MB, 40MB dan katta!'}
            
            return {'success': False, 'error': 'Yuklash muvaffaqiyatsiz'}
            
        except Exception as e:
            logger.error(f"❌ Xatolik: {e}")
            return {'success': False, 'error': str(e)}
    
    def cleanup(self):
        """Tozalash"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

async def send_with_signature(context, chat_id: int, text: str, **kwargs):
    """Xabar yuborish imzo bilan"""
    message = text + "\n\n👤 Isoqov Mironshoh"
    await context.bot.send_message(chat_id, message, **kwargs)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start komandasi"""
    user = update.effective_user
    
    text = f"""👋 Salom {user.first_name}!

🎬 YouTube Video Yuklovchi Bot

📥 *Qo'llanma:*
1. YouTube linkini yuboring
2. 5 soniya kuting
3. Video yuklanadi

⚠️ *Cheklovlar:*
• Maksimal hajm: 40MB
• Kunlik limit: 10 video
• Faqat YouTube videolari

📎 Link yuboring va boshlaymiz!"""
    
    buttons = [
        [InlineKeyboardButton("📥 Yuklash", callback_data='download_info')],
        [InlineKeyboardButton("📊 Statistika", callback_data='stats')],
        [InlineKeyboardButton("ℹ️ Yordam", callback_data='help')]
    ]
    
    await send_with_signature(
        context,
        update.effective_chat.id,
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_video_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Video linklarini qayta ishlash"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    url = update.message.text
    
    # Ogohlantirish
    wait_msg = await update.message.reply_text(
        "⏳ Video yuklanmoqda...\n5 soniya kuting!\n👤 Isoqov Mironshoh"
    )
    
    # Yuklash
    downloader = VideoDownloader()
    result = await downloader.download_video(url, user.id)
    
    if result['success']:
        try:
            # Video yuborish
            with open(result['file_path'], 'rb') as f:
                await update.message.reply_video(
                    video=f,
                    caption=f"✅ Yuklandi!\n📊 Hajmi: {result['file_size']}MB\n👤 Isoqov Mironshoh"
                )
            
            # Ogohlantirish
            await send_with_signature(
                context,
                chat_id,
                f"⚠️ Diqqat! Video hajmi {result['file_size']}MB. 40MB limitiga {40-result['file_size']:.1f}MB qoldi."
            )
            
        finally:
            # Tozalash
            if os.path.exists(result['file_path']):
                os.remove(result['file_path'])
            downloader.cleanup()
            await wait_msg.delete()
    else:
        await wait_msg.edit_text(
            f"❌ Xatolik: {result['error']}\n👤 Isoqov Mironshoh"
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Button bosilganda"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == 'download_info':
        text = "📥 Yuklash uchun YouTube linkini yuboring\n⏳ 5 soniya kutishingiz kerak\n⚠️ Maksimal hajm: 40MB"
    elif query.data == 'stats':
        stats = user_stats.get(user_id, {'downloads': 0, 'total_size': 0})
        text = f"📊 Statistika:\n📥 Yuklangan: {stats['downloads']} ta\n💾 Jami hajm: {stats['total_size']:.1f}MB"
    elif query.data == 'help':
        text = "ℹ️ Yordam:\n• Link yuboring → video yuklanadi\n• 40MB dan katta videolar yuklanmaydi\n• Har bir xabar ostida Isoqov Mironshoh"
    
    await query.edit_message_text(text + "\n\n👤 Isoqov Mironshoh")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xatolik"""
    logger.error(f"Xatolik: {context.error}")
    if update and update.effective_chat:
        await send_with_signature(
            context,
            update.effective_chat.id,
            "❌ Xatolik yuz berdi. Keyinroq urinib ko'ring."
        )

def main():
    """Asosiy funksiya"""
    try:
        logger.info("🚀 Bot ishga tushmoqda...")
        
        # ✅ FAQAT BIR JOYDA TOKEN QO'LLANILMOQDA
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Handlerlar
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # YouTube link pattern
        youtube_pattern = r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+'
        application.add_handler(MessageHandler(
            filters.TEXT & filters.Regex(youtube_pattern),
            handle_video_link
        ))
        
        # Boshqa xabarlar
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            lambda u, c: u.message.reply_text("YouTube linkini yuboring!\n👤 Isoqov Mironshoh")
        ))
        
        application.add_error_handler(error_handler)
        
        # Ishga tushirish
        logger.info("✅ Bot ishga tushdi!")
        application.run_polling(allowed_updates=Update.ALL_UPDATES)
        
    except Exception as e:
        logger.critical(f"💥 Bot ishga tushmadi: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
