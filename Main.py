import json
import os
import random
from hashlib import md5

import requests
from requests.adapters import HTTPAdapter

from utils import AES, UTC as pytz, MessagePush

requests.adapters.DEFAULT_RETRIES = 10
pwd = os.path.dirname(os.path.abspath(__file__)) + os.sep

s = requests.session()
s.mount('http://', HTTPAdapter(max_retries=10))
s.mount('https://', HTTPAdapter(max_retries=10))
s.keep_alive = False

headers = {
    "os": "android",
    "phone": "Xiaomi|Mi 12|12",
    "appVersion": "40",
    "Sign": "Sign",
    "cl_ip": "192.168.1.3",
    "User-Agent": "okhttp/3.14.9",
    "Content-Type": "application/json;charset=utf-8"
}


def getMd5(text: str):
    return md5(text.encode('utf-8')).hexdigest()


def parseUserInfo():
    allUser = ''
    if os.path.exists(pwd + "user.json"):
        print('找到配置文件，将从配置文件加载信息！')
        with open(pwd + "user.json", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines:
                allUser = allUser + line + '\n'
    else:
        return json.loads(os.environ.get("USERS", ""))
    return json.loads(allUser)


def save(user, uid, token):
    url = 'http://sxbaapp.zcj.jyt.henan.gov.cn/interface/clockindaily20220827.ashx'

    longitude = user["longitude"]
    latitude = user["latitude"]
    if user["randomLocation"]:
        longitude = longitude[0:len(longitude) - 1] + str(random.randint(0, 10))
        latitude = latitude[0:len(latitude) - 1] + str(random.randint(0, 10))

    data = {
        "dtype": 1,
        "uid": uid,
        "address": user["address"],
        "phonetype": user["deviceType"],
        "probability": -1,
        "longitude": longitude,
        "latitude": latitude
    }
    headers["Sign"] = getMd5(json.dumps(data) + token)
    res = requests.post(url, headers=headers, data=json.dumps(data))

    if res.json()["code"] == 1001:
        return True, res.json()["msg"]
    return False, res.json()["msg"]


def getToken():
    url = 'http://sxbaapp.zcj.jyt.henan.gov.cn/interface/token.ashx'
    res = requests.post(url, headers=headers)
    if res.json()["code"] == 1001:
        return True, res.json()["data"]["token"]
    return False, res.json()["msg"]


def login(user, token):
    password = getMd5(user["password"])
    deviceId = user["deviceId"]

    data = {
        "phone": user["phone"],
        "password": password,
        "dtype": 6,
        "dToken": deviceId
    }
    headers["Sign"] = getMd5((json.dumps(data) + token))
    url = 'http://sxbaapp.zcj.jyt.henan.gov.cn/interface/relog.ashx'
    res = requests.post(url, headers=headers, data=json.dumps(data))
    return res.json()


def prepareSign(user):
    if not user["enable"]:
        print(user['alias'], '未启用打卡，即将跳过')
        return

    print('已加载用户', user['alias'], '即将开始打卡')

    headers["phone"] = user["deviceType"]

    res, token = getToken()
    if not res:
        print('用户', user['alias'], '获取Token失败')
        MessagePush.pushMessage('职校家园打卡失败！', '职校家园打卡获取Token失败，错误原因：' + token, user["pushKey"])
        return

    loginResp = login(user, token)

    if loginResp["code"] != 1001:
        print('用户', user['alias'], '登录账号失败，错误原因：', loginResp["msg"])
        MessagePush.pushMessage('职校家园登录失败！', '职校家园登录失败，错误原因：' + loginResp["msg"], user["pushKey"])
        return

    uid = loginResp["data"]["uid"]
    resp, msg = save(user, uid, token)

    if resp:
        print(user["alias"], '打卡成功！')
        MessagePush.pushMessage('职校家园打卡成功！', '用户：' + user["phone"] + '职校家园打卡成功!', user["pushKey"])
        return
    print(user["alias"], "打卡失败")
    MessagePush.pushMessage('职校家园打卡失败！', '用户：' + user["phone"] + '职校家园打卡失败!原因:' + msg,
                            user["pushKey"])


if __name__ == '__main__':
    users = parseUserInfo()

    for user in users:
        try:
            prepareSign(user)
        except Exception as e:
            print('职校家园打卡失败，错误原因：' + str(e))
            MessagePush.pushMessage('职校家园打卡失败',
                                    '职校家园打卡失败,' +
                                    '具体错误信息：' + str(e)
                                    , user["pushKey"])
