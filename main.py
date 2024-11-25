import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import json
import time
import re
import threading
import hashlib
from concurrent.futures import ThreadPoolExecutor
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
import tempfile
import undetected_chromedriver as uc
import os
bot = telebot.TeleBot('7280173517:AAFEJU9dKxsKQW-BCfdFnISWftGkxlrSWME')
executor = ThreadPoolExecutor(max_workers=5)
# Хранилище для избранных товаров
user_favorites = {}
callback_data_map = {}  # Для хранения соответствия callback_data и названий товаров


def generate_callback_data(text):
    # Генерация хэша для callback_data
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:10]
def escape_markdown(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)

def init_webdriver():
    """Инициализация веб-драйвера."""
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Указываем временную директорию для ChromeDriver
    temp_dir = tempfile.mkdtemp()
    os.environ["UNDETECTED_CHROMEDRIVER_DIR"] = temp_dir

    driver = uc.Chrome(options=options)
    return driver

def scrolldown(driver, scrolls=10, pause_time=0.5):
    """Скроллинг страницы вниз."""
    for _ in range(scrolls):
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(pause_time)

def search_ozon(product_name):
    """Поиск товаров на Ozon с использованием Selenium."""
    driver = init_webdriver()
    try:
        # Открываем страницу поиска
        url = f"https://www.ozon.ru/search/?text={product_name}"
        driver.get(url)
        time.sleep(3)  # Ждем загрузки страницы

        # Скроллим вниз, чтобы подгрузить больше товаров
        scrolldown(driver, scrolls=15)

        # Находим карточки товаров
        product_cards = driver.find_elements(By.CSS_SELECTOR, '[data-widget="searchResultsV2"] .widget-search-result-container a')
        if not product_cards:
            return ["Нет результатов на Ozon."]

        results = []
        for card in product_cards[:5]:  # Берем только первые 5 товаров
            try:
                # Извлекаем название товара
                name_element = card.find_element(By.CSS_SELECTOR, '.tsBodyL')
                name = name_element.text if name_element else "Название не найдено"

                # Извлекаем цену товара
                price_element = card.find_element(By.CSS_SELECTOR, '.ui-e13')
                price = price_element.text if price_element else "Цена не указана"

                # Извлекаем ссылку на товар
                link = card.get_attribute("href")

                # Добавляем данные в результаты
                results.append({"name": name, "price": price, "url": link})
            except Exception as e:
                continue

        return results if results else ["Нет результатов на Ozon."]
    finally:
        driver.quit()

def get_product_info(product_url):
    try:
        response = requests.get(f"https://www.ozon.ru/api/composer-api.bx/page/json/v2?url={product_url}")
        json_data = json.loads(response.content.decode())
        full_name = json_data["seo"]["title"]
        description = json.loads(json_data["seo"]["script"][0]["innerHTML"])["description"]
        price = json.loads(json_data["seo"]["script"][0]["innerHTML"])["offers"]["price"]
        return {"name": full_name, "description": description, "price": price, "url": product_url}
    except Exception as e:
        return {"error": f"Ошибка получения данных: {e}"}



def search_sp_computer(product_name):
    try:
        driver = init_webdriver()
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
                results.append({"name": name, "url": full_url, "price": price})

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


def add_to_favorites(user_id, product_name):
    if user_id not in user_favorites:
        user_favorites[user_id] = []
    if product_name not in user_favorites[user_id]:
        user_favorites[user_id].append(product_name)


def show_favorites(user_id):
    return user_favorites.get(user_id, [])


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Найти товар", "Избранное")
    bot.send_message(message.chat.id, "Привет! Введите название товара для поиска.", reply_markup=markup)


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
            # Создаём клавиатуру для избранных товаров
            markup = types.InlineKeyboardMarkup()
            for favorite in favorites:
                markup.add(types.InlineKeyboardButton(text=favorite, callback_data=f"search_{favorite}"))
            bot.send_message(message.chat.id, "Ваши избранные товары:", reply_markup=markup)
        return

    bot.send_message(message.chat.id, f"Ищу товар: {product_name}")

    # Запуск поиска в отдельном потоке через ThreadPoolExecutor
    executor.submit(perform_search_and_respond, message, product_name)


def perform_search_and_respond(message, product_name):
    ozon_results = search_ozon(product_name)
    sp_computer_results = search_sp_computer(product_name)

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

    # Добавляем кнопки с уникальным callback_data
    markup = types.InlineKeyboardMarkup()
    for result in ozon_results[:5]:  # Максимум 5 кнопок
        if isinstance(result, dict):
            callback_data = generate_callback_data(result['name'])
            callback_data_map[callback_data] = result['name']
            markup.add(types.InlineKeyboardButton(text=result['name'], callback_data=callback_data))

    bot.send_message(message.chat.id, response, parse_mode='Markdown', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in callback_data_map)
def callback_add_to_favorites(call):
    bot.answer_callback_query(call.id)  # Подтверждаем нажатие
    product_name = callback_data_map[call.data]
    add_to_favorites(call.message.chat.id, product_name)
    bot.send_message(call.message.chat.id, f"Товар '{product_name}' добавлен в избранное.")



@bot.callback_query_handler(func=lambda call: call.data.startswith("search_"))
def callback_search_favorite(call):
    bot.answer_callback_query(call.id)
    product_name = call.data.split("search_")[-1]
    fake_message = types.SimpleNamespace(chat=call.message.chat, text=product_name)
    bot.send_message(call.message.chat.id, f"Повторный поиск: {product_name}")
    handle_text(fake_message)


bot.polling(non_stop=True)
