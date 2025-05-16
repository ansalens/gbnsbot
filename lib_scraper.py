from random import choice
from time import sleep
import json
import requests

URL = "https://opac.bisis.rs/sr-Latn/bisisWS/opac/search"
SLEEP_DURATION = 1
AGENTS = [
    'Mozilla/5.0 (Linux; Android 10; Alpha 20) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Mobile Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6300.2 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6269.2 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6066.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6096.0 Safari/537.36',
    'Mozilla/5.0 (Linux; Android 13; 23028RN4DG Build/TP1A.220624.014) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6381.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6399.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6284.0 Safari/537.36',
    'Mozilla/5.0 (Linux; Android 12; moto e22i Build/SOWS32.121-44-3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5860.2 Safari/537.36'
    ]
headers = {'Content-Type': 'application/json',
           'Host': 'opac.bisis.rs',
           'Library': 'gbns',
           'Accept': 'application/json,text/plain',
           'User-Agent': choice(AGENTS),
           'Accept-Encoding': 'gzip, deflate, br',
           'Accept-Language': 'en-US,en;q=0.9',
           'Refer': 'https://opac.bisis.rs/sr-Cyrl/search/result?s=70f3b2200c8d68e2b134524a2d',
           'Connection': 'keep-alive'
           }
libraries = {'Danilo Kis': {"item": {"label": "Данило Киш", "value": "27", "checked": True}, "type": 0},
             'Djura Danicic': {"item": {"label": "Ђура Даничић", "value": "01", "checked": True}, "type": 0}
             }


def prepare_data(title: str, author: str, library: str) -> (dict, str):
    """Prepare JSON data for a request to be sent.

    Loads JSON data in `data` variable and makes necessary edits to it.
    `loc_code` is location code of library e.g. "27".

    Returns
    -------
        data - JSON data for a future request.
        loc_code - Location code for chosen library for further use.
    """
    data_json = '{"searchModel":{"branches":[],"departments":[],"oper1":"AND","oper2":"AND","oper3":"AND","oper4":"AND","oper5":"AND","pref1":"AU","pref2":"TI","pref3":"LA","pref4":"PU","pref5":"PY","sort":"","text1":"","text2":"","text3":"srp","text4":"","text5":""},"options":{"pageSize":10,"currentPage":1,"filters":{"pubTypes":[],"pubYears":[],"languages":[],"authors":[],"locations":[],"subLocations":[],"subjects":[]},"sort":{"type":"PY_sort","ascending":false},"previewType":null,"lib":"gbns"}}'
    data = json.loads(data_json)

    loc_code = library['item']['value']
    data['options']['filters']['locations'].append(library)
    data['searchModel']['text1'] = author
    data['searchModel']['text2'] = title

    return data, loc_code


def check_available(ids: list, library: str) -> str:
    """Check if selected book is available in a chosen library.
    
    For each book ID from `ids` list, it sends a request and parses JSON
    in a way to check if that book is available in selected library.
    When it finds the first one that's available it returns status `msg` back.
    
    Arguments
    ---------
        ids - book IDs, each book ID is sent as mandatory data to the server.
       library - location code for chosen library.
    
    Raises
    ------
        HTTPError if something is wrong with HTTP request.
        JSONDecodeError if something is wrong with JSON response.
    
    Returns
    -------
        msg - Status message about the book's availability.
    """
    book_url = "https://opac.bisis.rs/sr-Latn/bisisWS/book"
    msg = ""

    for id_ in ids:
        try:
            r = requests.post(book_url, data=id_, headers=headers, timeout=5)
            r.raise_for_status()
            rjson = r.json()
            sleep(SLEEP_DURATION)
        except requests.HTTPError as http_err:
            print(f"Error occurred: {http_err}")
        except requests.exceptions.JSONDecodeError as json_err:
            print(f"JSON Error occurred: {json_err}")
        else:
            for location in rjson['items']:
                if location['locCode'] == library:
                    status = location['status']
                    #if status in ('BORROWED', 'NOT_SHOWABLE'):
                    #    print('Status: NEDOSTUPNA')
                    if status == "FREE":
                        url = f'https://opac.bisis.rs/sr-Latn/book/gbns/{id_}'
                        status = 'DOSTUPNA ✅'
                        msg = f'{status}\n{url}'
                        break
            else:
                continue
            break

    return msg


def parse_ids(json_data: dict) -> list:
    """Take JSON data response and return a list of book ids."""
    id_list = []
    for book in json_data['content']:
        id_list.append(book['_id'])

    return id_list


def find_book(data: dict) -> dict:
    """Search for a book and return a JSON response if book exists.
    
    With already prepared data, it sends a request to the server to verify
    if a book exists. If it does it will return JSON response for further
    processing.
    
    Raises
    ------
        HTTPError if something is wrong with HTTP request.
        JSONDecodeError if something is wrong with JSON response.
    
    Returns
    -------
        json_respone - JSON data about the book.
        0 - The book that was searched for, doesn't exist in the library.
    """
    try:
        r = requests.post(URL, json=data, headers=headers, timeout=5)
        r.raise_for_status()
        json_response = r.json()
    except requests.HTTPError as http_err:
        raise SystemExit(f"HTTP Error: {http_err}") from http_err
    except requests.exceptions.JSONDecodeError as json_err:
        if len(r.text) == 0:
            return 0
        raise SystemExit(f"JSON Error: {json_err}") from json_err
    #print(json_response)
    return json_response


def parse_json(json_response: dict, library: str):
    """Parse JSON data about the book and return status message.
    
    First it gets a list of ids, these ids are different identifiers for the
    same piece. Every id from `ids` is different in some way, such as edition,
    translation, etc. Then for the selected `library`, it checks if any of
    those ids is available, and crafts a status message that will be returned.
    
    Arguments
    ---------
        json_response - JSON data about the book.
        library - Location code for a library.

    Returns
    -------
        msg - Status message about book's availability.
    """
    ids = parse_ids(json_response)
    msg = check_available(ids, library)

    return msg


def telegram_search(title, author, library) -> str:
    """Search for a book in a library. Bundle function for telegram bot.
    
    This function bundles whole module functionality in order to search for
    the book in a library. Data preparation is first step, next is searching
    for the book and finally returning a message depending if it can be borrowed
    or not.
    
    Arguments
    ---------
        title - Book title.
        author - Book's author name.
        library - Library to search in for a book.
    
    Raises
    ------
        SystemExit - In case some unexpected error occurs.
    
    Returns
    -------
        msg - Status message along with URL for a book.
        "Knjiga nije pronadjena ⚠" - If the book is not found in the library.
        "Nazalost desila se greska ‼" - If some exception is encountered.
    """
    data, location_code = prepare_data(title, author, library)
    try:
        json_response = find_book(data)
        if not json_response:
            return "Knjiga nije pronadjena ⚠"
    except SystemExit as err:
        print(err)
        return "Nazalost desila se greska ‼"

    msg = parse_json(json_response, location_code)

    return msg
