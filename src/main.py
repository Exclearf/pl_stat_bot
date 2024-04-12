#!/usr/bin/env python3

from telebot import TeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from webScraper.scraper import *
from data_analyzer.data_analyzer import *
from repository.players_repository import *
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get('TG_BOT_API_KEY')

#! Initialization of deps
bot = TeleBot(BOT_TOKEN, parse_mode='HTML')

repository = PlayerRepository()

analyzer = DataAnalyzer()
results = analyzer.search_players('Odegaard')


scraper = Scraper('https://fbref.com/en/comps/9/stats/Premier-League-Stats', repository)
scraper.generate_player_data("https://fbref.com/en/players/907a5d7c/Adam-Smith")





FOOTBALL_PLAYERS = [
    {
        "id": 1,
        "name": "John Doe",
        "age": 24,
        "image": "./src/*",
    },
    {
        "id": 2,
        "name": "Carlos Ruiz",
        "age": 28,
        "image": "./src/*",
    },
    {
        "id": 3,
        "name": "Marco Bianchi",
        "age": 30,
        "image": "./src/*",
    }
]


@bot.message_handler(commands=['start'])
def start_hanlder(message: Message):
    message_text = "⚽️ Input name:"

    return bot.send_message(message.from_user.id, message_text)


@bot.message_handler(content_types=['text'])
def text_handler(message: Message):

    search_result = []

    for player in FOOTBALL_PLAYERS:
        if message.text in player['name']:
            search_result.append(player)

    if len(search_result) == 0:
        message_text = "There is not such football players"
        return bot.send_message(message.from_user.id, message_text)
    else:
        message_text = "Here is the result of the search:"

        keyboard = InlineKeyboardMarkup(row_width=1)
        for player in search_result:
            player_button = InlineKeyboardButton(player['name'], callback_data=f"player_{player['id']}")
            keyboard.add(player_button)

        return bot.send_message(message.from_user.id, message_text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda m: m.data.startswith('player_'))
def player_button_click_hanlder(callback: CallbackQuery):
    
    player_id = int(callback.data.split('_')[-1])

    for player in FOOTBALL_PLAYERS:
        if player['id'] == player_id:
            message_text = f"<b><i>{player['name']}</i>\n{player['age']}</b>"
            with open(player['image'], 'rb') as image:
                return bot.send_photo(callback.from_user.id, image, message_text)
    
    return bot.send_message(callback.from_user.id, "Unknow error")

    
#if __name__ == "__main__":
    #bot.infinity_polling()
