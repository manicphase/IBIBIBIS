from BeautifulSoup import BeautifulSoup as BS
import urllib2
import subprocess
import json
import collections
import sqlite3
import time
import updateipns
import traceback
import time


#board = "wg"
board = raw_input("Which board do you want to scrape? (defaults to wg)")
if board == "":
    board = "wg"

update = raw_input("Would you like to find an existing backup of this board? (Recommended) Y/n")
if "yY ".find(update) > -1:
    updateipns.update_db("4chan.%s.archive.db" % board)

store_db = raw_input("Do you want to store your database once scraping has finished, to allow others to use it? (overwrites ipns) Y/n")
if "yY ".find(store_db) > -1:
    store_db = True
else:
    store_db = False

store_db_p = raw_input("Do you want to store your database periodically, to allow others to use it? (overwrites ipns) Y/n")
if "yY ".find(store_db_p) > -1:
    store_db_p = True
else:
    store_db_p = False

def create_db(board):
    db = "4chan.%s.archive.db" % board
    conn = sqlite3.connect(db)
    c = conn.cursor()
    try:
        c.execute('''CREATE TABLE images
                 (ipfs_thumb_url text,
                 ipfs_image_url text,
                 image_url text,
                 thumb_url text,
                 original_page_hashes text,
                 count real)''')

        c.execute('''CREATE TABLE pages
                     (page_hash text,
                     image_hash text,
                     page_title text,
                     page_url text,
                     preview_hashes text)''')

    except:
        pass

    conn.close()

#Stolen from http://stackoverflow.com/questions/11331071/get-class-name-and-contents-using-beautiful-soup
def match_class(target):
    target = target.split()
    def do_match(tag):
        try:
            classes = dict(tag.attrs)["class"]
        except KeyError:
            classes = ""
        classes = classes.split()
        return all(c in classes for c in target)
    return do_match


def scrape_page(page_url, db):
    result = {"original_url": page_url, "images":[], "previews":[]}
    def store_file(url): # TODO: make this a thread!
        f = urllib2.urlopen(url).read()
        with open("image","wb") as im:
            im.write(f)
        image_hash = subprocess.check_output(["ipfs", "add", "image"]).split()[1]
        return image_hash

    page_html = urllib2.urlopen(page_url).read()

    soup = BS(page_html)

    page_title = soup.title.string
    conn = sqlite3.connect(db)
    c = conn.cursor()
    result["page_title"] = page_title
    c.execute("SELECT page_title from pages")
    titles = [t[0] for t in c.fetchall()]
    conn.close()

    htmlpage = page_html.decode("utf8")

    images = soup.findAll(match_class("fileThumb"))

    i = 0

    for item in images:
        i = i + 1
        image_url = dict(item.attrs)["href"]
        thumb_url = dict(item.find("img").attrs)["src"]
        try:
            item_dict = {"image_url":"http:"+image_url,
                     "thumb_url":"http:"+thumb_url,
                     "ipfs_image_url":store_file("http:"+image_url),
                     "ipfs_thumb_url":store_file("http:"+thumb_url),
                     "md5":dict(item.find("img").attrs)["data-md5"]}
            htmlpage = htmlpage.replace(image_url, "/ipfs/"+item_dict["ipfs_image_url"])
            htmlpage = htmlpage.replace(thumb_url, "/ipfs/"+item_dict["ipfs_thumb_url"])
            result["images"].append(item_dict)
            print "%s/%s mirrored %s to %s" % (i, len(images), image_url, item_dict["ipfs_image_url"])

        except:
            print "failed to mirror "
            pass

    open("ipfsd.html","wb").write(htmlpage.encode("utf8"))
    page_hash = subprocess.check_output(["ipfs", "add", "ipfsd.html"]).split()[1]
    result_page = "http://127.0.0.1:8080/ipfs/"+page_hash
    result["page_hash"] = page_hash

    return result

def add_results_to_db(result, db, page_url):
    conn = sqlite3.connect(db)
    c = conn.cursor()
    success = True
    try:
        previews = []
        for item in result["images"]:
            c.execute("SELECT * FROM images WHERE ipfs_image_url=?", (item["ipfs_image_url"],))
            rows = c.fetchall()
            if len(rows) == 0:
                previews.append(item["ipfs_thumb_url"])
                columns = ', '.join(item.keys())
                placeholders = ', '.join('?' * len(item))
                query = (item["ipfs_thumb_url"],
                        item["ipfs_image_url"],
                        item["image_url"],
                        item["thumb_url"],
                        json.dumps([result["page_hash"]]),
                        1)
                c.execute('INSERT INTO images VALUES (?,?,?,?,?,?)', query)
                print "added row to db"
            else:
                row = rows[0]
                count = row[5]+1
                pages = json.loads(row[4])
                if result["page_hash"] not in pages:
                    pages.append(result["page_hash"])
                    c.execute("UPDATE images SET original_page_hashes=?, count=? WHERE ipfs_image_url=?", (json.dumps(pages),
                              count, item["ipfs_image_url"]))
                    print "modified row"
                else:
                    print "entry already added for this page"
        images = [item["ipfs_image_url"] for item in result["images"]]
        previews = [item["ipfs_thumb_url"] for item in result["images"]]
        c.execute('INSERT INTO pages VALUES (?,?,?,?,?)',(result["page_hash"], json.dumps(images),
                                                          result["page_title"], page_url, json.dumps(previews)))
    except Exception as e:
        print e
        print "updating db failed"
        success = False

    conn.commit()
    conn.close()
    return success

def make_page_url_dict(db):
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("SELECT page_url FROM pages")
    stored_titles = [title[0] for title in c.fetchall()]
    c.close()
    return stored_titles

def main(board):
    db = "4chan.%s.archive.db" % board
    stored_titles = [t for t in make_page_url_dict(db) if t != "undefined"]
    archive_url = "http://boards.4chan.org/%s/archive" % board
    archive_soup = BS(urllib2.urlopen(archive_url).read())
    rows = archive_soup.findAll(match_class("quotelink"))
    rows.reverse()
    urls = [dict(row.attrs)["href"] for row in rows]
    to_scrape = [url for url in urls if url not in stored_titles]
    to_ignore = [url for url in urls if url in stored_titles]
    print "%s pages found. %s already mirrored. Scraping %s" % (len(rows), len(to_ignore), len(to_scrape))
    i = 0
    last_stored = time.time()
    #updateipns.update_ipns(db)
    for row in to_scrape:
        if (last_stored + 3600) > time.time() :
            # store db once an hour
            updateipns.update_ipns(db)
            last_stored = time.time()
        i = i + 1
        print "scraping page %s of %s" % (i, len(to_scrape))
        time.sleep(0.1)
        link = "http://boards.4chan.org"+row
        try:
            result = scrape_page(link, db)
            success = add_results_to_db(result, db, row)
            if success:
                print "Added page to db"
        except:
            print "something went wrong, oh well"
    if store_db:
        updateipns.update_ipns(db)


main(board)
