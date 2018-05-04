"""Generate a random page from a wikipedia category."""
import argparse
import random

import requests

DEBUGGING = False
max_depth = 4
current_depth = 0
header = "Garrett Credi's Random Page Bot(Contact @ gcc@ameritech.net)"
headerVal = {'Api-User-Agent': header}
base_url = 'https://en.wikipedia.org/w/api.php'


def print_debug(str):
    """Print strings if in debug/verbose mode mode."""
    global DEBUGGING
    if(DEBUGGING):
        print("DEBUG: " + str)


def generateRequestsParams(category, mode):
    """Generate the params for requests given a category and a mode."""
    cmtype = ""
    if(mode == "Subcat"):
        cmtype = 'subcat'
    elif(mode == "Subpage"):
        cmtype = 'page'
    params = {
        'format': 'json',
        'action': 'query',
        'list': 'categorymembers',
        'cmtitle': category,
        'cmlimit': 500,
        'cmtype': cmtype
    }
    if(mode == "Pagecats"):
        params = {
            'format': 'json',
            'action': 'query',
            'titles': category,
            'prop': 'categories'
        }
    return params


def wrappedRequest(category, mode):
    """Wrap a request to deal with connection errors."""
    global base_url
    params = generateRequestsParams(category, mode)
    global headerVal
    max_times = 5
    times = 0
    propertyString = 'categorymembers'
    while(times < max_times):
        try:
            r = requests.get(base_url, headers=headerVal, params=params)
            print_debug(str(r.json()))
            if(mode != "Pagecats"):
                return r.json()['query'][propertyString]
            else:
                for key in r.json()['query']['pages']:
                    return r.json()['query']['pages'][key]['categories']
        except requests.exceptions.ConnectionError as e:
            if(times > max_times):
                print_debug("{category} failed too many times ({times}) " +
                            " times. Moving on".format(
                                category=category,
                                times=times
                                )
                            )
                times = 0
                return [category]
            else:
                print_debug("Retrying {category} due to connection " +
                            " error".format(
                                cateogry=category
                                )
                            )
                times += 1


def getSubcategories(category):
    """Get subcategories of a given subcategory."""
    global max_depth, DEBUGGING
    current_depth = 1
    singleStepSubcategories = [category]
    allSubcategories = []
    while(current_depth <= max_depth):
        print_debug("Current tree depth {d}".format(d=current_depth))
        subcategoryTemp = []
        if(len(singleStepSubcategories) == 0):
            break
        for subcat in singleStepSubcategories:
            allSubcategories.append(subcat)
            subcategories = wrappedRequest(subcat, mode="Subcat")
            for cat in subcategories:
                title = cat['title']
                print_debug("{subcat} has subcategory {title}".format(
                                subcat=subcat,
                                title=title
                                )
                            )
                if(title not in allSubcategories):
                    allSubcategories.append(title)
                    subcategoryTemp.append(title)
                else:
                    print_debug("{t} already checked. Moving on".format(
                                                                    t=title
                                                                    )
                                )
        singleStepSubcategories = subcategoryTemp
        current_depth += 1
    return allSubcategories


def saveArray(category, subcats):
    """Save array to file."""
    filename = "{category}_subcats.txt".format(category=category)
    print_debug("Saving to {f}".format(f=filename))
    with open(filename, 'w') as f:
        for cat in subcats:
            f.write(cat+"\n")


def subcategoriesWithoutDuplicates(category):
    """Generate a list of subcategories without duplicates."""
    return set(getSubcategories(category))


def retreiveSubcategoriesFromLocation(category):
    """Get subcategories from file, or generate them from scratch."""
    subCats = []
    fileName = "{category}_subcats.txt".format(category=category)
    try:
        subCatFile = open(fileName, 'r')
        print_debug("Reading from {filename}".format(filename=fileName))
        for count, line in enumerate(subCatFile):
            subCats.append(line.replace("\n", ""))
        subCatFile.close()
    except IOError as ioError:
        print_debug("{fileName} does not exist. Building from " +
                    " network".format(fileName=fileName)
                    )
        subCats = subcategoriesWithoutDuplicates(category)
    return subCats


def checkPageSimilarity(page, subcategories):
    """Check the similarity of page to a list of subcategories.

    Verify if page truly is a subpage of a category.
    """
    global similarityVal
    pageCats = wrappedRequest(page, mode="Pagecats")
    points = 0.0
    # For every supercategory of page, if it is also in subcategories
    # the page is more likely to be a true subpage.
    for cat in pageCats:
        title = cat['title']
        if(title in subcategories):
            points += 1.0
    score = points/len(pageCats)
    if(score >= similarityVal):
        return True
    return False


def randomPage(category, save, regen, check):
    """Generate a random page from a category."""
    global DEBUGGING
    subCats = []
    read = True
    if(not regen):
        subCats = retreiveSubcategoriesFromLocation(category)
    if(regen or (not read)):
        print_debug("Rebuilding {category}".format(category=category))
        subCats = subcategoriesWithoutDuplicates(category)
    if(save or regen):
        saveArray(category, subCats)
    randomPage = None
    validRandomPage = True
    while(not randomPage or not validRandomPage):
        try:
            cat = random.sample(subCats, 1)[0]
            print_debug("Chose category {cat}".format(cat=cat))
            pages = wrappedRequest(cat, mode="Subpage")
            randomPage = random.choice(pages)['title']
            if(check):
                print_debug("Checking " + randomPage)
                validRandomPage = checkPageSimilarity(randomPage, subCats)
        except IndexError as a:
            print_debug("{cat} has no pages. Retrying".format(cat=cat))
    return randomPage


if(__name__ == "__main__"):
    parser = argparse.ArgumentParser(description='Get a random page from a ' +
                                     'wikipedia category')
    parser.add_argument('category', help="The category you wish to get a " +
                        "page from."
                        )
    parser.add_argument('--tree_depth',
                        nargs='?',
                        type=int,
                        default=4,
                        help="How far down to traverse the subcategory tree"
                        )
    parser.add_argument('--similarity',
                        nargs='?',
                        type=float,
                        default=.5,
                        help="What percent of page categories need to be " +
                        "in subcategory array. Must be used with -c/--check")
    parser.add_argument("-s",
                        "--save",
                        action="store_true",
                        help="Save subcategories to a file for quick re-runs"
                        )
    parser.add_argument("-r",
                        "--regen",
                        action="store_true",
                        help="Regenerate the subcategory file"
                        )
    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        help="Print debug lines"
                        )
    parser.add_argument("-c",
                        "--check",
                        action="store_true",
                        help="After finding page check to see that it truly " +
                        "fits in category"
                        )
    args = parser.parse_args()
    DEBUGGING = args.verbose
    max_depth = args.tree_depth
    similarityVal = args.similarity
    if(args.save and DEBUGGING):
        print("Saving!")
    if(args.regen and DEBUGGING):
        print("Regenerating!")
    print("https://en.wikipedia.org/wiki/" + randomPage("Category:" +
                                                        args.category,
                                                        save=args.save,
                                                        regen=args.regen,
                                                        check=args.check
                                                        )
          )
