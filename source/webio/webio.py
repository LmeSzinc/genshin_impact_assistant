import logging
import sys
import threading
import time

import pywebio.session

from source import webio
from source.webio import log_handler
from source.webio.pages import *

status = True


def main():
    webio.manager.reg_page('Main', MainPage())
    webio.manager.reg_page('Setting', SettingPage())
    webio.manager.load_page('Main')


'''    handler = log_handler.WebioHandler()

    logging.getLogger().addHandler(handler)'''

'''    t = threading.Thread(target=session_check_thread, daemon=False)
    pywebio.session.register_thread(t)
    t.start()
    threading.Thread(target=session_check_thread_t, daemon=False).start()


def session_check_thread_t():
    global status
    while True:
        if not status:
            sys.exit()
        status = False
        time.sleep(0.3)


def session_check_thread():
    global status
    while True:
        pywebio.session.get_current_session()
        status = True
        time.sleep(0.1)'''

if __name__ == '__main__':
    platform.tornado.start_server(main, auto_open_webbrowser=True, debug=True)
