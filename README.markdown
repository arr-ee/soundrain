Dependencies
------------

- Python >= 2.7 or argparse module
- urlgrabber >= 3.9.0
- lxml

Usage
-----
> soundrain.py [-h] [-a] [-o PATH] [-c] URL [URL ...]
> 
>  -h, --help            show this help message and exit  
>  -a, --all             download tracks from all pages of specified urls  
>  -o PATH, --output PATH save files to specified directory instead of current working directory  
>  -c, --create-dir      create sub-directories for every url given

###Examples

> `soundrain.py http://soundcloud.com/arr-ee`  
> Download last 10 user's tracks, save to current working dir

> `soundrain.py "http://soundcloud.com/arr-ee/favorites?page=5" http://soundcloud.com/somekindofawesome -c -o ~/Music`  
> Download tracks from 5th page of arr-ee's favorites and save them to ~/Music/arr-ee/favorites, then last 10 tracks from somekindofawesome, save to ~/Music/somekindofawesome
