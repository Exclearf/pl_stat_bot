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
import atexit
import time
import configparser 


# ! Initialization of deps

load_dotenv()

ITEMS_PER_SEARCH_PAGE = 5
ITEMS_PER_SEASON_PAGE = 3
BOT_TOKEN = os.environ.get('TG_BOT_API_KEY')

user_data = {}
bot = TeleBot(BOT_TOKEN, parse_mode='HTML')
repository = PlayerRepository()
analyzer = DataAnalyzer()
driver_pool = None

########################################################################################################################
#                                                 TG API SECTION                                                       #
########################################################################################################################
@bot.message_handler(commands=['start'])
def start_handler(message: Message):
    bot.send_photo(message.from_user.id, photo=user_data['images']['Start.png'])
    return


@bot.message_handler(content_types=['text'])
def text_handler(message: Message):
    player_data = analyzer.search_players(message.text)
    if len(player_data) == 0:
        with open('../resources/images/No footballer found.png', 'rb') as image:
            return bot.send_photo(chat_id=message.chat.id, photo=user_data['images']['No footballer found.png'])

    # Initialize data caching
    try:
        user_data[str(message.from_user.id)]
    except:
        user_data[str(message.from_user.id)] = dict()
    try:
        user_data[str(message.from_user.id)]['isParsing']
    except:
        user_data[str(message.from_user.id)]['isParsing'] = None
    next_message_id = message.message_id + 1
    try:
        user_data[str(message.from_user.id)][str(next_message_id)]
    except:
        user_data[str(message.from_user.id)][str(next_message_id)] = dict()
    user_data[str(message.from_user.id)][str(next_message_id)]['data'] = player_data
    user_data[str(message.from_user.id)][str(next_message_id)]['last_caption'] = ''
    user_data[str(message.from_user.id)][str(next_message_id)]['last_search'] = 0

    player_data_length = len(player_data)
    total_pages = math.ceil(player_data_length / ITEMS_PER_SEARCH_PAGE) - 1

    markup = generate_markup(player_data, 0, total_pages)
    bot.send_photo(chat_id=message.chat.id, photo=user_data['images']['Search Results.png'], reply_markup=markup)


@bot.callback_query_handler(
    func=lambda call: any(
        item in call.data for item in ['_goto_player_search_list', "back_player_list", "next_player_list",
                                       "current_page_player_list"]))
def callback_query_handler(call):
    data = call.data
    items = user_data[str(call.from_user.id)][str(call.message.message_id)]['data']
    total_pages = math.ceil(len(items) / ITEMS_PER_SEARCH_PAGE) - 1
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
        markup = generate_markup_search_page_list(total_pages, call_id=call.from_user.id, message_id=call.message.message_id)
        return bot.edit_message_media(media=InputMediaPhoto(user_data['images']['Choice of result page.png']), chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=markup)
    elif '_goto_player_search_list' in data:
        markup = generate_markup(items, int(data.split('_')[0]), total_pages)
        user_data[str(call.from_user.id)][str(call.message.message_id)]['last_search'] = int(data.split('_')[0])
        return bot.edit_message_media(media=InputMediaPhoto(user_data['images']['Search Results.png']), chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=markup)
    user_data[str(call.from_user.id)][str(call.message.message_id)]['last_search'] = new_page
    markup = generate_markup(items, new_page, total_pages)
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)


def scrape(player_link, chat_id, message_id):
    try:
        with driver_pool.get_driver(chat_id) as driver:
            bot.edit_message_media(chat_id=chat_id, message_id=message_id,
                                       media=InputMediaPhoto(user_data['images']['Browser found.png']))
            Scraper(repository, driver).generate_player_data(player_link)
    except Exception as e:
        raise e
    return


def prepare_for_scraping(player_link, chat_id, message_id):
    bot.edit_message_media(chat_id=chat_id, message_id=message_id,
                               media=InputMediaPhoto(user_data['images']['Waiting for a ready browser.png']))
    try:
        scrape(player_link=player_link, chat_id=chat_id, message_id=message_id)
        return True
    except TimeoutError as e:
        bot.edit_message_media(chat_id=chat_id, message_id=message_id,
                                   media=InputMediaPhoto(user_data['images']['Failed to acquire a browser.png']))
        return False
    except RuntimeError as e:
        bot.edit_message_media(chat_id=chat_id, message_id=message_id,
                                   media=InputMediaPhoto(user_data['images']["Who's that.png"]))
        return False

