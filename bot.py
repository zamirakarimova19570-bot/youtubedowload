import os
import asyncio
import logging
from datetime import datetime
from typing import Optional
import subprocess
import shutil

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# Bot tokeni - GitHub Secrets dan olinadi
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Log konfiguratsiyasi
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Statistikalar
user_stats = {}

class VideoDownloader:
    def __init__(self):
        self.max_size_mb = 40  # Maksimum hajm 40 MB
        self.temp_dir = "temp_downloads"
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def download_video(self, url: str, chat_id: int) -> Optional[dict]:
        """YouTube video yuklash"""
        try:
            # Foydalanuvchi statistikasi
            if chat_id not in user_stats:
                user_stats[chat_id] = {'downloads': 0, 'last_download': None}
            
            # 5 soniya kutish (ogohlantirish)
            await asyncio.sleep(5)
            
            # yt-dlp ni tekshirish
            try:
                downloader = 'yt-dlp'
                subprocess.run([downloader, '--version'], check=True, capture_output=True)
            except:
                downloader = 'youtube-dl'
            
            # Fayl nomi
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_template = f"{self.temp_dir}/{chat_id}_{timestamp}_%(title)s.%(ext)s"
            
            # Yuklash buyrug'i - 40MB limit uchun format tanlash
            cmd = [
                downloader,
                url,
                '-f', 'best[filesize<40M]',  # 40MB dan oshmasligi uchun
                '--max-filesize', '40M',
                '--no-playlist',
                '-o', output_template,
                '--quiet',
                '--no-warnings',
                '--format-sort', 'res,ext:mp4:m4a'
            ]
            
            logger.info(f"Yuklanmoqda: {url} | User: {chat_id}")
            
            # Yuklash jarayoni
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Yuklangan faylni topish
                for file in os.listdir(self.temp_dir):
                    if file.startswith(f"{chat_id}_{timestamp}"):
                        file_path = os.path.join(self.temp_dir, file)
                        file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB da
                        
                        if file_size <= self.max_size_mb:
                            # Statistikani yangilash
                            user_stats[chat_id]['downloads'] += 1
                            user_stats[chat_id]['last_download'] = datetime.now()
                            
                            return {
                                'success': True,
                                'file_path': file_path,
                                'file_size': round(file_size, 2),
                                'file_name': file
                            }
                        else:
                            os.remove(file_path)
                            return {'success': False, 'error': f'Fayl hajmi {file_size:.1f}MB, 40MB dan katta!'}
            
            return {'success': False, 'error': stderr.decode() if stderr else 'Noma\'lum xatolik'}
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return {'success': False, 'error': str(e)}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start komandasi"""
    user = update.effective_user
    welcome_text = f"""
👋 Assalomu alaykum {user.first_name}!

🎬 **YouTube Video Yuklovchi Bot** ga xush kelibsiz!

📥 Bot orqali YouTube videolarini yuklab olishingiz mumkin.

⚠️ **Ogohlantirish:**
• Video hajmi 40MB dan oshmasligi kerak
• Yuklash 5 soniya davom etadi
• Faqat bitta video yuklash mumkin

