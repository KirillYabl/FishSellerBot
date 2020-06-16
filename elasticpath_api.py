import requests

import time
import logging

from common_functions import raise_response_errors

logger = logging.getLogger(__name__)


class Access:
    """This class keep and update access token of Elasticpath

    Elasticpath token only works until "self.expires_in" arrives.
    It's bad practise asc token every query, better save queries.
    """

    def __init__(self, client_id):
        """Init access

        :param client_id: str, internal id of user in elasticpath
        """
        self.client_id = client_id
        self.expires = 0

        self.access_token = self.get_access_token()

    def get_access_token(self):
        """Get token if it active, else update before get.

        :return: access_token: str, elasticpath token
        """

        token_work = time.time() < self.expires

        if token_work:
            # No need update token
            return self.access_token

        data = {
            'client_id': self.client_id,
            'grant_type': 'implicit'
        }

        response = requests.post('https://api.moltin.com/oauth/access_token', data=data)
        raise_response_errors(response)

        response_json = response.json()

        self.access_token = response_json['access_token']
        self.expires = response_json['expires']

        logger.debug('elasticpathh access token was updated')

        return self.access_token


def get_authorization_headers(access_keeper):
    """Construct headers for next API queries.

    :param access_keeper: object, Access class instance
    :return:
    """
    access_token = access_keeper.get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    return headers


def get_all_products(access_keeper):
    """Get list of products

    :param access_keeper: object, Access class instance
    :return: list of dicts, list of products where product is dict
    """
    logger.debug('getting products...')
    headers = get_authorization_headers(access_keeper)

    response = requests.get('https://api.moltin.com/v2/products', headers=headers)
    raise_response_errors(response)

    products = response.json()['data']
    logger.debug(f'{len(products)} products was got')

    return products


def get_product_by_id(access_keeper, product_id):
    """Get one product by id (:product_id:).

    :param access_keeper: object, Access class instance
    :param product_id: str, id of product
    :return: dict, product params which recorded in dict
    """
    logger.debug(f'getting product by id: {product_id}...')
    headers = get_authorization_headers(access_keeper)

    response = requests.get(f'https://api.moltin.com/v2/products/{product_id}', headers=headers)
    raise_response_errors(response)

    product = response.json()['data']
    logger.debug('product was got')

    return product


def get_file_href_by_id(access_keeper, file_id):
    """Get href of file by id (:file_id:).

    :param access_keeper: object, Access class instance
    :param file_id: str, id of file
    :return: str, href
    """
    logger.debug(f'getting href by file id: {file_id}...')
    headers = get_authorization_headers(access_keeper)

    response = requests.get(f'https://api.moltin.com/v2/files/{file_id}', headers=headers)
    raise_response_errors(response)

    href = response.json()['data']['link']['href']
    logger.debug('href was got')

    return href


def add_product_to_cart(access_keeper, product_id, quantity, reference):
    """Add :quantity: of product to cart by :produt_id: for :reference: client.

    :param access_keeper: object, Access class instance
    :param product_id: str, id of product
    :param quantity: str or int, quantity of product (in pcs)
    :param reference: str, some internal string-ID of the client that is used to search for the cart in the future
    :return: dict, response of API
    """
    logger.debug(f'adding product {product_id} in cart. quantity: {quantity}. reference: {reference}...')
    headers = get_authorization_headers(access_keeper)
    headers['Content-Type'] = 'application/json'

    data = {'data':
        {
            'id': product_id,
            'type': 'cart_item',
            'quantity': int(quantity)  # if not int API return 400
        }
    }

    response = requests.post(f'https://api.moltin.com/v2/carts/{reference}/items', headers=headers, json=data)
    raise_response_errors(response)
    logger.debug('product was added')

    return response.json()


def get_cart_items_info(access_keeper, reference):
    """Get all product in cart for :reference:.

    :param access_keeper: object, Access class instance
    :param reference: str, some internal string-ID of the client that is used to search for the cart in the future
    :return: dict, keys 'products' (value list of dict with product params) and 'total_price' (value string with formatted price)
    """
    logger.debug(f'getting cart items. reference - {reference}...')
    headers = get_authorization_headers(access_keeper)

    response = requests.get(f'https://api.moltin.com/v2/carts/{reference}/items', headers=headers)
    raise_response_errors(response)
    logger.debug('cart items were got')

    response_json = response.json()
    items_in_cart = response_json['data']

    logger.debug(f'{len(items_in_cart)} items in cart')

    items_in_cart_for_response = {'products': []}
    for item in items_in_cart:
        item_in_cart = {
            'description': item['description'],
            'name': item['name'],
            'quantity': item['quantity'],
            'price_per_unit': item['meta']['display_price']['with_tax']['unit']['formatted'],
            'total_price': item['meta']['display_price']['with_tax']['value']['formatted'],
            'product_id': item['product_id'],
            'cart_item_id': item['id']
        }
        items_in_cart_for_response['products'].append(item_in_cart)
        logger.debug(f'item {item["id"]} was handled')

    total_price = response_json['meta']['display_price']['with_tax']['formatted']
    items_in_cart_for_response['total_price'] = total_price

    logger.debug('items in carts were handled')

    return items_in_cart_for_response


def delete_cart_item(access_keeper, reference, cart_item_id):
    """Delete product from :reference: cart by :cart_item_id:

    :param access_keeper: object, Access class instance
    :param reference: str, some internal string-ID of the client that is used to search for the cart in the future
    :param cart_item_id: str, id of item in cart
    :return: dict, response of API
    """
    logger.debug(f'delete cart item {cart_item_id}...')
    headers = get_authorization_headers(access_keeper)

    response = requests.delete(f'https://api.moltin.com/v2/carts/{reference}/items/{cart_item_id}', headers=headers)
    raise_response_errors(response)
    logger.debug(f'cart item {cart_item_id} was deleted')

    return response.json()


def create_customer(access_keeper, name, email):
    """Create a new customer with name-:name: and email-:email:.

    If the client exists, the status code 409 will be returned.
    If the name or email address is incorrect, status code 422 will be returned.
    Else result in json will be returned.

    :param access_keeper: object, Access class instance
    :param name: str, name of client, not Null
    :param email: str, email of client, should be valid (elasticpath API will check)
    :return: dict or int, info about creation or status code
    """
    logger.debug(f'Creating customer {name} with email {email}...')
    headers = get_authorization_headers(access_keeper)
    headers['Content-Type'] = 'application/json'

    data = {'data':
        {
            'type': 'customer',
            'name': name,
            'email': email
        }
    }

    response = requests.post('https://api.moltin.com/v2/customers', headers=headers, json=data)
    if response.status_code not in [409, 422]:
        raise_response_errors(response)
        logger.debug('customer was added')
        return response.json()

    return response.status_code
