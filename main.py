import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
bot = telebot.TeleBot('7280173517:AAFEJU9dKxsKQW-BCfdFnISWftGkxlrSWME')


def search_dns(product_name):
    try:
        url = f"https://www.dns-shop.ru/search/?q={product_name}"
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        for item in soup.select(".catalog-product"):
            name = item.select_one(".catalog-product__name").text.strip()
            price = item.select_one(".product-buy__price").text.strip()
            results.append(f"{name}: {price}")

        return results if results else ["Нет результатов на DNS."]
    except requests.RequestException:
        return ["Ошибка при запросе на DNS."]
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Найти товар')
    btn2 = types.KeyboardButton('Избранное')
    btn3 = types.KeyboardButton('Помощь')
    markup.add(btn1)
    markup.add(btn2, btn3)

    bot.send_message(
        message.chat.id,
        f"Привет, {message.from_user.first_name}! Я бот, который поможет тебе совершить выгодную покупку, нажми «Найти товар», чтобы я смог тебе помочь.",
        reply_markup=markup
    )


@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text == 'Найти товар':
        bot.send_message(message.chat.id, 'Введите конкретное название товара')
        bot.register_next_step_handler(message, search_product)
    elif message.text == 'Избранное':
        bot.send_message(message.chat.id, 'Ваши избранные товары:')
    elif message.text == 'Помощь':
        bot.send_message(message.chat.id, 'Помощь')
    elif message.text.lower() == 'привет':
        bot.send_message(message.chat.id, f"Привет, {message.from_user.first_name}!")
    else:
        bot.send_message(message.chat.id, "Неизвестная команда. Выберите действие на клавиатуре.")

def search_product(message):
    product_name = message.text.strip()
    bot.send_message(message.chat.id, f"Ищу товар: {product_name}")
    dns_results = search_dns(product_name)
    response = f"Результаты поиска для '{product_name}':\n\n"
    response += "DNS:\n" + "\n".join(dns_results) + "\n\n"
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(message.chat.id,
                     "Это бот для поиска товаров. Используйте кнопки на клавиатуре для работы с ботом.")


bot.polling(non_stop=True)