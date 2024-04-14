#!/usr/bin/env python3

from telebot import TeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, InputMediaPhoto
from webScraper.scraper import *
from webScraper.webDriverPool import *
from data_analyzer.data_analyzer import *
from repository.players_repository import *
import os
import math
from dotenv import load_dotenv
from datetime import datetime, timedelta
import time


# ! Initialization of deps
load_dotenv()
ITEMS_PER_SEARCH_PAGE = 5
ITEMS_PER_SEASON_PAGE = 3
TIMEOUT_FOR_DELETE_ON_FAILED_SEARCH = 100
user_data = {}
BOT_TOKEN = os.environ.get('TG_BOT_API_KEY')

bot = TeleBot(BOT_TOKEN, parse_mode='HTML')
repository = PlayerRepository()
analyzer = DataAnalyzer()
driver_pool = WebDriverPool(size=1)

########################################################################################################################
#                                                 TG API SECTION                                                       #
########################################################################################################################
@bot.message_handler(commands=['start'])
def start_handler(message: Message):
    with open('../resources/images/Start.png', 'rb') as image:
        return bot.send_photo(message.from_user.id, image)


@bot.message_handler(content_types=['text'])
def text_handler(message: Message):
    player_data = analyzer.search_players(message.text)
    if len(player_data) == 0:
        with open('../resources/images/No footballer found.png', 'rb') as image:
            return bot.send_photo(chat_id=message.chat.id, photo=image)

    # Initialize data caching
    user_data[message.from_user.id] = dict()
    user_data[message.from_user.id]['data'] = player_data
    user_data[message.from_user.id]['last_search'] = 0
    user_data[message.from_user.id]['last_season'] = 0
    user_data[message.from_user.id]['last_caption'] = ''

    player_data_length = len(player_data)
    total_pages = math.floor(player_data_length / ITEMS_PER_SEARCH_PAGE)
    if player_data_length % ITEMS_PER_SEARCH_PAGE == 0:
        total_pages -= 1

    markup = generate_markup(player_data, 0, total_pages)
    with open('../resources/images/Search Results.png', 'rb') as image:
        return bot.send_photo(message.chat.id, image, reply_markup=markup)


@bot.callback_query_handler(
    func=lambda call: any(
        item in call.data for item in ['_goto_player_search_list', "back_player_list", "next_player_list",
                                       "current_page_player_list"]))
def callback_query_handler(call):
    data = call.data
    items = user_data[call.from_user.id]['data']
    total_pages = math.floor(len(items) / ITEMS_PER_SEARCH_PAGE)
    try:
        current_page = int(call.json['message']['reply_markup']['inline_keyboard'][-1][1]['text'].split('/')[0]) - 1
    except:
        current_page = 0
    if data == "back_player_list":
        new_page = int(current_page) - 1
        if new_page < 0:
            new_page = total_pages
    elif data == "next_player_list":
        new_page = int(current_page) + 1
        if new_page > total_pages:
            new_page = 0
    elif data == "current_page_player_list":
        markup = generate_markup_search_page_list(total_pages, call_id=call.from_user.id)
        with open('../resources/images/Choice of result page.png', 'rb') as image:
            media = InputMediaPhoto(image)
            return bot.edit_message_media(media=media, chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=markup)
    elif '_goto_player_search_list' in data:
        markup = generate_markup(items, int(data.split('_')[0]), total_pages)
        user_data[call.from_user.id]['last_search'] = int(data.split('_')[0])
        with open('../resources/images/Search Results.png', 'rb') as image:
            media = InputMediaPhoto(image)
            return bot.edit_message_media(media=media, chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "You selected: " + data)
        return
    user_data[call.from_user.id]['last_search'] = new_page
    markup = generate_markup(items, new_page, total_pages)
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)


def scrape(player_link, chat_id, message_id):
    try:
        with driver_pool.get_driver(chat_id) as driver:
            with open('../resources/images/Browser found.png', 'rb') as image:
                bot.edit_message_media(chat_id=chat_id, message_id=message_id,
                                       media=InputMediaPhoto(image))
            Scraper(repository, driver).generate_player_data(player_link)
    except Exception as e:
        raise e
    return

def prepare_for_scraping(player_link, chat_id, message_id):
    with open('../resources/images/Waiting for a ready browser.png', 'rb') as image:
        bot.edit_message_media(chat_id=chat_id, message_id=message_id,
                               media=InputMediaPhoto(image))
    try:
        scrape(player_link=player_link, chat_id=chat_id, message_id=message_id)
        return True
    except TimeoutError as e:
        with open('../resources/images/Failed to acquire a browser.png', 'rb') as image:
            bot.edit_message_media(chat_id=chat_id, message_id=message_id,
                                   media=InputMediaPhoto(image))
        return False
    except RuntimeError as e:
        with open("../resources/images/Who's that.png", 'rb') as image:
            bot.edit_message_media(chat_id=chat_id, message_id=message_id,
                                   media=InputMediaPhoto(image))
        return False

