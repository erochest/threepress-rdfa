#!/usr/bin/env python
import sys
import spider

# Defaults
MAX_NUMBER_OF_PAGES_TO_CRAWL = 200
MAX_NUMBER_OF_LINKS_TO_FOLLOW = 5

def get_urls(uri, output):
    print "Spidering %s, getting %d maximum pages and following %d links deep." % (uri, MAX_NUMBER_OF_PAGES_TO_CRAWL, MAX_NUMBER_OF_LINKS_TO_FOLLOW)
    urls = spider.weburls(uri, 
                          width=MAX_NUMBER_OF_PAGES_TO_CRAWL,
                          depth=MAX_NUMBER_OF_LINKS_TO_FOLLOW)

    spider.urls = urls
    print "Generating report..."
    spider.webreport(output)
    print "Report of URLs written to %s" % output

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print 'Usage: urls.py http://example.com/ file-for-results.txt'
        sys.exit()
    get_urls(sys.argv[1], sys.argv[2]) 

