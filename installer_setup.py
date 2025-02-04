from source.util import *
import source.config
import os


def unzip():
    if not os.path.exists(os.path.join('source', 'cvAutoTrack_7.2.3', 'CVAUTOTRACK.dll')):
        import zipfile
        with zipfile.ZipFile(os.path.join('source', 'cvAutoTrack_7.2.3', 'CVAUTOTRACK.zip')) as f:
            f.extractall(os.path.join('source', 'cvAutoTrack_7.2.3'))
        return 'unzip successfully'
    return 'no operation required'


def auto_setup():
    print(unzip())
    print(source.config.template_translator())
    print(source.config.template_translator_tastic())

if __name__ == '__main__':
    auto_setup()