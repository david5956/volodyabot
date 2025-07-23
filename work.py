import telebot
from telebot import types
import os
import logging

# Настройки
logging.basicConfig(level=logging.INFO, filename='bot.log', 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(os.getenv('TELEGRAM_TOKEN'))

# База данных (временная)
orders = {}
prices = {
    'чб': {'односторонняя': 10, 'двухсторонняя': 15},
    'цветная': {'односторонняя': 20, 'двухсторонняя': 30}
}

# ===== ОСНОВНЫЕ КОМАНДЫ =====
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('🖨 Начать заказ')
    bot.send_message(message.chat.id, "Добро пожаловать в сервис печати от Володи!", reply_markup=markup)

# ===== СИСТЕМА ЗАКАЗА =====
@bot.message_handler(func=lambda m: m.text == '🖨 Начать заказ')
def start_order(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Черно-белая', 'Цветная')
    markup.add('🛒 Корзина')
    bot.send_message(message.chat.id, "Выберите тип печати:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ['Черно-белая', 'Цветная'])
def select_side(message):
    color_type = 'чб' if message.text == 'Черно-белая' else 'цветная'
    orders[message.chat.id] = {'type': color_type}
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Односторонняя', 'Двухсторонняя')
    markup.add('↩ Назад')
    bot.send_message(message.chat.id, "Выберите тип печати:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ['Односторонняя', 'Двухсторонняя'])
def confirm_order(message):
    chat_id = message.chat.id
    side_type = 'односторонняя' if message.text == 'Односторонняя' else 'двухсторонняя'
    
    orders[chat_id]['side'] = side_type
    price = prices[orders[chat_id]['type']][side_type]
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('✅ Подтвердить заказ', '❌ Отменить')
    markup.add('🛒 Корзина')
    
    bot.send_message(chat_id, 
                   f"Ваш выбор:\n"
                   f"Тип: {orders[chat_id]['type']}\n"
                   f"Стороны: {side_type}\n"
                   f"Цена: {price} руб.\n\n"
                   f"Подтверждаете?", reply_markup=markup)

# ===== КОРЗИНА И ОПЛАТА =====
@bot.message_handler(func=lambda m: m.text in ['🛒 Корзина', '✅ Подтвердить заказ'])
def show_cart(message):
    chat_id = message.chat.id
    if chat_id not in orders or not orders[chat_id]:
        bot.send_message(chat_id, "Корзина пуста!")
        return
    
    order = orders[chat_id]
    price = prices[order['type']][order['side']]
    
    text = (f"Текущий заказ:\n"
           f"Тип печати: {order['type']}\n"
           f"Стороны: {order['side']}\n"
           f"Итого: {price} руб.")
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('💳 Оплатить заказ', '✏️ Изменить')
    markup.add('❌ Отменить')
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '💳 Оплатить заказ')
def process_payment(message):
    chat_id = message.chat.id
    if chat_id not in orders:
        bot.send_message(chat_id, "Ошибка: заказ не найден")
        return
    
    order = orders[chat_id]
    price = prices[order['type']][order['side']] * 100  # В копейках
    
    try:
        bot.send_invoice(
            chat_id,
            title="Оплата печати",
            description=f"{order['type']} печать, {order['side']}",
            invoice_payload=f"order_{chat_id}",
            provider_token="1744374395:TEST:f7c0d8d60430fdf930fe",  # Тестовый токен
            start_parameter="print_order",
            currency="RUB",
            prices=[types.LabeledPrice("Печать", price)],
            need_email=True,
            need_phone_number=True
        )
    except Exception as e:
        logger.error(f"Payment error: {e}")
        bot.send_message(chat_id, "Ошибка при создании счета. Попробуйте позже.")

@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout(pre_checkout_query):
    try:
        chat_id = pre_checkout_query.from_user.id
        if chat_id in orders:
            bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
        else:
            bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False,
                                      error_message="Заказ не найден или устарел")
    except Exception as e:
        logger.error(f"Pre-checkout error: {e}")
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False,
                                  error_message="Произошла ошибка")

@bot.message_handler(content_types=['successful_payment'])
def process_successful_payment(message):
    chat_id = message.chat.id
    order = orders.get(chat_id)
    
    if not order:
        bot.send_message(chat_id, "Ошибка: данные заказа не найдены")
        return
    
    price = prices[order['type']][order['side']]
    email = message.successful_payment.order_info.email or "не указан"
    phone = getattr(message.successful_payment.order_info, 'phone_number', "не указан")
    
    # Уведомление пользователю
    bot.send_message(chat_id,
                   f"✅ Оплата прошла успешно!\n\n"
                   f"Детали заказа:\n"
                   f"Тип: {order['type']}\n"
                   f"Стороны: {order['side']}\n"
                   f"Сумма: {price} руб.\n"
                   f"Email: {email}\n"
                   f"Телефон: {phone}\n\n"
                   f"Ваш заказ передан в работу!",
                   reply_markup=types.ReplyKeyboardRemove())
    
    # Уведомление владельцу
    owner_id = 123456789  # Ваш ID
    bot.send_message(owner_id,
                   f"💰 Новый оплаченный заказ!\n"
                   f"От: @{message.from_user.username}\n"
                   f"Тип: {order['type']}\n"
                   f"Стороны: {order['side']}\n"
                   f"Сумма: {price} руб.\n"
                   f"Email: {email}\n"
                   f"Телефон: {phone}\n"
                   f"ID платежа: {message.successful_payment.telegram_payment_charge_id}")
    
    # Очистка заказа
    if chat_id in orders:
        del orders[chat_id]

@bot.message_handler(func=lambda m: m.text == '❌ Отменить')
def cancel_order(message):
    chat_id = message.chat.id
    if chat_id in orders:
        del orders[chat_id]
    bot.send_message(chat_id, "Заказ отменен", reply_markup=types.ReplyKeyboardRemove())
    start(message)

@bot.message_handler(func=lambda m: m.text == '✏️ Изменить')
def edit_order(message):
    chat_id = message.chat.id
    if chat_id in orders:
        del orders[chat_id]
    start_order(message)

@bot.message_handler(func=lambda m: m.text == '↩ Назад')
def back_to_menu(message):
    start_order(message)

# ===== ЗАПУСК =====
if __name__ == '__main__':
    logger.info("Бот запущен")
    bot.polling(none_stop=True)