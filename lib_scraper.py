from random import choice
from time import sleep
import json
import requests

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
URL = "https://opac.bisis.rs/sr-Latn/bisisWS/opac/search"
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
             'Djura Danicic': {"item": {"label": "Ђура Даничић", "value": "01", "checked": True}, "type": 0}}
indexed = {'1': ('Danilo Kis', 'Narodnog Fronta 47', 'Pon-Pet 07:30-20:00'),
           '2': ('Djura Danicic', 'Dunavska 1', 'Pon-Pet 07:30-20:00\n   Sub: 08:00-14:00')}

def prepare_data(title, author, library) -> (dict, str):
    """Prepare data for a request to be sent.

    Asks the user for title and author of the book, calls pick_library function
    to make him pick a library and then edits JSON data to reflect user choice.

    Returns
    -------
        JSON data for a future request
        Location code for chosen library for further use
    """
    data = '{"searchModel":{"branches":[],"departments":[],"oper1":"AND","oper2":"AND","oper3":"AND","oper4":"AND","oper5":"AND","pref1":"AU","pref2":"TI","pref3":"LA","pref4":"PU","pref5":"PY","sort":"","text1":"","text2":"","text3":"srp","text4":"","text5":""},"options":{"pageSize":10,"currentPage":1,"filters":{"pubTypes":[],"pubYears":[],"languages":[],"authors":[],"locations":[],"subLocations":[],"subjects":[]},"sort":{"type":"PY_sort","ascending":false},"previewType":null,"lib":"gbns"}}'
    data_json = json.loads(data)

    # title = input("Naslov: ")
    # author = input("Ime autora: ")
    # library = pick_library()
    loc_code = library['item']['value']
    data_json['options']['filters']['locations'].append(library)
    data_json['searchModel']['text1'] = author
    data_json['searchModel']['text2'] = title

    return data_json, loc_code


def pick_library() -> dict:
    """Take user input for library of choice, return subdict of libraries."""
    print("Biblioteke:")
    for index, lib in indexed.items():
        print(f"{index}) {lib[0]}\n-> {lib[1]}\n-> {lib[2]}")

    while (library := input(">>>  ")) not in indexed:
        pass

    return libraries[indexed[library][0]]


def parse_ids(json_data: dict) -> list:
    """Take JSON data response and return list of book ids."""
    id_list = []
    for book in json_data['content']:
        id_list.append(book['_id'])

    return id_list


def check_available(ids: list, library: str):
    """Check if selected books are available in a chosen library.
    
    For each book ID from ids list, it sends a request and parses JSON
    in a way to check if that book is available in library the user has
    chosen.
    
    Arguments
    ---------
    ids - list of book IDs, each book ID is sent as mandatory data to the server.
    library - location code for chosen library.
    
    Raises
    ------
    HTTPError if something is wrong with HTTP request.
    JSONDecodeError if something is wrong with JSON response from server.
    """
    book_url = "https://opac.bisis.rs/sr-Latn/bisisWS/book"

    for _id in ids:
        try:
            r = requests.post(book_url, data=_id, headers=headers, timeout=5)
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
                    if status == 'FREE':
                        url = f'https://opac.bisis.rs/sr-Latn/book/gbns/{_id}'
                        status = 'DOSTUPNA ✅'
                        msg = f'{status}\n{url}'
                        return msg


def find_book(data):
    try:
        r = requests.post(URL, json=data, headers=headers, timeout=5)
        if len(r.text) == 0:
            return -1
        r.raise_for_status()
        jsr = r.json()
    except requests.HTTPError as http_err:
        raise SystemExit(f"HTTP Error: {http_err}")
    except requests.exceptions.JSONDecodeError as json_err:
        raise SystemExit(f"JSON Error: {json_err}")
    else:
        return jsr


def parse_json(json_response, library):
    ids = parse_ids(json_response)
    msg = check_available(ids, library)

    return msg

# Implement logging
def telegram(title, author, library):
    data, location = prepare_data(title, author, library)
    try:
        json_response = find_book(data)
        if json_response == -1:
            return "Knjiga nije pronadjena ⚠"
    except SystemExit as err:
        print(err)
        return "Nazalost desila se greska ‼"
    msg = parse_json(json_response, location)
    return msg


def main():
    title = 'Misliti, brzo i sporo'
    author = ''
    library = libraries['Danilo Kis']
    data, library = prepare_data(title, author, library)
    json_response = find_book(data)
    # print('*'*20)
    # print(f'Pronadjeno ukupno: {json_response['totalElements']}')
    msg = parse_json(json_response, library)
    print(msg)

if __name__ == "__main__":
    main()
