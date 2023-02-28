import requests
from html.parser import HTMLParser

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko)'
                  'Chrome/52.0.2743.116 Safari/537.36'
}


class SrcPageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.flag = False
        self.script = ""

    def handle_starttag(self, tag, attrs):
        if tag == 'pre':
            self.flag = True

    def handle_data(self, data):
        if self.flag:
            self.script += data


class BasicParser(HTMLParser):
    def __init__(self, target: str):
        super().__init__()
        self.script = ""
        self.entries = []
        self.target = target
        self.isSrc = False

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            for key, value in attrs:
                if key == 'src':
                    if value[:4] == 'http':
                        url = value
                    elif self.target[-4:] == '.htm' or self.target[-5:] == ".html":
                        url = '/'.join(self.target.split('/')[:-1] + [value])
                    else:
                        url = self.target + '/' + value
                    page = requests.get(url, headers=headers)
                    self.script += page.text
            self.isSrc = True
        for key, value in attrs:
            if key == 'onclick':
                self.entries.append(('onclick', value))
            if key == 'onload':
                self.entries.append(('onload', value))

    def handle_data(self, data):
        if self.isSrc:
            self.script += data
            self.isSrc = False


link = "https://soaringe.github.io"


def analyze(entries):
    page = requests.get(link, headers=headers)
    parser = BasicParser(link)
    parser.feed(page.text)
    for pair in parser.entries:
        entries.append((pair[0], pair[1]))
    return parser.script


def fetch(url):
    global link
    link = url
    entries = []
    try:
        script = analyze(entries)
    except:
        script = analyze(entries)
    return script, entries
