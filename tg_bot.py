import logging
import math
from pprint import pprint
import json

import environs
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, Filters
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler
import redis

import elasticpath_api

logger = logging.getLogger(__name__)


def get_config():
    """Get config."""
    global _config

    try:
        return _config
    except NameError:
        _config = {}

        env = environs.Env()
        env.read_env()

        _config['tg_bot_token'] = env.str('TG_BOT_TOKEN')
        _config['proxy'] = env.str('PROXY', None)
        _config['elasticpath_client_id'] = env.str('ELASTICPATH_CLIENT_ID')
        _config['redis_db_password'] = env.str("REDIS_DB_PASSWORD")
        _config['redis_db_address'] = env.str("REDIS_DB_ADDRESS")
        _config['redis_db_port'] = env.int("REDIS_DB_PORT")
        _config['products_in_page'] = env.int("PRODUCTS_IN_PAGE")
        logger.debug('.env was read, config was constructed')

        return _config


def get_elasticpath_access_keeper():
    """Get object which keep elasticpath API access."""
    global _access_keeper

    try:
        return _access_keeper
    except NameError:
        config = get_config()
        _access_keeper = elasticpath_api.Access(config['elasticpath_client_id'])

        logger.debug('access_keeper was got')
        return _access_keeper


def get_database_connection():
    """Returns a connection to Redis DB or creates a new one if it does not already exist."""
    global _database
    try:
        return _database
    except NameError:
        config = get_config()
        _database = redis.Redis(host=config['redis_db_address'],
                                port=config['redis_db_port'],
                                password=config['redis_db_password'])
        logger.debug('connection with Redis DB was established')
        return _database


