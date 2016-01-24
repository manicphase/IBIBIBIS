import subprocess
import json
import urllib2
import time
import re

def safe_ipfs(string):
    if re.match("Qm[a-zA-Z0-9]{44}", string) and len(string) == 44:
        return string
    else:
        print "Invalid ipfs hash: {}".format(string)
        return False

def update_ipns(archive):
    # TODO: secure this
    db_hash = subprocess.check_output(["ipfs", "add", archive]).split()[1]
    with open(archive) as b:
        filesize = len(b.read())
    archive_details = {"timestamp": int(time.time()),
                       "ipfs_link": db_hash,
                       "filesize": filesize}
    try:
        archives = json.loads(open("archives.json").read())
        archives["archives"][archive] = archive_details
    except:
        archives = {"archives": {archive: archive_details}}

    open("archives.json", "w").write(json.dumps(archives))

    json_hash = subprocess.check_output(["ipfs", "add", "archives.json"]).split()[1]
    published = subprocess.check_output(["ipfs", "name", "publish", json_hash]).split()[2][:-1]
    print "published db to %s" % published


def update_db(db):
    print "Searching for database updates"
    trusted_nodes = json.loads(open("trusted_nodes.json").read())
    request_string = ""
    try:
        with open(archive) as b:
            largest_db = len(b.read())
    except:
        largest_db = 0
    for node in trusted_nodes:
        ipns_json = json.loads(urllib2.urlopen("http://127.0.0.1:8080/ipns/"+safe_ipfs(trusted_nodes[node])).read())
        if ipns_json["archives"][db]["filesize"] > largest_db:
            request_string = ipns_json["archives"][db]["ipfs_link"]
    print "Found file '%s' as update for '%s'. Downloading..." % (request_string, db)

    # just in case someone tries to rm -rf
    if safe_ipfs(request_string):
        subprocess.check_output(["ipfs", "get", "-o="+db, request_string])
