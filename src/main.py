#!/usr/bin/env python3

from telebot import TeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, InputMediaPhoto
from webScraper.scraper import *
from data_analyzer.data_analyzer import *
from repository.players_repository import *
import os
import math
from dotenv import load_dotenv

#! Initialization of deps
load_dotenv()
ITEMS_PER_PAGE = 5
user_data = {}
BOT_TOKEN = os.environ.get('TG_BOT_API_KEY')

bot = TeleBot(BOT_TOKEN, parse_mode='HTML')
repository = PlayerRepository()
analyzer = DataAnalyzer()
scraper = Scraper('https://fbref.com/en/comps/9/stats/Premier-League-Stats', repository)


def generate_markup(player_data, page, total_pages):
    keyboard = InlineKeyboardMarkup()

    start_index = page * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE

    for player in player_data[start_index:end_index]:
        player_button = InlineKeyboardButton(unidecode(player[0]), callback_data=f"player_{player[1]}")
        # player_button = InlineKeyboardButton(unidecode(player[0]), callback_data=f"player_{'123123'}")
        keyboard.add(player_button)

    last_row = []

    last_row.append(InlineKeyboardButton(text="Back", callback_data="back"))

    last_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages+1}", callback_data="current_page"))

    last_row.append(InlineKeyboardButton(text="Next", callback_data="next"))

    keyboard.row(*last_row)

    return keyboard

def generate_markup_page_list(total_pages):
    counter = 0
    current_row = []
    keyboard = InlineKeyboardMarkup()
    for page_num in range(0, total_pages+1):
        if counter > 4:
            counter = 0
            keyboard.row(*current_row)
            current_row = []
        counter += 1
        current_row.append(InlineKeyboardButton(text=f"{page_num+1}", callback_data=f"goto_{page_num}"))
    keyboard.row(*current_row)
    return keyboard


@bot.message_handler(commands=['start'])
def start_hanlder(message: Message):
    with open('../resources/images/Start.png', 'rb') as image:
        return bot.send_photo(message.from_user.id, image)


@bot.message_handler(content_types=['text'])
def text_handler(message: Message):
    player_data = analyzer.search_players(message.text)
    user_data[message.from_user.id] = player_data
    total_pages = math.floor(len(user_data[message.from_user.id])/ITEMS_PER_PAGE)
    if len(player_data) == 0:
        message_text = "There is not such football players"
        return bot.send_message(message.from_user.id, message_text)
    else:
        markup = generate_markup(player_data, 0, total_pages)
        with open('../resources/images/Search Results.png', 'rb') as image:
            return bot.send_photo(message.chat.id, image, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query_handler(call):
    data = call.data
    items = user_data[call.from_user.id]
    total_pages = math.floor(len(items)/ITEMS_PER_PAGE)
    current_page = int(call.json['message']['reply_markup']['inline_keyboard'][-1][1]['text'].split('/')[0])-1
    if data == "back":
        new_page = int(current_page) - 1
        if new_page < 0:
            new_page = total_pages
    elif data == "next":
        new_page = int(current_page) + 1
        if new_page > total_pages:
            new_page = 0
    elif data == "current_page":
        markup = generate_markup_page_list(total_pages)
        with open('../resources/images/Choice of result page.png', 'rb') as image:
            media = InputMediaPhoto(image)
            return bot.edit_message_media(media=media, chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      reply_markup=markup)
    elif data.find('goto') != -1:
        markup = generate_markup(items, int(data.split('_')[1]), total_pages)
        return bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "You selected: " + data)
        return
    markup = generate_markup(items, new_page, total_pages)
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda m: m.data.startswith('player_'))
def player_button_click_hanlder(callback: CallbackQuery):
    
    player_id = int(callback.data.split('_')[-1])
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
    for player in FOOTBALL_PLAYERS:
        if player['id'] == player_id:
            message_text = f"<b><i>{player['name']}</i>\n{player['age']}</b>"
            with open(player['image'], 'rb') as image:
                return bot.send_photo(callback.from_user.id, image, message_text)
    
    return bot.send_message(callback.from_user.id, "Unknow error")

    
if __name__ == "__main__":
    bot.infinity_polling()
