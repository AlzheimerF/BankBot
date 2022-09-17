from bs4 import BeautifulSoup as BS
import os.path
import os
import time
from time import sleep
import threading
import pytz
from threading import Thread
import datetime
import schedule
import json
import requests
from currencybotconfig import TOKEN, ADMIN_USER_ID
import telebot
from telebot.types import (
InlineKeyboardMarkup,
InlineKeyboardButton)

bot = telebot.TeleBot(TOKEN)

url = "https://www.akchabar.kg/ru/exchange-rates/"
html = requests.get(url).text


@bot.message_handler(commands=["start"])
def welcome(message):
    with open("users_register.txt", "a") as ur:
        ur.close()
    users = set()
    with open("users_register.txt", "r") as ur:
        for line in ur:
            users.add(line.strip())
    if not str(message.chat.id) in users:
        with open("users_register.txt", "a") as ur:
            ur.write(str(message.chat.id) + "\n")
    welcome_text = f"Добро пожаловать! Это бот, который предоставляет информацию о текущих курсах валют в Бишкеке. " \
                   f"Пожалуйста, выберите валюту, чтобы узнать курс."
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup_adder(), parse_mode="HTML")


def markup_adder():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    dollar = InlineKeyboardButton("Доллар США", callback_data="USD")
    euro = InlineKeyboardButton("Евро", callback_data="EUR")
    ruble = InlineKeyboardButton("Российский рубль", callback_data="RUB")
    tenge = InlineKeyboardButton("Казахский тенге", callback_data="KZT")
    markup.add(dollar, euro, ruble, tenge)
    return markup


@bot.callback_query_handler(func=lambda call: call.data in ["USD", "EUR", "RUB", "KZT"])
def callback_rates(call):
    message = call.message
    global date_
    date_ = datetime.datetime.fromtimestamp(message.date, tz=pytz.timezone('UTC')).\
        astimezone(pytz.timezone('Asia/Bishkek')).strftime("%Y-%m-%d %H:%M")
    global date_file
    date_file = datetime.datetime.fromtimestamp(message.date, tz=pytz.timezone('UTC')).\
        astimezone(pytz.timezone('Asia/Bishkek')).strftime("%Y_%m_%d_%H")
    text_message = show_rates(call.data)
    bot.send_message(message.chat.id, text_message, reply_markup=markup_adder(), parse_mode="HTML")


def show_rates(currency):
    currency_name = {"USD": "доллара", "EUR": "евро", "RUB": "рубля", "KZT": "тенге"}
    if not os.path.exists(f"x_rates{date_file}.json"):
        parser(html)
    if os.path.exists(f"x_rates{date_file}.json"):
        ccy_indices = {"USD": [0, 1], "EUR": [2, 3], "RUB": [4, 5], "KZT": [6, 7]}
        with open(f"x_rates{date_file}.json", "r", encoding="utf-8") as json_file:
            x_rates = json.load(json_file)
            with open("temp.txt", "w", encoding="utf-8") as temp:
                temp.write(f"Курс <b>{currency_name.get(currency)}</b> в коммерческих банках Бишкека и "
                           f"обменных бюро Моссовета на <b>{date_}</b>:\n\n")
                for key, value in x_rates.items():
                    temp.write(f"<b>{key}</b>:\nПокупка: <b>{value[ccy_indices.get(currency)[0]]}</b>  -  "
                               f"Продажа: <b>{value[ccy_indices.get(currency)[1]]}</b>\n")
    with open("temp.txt", "r", encoding="utf-8") as file:
        x_rate_text = file.read()
        return x_rate_text


def parser(html):
    x_rates = {}
    soup = BS(html, 'html.parser')
    table = soup.find('table', attrs={'id': 'rates_table'})
    table_body = table.find('tbody')
    rows = table_body.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        cols = [ele.text.strip() for ele in cols]
        x_rates.update({cols[0]: cols[1:]})
        with open(f'x_rates{date_file}.json', 'w', encoding="utf-8") as xf:
            json.dump(x_rates, xf, ensure_ascii=False)


def daily_distribution():
    global date_file
    date_file = datetime.datetime.now(tz=pytz.timezone('UTC')).\
        astimezone(pytz.timezone('Asia/Bishkek')).strftime("%Y_%m_%d_%H")
    global date_
    date_ = datetime.datetime.now(tz=pytz.timezone('UTC')).\
        astimezone(pytz.timezone('Asia/Bishkek')).strftime("%Y-%m-%d %H:%M")
    users = set()
    with open("users_register.txt", "r") as ur:
        for line in ur:
            users.add(line.strip())
        for user in users:
            for item in ["USD", "EUR", "RUB", "KZT"]:
                bot.send_message(user, show_rates(item), reply_markup=None, parse_mode="HTML")
            distribution_text = f"Это была автоматическая рассылка бота о курсах валют на <b>{date_}</b>. " \
                                f"Вы будете получать данное уведомление ежедневно в <b>12:00</b>."
            bot.send_message(user, distribution_text, reply_markup=markup_adder(), parse_mode="HTML")


def my_scheduler():
    schedule.every().day.at("06:00").do(daily_distribution)
    while True:
        schedule.run_pending()
        time.sleep(1)


thread = Thread(target=my_scheduler, daemon=True)
thread.start()
bot.infinity_polling()