def concurrent_error_handler(call: CallbackQuery, ):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="Back to the results", callback_data=f"{user_data[str(call.from_user.id)][str(call.message.message_id)]['last_search']}_goto_player_search_list"))
    bot.edit_message_media(chat_id=call.message.chat.id, message_id=call.message.message_id,
                           media=InputMediaPhoto(user_data['images']['Wait for previous.png']), reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: '_playerUrl' in call.data)
def player_button_click_handler(call: CallbackQuery):
    player_id = call.data.split('_playerUrl')[0]
    player_link = "https://fbref.com/en/players/" + player_id
    player_name = player_id.split('/')[-1].replace('-', ' ')
    player_data_filepath = '../resources/data/parsed_players/' + player_id.split('/')[-1] + '/'

    if os.path.exists(player_data_filepath):
        with open(player_data_filepath + player_id.split('/')[-1] + '.json', 'rb') as file:
            if datetime.now() - datetime.fromisoformat(json.load(file)['creationDate']) > timedelta(minutes=60):
                if user_data[str(call.from_user.id)]['isParsing'] is False or user_data[str(call.from_user.id)]['isParsing'] is None:
                    user_data[str(call.from_user.id)]['isParsing'] = True
                else:
                    concurrent_error_handler(call)
                    return
                success = prepare_for_scraping(player_link=player_link, chat_id=call.message.chat.id, message_id=call.message.message_id)
                user_data[str(call.from_user.id)]['isParsing'] = False
                if not success:
                    return
    else:
        if user_data[str(call.from_user.id)]['isParsing'] is False or user_data[str(call.from_user.id)]['isParsing'] is None:
            user_data[str(call.from_user.id)]['isParsing'] = True
        else:
            concurrent_error_handler(call)
            return
        success = prepare_for_scraping(player_link=player_link, chat_id=call.message.chat.id,
                                       message_id=call.message.message_id)
        user_data[str(call.from_user.id)]['isParsing'] = False
        if not success:
            return

    data = analyzer.get_player_data(player_id.split('/')[-1])
    basic_data = analyzer.player_basic_data(player_id.split('/')[-1])
    seasons = analyzer.player_years(data)
    total_pages = math.ceil(len(seasons) / ITEMS_PER_SEASON_PAGE) - 1
    caption = ""
    caption += basic_data['fullName'] and f"<b>General information:</b>\n"
    caption += f"\n"
    caption += basic_data['fullName'] and f"<b>Full Name:</b> {basic_data['fullName']}\n"
    caption += basic_data['age'] and f"<b>Age:</b> {basic_data['age']}\n"
    caption += basic_data.get('club', basic_data['squad']) and f"<b>Club:</b> {basic_data.get('club', basic_data['squad'])}\n"
    caption += basic_data['nationality'] and f"<b>Nation:</b> {basic_data['nationality']}\n"
    caption += basic_data['position'] and f"<b>Position:</b> {basic_data['position']}\n"
    caption += basic_data['footed'] and f"<b>Footed:</b> {basic_data['footed']}\n"
    caption += basic_data['shortDescription'] and f"<b>About:</b> {basic_data['shortDescription']}\n\n"
    if analyzer.isGK(player_name):
        is_stats_available = basic_data['squad'] and basic_data['matchesPlayed'] and basic_data['competition'] and basic_data['leagueRank'] and basic_data['cleanSheets'] and basic_data[
            'goalsAgainst']
    else:
        is_stats_available = basic_data['squad'] and basic_data['matchesPlayed'] and basic_data['competition'] and basic_data['leagueRank'] and basic_data['goals'] and basic_data[
            'assists']
    caption += is_stats_available and f"<b>Season 2023-2024</b>\n"
    caption += is_stats_available and f"\n"
    caption += basic_data['squad'] and f"<b>Squad:</b> {basic_data['squad']}\n"
    caption += basic_data['leagueRank'] and f"<b>Rank:</b> {basic_data['leagueRank']}\n"
    caption += basic_data['matchesPlayed'] and f'<b>Matches Played:</b> {basic_data["matchesPlayed"]}\n'
    caption += basic_data['competition'] and f'<b>Competition:</b> {basic_data["competition"]}\n'
    if analyzer.isGK(player_name):
        caption += basic_data['cleanSheets'] and f"<b>Clean Sheets:</b> {basic_data['cleanSheets']}\n"
        caption += basic_data['goalsAgainst'] and f"<b>Goals Against:</b> {basic_data['goalsAgainst']}\n"
    else:
        caption += basic_data['goals'] and f"<b>Goals:</b> {basic_data['goals']}\n"
        caption += basic_data['assists'] and f"<b>Assists:</b> {basic_data['assists']}\n"

    season = 0
    try:
        season = user_data[str(call.from_user.id)][str(call.message.message_id)][player_id.split('/')[-1]]['last_season']
    except:
        pass
    try:
        user_data[str(call.from_user.id)][str(call.message.message_id)][player_id.split('/')[-1]]
    except:
        user_data[str(call.from_user.id)][str(call.message.message_id)][player_id.split('/')[-1]] = dict()
    user_data[str(call.from_user.id)][str(call.message.message_id)][player_id.split('/')[-1]]['last_season'] = season
    markup = generate_markup_seasons(player_name=player_id.split('/')[-1], player_seasons=seasons, page=season,
                                     total_pages=total_pages, call_id=call.from_user.id, message_id=call.message.message_id)
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

    m_response = bot.edit_message_media(chat_id=call.message.chat.id, message_id=call.message.message_id,
                           media=InputMediaPhoto(image))
    if caption:
        bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=caption,
                                 reply_markup=markup)
    user_data[str(call.from_user.id)][str(call.message.message_id)]['last_caption'] = caption
    user_data[str(call.from_user.id)][str(call.message.message_id)]['last_image_path'] = m_response.photo[0].file_id
    image.close()

