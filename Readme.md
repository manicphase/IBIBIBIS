#IBIBIBIS
(IPFS backed image board image based image search)

Works great on raspberry PI!

To use this software

1. install IPFS and run the daemon
2. download this project
3. in terminal, navigate to this folder and type "pip install -r requirements.txt"
4. run server by typing "python server.py", follow the instructions then point your browser at 127.0.0.1:5000
5. to scrape a board type "python scraper.py" and follow the instructions
6. pass IPNS addresses to eachother to access eachother's archives.
7. add eachothers addresses to trusted_nodes.json

The current database is less than 9MB and has details of around 25000 files archived from the wallpaper board on 4chan.
Files are ordered by the amount of times they have been posted. Click "add to filter" on images to re-order them in terms of
relevance of the images in the filter. The more threads an image shares with the filter the higher the priority.

This program will start off loading slow, but will speed up.


![screenshot](https://ipfs.pics/ipfs/QmdUngqEpf3DMyBLx7NX1RV2ztDNkB7ALBCEwHDdX7YouU)
