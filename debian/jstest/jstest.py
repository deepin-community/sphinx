#!/usr/bin/python3
# encoding=UTF-8

# Copyright © 2011 Jakub Wilk <jwilk@debian.org>
#           © 2013-2022 Dmitry Shachnev <mitya57@debian.org>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import unittest

from PyQt6.QtCore import QTimer, QUrl, QUrlQuery
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView

default_time_limit = 40_000  # msecs
timer_step = 1_000  # msecs

# HTTP browser
# ============

class Page(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceId):
        print(f"[{level}] {sourceId}:{lineNumber}: {message}")


class View(QWebEngineView):
    def __init__(self):
        super().__init__()
        self.result = None
        self._page = Page(parent=self)
        self._page.loadFinished.connect(self.onLoadFinished)
        self.setPage(self._page)
        self._timer = None
        self._time_limit = default_time_limit

    def setResult(self, result):
        self.result = result

    def onLoadFinished(self):
        self._timer = QTimer(parent=self)
        self._timer.timeout.connect(self.runJavaScript)
        self._timer.start(timer_step)

    def runJavaScript(self):
        if self._time_limit <= 0:
            raise TimeoutError
        script = """
        result = {
            n_results: $('#search-results > p:first').text().match(/found (\d+) page/)[1],
            n_links: $('#search-results a').length,
            n_highlights: $('#search-results .highlighted').length,
        };
        result
        """
        self._page.runJavaScript(script, self.setResult)
        self._time_limit -= timer_step

    def waitForResult(self):
        app = QApplication.instance()
        while self.result is None:
            app.processEvents()
        self._timer.stop()


# Actual tests
# ============

def test_html(result, options):

    class TestCase(unittest.TestCase):

        if options.n_results is not None:
            def test_n_results(self):
                n_results = int(result['n_results'])
                self.assertEqual(n_results, options.n_results)

        if options.n_links is not None:
            def test_n_links(self):
                n_links = int(result['n_links'])
                self.assertEqual(n_links, options.n_links)

        if options.n_highlights is not None:
            def test_n_highlights(self):
                n_highlights = int(result['n_highlights'])
                self.assertEqual(n_highlights, options.n_highlights)

    TestCase.__name__ = 'TestCase(%r)' % options.search_term

    suite = unittest.TestLoader().loadTestsFromTestCase(TestCase)
    return unittest.TextTestRunner(verbosity=2).run(suite)

def test_directory(directory, options, time_limit=default_time_limit):
    url = QUrl.fromLocalFile(f'{directory}/search.html')
    query = QUrlQuery()
    query.addQueryItem('q', options.search_term)
    url.setQuery(query)
    view = View()
    view.load(url)
    view.show()
    view.waitForResult()
    return test_html(view.result, options)

# vim:ts=4 sw=4 et