def get_cart_msg_and_keyboard(bot, update):
    """Get cart info message and keyboard for cart interaction."""
    access_keeper = get_elasticpath_access_keeper()
    cart_items_info = elasticpath_api.get_cart_items_info(access_keeper, update.message.chat_id)
    total_price = cart_items_info['total_price']
    product_messages = []
    keyboard = []
    for item in cart_items_info['products']:
        item_msg = f'{item["name"]}\n{item["description"]}\n{item["price_per_unit"]} шт.\n'
        item_msg += f'{item["quantity"]} шт. в корзине за {item["total_price"]}'
        product_messages.append(item_msg)

        keyboard.append([InlineKeyboardButton(f'Убрать из корзины {item["name"]}', callback_data=item['cart_item_id'])])

        logger.debug(f'item {item["cart_item_id"]} was processed, btn added')

    keyboard.append([InlineKeyboardButton('В меню', callback_data='to_menu')])
    keyboard.append([InlineKeyboardButton('Оплата', callback_data='payment')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    logger.debug(f'keyboard was constructed')

    msg = '\n\n'.join(product_messages) + f'\n\nОбщая цена: {total_price}'
    return msg, reply_markup


def send_cart_info(bot, update):
    """Send message with cart info (name, description, price per unit, quantity, total_price)."""
    msg, reply_markup = get_cart_msg_and_keyboard(bot, update)

    bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
    bot.send_message(text=msg, chat_id=update.message.chat_id, reply_markup=reply_markup)

    return 'HANDLE_CART'


def start(bot, update):
    """Bot /start command."""
    page = 0
    if update.message.reply_markup:
        bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
        if update.data.startswith('page#'):
            _, str_page = update.data.split('#')
            page = int(str_page)

    logger.debug(f'page number: {page}')

    access_keeper = get_elasticpath_access_keeper()
    products = elasticpath_api.get_all_products(access_keeper)
    config = get_config()
    products_in_page = config['products_in_page']

    # sort for pagination, always return similar results for similar page
    sorted_products = sorted(products, key=lambda x: x['name'])
    products_pages = []
    max_pages = math.ceil(len(sorted_products) / products_in_page)
    for cur_page in range(0, max_pages):
        page_start = products_in_page * cur_page
        page_end = products_in_page * (cur_page + 1)
        products_pages.append(sorted_products[page_start:page_end])

    keyboard = []

    for product in products_pages[page]:
        product_name = product['name']
        product_id = product['id']

        btn = InlineKeyboardButton(product_name, callback_data=product_id)

        keyboard.append([btn])
        logger.debug(f'product {product_name} was added to keyboard. Product id: {product_id}')

    previous_next_buttons = []
    if page != 0:
        previous_next_buttons.append(InlineKeyboardButton('<< назад', callback_data=f'page#{page - 1}'))
    if page != (len(products_pages) - 1):
        previous_next_buttons.append(InlineKeyboardButton('вперед >>', callback_data=f'page#{page + 1}'))

    if previous_next_buttons:
        keyboard.append(previous_next_buttons)

    keyboard.append([InlineKeyboardButton('Корзина', callback_data='cart')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    logger.debug(f'keyboard was constructed')

    bot.send_message(text='Выберите продукт', reply_markup=reply_markup, chat_id=update.message.chat_id)

    return 'HANDLE_MENU'


def get_cart_product(access_keeper, chat_id, product_id):
    """Get info abouc product in cart by :product_id: for user :chat_id:"""
    cart_items_info = elasticpath_api.get_cart_items_info(access_keeper, chat_id)['products']
    default_product = {
        'description': '',
        'name': '',
        'quantity': 0,
        'price_per_unit': '',
        'total_price': '$0.00',
        'product_id': '',
        'cart_item_id': ''
    }
    cart_product = [product for product in cart_items_info if product['product_id'] == product_id]

    try:
        cart_product = cart_product[0]
    except IndexError:
        cart_product = default_product

    return cart_product


def handle_menu(bot, update):
    """Menu with products."""
    query = update.callback_query

    logger.debug(f'query.data = {query.data}')

    if query.data.startswith('page#'):
        logger.debug('go to :start: function')
        condition = start(bot, query)
        return condition

    if query.data == 'cart':
        logger.debug('go to :send_cart_info: function')
        condition = send_cart_info(bot, query)
        return condition

    logger.debug('returning description of product')

    product_id = query.data
    access_keeper = get_elasticpath_access_keeper()
    product = elasticpath_api.get_product_by_id(access_keeper, product_id)
    image_id = product['relationships']['main_image']['data']['id']
    image_href = elasticpath_api.get_file_href_by_id(access_keeper, image_id)

    cart_product = get_cart_product(access_keeper, query.message.chat_id, product_id)

    bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

    stock_level = product['meta']['stock']['level']
    msg = f"""
    {product['name']}

    {product['meta']['display_price']['with_tax']['formatted']} per unit ({product['weight']['kg']} kg)
    {stock_level} units on stock

    {product['description']}

    В корзине {cart_product['quantity']} шт. на {cart_product['total_price']}
    """
    logger.debug('reply message was constructed')

    add_to_cart_buttons = []
    logger.debug(f'On stock: {stock_level} pcs')
    for quantity in [1, 5, 10]:
        if quantity <= stock_level:
            callback_data = f'{product_id}\n{quantity}'
            add_to_cart_buttons.append(InlineKeyboardButton(f'{quantity} шт.', callback_data=callback_data))
            logger.debug(f'Button with {quantity} psc was added')

    keyboard = [
        add_to_cart_buttons,
        [InlineKeyboardButton('Корзина', callback_data='cart')],
        [InlineKeyboardButton('Назад', callback_data='back_to_products')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    logger.debug('Keyboard was constructed')

    bot.send_photo(chat_id=query.message.chat_id, photo=image_href, caption=msg, reply_markup=reply_markup)
    return 'HANDLE_DESCRIPTION'


def waiting_email(bot, update):
    """Condition that wait email from user."""
    user_email = update.message.text
    access_keeper = get_elasticpath_access_keeper()

    customer_or_status_code = elasticpath_api.create_customer(access_keeper=access_keeper,
                                                              name=update.message.chat.username,
                                                              email=user_email)

    if customer_or_status_code == 422:
        # invalid email
        logger.debug('User entered invalid data')
        msg = 'Вы ввели неправильный email, пожалуйста пришлите снова, пример: example@gmail.com'
        bot.send_message(text=msg, chat_id=update.message.chat_id)
        return 'WAITING_EMAIL'

    if customer_or_status_code != 409:
        # email has not added to CMS yet
        logger.debug('New customer was created')
        user_email = customer_or_status_code['data']['email']

    msg = f'Вы прислали мне эту почту: {user_email}.\nСпасибо, мы скоро свяжеся с вами!\n\nВаш заказ:\n'
    msg_cart, _ = get_cart_msg_and_keyboard(bot, update)
    bot.send_message(text=msg + msg_cart, chat_id=update.message.chat_id)

    condition = start(bot, update)
    return condition


def handle_cart(bot, update):
    """Cart menu."""
    query = update.callback_query
    if query.data == 'to_menu':
        logger.debug('User chose return to menu')
        condition = start(bot, query)
        return condition

    if query.data == 'payment':
        logger.debug('User chose payment')
        msg = 'Пожалуйста, пришлите ваш email'
        bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
        bot.send_message(text=msg, chat_id=query.message.chat_id)
        return 'WAITING_EMAIL'

    access_keeper = get_elasticpath_access_keeper()
    cart_item_id = query.data
    logger.debug(f'User deleting item from cart, cart_item_id: {cart_item_id}')
    elasticpath_api.delete_cart_item(access_keeper, query.message.chat_id, cart_item_id)

    condition = send_cart_info(bot, query)
    return condition


def handle_description(bot, update):
    """Product description menu."""
    query = update.callback_query
    if query.data == 'back_to_products':
        logger.debug('User chose return to products')
        condition = start(bot, query)
        return condition

    if query.data == 'cart':
        logger.debug('User chose watch the cart')
        condition = send_cart_info(bot, query)
        return condition

    access_keeper = get_elasticpath_access_keeper()
    product_id, quantity = query.data.split()
    logger.debug(f'User chose add product to cart. Product_id = {product_id}; quantity={quantity}')
    elasticpath_api.add_product_to_cart(access_keeper, product_id, quantity, query.message.chat_id)
    update.callback_query.answer(text='Товар добавлен в корзину', show_alert=True)
    query.data = product_id
    condition = handle_menu(bot, update)
    return condition


def handle_users_reply(bot, update):
    """Bot's state machine."""
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return

    if user_reply == '/start':
        user_state = 'START'
        db.set(chat_id, user_state)
    else:
        user_state = db.get(chat_id).decode("utf-8")

    logger.debug(f'User state: {user_state}')

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'WAITING_EMAIL': waiting_email
    }
    state_handler = states_functions[user_state]
    next_state = state_handler(bot, update)
    db.set(chat_id, next_state)


def error(bot, update, error_obj):
    """Log Errors caused by Updates."""
    logger.warning(f'Update "{update}" caused error "{error_obj}"')


def main():
    logging.basicConfig(format='%(asctime)s  %(name)s  %(levelname)s  %(message)s', level=logging.DEBUG)

    config = get_config()
    # Create the Updater and pass it your bot's token.
    request_kwargs = None
    if config['proxy']:
        request_kwargs = {'proxy_url': config['proxy']}
        logger.debug(f'Using proxy - {config["proxy"]}')
    updater = Updater(token=config['tg_bot_token'], request_kwargs=request_kwargs)
    logger.debug('Connection with TG was established')

    updater.dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_error_handler(error)

    # Start the Bot
    updater.start_polling()


if __name__ == '__main__':
    main()
