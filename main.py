import telebot
from telebot import types
bot = telebot.TeleBot('7280173517:AAFEJU9dKxsKQW-BCfdFnISWftGkxlrSWME')
@bot.message_handler(commands = ['start'])
def start (message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    bth1 = types.KeyboardButton('Найти товар')
    markup.row(bth1)
    bth2 = types.KeyboardButton('Избранное')
    bth3 = types.KeyboardButton('Помощь')
    markup.row(bth2, bth3)
    bot.send_message(message.chat.id,f"Привет, {message.from_user.first_name}! Я бот, который поможет тебе совершить выгодную покупку, нажми «найти товар», чтобы я смог тебе помочь", reply_markup=markup)
    bot.register_next_step_handler(message, on_click)

def on_click(message):
    if message.text == 'Найти товар':
        bot.send_message(message.chat.id, 'Введите конкретное название товара')
    elif message.text == 'Избранное':
        bot.send_message(message.chat.id, 'Ваши избранные товары:')
    elif message.text == 'Помощь':
        bot.send_message(message.chat.id, 'Помощь')

@bot.message_handler(commands = ['site'])
def main (message):
    bot.send_message(message.chat.id, "Help info")

@bot.message_handler(commands = ['start', 'main', 'hello'])
def main (message):
    bot.send_message(message.chat.id, f"Привет, {message.from_user.first_name}! Я бот, который поможет тебе совершить выгодную покупку, нажми «найти товар», чтобы я смог тебе помочь")

@bot.message_handler(commands = ['help'])
def main (message):
    bot.send_message(message.chat.id, "Help info")

@bot.message_handler()
def main (message):
    if message.text.lower() == 'привет':
        bot.send_message(message.chat.id, f"Привет, {message.from_user.first_name}!")
bot.polling(non_stop=True)
''' бу
'''