@bot.callback_query_handler(func=lambda call: '__do_nothing' in call.data)
def do_nothing_handler(call: CallbackQuery):
    return

def getGraphDisplayName(name):
    return "".join(name.replace('_', '/').replace('-', ' '))

@bot.callback_query_handler(func=lambda call: '_statistic-page' in call.data)
def create_stat_data_message(call: CallbackQuery):
    data_parts = call.data.split('_')
    name = data_parts[0]
    season = data_parts[1]
    graph_index = data_parts[2]
    graph_type = data_parts[3]

    graph_list = []

    if graph_index == 'X':
        try:
            graph_index = user_data[str(call.from_user.id)][str(call.message.message_id)][name][graph_type]
        except:
            graph_index = '0'
            user_data[str(call.from_user.id)][str(call.message.message_id)][name][graph_type] = graph_index
    else:
        user_data[str(call.from_user.id)][str(call.message.message_id)][name][graph_type] = graph_index


    match graph_type:
        case 'standard':
            graph_list = ['Goals_Assists', 'Cards']
        case 'passing':
            graph_list = ['Assists', 'Passes']
        case 'shooting':
            graph_list = ['Shots_Distance', 'Shots_Goals']
        case 'bgk':
            graph_list = ['Penalties_Shots', 'Saves']
        case 'agk':
            graph_list = ['Advanced-Data', 'Passes', 'Sweeper-Activities']

    keyboard = InlineKeyboardMarkup()
    image_path = '../resources/images/Error.png'
    match graph_index:
        case '0':
            row = [InlineKeyboardButton(text=f"{getGraphDisplayName(graph_list[0])} \U00002705", callback_data=f'__do_nothing'),
                          InlineKeyboardButton(text=f'{getGraphDisplayName(graph_list[1])}', callback_data=f'{name}_{season}_1_{graph_type}_statistic-page')]

            keyboard.row(*row)
            if graph_type == 'agk':
                keyboard.add(InlineKeyboardButton(text=f'{getGraphDisplayName(graph_list[2])}', callback_data=f'{name}_{season}_2_{graph_type}_statistic-page'))

            image_path = f'../resources/data/parsed_players/{name}/graph/{graph_type}/{graph_list[0]}.png'
        case '1':
            row = [InlineKeyboardButton(text=f'{getGraphDisplayName(graph_list[0])}',
                                               callback_data=f'{name}_{season}_0_{graph_type}_statistic-page'),
                          InlineKeyboardButton(text=f'{getGraphDisplayName(graph_list[1])} \U00002705', callback_data=f'__do_nothing')]

            keyboard.row(*row)
            if graph_type == 'agk':
                keyboard.add(InlineKeyboardButton(text=f'{getGraphDisplayName(graph_list[2])}', callback_data=f'{name}_{season}_2_{graph_type}_statistic-page'))

            image_path = f'../resources/data/parsed_players/{name}/graph/{graph_type}/{graph_list[1]}.png'
        case '2':
            row = [InlineKeyboardButton(text=f"{getGraphDisplayName(graph_list[0])}",
                                        callback_data=f'{name}_{season}_0_{graph_type}_statistic-page'),
                   InlineKeyboardButton(text=f"{getGraphDisplayName(graph_list[1])}", callback_data=f'{name}_{season}_1_{graph_type}_statistic-page')]

            keyboard.row(*row)
            if graph_type == 'agk':
                keyboard.add(
                    InlineKeyboardButton(text=f"{getGraphDisplayName(graph_list[2])}  \U00002705", callback_data=f'__do_nothing'))


            image_path = f'../resources/data/parsed_players/{name}/graph/{graph_type}/{graph_list[2]}.png'


    keyboard.add(InlineKeyboardButton(text='Back', callback_data=f'{name}_{season}_display-seasons'))
    with open(image_path, 'rb') as image:
        bot.edit_message_media(chat_id=call.message.chat.id, message_id=call.message.message_id,
                               media=InputMediaPhoto(image), reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: '_statistics' in call.data)
