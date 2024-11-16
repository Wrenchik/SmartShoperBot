import telebot
from telebot import types, util
import requests
from bs4 import BeautifulSoup
import json
import time
import re
import undetected_chromedriver as uc
from selenium_stealth import stealth
from curl_cffi import requests as curl_requests
from selenium import webdriver
from types import SimpleNamespace
bot = telebot.TeleBot('7280173517:AAFEJU9dKxsKQW-BCfdFnISWftGkxlrSWME')


# Хранилище для избранных товаров
user_favorites = {}
callback_data_map = {}  # Для хранения соответствия callback_data и названий товаров


def init_webdriver():
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = uc.Chrome(options=options)
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True)
    driver.maximize_window()
    return driver


def scrolldown(driver, deep):
    for _ in range(deep):
        driver.execute_script('window.scrollBy(0, 500)')
        time.sleep(0.1)


def get_product_info(product_url):
    session = curl_requests.Session()
    try:
        raw_data = session.get(f"https://www.ozon.ru/api/composer-api.bx/page/json/v2?url={product_url}")
        json_data = json.loads(raw_data.content.decode())

        full_name = json_data["seo"]["title"]
        description = json.loads(json_data["seo"]["script"][0]["innerHTML"])["description"]
        price = json.loads(json_data["seo"]["script"][0]["innerHTML"])["offers"]["price"]

        return {
            "name": full_name,
            "description": description,
            "price": price,
            "url": product_url
        }
    except Exception as e:
        return {"error": f"Ошибка получения данных: {e}"}


def search_ozon(product_name):
    driver = init_webdriver()
    url = f"https://www.ozon.ru/search/?text={product_name}&from_global=true"
    driver.get(url)
    scrolldown(driver, 20)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    results = []
    content_with_cards = soup.find("div", {"class": "widget-search-result-container"})
    if not content_with_cards:
        return ["Нет результатов на Ozon."]

    cards = content_with_cards.find_all("a", href=True)
    for card in cards[:5]:
        card_url = card["href"]
        full_url = f"https://www.ozon.ru{card_url}"
        product_info = get_product_info(full_url)

        if product_info and "error" not in product_info:
            results.append({
                "name": product_info['name'],
                "url": full_url,
                "price": product_info['price']
            })

    return results if results else ["Нет результатов на Ozon."]


def search_sp_computer(product_name):
    try:
        options = uc.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = uc.Chrome(options=options)

        url = f"https://www.sp-computer.ru/search/?q={product_name}"
        driver.get(url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()

        results = []
        for item in soup.find_all('script'):
            if 'JCCatalogItem' in item.text:
                json_text = item.text.split('new JCCatalogItem(')[-1].split(');')[0]
                name = extract_value(json_text, 'NAME')
                price = extract_value(json_text, 'PRICE')
                detail_url = extract_value(json_text, 'DETAIL_PAGE_URL')
                full_url = f"https://www.sp-computer.ru{detail_url}"
                results.append({
                    "name": name,
                    "url": full_url,
                    "price": price
                })

        return results if results else ["Нет результатов на SP-Computer."]
    except Exception as e:
        return [f"Ошибка при запросе на SP-Computer: {e}"]


def extract_value(json_text, key):
    try:
        pattern = rf"'{key}':'(.*?)'"
        match = re.search(pattern, json_text)
        return match.group(1) if match else "Данные не найдены"
    except Exception:
        return "Ошибка извлечения данных"


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Найти товар", "Избранное")
    bot.send_message(message.chat.id, "Привет! Введите название товара для поиска.", reply_markup=markup)


# Добавить товар в избранное
def add_to_favorites(user_id, product_name):
    if user_id not in user_favorites:
        user_favorites[user_id] = []
    if product_name not in user_favorites[user_id]:
        user_favorites[user_id].append(product_name)


# Показать избранное
def show_favorites(user_id):
    return user_favorites.get(user_id, [])


@bot.message_handler(content_types=['text'])
def handle_text(message):
    product_name = message.text.strip()
    if product_name == 'Найти товар':
        bot.send_message(message.chat.id, "Введите название товара для поиска.")
        return
    if product_name == 'Избранное':
        favorites = show_favorites(message.chat.id)
        if not favorites:
            bot.send_message(message.chat.id, "У вас пока нет избранных товаров.")
        else:
            # Отображаем избранные товары как кнопки
            markup = types.InlineKeyboardMarkup()
            for favorite in favorites:
                markup.add(types.InlineKeyboardButton(text=favorite, callback_data=f"search_{favorite}"))
            bot.send_message(message.chat.id, "Ваши избранные товары:", reply_markup=markup)
        return

    bot.send_message(message.chat.id, f"Ищу товар: {product_name}")

    # Получаем результаты
    ozon_results = search_ozon(product_name)
    sp_computer_results = search_sp_computer(product_name)

    # Формируем ответ
    response = f"*Результаты поиска для '{product_name}':*\n\n"

    # Добавляем результаты Ozon
    response += "*Ozon:*\n"
    for result in ozon_results:
        if isinstance(result, dict):
            response += f"[{result['name']}]({result['url']}): {result['price']} RUB\n"
        else:
            response += result + "\n"

    # Добавляем результаты SP-Computer
    response += "\n*SP-Computer:*\n"
    for result in sp_computer_results:
        if isinstance(result, dict):
            response += f"[{result['name']}]({result['url']}): {result['price']} RUB\n"
        else:
            response += result + "\n"

    # Добавляем одну кнопку "Добавить в избранное"
    markup = types.InlineKeyboardMarkup()
    callback_data = f"add_{product_name}"
    callback_data_map[callback_data] = product_name
    markup.add(types.InlineKeyboardButton(text="Добавить в избранное", callback_data=callback_data))

    bot.send_message(message.chat.id, response, parse_mode='Markdown', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("add_"))
def callback_add_to_favorites(call):
    """Обработчик кнопки 'Добавить в избранное'."""
    bot.answer_callback_query(call.id)  # Сразу отвечаем на callback-запрос
    product_name = callback_data_map.get(call.data, "Неизвестный товар")
    add_to_favorites(call.message.chat.id, product_name)
    bot.send_message(call.message.chat.id, f"{product_name} добавлен в избранное")


@bot.callback_query_handler(func=lambda call: call.data.startswith("search_"))
def callback_search_favorite(call):
    """Обработчик выбора товара из избранного."""
    bot.answer_callback_query(call.id)  # Отвечаем на callback-запрос
    product_name = call.data.split("search_")[-1]  # Извлекаем название товара

    # Передаем "фальшивое" сообщение в handle_text
    fake_message = SimpleNamespace(chat=call.message.chat, text=product_name)
    bot.send_message(call.message.chat.id, f"Повторный поиск: {product_name}")
    handle_text(fake_message)

bot.polling(non_stop=True)