@bot.callback_query_handler(func=lambda call: '_playerUrl' in call.data)
def player_button_click_handler(call: CallbackQuery):
    player_id = call.data.split('_playerUrl')[0]
    player_link = "https://fbref.com/en/players/" + player_id
    player_name = player_id.split('/')[-1].replace('-', ' ')
    player_data_filepath = '../resources/data/parsed_players/' + player_id.split('/')[-1] + '/'

    if os.path.exists(player_data_filepath):
        with open(player_data_filepath + player_id.split('/')[-1] + '.json', 'rb') as file:
            if datetime.now() - datetime.fromisoformat(json.load(file)['creationDate']) > timedelta(minutes=2):
                success = prepare_for_scraping(player_link=player_link, chat_id=call.message.chat.id, message_id=call.message.message_id)
                if not success:
                    return
    else:
        success = prepare_for_scraping(player_link=player_link, chat_id=call.message.chat.id,
                                       message_id=call.message.message_id)
        if not success:
            return
    data = analyzer.get_player_data(player_name)
    basic_data = analyzer.player_basic_data(data)
    seasons = analyzer.player_years(data)
    total_pages = math.floor(len(seasons) / ITEMS_PER_SEASON_PAGE)
    caption = ""
    caption += basic_data['fullName'] and f"<b>General information:</b>\n"
    caption += f"\n"
    caption += basic_data['fullName'] and f"<b>Full Name:</b> {basic_data['fullName']}\n"
    caption += basic_data['age'] and f"<b>Age:</b> {basic_data['age']}\n"
    caption += basic_data['nationality'] and f"<b>Nation:</b> {basic_data['nationality']}\n"
    caption += basic_data['position'] and f"<b>Position:</b> {basic_data['position']}\n"
    caption += basic_data['footed'] and f"<b>Footed:</b> {basic_data['footed']}\n"
    caption += basic_data['shortDescription'] and f"<b>About:</b> {basic_data['shortDescription']}\n\n"

    is_stats_available = basic_data['squad'] and basic_data['leagueRank'] and basic_data['goals'] and basic_data['assists']
    caption += is_stats_available and f"<b>Season 2023-2024</b>\n"
    caption += is_stats_available and f"\n"
    caption += basic_data['squad'] and f"<b>Squad:</b> {basic_data['squad']}\n"
    caption += basic_data['leagueRank'] and f"<b>Rank:</b> {basic_data['leagueRank']}\n"
    caption += basic_data['goals'] and f"<b>Goals:</b> {basic_data['goals']}\n"
    caption += basic_data['assists'] and f"<b>Assists:</b> {basic_data['assists']}\n"

    markup = generate_markup_seasons(player_name=player_id.split('/')[-1], player_seasons=seasons, page=0,
                                     total_pages=total_pages, call_id=call.from_user.id)
    image = None
    image_path = analyzer.player_path(player_name)
    if os.path.exists(image_path + '_wiki.jpeg'):
        image_path = image_path + '_wiki.jpeg'
        image = open(image_path, 'rb')
    elif os.path.exists(image_path + '.jpeg'):
        image_path = image_path + '.jpeg'
        image = open(image_path, 'rb')
    else:
        image_path = '../resources/images/No image found.png'
        image = open(image_path, 'rb')

    bot.edit_message_media(chat_id=call.message.chat.id, message_id=call.message.message_id,
                           media=InputMediaPhoto(image))
    if caption:
        bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=caption,
                                 reply_markup=markup)
    user_data[call.from_user.id]['last_caption'] = caption
    user_data[call.from_user.id]['last_image_path'] = image_path
    image.close()


@bot.callback_query_handler(func=lambda call: any(item in call.data for item in
                                                  ['_seasons', "_back_player_seasons", "_current_page_player_seasons",
                                                   "_next_player_seasons", '_goto_player_season_page']))