def player_button_click_handler(call: CallbackQuery):
    data_parts = call.data.split('_')
    player_name = data_parts[0]
    season = data_parts[1]
    graph_type = data_parts[3]

    match(graph_type):
        case 'standard':
            analyzer.player_graph_standard_ga(player_name)
            analyzer.player_graph_standard_cards(player_name)
            create_stat_data_message(call)
        case 'passing':
            analyzer.player_graph_passing_assists(player_name)
            analyzer.player_graph_passing_distance(player_name)
            create_stat_data_message(call)
        case 'shooting':
            analyzer.player_graph_shooting(player_name)
            analyzer.player_graph_shooting_distance(player_name)
            create_stat_data_message(call)
        case 'bgk':
            analyzer.player_graph_bgk_penalties(player_name)
            analyzer.player_graph_bgk_saves(player_name)
            create_stat_data_message(call)
        case 'agk':
            analyzer.player_graph_agk(player_name)
            analyzer.player_graph_agk_sweeper(player_name)
            analyzer.player_graph_agk_passes(player_name)
            create_stat_data_message(call)


@bot.callback_query_handler(func=lambda call: 'display-seasons' in call.data)
def player_button_click_handler(call: CallbackQuery):
    data_parts = call.data.split('_')
    name = data_parts[0]
    season = data_parts[1]
    is_goal_keeper = analyzer.isGK(name)
    text = ''
    keyboard = InlineKeyboardMarkup()
    if season == 'all':
        bot.edit_message_media(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                   media=InputMediaPhoto(user_data['images']['What interests.png']))
        if is_goal_keeper:
            keyboard.add(
                InlineKeyboardButton(text=f"Standard Goalkeeping", callback_data=f"{name}_{season}_X_bgk_statistics"))
            keyboard.add(
                InlineKeyboardButton(text=f"Advanced Goalkeeping", callback_data=f"{name}_{season}_X_agk_statistics"))
        else:
            keyboard.add(
                InlineKeyboardButton(text=f"Standard Statistic", callback_data=f"{name}_{season}_X_standard_statistics"))
            keyboard.add(
                InlineKeyboardButton(text=f"Passing Statistic", callback_data=f"{name}_{season}_X_passing_statistics"))
            keyboard.add(
                InlineKeyboardButton(text=f"Shooting Statistic", callback_data=f"{name}_{season}_X_shooting_statistics"))

    else:
        data = analyzer.player_season_data(name, season)
        text += data and f'<b>{name.split(" ")[0]}`s Season {season}</b>\n'
        if not data['age']:
            bot.edit_message_media(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                   media=InputMediaPhoto(user_data['images']['No season data.png']))
        else:
            text += '\n'
            text += data['age'] and f'<b>Age:</b> {data["age"]}\n'
            text += data['squad'] and f'<b>Squad:</b> {data["squad"]}\n'
            text += data['leagueRank'] and f'<b>League Rank:</b> {data["leagueRank"]}\n'
            text += data['matchesPlayed'] and f'<b>Matches Played:</b> {data["matchesPlayed"]}\n'
            text += data['competition'] and f'<b>Competition:</b> {data["competition"]}\n'
            if analyzer.isGK(name):
                text += data['cleanSheets'] and f"<b>Clean Sheets:</b> {data['cleanSheets']}\n"
                text += data['goalsAgainst'] and f"<b>Goals Against:</b> {data['goalsAgainst']}\n"
            else:
                text += data['goals'] and f"<b>Goals:</b> {data['goals']}\n"
                text += data['assists'] and f"<b>Assists:</b> {data['assists']}\n"
                bot.edit_message_media(media=InputMediaPhoto(user_data['images']['Season result.png']), chat_id=call.message.chat.id, message_id=call.message.message_id)


    keyboard.add(InlineKeyboardButton(text=f"Back to player page", callback_data=f"{name}_display-back_button-seasons"))

    bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: 'display-back_button-seasons' in call.data)
