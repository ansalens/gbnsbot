import lib_scraper


def pick_library() -> dict:
    """Take user input for library of choice, return subdict of libraries."""
    indexed = {'1': ('Danilo Kis', 'Narodnog Fronta 47', 'Pon-Pet 07:30-20:00'),
               '2': ('Djura Danicic', 'Dunavska 1', 'Pon-Pet 07:30-20:00\nSub 08:00-14:00')}

    print("Biblioteke:")
    for index, lib in indexed.items():
        print(f"{index}) {lib[0]}\n-> {lib[1]}\n-> {lib[2]}")

    while (library := input(">>>  ")) not in indexed:
        pass

    return lib_scraper.libraries[indexed[library][0]]


def main():
    title = input("Unesi naslov: ")
    author = input("Unesi autora knjige: ")
    library = lib_scraper.libraries['Danilo Kis']
    data, library = lib_scraper.prepare_data(title, author, library)
    json_response = lib_scraper.find_book(data)
    print('*'*20)
    print(f'Pronadjeno ukupno: {json_response['totalElements']}')
    msg = lib_scraper.parse_json(json_response, library)
    print(msg)

if __name__ == "__main__":
    main()