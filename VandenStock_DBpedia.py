import urllib.request
import urllib.response
import urllib.parse
import lxml.etree
import sys
import json


def clean(string: str) -> str:
    """
    Clean input string and URL encode for safe search
    """     
    if len(string) > 0 and not string.isspace(): # valid input string?
        string = string.strip().casefold() # strip of unnecessary whitespace and lowercase
        string = urllib.parse.quote(string) # encode for safe URL search
        return string

    else:
        sys.exit('That is an empty string... Try again.') # if not valid input string, exit program


def getAPIprefix() -> str:
    """
    Detect functioning DBpedia lookup API
    """
    prefixes = ["https://lookup.dbpedia.org/api/search/PrefixSearch?QueryString=",
                "http://lookup.dbpedia.org/api/search/PrefixSearch?QueryString=",
                "https://lookup.dbpedia.org/api/prefix?query=",
                "http://lookup.dbpedia.org/api/prefix?query=",
                "http://akswnc7.informatik.uni-leipzig.de/lookup/api/search?query="]
    for prefix in prefixes:
        with urllib.request.urlopen(prefix + "Antwerp") as test:
            if test.status == 200:
                return prefix
    sys.exit("No functioning DBpedia lookup API found!")


def extract_books(query_results: bytes) -> str:
    """
    Query the DBpedia response for hits specifically about books
    Condition: the text in Classes/Class/URI == 'http://dbpedia.org/ontology/Book'
    """
    BOOK_IDENTIFIER = "http://dbpedia.org/ontology/Book" # condition to filter out results on books
    tree = lxml.etree.fromstring(query_results) # turn XML string into etree object

    dict_of_books = {} # in case of multiple results: save all
    for element in tree.iter("URI"): # navigate tree for URI elements
        if element.text == BOOK_IDENTIFIER: # apply condition
            # access relevant elements in tree for that result
            Class = element.getparent()
            Classes = Class.getparent()
            Description = Classes.getprevious()
            URI = Description.getprevious() # resource with extra information on book
            Label = URI.getprevious() # name of the book

            dict_of_books[Label.text] = URI.text 

    if len(dict_of_books) == 0: # if there are no booktitles related to the search
        sys.exit("There are no books found for your search query... Try again.")

    elif len(dict_of_books) == 1: # 1 hit: transform URI for metadata into URI in json format
        for title, resource in dict_of_books.items():
            URI_json = resource.replace("resource", "data")
            URI_json = URI_json + '.json'
        
        print("Results for '{}':".format(title))

    else: # multiple book results
        list_of_books = list(dict_of_books)
        print('There are multiple titles available. Please select 1 by entering their index')
        for idx, bookname in enumerate(list_of_books):
            print('-', idx, ':', bookname)
        choice = input('Which book do you choose? ') # provide user with choice

        title = list_of_books[int(choice)] # access that choice's title to access its URI in dict
        URI_json = dict_of_books[title].replace("resource", "data") # transform URI for metadata into URI in json format
        URI_json = URI_json + '.json'

        print("Results for '{}':".format(title))
    
    return URI_json


def extract_metadata(URI:str) -> dict:
    """
    Follow URI to metadata in json format on selected novel and extract info 
    Extract metadata on: author, publisher, publication date, number of pages, genre and an abstract of the book
    """
    # fixed URI identifiers per piece of metadata
    AUTHOR_ID = "http://dbpedia.org/ontology/author"
    PUBLISHER_ID = "http://dbpedia.org/ontology/publisher"
    PUBLICATIONDATE_ID = "http://dbpedia.org/property/published"
    PAGES_ID = "http://dbpedia.org/ontology/numberOfPages"
    GENRE_ID = "http://dbpedia.org/property/genre"
    ABSTRACT_ID = "http://dbpedia.org/ontology/abstract"
    
    # initialize answers
    AUTHOR_ANSWER = 'not found'
    AUTHOR_URI = 'not found'
    PUBLISHER_ANSWER = 'not found'
    PUBLISHER_URI = 'not found'
    PUBLICATIONDATE_ANSWER = 'not found'
    PAGES_ANSWER = 'not found'
    GENRE_ANSWER = 'not found'
    ABSTRACT_ANSWER = 'not found' 
    
    # open metadata URI
    try:
        with urllib.request.urlopen(URI) as page:
            json_string = page.read()
            json_dict = json.loads(json_string)
            
        # if relevant metadata is found, extract info and update answer
        for key, value in json_dict.items():
            for resource, aspects in value.items():
                if resource == AUTHOR_ID:
                    for lst in value[resource]:
                        AUTHOR_URI = lst['value'] # extract URI
                        AUTHOR_ANSWER = AUTHOR_URI.split('/')[-1].replace('_', ' ') # extract answer for URI via string manipulation     
                elif resource == PUBLISHER_ID:
                    for lst in value[resource]:
                        PUBLISHER_URI = lst['value']
                        PUBLISHER_ANSWER = PUBLISHER_URI.split('/')[-1].replace('_', ' ')
                elif resource == PUBLICATIONDATE_ID:
                    for lst in value[resource]:
                        PUBLICATIONDATE_ANSWER = lst['value']
                elif resource == PAGES_ID:
                    for lst in value[resource]:
                        PAGES_ANSWER = lst['value']
                elif resource == GENRE_ID:
                    for lst in value[resource]:
                        GENRE_URI = lst['value']
                        GENRE_ANSWER = GENRE_URI.split('/')[-1].replace('_', ' ')
                elif resource == ABSTRACT_ID:
                    for dic in value[resource]: 
                        for k, v in dic.items():
                            if dic[k] == 'en': # extract abstract in English!
                                ABSTRACT_ANSWER = dic['value']
        
        # return answers as dict
        return {'AUTHOR': AUTHOR_ANSWER, 
        'AUTHOR_RESOURCE': AUTHOR_URI,
        'PUBLISHER': PUBLISHER_ANSWER, 
        'PUBLISHER_RESOURCE': PUBLISHER_URI,
        'PUBLICATION DATE': PUBLICATIONDATE_ANSWER, 
        'NUMBER OF PAGES': PAGES_ANSWER, 
        'GENRE': GENRE_ANSWER, 
        'ABSTRACT': ABSTRACT_ANSWER}
             
    except urllib.error.HTTPError as HTTPError:
        print(HTTPError)
        exit(HTTPError)
    except urllib.error.URLError as URLError:
        print(URLError)
        exit(URLError)


def display_results(metadata: dict):
    """
    Format the extracted metadata and display as response to user
    """
    for key, value in metadata.items():
        if key.endswith('RESOURCE') and value != 'not found': # ouput resource for extra metadata on item differently
            print("-> for more info see {}".format(value))
        elif key =='ABSTRACT':
        	print("- {}: \n{}".format(key, value))
        else:
            print("- {}: {}".format(key, value))


def query_DBpedia(search: str):
    """
    Query DBpedia API for metadata on the book specified by the user
    Return response or exit with errorcode
    """
    bookname = clean(search)
    DBPEDIA_PREFIX = getAPIprefix()
    url = DBPEDIA_PREFIX + bookname

    try:
        with urllib.request.urlopen(url) as query:
            result = query.read()  
            
        book_results = extract_books(result)
        metadata = extract_metadata(book_results)
        answer = display_results(metadata)
        
    except urllib.error.HTTPError as HTTPError:
        print(HTTPError)
        exit(HTTPError)
    except urllib.error.URLError as URLError:
        print(URLError)
        exit(URLError)
