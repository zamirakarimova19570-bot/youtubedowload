#!/usr/bin/env python3
"""
YouTube Video Downloader Bot
Developer: Isoqov Mironshoh
"""

import os
import sys

# ========== TOKEN TEKSHIRISH ==========
print("🔍 Tokenni tekshiryapman...")

# 1-USUL: to'g'ridan-to'g'ri environment dan
token = os.getenv('7879907267:AAE6zgRgFm9tC35V0MHZte1B5IVBsh8J5DE')

# 2-USUL: GitHub Actions uchun qo'shimcha tekshirish
if not token and 'GITHUB_ACTIONS' in os.environ:
    print("ℹ️ GitHub Actions muhitida")
    # GitHub Actions dagi barcha o'zgaruvchilarni ko'rish
    for key, value in os.environ.items():
        if 'BOT' in key or 'TOKEN' in key:
            print(f"   {key} = {value[:5]}... (uzunligi: {len(value)})")
            if 'BOT_TOKEN' in key and value:
                token = value
                break

if not token:
    print("=" * 50)
    print("❌ XATOLIK: BOT_TOKEN topilmadi!")
    print("=" * 50)
    print("GitHub Secrets ga BOT_TOKEN qo'shing")
    print("yoki lokalda: export BOT_TOKEN='token_here'")
    print("=" * 50)
    sys.exit(1)

print("✅ Token topildi!")
print(f"👤 Developer: Isoqov Mironshoh")

# Endi qolgan kutubxonalarni import qilamiz
import asyncio
import logging
from datetime import datetime
import subprocess
import tempfile
import shutil

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ========== LOGGING ==========
logging.basicConfig(
    format='%(asctime)s - %(message)s\n👤 Isoqov Mironshoh',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== YUKLOVCHI ==========
class VideoDownloader:
    def __init__(self):
        self.max_size = 40
        self.temp_dir = tempfile.mkdtemp()
    
    async def download(self, url: str, user_id: int):
        """Video yuklash"""
        try:
            await asyncio.sleep(5)
            
            # Yuklovchini tanlash
            try:
                subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
                cmd = ['yt-dlp']
            except:
                cmd = ['youtube-dl']
            
            # Fayl nomi
            output = f"{self.temp_dir}/%(title)s.%(ext)s"
            cmd.extend([
                url,
                '-f', 'best[filesize<40M]',
                '--max-filesize', '40M',
                '-o', output,
                '--quiet'
            ])
            
            logger.info(f"📥 Yuklanmoqda...")
            
            # Yuklash
            process = await asyncio.create_subprocess_exec(*cmd)
            await process.wait()
            
            if process.returncode == 0:
                for file in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, file)
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    
                    if size_mb <= self.max_size:
                        return {
                            'success': True,
                            'path': file_path,
                            'size': round(size_mb, 2)
                        }
            
            return {'success': False, 'error': 'Yuklash muvaffaqiyatsiz'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def cleanup(self):
        """Tozalash"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

# ========== BOT FUNKSIYALARI ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komandasi"""
    text = """👋 YouTube Video Yuklovchi Bot

📥 Video linkini yuboring:
• 5 soniya kuting
• Video yuklanadi
• Maksimal hajm: 40MB

👤 Isoqov Mironshoh"""
    
    buttons = [[InlineKeyboardButton("📥 Yuklash", callback_data='help')]]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Linkni qayta ishlash"""
    user = update.effective_user
    
    # Kutish xabari
    msg = await update.message.reply_text("⏳ 5 soniya kuting...\n👤 Isoqov Mironshoh")
    
    # Yuklash
    downloader = VideoDownloader()
    result = await downloader.download(update.message.text, user.id)
    
    if result['success']:
        # Video yuborish
        with open(result['path'], 'rb') as f:
            await update.message.reply_video(
                video=f,
                caption=f"✅ Yuklandi!\n📊 Hajmi: {result['size']}MB\n👤 Isoqov Mironshoh"
            )
        
        # Ogohlantirish
        await update.message.reply_text(
            f"⚠️ Diqqat! Video {result['size']}MB.\n👤 Isoqov Mironshoh"
        )
        
        # Tozalash
        os.remove(result['path'])
    else:
        await msg.edit_text(f"❌ Xatolik: {result['error']}\n👤 Isoqov Mironshoh")
    
    downloader.cleanup()

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Button bosilganda"""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "📥 YouTube linkini yuboring!\n👤 Isoqov Mironshoh"
    )

# ========== ASOSIY FUNKSIYA ==========
def main():
    """Dasturni ishga tushirish"""
    try:
        print("🤖 Bot ishga tushmoqda...")
        
        # ✅ FAQAT BIR JOYDA TOKEN ISHLATILADI
        app = Application.builder().token(token).build()
        
        # Handlerlar
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_click))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
        
        # Ishga tushirish
        print("✅ Bot ishga tushdi!")
        app.run_polling()
        
    except Exception as e:
        print(f"❌ Xatolik: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