def player_button_click_handler(call: CallbackQuery):
    data_parts = call.data.split('_')
    player_name = data_parts[0]
    data = analyzer.get_player_data(player_name)
    seasons = analyzer.player_years(data)
    total_pages = math.ceil(len(seasons) / ITEMS_PER_SEASON_PAGE) - 1
    try:
        bot.edit_message_media(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                media=InputMediaPhoto(user_data[str(call.from_user.id)][str(call.message.message_id)]['last_image_path']))
    except:
        pass

    try:
        bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                 caption=user_data[str(call.from_user.id)][str(call.message.message_id)]['last_caption'])
    except:
        pass

    page = 0
    try:
        page = user_data[str(call.from_user.id)][str(call.message.message_id)][player_name]['last_season']
    except:
        pass

    markup = generate_markup_seasons(player_name=player_name, player_seasons=seasons, page=page,
                                     total_pages=total_pages, call_id=call.from_user.id, message_id=call.message.message_id)
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: any(item in call.data for item in
                                                  ["_back_player_seasons", "_current_page_player_seasons",
                                                   "_next_player_seasons", '_goto_player_season_page']))
def callback_query_handler(call):
    data = call.data
    player_name = call.data.split('_')[0]
    seasons = analyzer.player_years(analyzer.get_player_data(player_name))
    total_pages = math.ceil(len(seasons) / ITEMS_PER_SEASON_PAGE) - 1
    try:
        current_page = int(call.json['message']['reply_markup']['inline_keyboard'][-2][1]['text'].split('/')[0]) - 1
    except:
        return
    try:
        current_page = user_data[str(call.from_user.id)][str(call.message.message_id)][player_name]['last_season']
    except:
        pass
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
                                                   call_id=call.from_user.id, message_id=call.message.message_id)
        return bot.edit_message_media(media=InputMediaPhoto(user_data['images']['Choice of result page.png']), chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=markup)
    elif '_goto_player_season_page' in data:
        markup = generate_markup_seasons(player_name=player_name, player_seasons=seasons, page=int(data.split('_')[1]),
                                         total_pages=total_pages, call_id=call.from_user.id, message_id=call.message.message_id)
        user_data[str(call.from_user.id)][str(call.message.message_id)][player_name]['last_season'] = int(data.split('_')[1])
        bot.edit_message_media(media=InputMediaPhoto(user_data[str(call.from_user.id)][str(call.message.message_id)]['last_image_path']), chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.edit_message_caption(caption=user_data[str(call.from_user.id)][str(call.message.message_id)]['last_caption'], chat_id=call.message.chat.id,
                                     message_id=call.message.message_id, reply_markup=markup)
        return
    user_data[str(call.from_user.id)][str(call.message.message_id)][player_name]['last_season'] = new_page
    markup = generate_markup_seasons(player_seasons=seasons, page=new_page, total_pages=total_pages,
                                     call_id=call.from_user.id, player_name=player_name, message_id=call.message.message_id)
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

########################################################################################################################
#                                            HELPER METHODS FOR TG API                                                 #
########################################################################################################################
def generate_markup_seasons(player_name, player_seasons, page, total_pages, call_id, message_id):
    keyboard = InlineKeyboardMarkup()

    start_index = page * ITEMS_PER_SEASON_PAGE
    end_index = start_index + ITEMS_PER_SEASON_PAGE

    for season in player_seasons[::-1][start_index:end_index]:
        season_button = InlineKeyboardButton(unidecode(season).capitalize(),
                                             callback_data=f"{player_name}_{season}_display-seasons")
        keyboard.add(season_button)

    if total_pages > 0:
        row = [InlineKeyboardButton(text="◄", callback_data=f"{player_name}_back_player_seasons"),
               InlineKeyboardButton(text=f"{page + 1}/{total_pages + 1}",
                                    callback_data=f"{player_name}_current_page_player_seasons"),
               InlineKeyboardButton(text="►", callback_data=f"{player_name}_next_player_seasons")]

        keyboard.row(*row)

    keyboard.add(InlineKeyboardButton(text="Back to the results", callback_data=f"{user_data[str(call_id)][str(message_id)]['last_search']}\
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


def generate_markup_search_page_list(total_pages, call_id, message_id):
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
                                      callback_data=f"{user_data[str(call_id)][str(message_id)]['last_search']}_goto_player_search_list"))
    return keyboard


def generate_markup_seasons_page_list(total_pages, call_id, player_name, message_id):
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
                                      callback_data=f"{player_name}_{user_data[str(call_id)][str(message_id)][player_name]['last_season']}_goto_player_season_page"))
    return keyboard

