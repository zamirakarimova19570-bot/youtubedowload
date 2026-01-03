import os
import asyncio
import logging
from datetime import datetime
from typing import Optional
import subprocess

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ✅ FAQAT BIR JOYDA TOKEN QO'YILGAN
BOT_TOKEN = os.getenv('7879907267:AAE6zgRgFm9tC35V0MHZte1B5IVBsh8J5DE')

# Agar token bo'lmasa, dastur to'xtaydi
if not BOT_TOKEN:
    print("❌ XATOLIK: BOT_TOKEN environment variable topilmadi!")
    print("ℹ️ GitHub Secrets ga BOT_TOKEN qo'shing yoki .env faylida belgilang")
    exit(1)

# Log konfiguratsiyasi - har bir logda imzo
class SignatureLogger(logging.Formatter):
    def format(self, record):
        message = super().format(record)
        return f"{message}\n👤 Isoqov Mironshoh"

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(SignatureLogger('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Statistikalar
user_stats = {}

class VideoDownloader:
    def __init__(self):
        self.max_size_mb = 40
        self.temp_dir = "temp_downloads"
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def download_video(self, url: str, chat_id: int) -> Optional[dict]:
        """YouTube video yuklash"""
        try:
            # Foydalanuvchi statistikasi
            if chat_id not in user_stats:
                user_stats[chat_id] = {'downloads': 0, 'last_download': None}
            
            # 5 soniya kutish
            await asyncio.sleep(5)
            
            # yt-dlp ni tekshirish
            try:
                downloader = 'yt-dlp'
                subprocess.run([downloader, '--version'], check=True, capture_output=True, timeout=5)
            except:
                downloader = 'youtube-dl'
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_template = f"{self.temp_dir}/{chat_id}_{timestamp}_%(title)s.%(ext)s"
            
            cmd = [
                downloader,
                url,
                '-f', 'best[filesize<40M]',
                '--max-filesize', '40M',
                '--no-playlist',
                '-o', output_template,
                '--quiet',
                '--no-warnings'
            ]
            
            logger.info(f"Video yuklanmoqda: {url[:50]}... | User: {chat_id}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                for file in os.listdir(self.temp_dir):
                    if file.startswith(f"{chat_id}_{timestamp}"):
                        file_path = os.path.join(self.temp_dir, file)
                        file_size = os.path.getsize(file_path) / (1024 * 1024)
                        
                        if file_size <= self.max_size_mb:
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
            logger.error(f"Download xatosi: {e}")
            return {'success': False, 'error': str(e)}

async def send_with_signature(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, **kwargs):
    """Har bir xabar ostiga imzo qo'shish"""
    signature = "\n\n👤 Isoqov Mironshoh"
    await context.bot.send_message(chat_id, text + signature, **kwargs)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start komandasi"""
    user = update.effective_user
    welcome_text = f"""👋 Assalomu alaykum {user.first_name}!

🎬 **YouTube Video Yuklovchi Bot** ga xush kelibsiz!

📥 Bot orqali YouTube videolarini yuklab olishingiz mumkin.

⚠️ **Ogohlantirish:**
• Video hajmi 40MB dan oshmasligi kerak
• Yuklash 5 soniya davom etadi
• Faqat bitta video yuklash mumkin

📎 Video linkini yuboring."""
    
    keyboard = [
        [InlineKeyboardButton("📥 Video Yuklash", callback_data='download_info')],
        [InlineKeyboardButton("📊 Mening statistikam", callback_data='stats')],
        [InlineKeyboardButton("ℹ️ Yordam", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await send_with_signature(
        context, 
        update.message.chat_id, 
        welcome_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xabarlarni qayta ishlash"""
    message = update.message
    chat_id = message.chat_id
    text = message.text.strip()
    
    if 'youtube.com' in text or 'youtu.be' in text:
        warning_msg = await message.reply_text(
            "⏳ **Video yuklanmoqda...**\n"
            "Iltimos, 5 soniya kuting!\n"
            "📦 Maksimum hajm: 40MB\n\n"
            "🔄 Jarayon davom etmoqda...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        downloader = VideoDownloader()
        result = await downloader.download_video(text, chat_id)
        
        if result['success']:
            try:
                with open(result['file_path'], 'rb') as video_file:
                    await message.reply_video(
                        video=video_file,
                        caption=f"✅ **Video muvaffaqiyatli yuklandi!**\n"
                               f"📊 Hajmi: {result['file_size']}MB\n"
                               f"📛 Nomi: {result['file_name'][:30]}...",
                        parse_mode=ParseMode.MARKDOWN
                    )
                
                # Ogohlantirish xabari
                await send_with_signature(
                    context,
                    chat_id,
                    f"⚠️ **Diqqat!** Video hajmi {result['file_size']}MB. "
                    f"40MB limitiga {40 - result['file_size']:.1f}MB qoldi.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
            finally:
                if os.path.exists(result['file_path']):
                    os.remove(result['file_path'])
                await warning_msg.delete()
        else:
            await warning_msg.edit_text(
                f"❌ **Xatolik yuz berdi!**\n\n"
                f"Sabab: {result['error']}\n\n"
                f"Boshqa video linkini yuboring.",
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        await send_with_signature(
            context,
            chat_id,
            "❌ Iltimos, YouTube video linkini yuboring!\n"
            "Namuna: https://www.youtube.com/watch?v=...",
            parse_mode=ParseMode.MARKDOWN
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Button bosilganda"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'download_info':
        text = "📥 **Video Yuklash:**\n1. YouTube linkini yuboring\n2. 5 soniya kuting\n3. Video yuklanadi\n⚠️ Maksimum 40MB"
    elif query.data == 'stats':
        stats = user_stats.get(query.message.chat_id, {'downloads': 0, 'last_download': None})
        text = f"📊 **Statistika:**\n📥 Yuklangan: {stats['downloads']} ta\n⏰ So'nggi: {stats['last_download'].strftime('%H:%M') if stats['last_download'] else 'Yoq'}"
    elif query.data == 'help':
        text = "ℹ️ **Yordam:**\nBot YouTube videolarini yuklaydi\nLimit: 40MB per video\nYordam: @IsoqovMironshoh"
    
    await query.edit_message_text(text + "\n\n👤 Isoqov Mironshoh", parse_mode=ParseMode.MARKDOWN)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xatoliklarni ushlash"""
    logger.error(f"Xatolik: {context.error}")
    if update and update.effective_chat:
        await send_with_signature(
            context,
            update.effective_chat.id,
            "❌ Xatolik yuz berdi! Iltimos, qayta urinib ko'ring.",
            parse_mode=ParseMode.MARKDOWN
        )

def main():
    """Asosiy dastur"""
    logger.info("🤖 Bot ishga tushmoqda...")
    
    # ✅ FAQAT BIR MARTA TOKEN QO'LLANILMOQDA
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlerlar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    # Botni ishga tushirish
    logger.info("✅ Bot ishga tushdi!")
    logger.info("👤 Isoqov Mironshoh tomonidan yaratildi")
    
    application.run_polling(allowed_updates=Update.ALL_UPDATES)

if __name__ == '__main__':
    main()
