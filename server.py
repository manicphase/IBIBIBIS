import json
import collections
import sqlite3
import urllib2
import os.path
import subprocess
import updateipns
from flask import Flask, Response, request

conn = sqlite3.connect('imagehashes (another copy).db')

c = conn.cursor()

app = Flask(__name__)

db = "4chan.wg.archive.db"

update = raw_input("do you want to search for an up to date database? Y/n ")

if "yY ".find(update) > -1:
    updateipns.update_db(db)

@app.route("/")
def get_stuff(filter=None, filetype=None, start=0):
    try:
        start = int(request.args.get('start'))
        print start
    except:
        pass
    try:
        filter = request.args.get('filter').split(",")
        if len(filter[0]) == 0:
            filter = None
    except:
        pass
    hashes = filter
    conn = sqlite3.connect(db)
    c = conn.cursor()
    h = """
        <style type="text/css">
        .tile {
            float: left;
            width: 125;
            height: 200;
            overflow: hidden;
        }
        .filtered {
            background: green;
        }

        .image-frame {
            height: 140;
            overflow: hidden;
        }
        .full-width {
            width: 100px;
            overflow: hidden;
        }
        .image {
            float: left;
            width: 100%;
            overflow: hidden;

        }
        </style>"""
    print filter
    if filter is None:
        if filetype is not None:
            c.execute("SELECT * FROM images WHERE image_url LIKE '%{}'".format(filetype))
        else:
            c.execute("SELECT * FROM images ORDER BY count DESC")
        result = c.fetchall()[1:][start:start+120]
        print len(result)
    else:
        hashes = filter
        comp = []
        image_dict = {}
        for search_hash in hashes:
            c.execute("SELECT * FROM images WHERE ipfs_image_url=?", (search_hash,))
            pages = c.fetchall()
            pages = json.loads(pages[0][4])

            for item in pages:
                try:
                    c.execute("SELECT * FROM pages WHERE page_hash=?", (item,))
                    results = c.fetchall()[0]
                    images = json.loads(results[1])
                    previews = json.loads(results[4])
                    for i in range(len(images)):
                        image_dict[images[i]] = previews[i]
                    comp = comp+images
                except:
                    print "broken page reference"
        counter=collections.Counter(comp)

        print len(counter.values())
        print len(comp)

        counter = counter.most_common()
        print "%s results to present" % len(counter)
        result = []
        for t_item in counter[start:start+120]:
            item = t_item[0]
            try:
                #c.execute("SELECT ipfs_thumb_url FROM images WHERE ipfs_image_url=?", (item,))
                #preview = c.fetchall()[0][0]
                preview = image_dict[item]
                #h = h + "<a href=/ipfs/"+item+" target=_blank>"
                #h = h + "<img src=/ipfs/"+preview+" /></a>\n"
                result.append([preview,item,0,0,0,t_item[1]])
            except:
                print "FAILED"
                pass

        print "%s results to present" % len(result)

    if hashes is None:
        hashes = []
    for item in result:
        hs = []
        hs = hs + hashes
        if item[1] in hs:
            hs.remove(item[1])
            filter_string = ",".join(hs)
            if len(hs) > 0:
                filter_line = "<a href=/?filter="+filter_string+" >Remove from filter</a><br>"
            else:
                filter_line = "<a href=/ >Remove from filter</a><br>"
            class_line = "<div class='tile filtered'>"

        else:
            hs.append(item[1])
            filter_string = ",".join(hs)
            filter_line = "<a href=/?filter="+filter_string+" >Add to filter</a><br>"
            class_line = "<div class='tile'>"

        h = h + class_line + "relevance: " + str(int(item[5]))
        h = h + "<div class=image-frame><a href=/view/"+item[1]+" target=_blank alt='text' >"
        h = h + "<img class=image src=/ipfs/"+item[0]+" alt='text' /></a></div>\n"
        h = h + filter_line
        h = h + "</div>"
    conn.close()
    h = h + "<br><a href = /?start=%s&filter=%s >NEXT</a>" % (start+120, ",".join(hashes))
    return h

@app.route("/view/<filehash>")
def view(filehash):
    h = """
            <style>
            .full-width {
                width: 100%%;
                overflow: hidden;
            }
            .image {
                float: left;
                width: 100%%;
                overflow: hidden;

            }
            </style>
            <div class=full-width>
                <img class=image src=/ipfs/%s />
            </div>""" % filehash
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("SELECT original_page_hashes FROM images WHERE ipfs_image_url=?", (filehash,))
    pages = json.loads(c.fetchone()[0])
    for page in pages:
        try:
            c.execute("SELECT * FROM pages WHERE page_hash=?", (page,))
            data = c.fetchone()
            h = h + "<br>" + "<a href=/ipfs/"+data[0]+">"+data[2]+"</a>"
        except:
            pass
    return h

@app.route("/ipfs/<filehash>")
def ipfs(filehash):
    r = urllib2.urlopen("http://localhost:8080/ipfs/"+filehash)
    content_type = r.info().getheader('Content-Type')
    response = Response(r.read())
    response.headers["Content-Type"] = content_type
    return response


@app.route("/filetype/<filetype>")
def filter_filetype(filetype):
    return get_stuff(filetype=filetype)


if __name__ == '__main__':
    app.run(host="0.0.0.0", threaded=True, debug=True)
