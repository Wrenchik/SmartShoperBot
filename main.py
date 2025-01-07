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
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import aiohttp

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

async def search_mvideo(product_name):
    driver = init_webdriver()
    try:
        url = f"https://www.mvideo.ru/product-list-page?q={product_name}"
        driver.get(url)
        time.sleep(3)
        scrolldown(driver, scrolls=10)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        results = []

        product_cards = soup.select(".product-card")
        for card in product_cards[:5]:
            name = card.select_one(".product-title__text")
            price = card.select_one(".price__main-value")
            link = card.select_one("a.product-title__text")["href"]
            if name and price and link:
                results.append({
                    "name": name.text.strip(),
                    "price": price.text.strip(),
                    "url": f"https://www.mvideo.ru{link}"
                })

        return results if results else ["Нет результатов на М.Видео."]
    finally:
        driver.quit()

async def search_wildberries(product_name):
    driver = init_webdriver()
    try:
        url = f"https://www.wildberries.ru/catalog/0/search.aspx?search={product_name}"
        driver.get(url)
        time.sleep(3)
        scrolldown(driver, scrolls=10)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        results = []

        product_cards = soup.select(".product-card__wrapper")
        for card in product_cards[:5]:
            name = card.select_one(".goods-name")
            price = card.select_one(".price-value")
            link = card.select_one("a")["href"]
            if name and price and link:
                results.append({
                    "name": name.text.strip(),
                    "price": price.text.strip(),
                    "url": f"https://www.wildberries.ru{link}"
                })

        return results if results else ["Нет результатов на Wildberries."]
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

async def search_technopark(product_name):
    url = "https://www.technopark.ru/search/"
    params = {
        "q": product_name,
        "withContent": "true",
        "strategy": "vectors_extended,zero_queries"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36"
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    return [f"Ошибка при парсинге Technopark.ru: {response.status}"]

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                results = []
                product_cards = soup.select(".product-card")  # Подкорректируйте селектор для Technopark.
                for card in product_cards[:5]:
                    name = card.select_one(".product-card__title")
                    price = card.select_one(".product-card__price")
                    link = card.select_one("a")["href"]

                    if name and price and link:
                        results.append({
                            "name": name.text.strip(),
                            "price": price.text.strip(),
                            "url": f"https://www.technopark.ru{link}"
                        })

                return results if results else ["Нет результатов на Technopark.ru."]
        except Exception as e:
            return [f"Ошибка при парсинге Technopark.ru: {str(e)}"]


async def fake_search(product_name):
    return ["Нет результатов."]


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
        # Получаем список избранных товаров
        favorites = user_favorites.get(message.chat.id, [])
        if not favorites:
            await bot.send_message(message.chat.id, "У вас пока нет избранных товаров.")
        else:
            for favorite in favorites:
                # Создаем клавиатуру с кнопками
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton(
                        text="🔍 Найти",
                        callback_data=f"search_{favorite}"
                    ),
                    types.InlineKeyboardButton(
                        text="❌ Удалить",
                        callback_data=f"delete_{favorite}"
                    )
                )
                # Отправляем сообщение с кнопками
                await bot.send_message(
                    message.chat.id,
                    f"*{favorite}*",  # Название товара
                    parse_mode="Markdown",
                    reply_markup=markup
                )
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
    ozon_results, sp_computer_results, mvideo_results, wildberries_results, technopark_results = await asyncio.gather(
        fake_search(product_name),
        search_sp_computer(product_name),
        fake_search(product_name),
        fake_search(product_name),
        search_technopark(product_name)
    )

    # Формирование ответа
    response = f"*Результаты поиска для '{product_name}':*\n\n"

    for platform, results in [
        ("Ozon", ozon_results),
        ("SP-Computer", sp_computer_results),
        ("М.Видео", mvideo_results),
        ("Wildberries", wildberries_results),
        ("Технопарк", technopark_results),
    ]:
        response += f"*{platform}:*\n"
        for result in results:
            if isinstance(result, dict):
                response += f"[{result['name']}]({result['url']}): {result['price']} RUB\n"
            else:
                response += result + "\n"
        response += "\n"

    # Добавление кнопки "Добавить в избранное"
    markup = types.InlineKeyboardMarkup()
    callback_data = generate_callback_data(product_name)
    callback_data_map[callback_data] = product_name
    markup.add(types.InlineKeyboardButton(text="Добавить в избранное", callback_data=callback_data))

    await bot.send_message(message.chat.id, response, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("search_"))
async def callback_search_favorite(call):
    await bot.answer_callback_query(call.id)
    product_name = call.data[len("search_"):]
    await bot.send_message(call.message.chat.id, f"Ищу товар: {product_name}")
    # Логика поиска как в handle_text


@bot.callback_query_handler(func=lambda call: call.data.startswith("search_"))
async def callback_search_favorite(call):
    await bot.answer_callback_query(call.id)

    # Извлечение и декодирование названия товара из callback_data
    callback_data = call.data[len("search_"):]
    product_name = callback_data_map.get(callback_data, None)  # Получаем название из карты callback_data

    if not product_name:
        await bot.send_message(call.message.chat.id, "Ошибка: не удалось найти товар для поиска.")
        return

    await bot.send_message(product_name.chat.id, f"Ищу товар: {product_name}")
    ozon_results, sp_computer_results, mvideo_results, wildberries_results, technopark_results = await asyncio.gather(
        fake_search(product_name),
        search_sp_computer(product_name),
        fake_search(product_name),
        fake_search(product_name),
        search_technopark(product_name)
    )

    # Формирование ответа
    response = f"*Результаты поиска для '{product_name}':*\n\n"

    for platform, results in [
        ("Ozon", ozon_results),
        ("SP-Computer", sp_computer_results),
        ("М.Видео", mvideo_results),
        ("Wildberries", wildberries_results),
        ("Технопарк", technopark_results),
    ]:
        response += f"*{platform}:*\n"
        for result in results:
            if isinstance(result, dict):
                response += f"[{result['name']}]({result['url']}): {result['price']} RUB\n"
            else:
                response += result + "\n"
        response += "\n"

    # Добавление кнопки "Добавить в избранное"
    markup = types.InlineKeyboardMarkup()
    callback_data = generate_callback_data(product_name)
    callback_data_map[callback_data] = product_name
    markup.add(types.InlineKeyboardButton(text="Добавить в избранное", callback_data=callback_data))

    await bot.send_message(product_name.chat.id, response, parse_mode='Markdown', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
async def callback_delete_favorite(call):
    await bot.answer_callback_query(call.id)
    product_name = call.data[len("delete_"):]  # Извлечение названия товара

    # Удаляем товар из избранного
    if call.message.chat.id in user_favorites:
        try:
            user_favorites[call.message.chat.id].remove(product_name)
            await bot.send_message(call.message.chat.id, f"Товар '{product_name}' удален из избранного.")
        except ValueError:
            await bot.send_message(call.message.chat.id, "Товар не найден в избранном.")
    else:
        await bot.send_message(call.message.chat.id, "У вас пока нет избранных товаров.")



@bot.callback_query_handler(func=lambda call: call.data in callback_data_map)
async def callback_add_to_favorites(call):
    await bot.answer_callback_query(call.id)
    product_name = callback_data_map[call.data]
    add_to_favorites(call.message.chat.id, product_name)
    await bot.send_message(call.message.chat.id, f"Товар '{product_name}' добавлен в избранное.")

# Запуск асинхронного бота
asyncio.run(bot.polling(non_stop=True))