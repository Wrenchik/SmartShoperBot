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

# Инициализация бота
bot = telebot.TeleBot('7280173517:AAFEJU9dKxsKQW-BCfdFnISWftGkxlrSWME')


### Инициализация браузера для Ozon
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


### Функция для скроллинга страницы (Ozon)
def scrolldown(driver, deep):
    for _ in range(deep):
        driver.execute_script('window.scrollBy(0, 500)')
        time.sleep(0.1)


### Парсинг данных с Ozon
def get_product_info(product_url):
    session = curl_requests.Session()
    try:
        raw_data = session.get(f"https://www.ozon.ru/api/composer-api.bx/page/json/v2?url={product_url}")
        json_data = json.loads(raw_data.content.decode())

        full_name = json_data["seo"]["title"]
        description = json.loads(json_data["seo"]["script"][0]["innerHTML"])["description"]
        price = json.loads(json_data["seo"]["script"][0]["innerHTML"])["offers"]["price"]
        image_url = json.loads(json_data["seo"]["script"][0]["innerHTML"])["image"]

        return {
            "name": full_name,
            "description": description,
            "price": price,
            "url": product_url,
            "image": image_url
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



### Функция для поиска на SP-Computer
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
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()

        results = []

        keywords = product_name.split()

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

### Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Найти товар')
    markup.add(btn1)
    bot.send_message(message.chat.id, "Привет! Введите название товара для поиска.", reply_markup=markup)


### Обработчик текста (поиск товаров)
@bot.message_handler(content_types=['text'])
def handle_text(message):
    product_name = message.text.strip()
    bot.send_message(message.chat.id, f"Ищу товар: {product_name}")

    # Получаем результаты с Ozon и SP-Computer
    ozon_results = search_ozon(product_name)
    sp_computer_results = search_sp_computer(product_name)

    # Формируем и отправляем ответ
    response = f"Результаты поиска для '{product_name}':\n\n"

    # Форматируем результаты с Ozon
    response += "Ozon:\n"
    for result in ozon_results:
        if isinstance(result, dict):
            # Форматируем результат как [Название](ссылка)
            response += f"[{result['name']}]({result['url']}): {result['price']} RUB\n"
        else:
            response += result + "\n"

    # Форматируем результаты с SP-Computer
    response += "\nSP-Computer:\n"
    for result in sp_computer_results:
        if isinstance(result, dict):
            # Форматируем результат как [Название](ссылка)
            response += f"[{result['name']}]({result['url']}): {result['price']} RUB\n"
        else:
            response += result + "\n"

    # Проверка длины сообщения и разбиение на части, если нужно
    if len(response) > 4096:
        parts = util.split_string(response, 4096)
        for part in parts:
            bot.send_message(message.chat.id, part, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, response, parse_mode='Markdown')



### Запуск бота
bot.polling(non_stop=True)