📎 Video linkini yuboring yoki quyidagi buttonlardan foydalaning.
    """
    
    keyboard = [
        [InlineKeyboardButton("📥 Video Yuklash", callback_data='download_info')],
        [InlineKeyboardButton("📊 Mening statistikam", callback_data='stats')],
        [InlineKeyboardButton("ℹ️ Yordam", callback_data='help')],
        [InlineKeyboardButton("🎥 Namuna Video", url='https://youtu.be/dQw4w9WgXcQ')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xabarlarni qayta ishlash"""
    message = update.message
    chat_id = message.chat_id
    text = message.text.strip()
    
    # YouTube linkini tekshirish
    if 'youtube.com' in text or 'youtu.be' in text:
        # Ogohlantirish xabari
        warning_msg = await message.reply_text(
            "⏳ **Video yuklanmoqda...**\n"
            "Iltimos, 5 soniya kuting!\n"
            f"📦 Maksimum hajm: 40MB\n\n"
            "🔄 Jarayon davom etmoqda...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Video yuklash
        downloader = VideoDownloader()
        result = await downloader.download_video(text, chat_id)
        
        if result['success']:
            # Yuklash muvaffaqiyatli
            try:
                # Video yuborish
                with open(result['file_path'], 'rb') as video_file:
                    await message.reply_video(
                        video=video_file,
                        caption=(
                            f"✅ **Video muvaffaqiyatli yuklandi!**\n"
                            f"📊 Hajmi: {result['file_size']}MB\n"
                            f"📛 Nomi: {result['file_name'][:30]}...\n\n"
                            f"👤 Yuklagan: {update.effective_user.first_name}\n"
                            f"⏰ Vaqti: {datetime.now().strftime('%H:%M:%S')}"
                        ),
                        parse_mode=ParseMode.MARKDOWN
                    )
                
                # Foydalanuvchini ogohlantirish
                await message.reply_text(
                    f"⚠️ **Diqqat!** Video hajmi {result['file_size']}MB. "
                    f"40MB limitiga {40 - result['file_size']:.1f}MB qoldi.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
            finally:
                # Faylni o'chirish
                if os.path.exists(result['file_path']):
                    os.remove(result['file_path'])
                
                # Warning xabarini o'chirish
                await warning_msg.delete()
        else:
            # Xatolik xabari
            await warning_msg.edit_text(
                f"❌ **Xatolik yuz berdi!**\n\n"
                f"Sabab: {result['error']}\n\n"
                f"Boshqa video linkini yuboring yoki hajmi kichikroq video tanlang.",
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        # YouTube linki emas
        await message.reply_text(
            "❌ Iltimos, YouTube video linkini yuboring!\n"
            "Namuna: https://www.youtube.com/watch?v=...",
            parse_mode=ParseMode.MARKDOWN
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Button bosilganda"""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    
    if query.data == 'download_info':
        text = """
📥 **Video Yuklash bo'yicha ko'rsatma:**

1. YouTube'dan video linkini nusxalang
2. Linkni shu yerga yuboring
3. 5 soniya kuting
4. Video avtomatik yuklanadi

⚠️ **Cheklovlar:**
• Maksimum hajm: 40MB
• Faqat YouTube videolari
• Bir vaqtda bitta video
        """
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
    
    elif query.data == 'stats':
        stats = user_stats.get(chat_id, {'downloads': 0, 'last_download': None})
        text = f"""
📊 **Sizning statistikangiz:**

📥 Yuklangan videolar: {stats['downloads']} ta
⏰ So'nggi yuklash: {stats['last_download'].strftime('%Y-%m-%d %H:%M') if stats['last_download'] else 'Hali mavjud emas'}

💾 Limit: 40MB per video
🔢 Maksimum: 10 video/kun
        """
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
    
    elif query.data == 'help':
        text = """
ℹ️ **Yordam va Qo'llanma**

**Qanday ishlatiladi?**
1. Botni ishga tushiring: /start
2. YouTube video linkini yuboring
3. Video avtomatik yuklanadi

**Muhim eslatmalar:**
• Video 40MB dan oshmasligi kerak
• Yuklash 5-10 soniya davom etadi
• Katta videolar uchun premium versiya

📞 **Bog'lanish:** @IsoqovMironshoh
        """
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

async def add_signature(context: ContextTypes.DEFAULT_TYPE):
    """Har bir xabar ostiga imzo qo'shish"""
    # Bu handler har bir yuborilgan xabar uchun ishlatiladi
    pass

async def post_init(application: Application):
    """Bot ishga tushganda"""
    logger.info("Bot ishga tushdi! ✅")
    logger.info(f"Isoqov Mironshoh tomonidan yaratildi")
    
    # Barcha yangi xabarlarga imzo qo'shish
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

def main():
    """Asosiy dastur"""
    # Bot ilovasini yaratish
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Handlerlar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Botni ishga tushirish
    application.run_polling(allowed_updates=Update.ALL_UPDATES)

if __name__ == '__main__':
    main()