def redo_the_images(user_id):
    user_data['images'] = dict()
    for file_path in os.listdir('../resources/images'):
        with open(f'../resources/images/{file_path}', 'rb') as image:
            m = bot.send_photo(user_id, photo=image)
            user_data['images'][file_path] = m.photo[0].file_id
            bot.delete_message(chat_id=m.chat.id, message_id=m.id)
    print('Finished the file_id actualization')

########################################################################################################################
#                                               START THE MAIN LOOP                                                    #
########################################################################################################################

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('../config.ini')

    config_name = config['DEFAULT'].get("use_config", 'DEFAULT')

    if config_name != 'DEFAULT':
        user_choice = input("Custom config detected.\nType 'y' to use it: ").strip()
        if user_choice.lower() not in ['yes', 'y']:
            config_name = 'DEFAULT'

    print(f'Using {config_name} config values')
    config_data = config[config_name]

    ITEMS_PER_SEASON_PAGE = int(config_data.get('items_per_season_page', 3))
    ITEMS_PER_SEARCH_PAGE = int(config_data.get('items_per_search_page', 5))
    driver_pool = WebDriverPool(size=config_data.get('max_browser_number', 1),
                                browser_timeout=config_data.get('browser_lifecycle_time', 360),
                                driver_pool_monitor_frequency=config_data.get('check_release_interval', 60),
                                max_wait_time=config_data.get('max_wait_time', 30),
                                headless=config_data.get('headless_mode', 'True'))
    try:
        with driver_pool.get_driver() as driver:
            '1'
            #Scraper(repository, driver).prepare_dataset()
    except Exception as e:
        print('There has been an error while creating a dataset.')
        print(str(e))
    else:
        try:
            with open("../resources/data/user_data.json", 'r') as json_file:
                data = json.load(json_file)
                user_data = data
        except FileNotFoundError:
            print('No user_data.json was found.')
        user_choice = input("Do you want to actualize the file_id`s of the attachments?\nInput: ")

        if user_choice.lower() in ['yes', 'y']:
            user_choice = input('Please, supply your user_id: ')
            try:
                redo_the_images(user_id=user_choice)
            except Exception as e:
                print("Something has gone wrong while actualizing file_ids")
            print('Finished actualizing')
        bot.infinity_polling()

def exit_handler():
    with open("../resources/data/user_data.json", "w") as outfile:
        json.dump(user_data, outfile, indent=4, default=str)


atexit.register(exit_handler)