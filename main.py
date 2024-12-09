import asyncio
from telebot.async_telebot import AsyncTeleBot
from telebot import types
import requests
from bs4 import BeautifulSoup
import json
import time
import re
import hashlib
import os
import tempfile
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
import undetected_chromedriver as uc
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = AsyncTeleBot(BOT_TOKEN)

# Хранилище для избранных товаров
user_favorites = {}
callback_data_map = {}

def generate_callback_data(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:10]

def escape_markdown(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)

def init_webdriver():
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    temp_dir = tempfile.mkdtemp()
    os.environ["UNDETECTED_CHROMEDRIVER_DIR"] = temp_dir

    driver = uc.Chrome(options=options)
    return driver

def scrolldown(driver, scrolls=10, pause_time=0.5):
    for _ in range(scrolls):
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(pause_time)

async def search_ozon(product_name):
    driver = init_webdriver()
    try:
        url = f"https://www.ozon.ru/search/?text={product_name}"
        driver.get(url)
        time.sleep(3)
        scrolldown(driver, scrolls=15)

        product_cards = driver.find_elements(By.CSS_SELECTOR, '[data-widget="searchResultsV2"] .widget-search-result-container a')
        if not product_cards:
            return ["Нет результатов на Ozon."]

        results = []
        for card in product_cards[:5]:
            try:
                name_element = card.find_element(By.CSS_SELECTOR, '.tsBodyL')
                name = name_element.text if name_element else "Название не найдено"

                price_element = card.find_element(By.CSS_SELECTOR, '.ui-e13')
                price = price_element.text if price_element else "Цена не указана"

                link = card.get_attribute("href")
                results.append({"name": name, "price": price, "url": link})
            except Exception:
                continue
        return results if results else ["Нет результатов на Ozon."]
    finally:
        driver.quit()

async def search_sp_computer(product_name):
    driver = init_webdriver()
    try:
        url = f"https://www.sp-computer.ru/search/?q={product_name}"
        driver.get(url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, "html.parser")

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
    finally:
        driver.quit()

def extract_value(json_text, key):
    pattern = rf"'{key}':'(.*?)'"
    match = re.search(pattern, json_text)
    return match.group(1) if match else "Данные не найдены"

def add_to_favorites(user_id, product_name):
    if user_id not in user_favorites:
        user_favorites[user_id] = []
    if product_name not in user_favorites[user_id]:
        user_favorites[user_id].append(product_name)

def show_favorites(user_id):
    return user_favorites.get(user_id, [])

@bot.message_handler(commands=['start'])
async def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Найти товар", "Избранное")
    markup.add("Промокоды", "Помощь")
    markup.add("О боте")

    start_message = (
        "Привет!\n"
        "Я ваш персональный помощник в поиске выгодных цен и крутых предложений на маркетплейсах!\n\n"
        "Введите название товара, и я найду лучшие варианты с ценами, описаниями и ссылками.\n\n"
        "Давайте начнем! Просто нажмите \"Найти товар\" в меню.\n\n"
        "Нужна помощь? Нажмите \"Помощь\" в меню.\n\n"
        "P.S. Цены актуальны на момент запроса."
    )
    await bot.send_message(message.chat.id, start_message, reply_markup=markup)

@bot.message_handler(content_types=['text'])
async def handle_text(message):
    product_name = message.text.strip()

    if product_name == 'Найти товар':
        await bot.send_message(message.chat.id, "Введите название товара для поиска.")
        return

    if product_name == 'Избранное':
        favorites = show_favorites(message.chat.id)
        if not favorites:
            await bot.send_message(message.chat.id, "У вас пока нет избранных товаров.")
        else:
            markup = types.InlineKeyboardMarkup()
            for favorite in favorites:
                markup.add(types.InlineKeyboardButton(text=favorite, callback_data=f"search_{favorite}"))
            await bot.send_message(message.chat.id, "Ваши избранные товары:", reply_markup=markup)
        return

    if product_name == 'Промокоды':
        promo_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        promo_markup.add("Промокоды Ozon", "Промокоды Wildberries")
        promo_markup.add("Промокоды Мегамаркета", "Промокоды Яндекс Маркет")
        promo_markup.add("Назад")
        await bot.send_message(message.chat.id, "Выберите маркетплейс для просмотра промокодов:", reply_markup=promo_markup)
        return

    if product_name == 'Помощь':
        help_text = (
            "Добро пожаловать в справочную секцию!\n\n"
            "Функционал нашего бота:\n"
            "1. Поиск товара\n"
            "• Введите название.\n"
            "• Я найду лучшие предложения с ценами, кратким описанием и ссылками на маркетплейсы.\n\n"
            "2. Избранное\n"
            "• Добавляйте товары в избранное, чтобы следить за ценами.\n\n"
            "3. Промокоды\n"
            "• Узнавайте о новых промокодах и скидках.\n"
            "• Применяйте их на маркетплейсы для выгодных покупок.\n\n"
            "Обратная связь:\n"
            "Если у вас есть вопросы или предложения, напишите нам: smartshoperbotsup@gmail.com\n\n"
            "Спасибо, что пользуетесь ботом!"
        )
        await bot.send_message(message.chat.id, help_text)
        return

    if product_name == 'О боте':
        about_text = (
            "Добро пожаловать в информационную секцию!\n\n"
            "Этот бот создан, чтобы помочь вам находить самые выгодные предложения на маркетплейсах. "
            "Он собирает актуальные цены с таких платформ, как Ozon, Wildberries и Яндекс.Маркет, и предоставляет вам:\n\n"
            "• Лучшие цены на товары с кратким описанием и ссылками.\n"
            "• Возможность сохранять товары в избранное.\n"
            "• Промокоды и скидки на популярные товары."
        )
        await bot.send_message(message.chat.id, about_text)
        return

    if product_name in ['Промокоды Ozon', 'Промокоды Wildberries', 'Промокоды Мегамаркета', 'Промокоды Яндекс Маркет']:
        await bot.send_message(message.chat.id, f"Скоро будут доступны актуальные промокоды для {product_name}!")
        return

    if product_name == 'Назад':
        await start(message)
        return

    await bot.send_message(message.chat.id, f"Ищу товар: {product_name}")
    ozon_results, sp_computer_results = await asyncio.gather(
        search_ozon(product_name),
        search_sp_computer(product_name)
    )

    response = f"*Результаты поиска для '{product_name}':*\n\n"
    response += "*Ozon:*\n"
    for result in ozon_results:
        if isinstance(result, dict):
            response += f"[{result['name']}]({result['url']}): {result['price']} RUB\n"
        else:
            response += result + "\n"
    response += "\n*SP-Computer:*\n"
    for result in sp_computer_results:
        if isinstance(result, dict):
            response += f"[{result['name']}]({result['url']}): {result['price']} RUB\n"
        else:
            response += result + "\n"

    markup = types.InlineKeyboardMarkup()
    for result in ozon_results[:5]:
        if isinstance(result, dict):
            callback_data = generate_callback_data(result['name'])
            callback_data_map[callback_data] = result['name']
            markup.add(types.InlineKeyboardButton(text=result['name'], callback_data=callback_data))

    await bot.send_message(message.chat.id, response, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in callback_data_map)
async def callback_add_to_favorites(call):
    await bot.answer_callback_query(call.id)
    product_name = callback_data_map[call.data]
    add_to_favorites(call.message.chat.id, product_name)
    await bot.send_message(call.message.chat.id, f"Товар '{product_name}' добавлен в избранное.")

# Запуск асинхронного бота
asyncio.run(bot.polling(non_stop=True))
