import sys, os, json
from loguru import logger
import json
import os
import sys

from loguru import logger

# 配置基本目录
root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
source_path = root_path + '\\source'
if sys.path[0] != root_path:
    sys.path.insert(0, root_path)
if sys.path[1] != source_path:
    sys.path.insert(1, source_path)


# 加载json
def loadjson(json_name='config.json'):
    # try:
    f = open('config/' + json_name, 'r')
    content = f.read()
    a = json.loads(content)
    f.close()
    return a


global config_json
config_json = loadjson("config.json")

# 设置debug
DEBUG_MODE = False
DEBUG_MODE = config_json["DEBUG"]

# 设置env path
env_folder_path = config_json["env_floder_path"]
env_path = os.path.abspath(os.path.join(root_path, env_folder_path))
if True:
    if sys.path[2] != env_path:
        sys.path.insert(2, env_path)

# 校验目录


# 配置logger
logger.remove(handler_id=None)
logger.add('runtime.log', level="TRACE", backtrace=True)
if DEBUG_MODE:
    logger.add(sys.stdout, level="TRACE", backtrace=True)
else:
    logger.add(sys.stdout, level="INFO", backtrace=True)

if not os.path.exists(root_path):
    logger.error("目录不存在：" + root_path + " 请检查")
if not os.path.exists(source_path):
    logger.error("目录不存在：" + source_path + " 请检查")
if not os.path.exists(env_path):
    logger.error("目录不存在：" + env_path + " 请检查")

import ctypes, pickle


# 检查管理员
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


if not is_admin():
    # print('try to get administrator')
    # ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
    # print('administrator have been obtained')
    logger.error("请用管理员权限运行")


def isint(x):
    try:
        a = int(x)
    except ValueError:
        return False
    else:
        return True


def savejson(x, json_name='config.json'):
    b = json.dumps(x, sort_keys=True, indent=4)
    f2 = open(json_name, 'w')
    f2.write(b)
    f2.close()


def loadfileP(filename):
    with open('wordlist//' + filename + '.wl', 'rb') as fp:
        list1 = pickle.load(fp)
    return list1


def savefileP(filename, item):
    with open('wordlist//' + filename + '.wl', 'w+b') as fp:  # 把 t 对象存到文件中
        pickle.dump(item, fp)


def reflash_config():
    global config_json
    configjson = loadjson("config.json")

# if __name__=='__main__':

#     print(1/0)
#     pass
