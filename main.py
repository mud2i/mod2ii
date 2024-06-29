import logging
import os
import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext
from dotenv import load_dotenv

# تحميل متغيرات البيئة من ملف .env
load_dotenv()

# إعداد سجل الأخطاء
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# إعداد متغيرات البوت من متغيرات البيئة
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = int(os.getenv('CHAT_ID'))

URLS = [
    'https://www.dzrt.com/ar/mint-fusion.html',  # اسم المنتج: icy rush
    'https://www.dzrt.com/ar/garden-mint.html',  # اسم المنتج: garden mint
    'https://www.dzrt.com/ar/edgy-mint.html'  # اسم المنتج: edgy mint
]

# روابط الصور
IMAGE_URLS = {
    'mint-fusion': {
        'available': 'https://i.imgur.com/8sBgt6j.png',
        'unavailable': 'https://i.imgur.com/bjbRPlw.png'
    },
    'garden-mint': {
        'available': 'https://i.imgur.com/gBpn6Qq.png',
        'unavailable': 'https://i.imgur.com/z9KJVg8.png'
    },
    'edgy-mint': {
        'available': 'https://i.imgur.com/lLuPJwg.png',
        'unavailable': 'https://i.imgur.com/bq7HlyB.png'
    }
}

# حالة توفر المنتج
product_availability = {}

async def start(update: Update, context: CallbackContext) -> None:
    """وظيفة استجابة للأمر /start"""
    await update.message.reply_text('برمجة @mod2i')
    logger.info("Received /start command")
    # إرسال رسالة تجريبية عند بدء التشغيل
    context.job_queue.run_once(send_test_message, when=0, chat_id=update.effective_chat.id)


def check_website(url):
    """فحص الموقع للتحقق من توفر المنتج"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # تحقق من حالة توفر المنتج
        stock_status = soup.find('div', class_='stock unavailable')
        available_status = soup.find('div', class_='availability only configurable-variation-qty')

        if stock_status and 'سيتم توفيرها في المخزون قريباً' in stock_status.get_text():
            return 'غير متوفر', IMAGE_URLS[url.split('/')[-1].split('.')[0]]['unavailable']
        elif available_status and 'left' in available_status.get_text():
            return 'متوفر', IMAGE_URLS[url.split('/')[-1].split('.')[0]]['available']

        # إالبحث في عناصر أخرى
        stock_status = soup.find('div', class_='stock')
        if stock_status:
            status_text = stock_status.get_text(strip=True)
            if 'متوفر' in status_text:
                return 'متوفر', IMAGE_URLS[url.split('/')[-1].split('.')[0]]['available']
            elif 'سيتم توفيرها في المخزون قريبًا' in status_text:
                return 'غير متوفر', IMAGE_URLS[url.split('/')[-1].split('.')[0]]['unavailable']

        stock_status = soup.find('div', class_='product-info-stock-sku')
        if stock_status:
            unavailable_status = stock_status.find('div', class_='stock unavailable')
            if  unavailable_status and 'سيتم توفيرها في المخزون قريبًا' in unavailable_status.get_text():
                return 'غير متوفر', IMAGE_URLS[url.split('/')[-1].split('.')[0]]['unavailable']

        # إذا كانت حالة التوفر غير معروفة
        return 'غير معروف', None

    except Exception as e:
        logger.error(f'Error checking website {url}: {e}')
        return 'خطأ', None


def create_keyboard_for_availability(status):
    """إنشاء لوحة المفاتيح التفاعلية"""
    if status == 'متوفر':
        keyboard = [
            [InlineKeyboardButton("السلة 🛒", url="https://www.dzrt.com/ar/checkout/cart/")],
            [InlineKeyboardButton("المنتجات ➕", url="https://www.dzrt.com/ar/our-products.html")],
            [InlineKeyboardButton("الدفع 💲", url="https://www.dzrt.com/ar/onestepcheckout.html")],
            [InlineKeyboardButton("طلباتي 📄", url="https://www.dzrt.com/ar/sales/order/history/")],
            [InlineKeyboardButton("تسجيل الدخول 🔒", url="https://www.dzrt.com/ar/customer/account/login")]
        ]
    else:  # لحالة "غير متوفر"
        keyboard = [
            [InlineKeyboardButton("السلة 🛒", url="https://www.dzrt.com/ar/checkout/cart/")],
            [InlineKeyboardButton("طلباتي 📄", url="https://www.dzrt.com/ar/sales/order/history/")]
        ]
    return InlineKeyboardMarkup(keyboard)


async def notify_products(context: CallbackContext) -> None:
    """وظيفة إخطار المستخدمين عن تحديثات المنتجات"""
    job = context.job
    logger.info("🚀🚀 Update 🚀🚀..")

    for url in URLS:
        status, img_url = check_website(url)
        product_key = url.split('/')[-1].split('.')[0]

        if url not in product_availability:
            product_availability[url] = status

        previous_status = product_availability[url]

        if status == 'غير متوفر' and previous_status == 'متوفر':
            product_availability[url] = status
            keyboard = create_keyboard_for_availability(status)
            message = f"❌ <a href='{url}'>{product_key.replace('-', ' ')}</a> : نفذ\n"
            await context.bot.send_photo(chat_id=job.chat_id, photo=img_url, caption=message, reply_markup=keyboard, parse_mode='HTML')

        elif status == 'متوفر' and previous_status != 'متوفر':
            product_availability[url] = status
            keyboard = create_keyboard_for_availability(status)
            message = f"✅ <a href='{url}'>{product_key.replace('-', ' ')}</a>👈🏻 متوفرالان\n"
            await context.bot.send_photo(chat_id=job.chat_id, photo=img_url, caption=message, reply_markup=keyboard, parse_mode='HTML')


async def error_handler(update: Update, context: CallbackContext) -> None:
    """وظيفة لمعالجة الأخطاء"""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    # إخطار المستخدم بوجود خطأ


async def send_test_message(context: CallbackContext):
    """إرسال رسالة تجريبية عند بدء تشغيل البوت"""
    try:
        for url in URLS:
            status, img_url = check_website(url)
            product_key = url.split('/')[-1].split('.')[0]
            message = f"رسالة تجريبية: حالة المنتج حالياً هي {status}\n"
            if url == 'https://www.dzrt.com/ar/mint-fusion.html':
                message += f"<a href='{url}'>منت فيوجن</a>"
            keyboard = create_keyboard_for_availability(status)
            await context.bot.send_photo(chat_id=context.job.chat_id, photo=img_url, caption=message, reply_markup=keyboard, parse_mode='HTML')
        logger.info("📛📛 Test Message Sent  📛📛")
    except Exception as e:
        logger.error(f"Error sending test message: {e}")


def main() -> None:
    """الوظيفة الرئيسية لتشغيل البوت"""
    application = Application.builder().token(TOKEN).build()

    # إضافة معالج الأوامر
    application.add_handler(CommandHandler("start", start))

    # إضافة معالج الأخطاء
    application.add_error_handler(error_handler)

    # إعداد وظيفة متكررة لفحص الموقع كل 15 ثانية
    job_queue = application.job_queue
    # استبدال-8 بمعرف المجموعة مع علامة سالب في البداية
    job_queue.run_repeating(notify_products, interval=10, first=10, chat_id=CHAT_ID)

    # بدء تشغيل البوت
    application.run_polling()


if __name__ == '__main__':
    main()
