#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
from json import loads
from lxml import html, etree
from htmlentitydefs import name2codepoint

from urlgrabber.grabber import URLGrabber
import urlgrabber.progress as progress

# TODO
# Concurrent download AND page retrieving
# Page caching
# User-defined file naming scheme
# Multi-download-aware progress indicator

# Some common xpath expressions and regexes
_next_page = etree.XPath("//div[@class='pagination']\
                                 /a[@class='next_page']")
_tracks = etree.XPath("//div[@data-sc-track]/script[1]")
_sc = re.compile("http://(?:www\.)?soundcloud.com/([\w-]+)(?:/.*)?", re.I)
_page = re.compile("page=(\d?)", re.I)
_sanitize = re.compile("[|/\\?%*:><]")

# Exceptions
class WrongURL(Exception):
    def __init__(self, url):
        self.url = url

    def __str__(self):
        return repr(self.url)


class WrongPage(Exception):
    def __init__(self, code):
        self.code = code

    def __str__(self):
        return repr(self.code)

# Handy methods

def unhtml(string):
    """
    Converts all html entities in string to human-readble chars, e.g.
    &amp; -> &
    Thanks to http://wiki.python.org/moin/EscapingHtml for the func.
    After that, it will make it ascii-decodable while preserving fancy chars
    like &raquo; and stuff.
    """
    return re.sub('&(%s);' % '|'.join(name2codepoint),
                  lambda m: unichr(name2codepoint[m.group(1)]),
                  string).encode('utf-8', 'xmlcharrefreplace')

# Setting up the grabber

grabber = URLGrabber(progress_obj=progress.text_progress_meter())
urlopen = grabber.urlopen

class Page(object):
    def __init__(self, url):
        match = _sc.match(url)
        if match is not None:
            self.url = url
        else:
            raise WrongURL(url)
        page = urlopen(url)
        if page.http_code != 200:
            raise WrongPage(page.http_code)
        self.tree = html.fromstring(page.read())
        self.tracks = []
        self._get_tracks()

    def last_page(self):
        """Returns number of subpages of this page, i.e. on "tracks" page there
        are 10 tracks per subpage, and if we need all tracks, we must iterate
        through all of them (by adding "?page=pagenum" to the URL).
        """
        try:
            last_page_lnk = _next_page(self.tree)[0].getprevious()
            pages_no = int(last_page_lnk.text)
        except IndexError:
            pages_no = 1
        return pages_no

    def _get_tracks(self):
        """Populates tracks property with Track objects made of page's data"""
        for track in _tracks(self.tree):
            parsed_info = loads(re.search("(\(.*\))",
                                track.text).group(1)[1:-1])  # cuttin slack
            self.tracks.append(Track(data=parsed_info))


class Track(dict):
    def __init__(self, data):
        try:
            if _sc.match(data):
                self.update(Page(data).tracks[0])
            else:
                raise Exception("No data!")
        except TypeError:
            self.update(data)
        self["title_orig"] = self["title"]
        self["title"] = _sanitize.sub("", unhtml(self["title_orig"]))

    def download(self):
        track = urlopen(str(self["streamUrl"]))  # de-unicode for pycurl
        return track


if __name__ == '__main__':
    import argparse
    import urlparse

    def sc_link(link):
        if not _sc.match(link):
            raise argparse.ArgumentTypeError('\'%s\' is not a valid ' \
                                             'Soundcloud link.' % link)
        return link

    def path(path):
        path = os.path.abspath(path)
        if not os.path.exists(path):
            raise argparse.ArgumentTypeError('Directory %s does not exist!' %
                                            path)
        return path

    def url_builder(full_path, page_no, all_pages=False):
        url = "http://soundcloud.com%s" % full_path
        page = Page(url)
        last_page = page.last_page()
        urls = []
        if all_pages:
            for i in xrange(1, last_page+1, 1):
                urls.append("%s?page=%d" % (url, i))
        else:
            urls.append("%s?page=%d" % (url, page_no))
        return urls

    def create_dirs(full_path, cwd):
        dirparts = full_path.split('/')
        d = os.path.join(cwd, *dirparts)
        if not os.path.isdir(d):
            os.makedirs(d)
        return d

    parser = argparse.ArgumentParser(description='Grabs sounds')
    parser.add_argument("-a", "--all", action='store_true', default=False,
                        help="""download tracks from all pages of specified
                        urls""")
    parser.add_argument("-o", "--output", metavar='PATH', default=os.getcwdu(),
                        type=path, help="""save files to specified
                        directory instead of current working directory""")
    parser.add_argument("-c", "--create-dir", action='store_true',
                        default=False, help="""create sub-directories for every
                        url given""")
    parser.add_argument("urls", nargs='+', metavar='URL', type=sc_link)
    args = parser.parse_args()

    targets = []
    output_path = args.output

    print args

    for url in args.urls:
        parsed_url = urlparse.urlparse(str(url))
        req_page = re.search(".*page=(\d+).*", parsed_url.query)
        page_count = int(req_page.group(1)) if req_page else 1
        targets.append({"path":parsed_url.path, "pages":page_count})

    for i in targets:
        i["targets"] = url_builder(i["path"], i["pages"], args.all)
        if args.create_dir:
            i["output"] = create_dirs(i["path"], args.output)
        else:
            i["output"] = args.output

    for link in targets:
        for target in link["targets"]:
            all_songs = Page(target).tracks
            for song in all_songs:
                fd = open(os.path.join(link["output"], song["title"] + ".mp3"), "w")
                fd.write(song.download().read())
                fd.close()
