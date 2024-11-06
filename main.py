import telebot
from telebot import types

import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import time
import re
bot = telebot.TeleBot('7280173517:AAFEJU9dKxsKQW-BCfdFnISWftGkxlrSWME')
def search_ozon(product_name):
    # Код для поиска на Ozon (оставьте как в вашем проекте)
    pass

def search_mvideo(product_name):
    # Код для поиска на M.Video (оставьте как в вашем проекте)
    pass

def search_dns(product_name):
    # Код для поиска на DNS (оставьте как в вашем проекте)
    pass

# Новая функция для поиска на SP-Computer
def search_sp_computer(product_name):
    try:
        # Настраиваем undetected-chromedriver для обхода антибот-защиты
        options = uc.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = uc.Chrome(options=options)

        # Переходим на страницу поиска с запросом
        url = f"https://www.sp-computer.ru/search/?q={product_name}"
        driver.get(url)
        time.sleep(3)  # Ожидаем загрузку JavaScript

        # Получаем HTML-контент и парсим с помощью BeautifulSoup
        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()

        # Ищем данные о товаре на странице
        results = []

        # Извлекаем ключевые слова из названия для фильтрации
        keywords = product_name.split()  # Разбиваем запрос на отдельные слова

        for item in soup.find_all('script'):
            if 'JCCatalogItem' in item.text:
                # Вытаскиваем JSON-данные из JavaScript-кода
                json_text = item.text.split('new JCCatalogItem(')[-1].split(');')[0]

                # Извлекаем нужные данные (название и цену)
                name = extract_value(json_text, 'NAME')
                price = extract_value(json_text, 'PRICE')

                # Проверяем, что хотя бы одно ключевое слово присутствует в названии товара
                if any(keyword.lower() in name.lower() for keyword in keywords):
                    results.append(f"{name}: {price} RUB")

        return results if results else ["Нет результатов на SP-Computer."]
    except Exception as e:
        return [f"Ошибка при запросе на SP-Computer: {e}"]



def extract_value(json_text, key):
    try:
        pattern = rf"'{key}':'(.*?)'"  # Шаблон для поиска значения по ключу
        match = re.search(pattern, json_text)
        return match.group(1) if match else "Данные не найдены"
    except Exception:
        return "Ошибка извлечения данных"

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

    sp_computer_results = search_sp_computer(product_name)
    response = f"Результаты поиска для '{product_name}':\n\n"
    response += "SP-Computer:\n" + "\n".join(sp_computer_results)

    bot.send_message(message.chat.id, response)


@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(message.chat.id,
                     "Это бот для поиска товаров. Используйте кнопки на клавиатуре для работы с ботом.")


bot.polling(non_stop=True)