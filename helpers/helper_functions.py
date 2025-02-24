# helpers/helper_functions.py
import requests

def load_template_from_github(url: str) -> str:
    """
    Load template text from a remote GitHub raw URL.
    """
    response = requests.get(url)
    response.raise_for_status()  # Raise an HTTPError if the request failed.
    return response.text
