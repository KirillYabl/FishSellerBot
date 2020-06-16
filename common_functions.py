import requests


def raise_response_errors(response):
    """Check response for errors.
    raise error if some error in response

    :param response: requests response object
    """
    # check HTTPError
    response.raise_for_status()
    # some sites can return 200 and write error in body
    if 'error' in response.json():
        raise requests.exceptions.HTTPError(response.json()['error'])