def callback_query_handler(call):
    data = call.data
    player_name = call.data.split('_')[0]
    seasons = analyzer.player_years(analyzer.get_player_data(player_name))
    total_pages = math.floor(len(seasons) / ITEMS_PER_SEASON_PAGE)
    if (len(seasons) % ITEMS_PER_SEASON_PAGE) == 0:
        total_pages -= 1
    try:
        current_page = int(call.json['message']['reply_markup']['inline_keyboard'][-2][1]['text'].split('/')[0]) - 1
    # noinspection PyBroadException
    except:
        return
    if "_back_player_seasons" in data:
        new_page = int(current_page) - 1
        if new_page < 0:
            new_page = total_pages
    elif "_next_player_seasons" in data:
        new_page = int(current_page) + 1
        if new_page > total_pages:
            new_page = 0
    elif "_current_page_player_seasons" in data:
        markup = generate_markup_seasons_page_list(total_pages=total_pages, player_name=player_name,
                                                   call_id=call.from_user.id)
        with open('../resources/images/Choice of result page.png', 'rb') as image:
            media = InputMediaPhoto(image)
            return bot.edit_message_media(media=media, chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=markup)
    elif '_goto_player_season_page' in data:
        markup = generate_markup_seasons(player_name=player_name, player_seasons=seasons, page=int(data.split('_')[1]),
                                         total_pages=total_pages, call_id=call.from_user.id)
        user_data[call.from_user.id]['last_season'] = int(data.split('_')[1])
        with open(user_data[call.from_user.id]['last_image_path'], 'rb') as image:
            media = InputMediaPhoto(image)
            bot.edit_message_media(media=media, chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.edit_message_caption(caption=user_data[call.from_user.id]['last_caption'], chat_id=call.message.chat.id,
                                     message_id=call.message.message_id, reply_markup=markup)
            return
    else:
        bot.answer_callback_query(call.id, "You selected: " + data)
        return
    user_data[call.from_user.id]['last_season'] = new_page
    markup = generate_markup_seasons(player_seasons=seasons, page=new_page, total_pages=total_pages,
                                     call_id=call.from_user.id, player_name=player_name)
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)


########################################################################################################################
#                                            HELPER METHODS FOR TG API                                                 #
########################################################################################################################
def generate_markup_seasons(player_name, player_seasons, page, total_pages, call_id):
    keyboard = InlineKeyboardMarkup()

    start_index = page * ITEMS_PER_SEASON_PAGE
    end_index = start_index + ITEMS_PER_SEASON_PAGE

    for season in player_seasons[::-1][start_index:end_index]:
        season_button = InlineKeyboardButton(unidecode(season).capitalize(),
                                             callback_data=f"{player_name}_{season}_seasons")
        keyboard.add(season_button)

    if total_pages > 1:
        row = [InlineKeyboardButton(text="◄", callback_data=f"{player_name}_back_player_seasons"),
               InlineKeyboardButton(text=f"{page + 1}/{total_pages + 1}",
                                    callback_data=f"{player_name}_current_page_player_seasons"),
               InlineKeyboardButton(text="►", callback_data=f"{player_name}_next_player_seasons")]

        keyboard.row(*row)

    keyboard.row(InlineKeyboardButton(text="Back to the results", callback_data=f"{user_data[call_id]['last_search']}\
    _goto_player_search_list"))

    return keyboard


def generate_markup(player_data, page, total_pages):
    keyboard = InlineKeyboardMarkup()

    start_index = page * ITEMS_PER_SEARCH_PAGE
    end_index = start_index + ITEMS_PER_SEARCH_PAGE

    for player in player_data[start_index:end_index]:
        player_button = InlineKeyboardButton(unidecode(player[0]), callback_data=f"{player[1]}_playerUrl")
        keyboard.add(player_button)

    if total_pages > 0:
        last_row = [InlineKeyboardButton(text="◄", callback_data="back_player_list"),
                    InlineKeyboardButton(text=f"{page + 1}/{total_pages + 1}", callback_data=f"current_page_player_list"),
                    InlineKeyboardButton(text="►", callback_data="next_player_list")]

        keyboard.row(*last_row)

    return keyboard


def generate_markup_search_page_list(total_pages, call_id):
    counter = 0
    current_row = []
    keyboard = InlineKeyboardMarkup()
    for page_num in range(0, total_pages + 1):
        if counter > 4:
            counter = 0
            keyboard.row(*current_row)
            current_row = []
        counter += 1
        current_row.append(
            InlineKeyboardButton(text=f"{page_num + 1}", callback_data=f"{page_num}_goto_player_search_list"))
    keyboard.row(*current_row)

    keyboard.add(InlineKeyboardButton(text="Go back to result",
                                      callback_data=f"{user_data[call_id]['last_search']}_goto_player_search_list"))
    return keyboard


def generate_markup_seasons_page_list(total_pages, call_id, player_name):
    counter = 0
    current_row = []
    keyboard = InlineKeyboardMarkup()

    for page_num in range(0, total_pages + 1):
        if counter > 4:
            counter = 0
            keyboard.row(*current_row)
            current_row = []
        counter += 1
        current_row.append(InlineKeyboardButton(text=f"{page_num + 1}",
                                                callback_data=f"{player_name}_{page_num}_goto_player_season_page"))
    keyboard.row(*current_row)

    keyboard.add(InlineKeyboardButton(text="Go back to result",
                                      callback_data=f"{player_name}_{user_data[call_id]['last_season']}_goto_player_season_page"))
    return keyboard


########################################################################################################################
#                                               START THE MAIN LOOP                                                    #
########################################################################################################################

if __name__ == "__main__":
    with driver_pool.get_driver() as driver:
        Scraper(repository, driver).prepare_dataset()
    bot.infinity_polling()
