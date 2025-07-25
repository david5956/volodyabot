import telebot
from telebot import types
import os
import logging
from config import PAYMENT_TOKEN, ADMIN_ID

# Настройки логирования
logging.basicConfig(
    level=logging.INFO,
    filename='bot.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = telebot.TeleBot(os.getenv('TELEGRAM_TOKEN'))

# Вспомогательные функции для логирования
def log_user_action(message, action):
    user = message.from_user
    logger.info(f"UserID:{user.id} ChatID:{message.chat.id} Username:@{user.username} - {action}")

def log_user_error(message, error):
    user = message.from_user
    logger.error(f"UserID:{user.id} ChatID:{message.chat.id} Username:@{user.username} - ERROR: {error}")

# База данных и цены
orders = {}
prices = {
    'чб': {'односторонняя': 10, 'двухсторонняя': 15},
    'цветная': {'односторонняя': 20, 'двухсторонняя': 30},
    'формат': {'A5': 1, 'A4': 1.5, 'A3': 2, 'A2': 3}
}

# ===== ОСНОВНЫЕ КОМАНДЫ =====
@bot.message_handler(commands=['start'])
def start(message):
    try:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('🖨 Начать заказ')
        bot.send_message(
            message.chat.id,
            "Добро пожаловать в сервис печати от Володи!",
            reply_markup=markup
        )
        log_user_action(message, "Пользователь начал работу с ботом")
    except Exception as e:
        log_user_error(message, f"Ошибка в команде /start: {str(e)}")

# ===== СИСТЕМА ЗАКАЗА =====
@bot.message_handler(func=lambda m: m.text == '🖨 Начать заказ')
def start_order(message):
    try:
        chat_id = message.chat.id
        orders[chat_id] = {}
        ask_color_type(message)
        log_user_action(message, "Начал оформление заказа")
    except Exception as e:
        log_user_error(message, f"Ошибка при начале заказа: {str(e)}")

def ask_color_type(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Черно-белая', 'Цветная')
    bot.send_message(message.chat.id, "Выберите тип печати:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ['Черно-белая', 'Цветная'])
def select_color_type(message):
    try:
        chat_id = message.chat.id
        color_type = 'чб' if message.text == 'Черно-белая' else 'цветная'
        orders[chat_id]['type'] = color_type
        log_user_action(message, f"Выбрал тип печати: {color_type}")
        ask_page_count(message)
    except Exception as e:
        log_user_error(message, f"Ошибка выбора типа печати: {str(e)}")

def ask_page_count(message):
    try:
        markup = types.ReplyKeyboardRemove()
        msg = bot.send_message(
            message.chat.id,
            "Введите количество страниц (число):",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, process_page_count)
    except Exception as e:
        log_user_error(message, f"Ошибка запроса количества страниц: {str(e)}")

def process_page_count(message):
    try:
        chat_id = message.chat.id
        page_count = int(message.text)
        if page_count <= 0:
            raise ValueError("Некорректное количество страниц")
        
        orders[chat_id]['page_count'] = page_count
        log_user_action(message, f"Указал количество страниц: {page_count}")
        ask_format(message)
    except Exception as e:
        log_user_error(message, f"Ошибка обработки количества страниц: {str(e)}")
        bot.send_message(chat_id, "Пожалуйста, введите корректное число!")
        ask_page_count(message)

def ask_format(message):
    try:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('A5', 'A4', 'A3', 'A2')
        bot.send_message(
            message.chat.id,
            "Выберите формат бумаги:",
            reply_markup=markup
        )
    except Exception as e:
        log_user_error(message, f"Ошибка запроса формата бумаги: {str(e)}")

@bot.message_handler(func=lambda m: m.text in ['A5', 'A4', 'A3', 'A2'])
def select_format(message):
    try:
        chat_id = message.chat.id
        paper_format = message.text
        orders[chat_id]['format'] = paper_format
        log_user_action(message, f"Выбрал формат бумаги: {paper_format}")
        
        if orders[chat_id]['page_count'] > 1:
            ask_side_type(message)
        else:
            ask_file(message)
    except Exception as e:
        log_user_error(message, f"Ошибка выбора формата бумаги: {str(e)}")

def ask_side_type(message):
    try:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Односторонняя', 'Двухсторонняя')
        bot.send_message(
            message.chat.id,
            "Выберите тип печати:",
            reply_markup=markup
        )
    except Exception as e:
        log_user_error(message, f"Ошибка запроса типа печати: {str(e)}")

@bot.message_handler(func=lambda m: m.text in ['Односторонняя', 'Двухсторонняя'])
def select_side_type(message):
    try:
        chat_id = message.chat.id
        side_type = message.text.lower()
        orders[chat_id]['side'] = side_type
        log_user_action(message, f"Выбрал тип печати: {side_type}")
        ask_file(message)
    except Exception as e:
        log_user_error(message, f"Ошибка выбора типа печати: {str(e)}")

def ask_file(message):
    try:
        markup = types.ReplyKeyboardRemove()
        msg = bot.send_message(
            message.chat.id,
            "Пожалуйста, прикрепите файл для печати (PDF, DOCX, JPG):"
        )
        bot.register_next_step_handler(msg, process_file)
    except Exception as e:
        log_user_error(message, f"Ошибка запроса файла: {str(e)}")

def process_file(message):
    try:
        chat_id = message.chat.id
        if message.document:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            orders[chat_id]['file'] = {
                'file_name': message.document.file_name,
                'file_id': message.document.file_id
            }
            log_user_action(message, f"Загрузил файл: {message.document.file_name}")
            ask_comment(message)
        else:
            bot.send_message(chat_id, "Пожалуйста, прикрепите файл!")
            ask_file(message)
    except Exception as e:
        log_user_error(message, f"Ошибка обработки файла: {str(e)}")

def ask_comment(message):
    try:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Пропустить')
        msg = bot.send_message(
            message.chat.id,
            "Хотите добавить комментарий к заказу?",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, process_comment)
    except Exception as e:
        log_user_error(message, f"Ошибка запроса комментария: {str(e)}")

def process_comment(message):
    try:
        chat_id = message.chat.id
        if message.text != 'Пропустить':
            orders[chat_id]['comment'] = message.text
            log_user_action(message, f"Добавил комментарий: {message.text}")
        else:
            log_user_action(message, "Пропустил добавление комментария")
        
        show_order_summary(message)
    except Exception as e:
        log_user_error(message, f"Ошибка обработки комментария: {str(e)}")

def show_order_summary(message):
    try:
        chat_id = message.chat.id
        order = orders[chat_id]
        
        # Расчет стоимости
        base_price = prices[order['type']].get(order.get('side', 'односторонняя'), 10)
        format_multiplier = prices['формат'][order['format']]
        total = base_price * order['page_count'] * format_multiplier
        
        text = (f"📝 Ваш заказ:\n"
               f"Тип: {order['type']}\n"
               f"Страниц: {order['page_count']}\n"
               f"Формат: {order['format']}\n")
        
        if order.get('side'):
            text += f"Тип печати: {order['side']}\n"
        
        text += f"Файл: {order['file']['file_name']}\n"
        
        if order.get('comment'):
            text += f"Комментарий: {order['comment']}\n"
        
        text += f"\nИтого: {total} руб."
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('✅ Подтвердить заказ', '❌ Отменить')
        bot.send_message(chat_id, text, reply_markup=markup)
        
        log_user_action(message, f"Показал итог заказа. Сумма: {total} руб.")
    except Exception as e:
        log_user_error(message, f"Ошибка показа итогов заказа: {str(e)}")

# ===== ОПЛАТА И КОРЗИНА =====
@bot.message_handler(func=lambda m: m.text == '✅ Подтвердить заказ')
def confirm_order(message):
    try:
        chat_id = message.chat.id
        order = orders.get(chat_id)
        
        if not order:
            bot.send_message(chat_id, "Ошибка: заказ не найден")
            return
        
        # Расчет стоимости
        base_price = prices[order['type']].get(order.get('side', 'односторонняя'), 10)
        format_multiplier = prices['формат'][order['format']]
        total = int(base_price * order['page_count'] * format_multiplier * 100)  # Важно: целое число в копейках
        
        # Получаем токен из конфига
        provider_token =PAYMENT_TOKEN  
        
        bot.send_invoice(
            chat_id,
            title="Оплата печати",
            description=f"{order['type']} печать, {order['format']}",
            invoice_payload=f"order_{chat_id}",
            provider_token=provider_token,
            start_parameter="print_order",
            currency="RUB",
            prices=[types.LabeledPrice("Печать", total)],
            need_email=True,
            need_phone_number=True
        )
        
    except Exception as e:
        logger.error(f"Ошибка создания инвойса: {str(e)}", exc_info=True)
        bot.send_message(chat_id, "Извините, произошла ошибка. Мы уже работаем над её устранением.")
        
        # Отправляем уведомление себе
        bot.send_message(
            931928744,  # Ваш ID
            f"⚠️ Ошибка оплаты у @{message.from_user.username}:\n{str(e)}"
        )

@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout(pre_checkout_query):
    try:
        user_id = pre_checkout_query.from_user.id
        if user_id in orders:
            bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
            logger.info(f"UserID:{user_id} - Подтвержден pre-checkout запрос")
        else:
            bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False,
                                      error_message="Заказ не найден или устарел")
            logger.error(f"UserID:{user_id} - Недействительный pre-checkout запрос")
    except Exception as e:
        logger.error(f"Ошибка обработки pre-checkout: {str(e)}")
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False,
                                  error_message="Произошла ошибка")

@bot.message_handler(content_types=['successful_payment'])
def process_successful_payment(message):
    try:
        chat_id = message.chat.id
        order = orders.get(chat_id)
        
        if not order:
            bot.send_message(chat_id, "Ошибка: данные заказа не найдены")
            log_user_error(message, "Оплата без сохраненного заказа")
            return
        
        # Расчет стоимости
        base_price = prices[order['type']].get(order.get('side', 'односторонняя'), 10)
        format_multiplier = prices['формат'][order['format']]
        total = base_price * order['page_count'] * format_multiplier
        
        email = message.successful_payment.order_info.email or "не указан"
        phone = getattr(message.successful_payment.order_info, 'phone_number', "не указан")
        
        # Уведомление пользователю
        bot.send_message(
            chat_id,
            f"✅ Оплата прошла успешно!\n\n"
            f"Детали заказа:\n"
            f"Тип: {order['type']}\n"
            f"Стороны: {order['side']}\n"
            f"Сумма: {total} руб.\n"
            f"Email: {email}\n"
            f"Телефон: {phone}\n\n"
            f"Ваш заказ передан в работу!",
            reply_markup=types.ReplyKeyboardRemove()
        )
        
        # Уведомление владельцу 
        owner_id = ADMIN_ID
        bot.send_message(
            owner_id,
            f"💰 Новый оплаченный заказ!\n"
            f"От: @{message.from_user.username}\n"
            f"Тип: {order['type']}\n"
            f"Стороны: {order['side']}\n"
            f"Сумма: {total} руб.\n"
            f"Email: {email}\n"
            f"Телефон: {phone}\n"
            f"ID платежа: {message.successful_payment.telegram_payment_charge_id}"
        )
        
        log_user_action(message, f"Успешная оплата заказа. Сумма: {total} руб.")
        
        # Очистка заказа
        if chat_id in orders:
            del orders[chat_id]
    except Exception as e:
        log_user_error(message, f"Ошибка обработки оплаты: {str(e)}")

@bot.message_handler(func=lambda m: m.text == '❌ Отменить')
def cancel_order(message):
    try:
        chat_id = message.chat.id
        if chat_id in orders:
            del orders[chat_id]
        bot.send_message(chat_id, "Заказ отменен", reply_markup=types.ReplyKeyboardRemove())
        start(message)
        log_user_action(message, "Отменил заказ")
    except Exception as e:
        log_user_error(message, f"Ошибка отмены заказа: {str(e)}")

@bot.message_handler(func=lambda m: m.text == '✏️ Изменить')
def edit_order(message):
    try:
        chat_id = message.chat.id
        if chat_id in orders:
            del orders[chat_id]
        start_order(message)
        log_user_action(message, "Редактирование заказа")
    except Exception as e:
        log_user_error(message, f"Ошибка редактирования заказа: {str(e)}")

if __name__ == '__main__':
    logger.info("===== БОТ ЗАПУЩЕН =====")
    bot.polling(none_stop=True)