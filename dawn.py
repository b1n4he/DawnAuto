import ast
import json
import re

import requests
import random
import time
import datetime
import urllib3
from PIL import Image
import base64
from io import BytesIO
import ddddocr
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from loguru import logger

KeepAliveURL = "https://www.aeropres.in/chromeapi/dawn/v1/userreward/keepalive"
GetPointURL = "https://www.aeropres.in/api/atom/v1/userreferral/getpoint"
LoginURL = "https://www.aeropres.in//chromeapi/dawn/v1/user/login/v2"
PuzzleID = "https://www.aeropres.in/chromeapi/dawn/v1/puzzle/get-puzzle"

# 创建一个请求会话
session = requests.Session()

# 设置通用请求头
headers = {
    "Content-Type": "application/json",
    "Origin": "chrome-extension://fpdkjdnhkakefebpekbdhillbhonfjjp",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Priority": "u=1, i",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
}


def GetPuzzleID():
    r = session.get(PuzzleID, headers=headers,verify=False).json()
    puzzid = r['puzzle_id']
    return puzzid

# 检查验证码算式
def IsValidExpression(expression):
    # 检查表达式是否为6位的字母和数字组合
    pattern = r'^[A-Za-z0-9]{6}$'
    if re.match(pattern, expression):
        return True
    return False

# 验证码识别
def RemixCaptacha(base64_image):
    # 将Base64字符串解码为二进制数据
    image_data = base64.b64decode(base64_image)
    # 使用BytesIO将二进制数据转换为一个可读的文件对象
    image = Image.open(BytesIO(image_data))
    #####################################
    # 将图像转换为 RGB 模式（如果不是的话）
    image = image.convert('RGB')
    # 创建一个新的图像（白色背景）
    new_image = Image.new('RGB', image.size, 'white')
    # 获取图像的宽度和高度
    width, height = image.size
    # 遍历所有像素
    for x in range(width):
        for y in range(height):
            pixel = image.getpixel((x, y))
            # 如果像素是黑色，则保留；否则设为白色
            if pixel == (48, 48, 48):  # 黑色像素
                new_image.putpixel((x, y), pixel)  # 保留原始黑色
            else:
                new_image.putpixel((x, y), (255, 255, 255))  # 替换为白色

    ##################

    # 创建OCR对象
    ocr = ddddocr.DdddOcr(show_ad=False)
    ocr.set_ranges(0)
    result = ocr.classification(new_image)
    logger.debug(f'[1] 验证码识别结果：{result}，是否为可计算验证码 {IsValidExpression(result)}',)
    if IsValidExpression(result) == True:
        #rc = eval(result)
        return result


def login(USERNAME,PASSWORD):
    puzzid = GetPuzzleID()
    current_time = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds').replace("+00:00", "Z")
    data = {
        "username": USERNAME,
        "password": PASSWORD,
        "logindata": {
            "_v": "1.0.7",
            "datetime": current_time
        },
        "puzzle_id":puzzid ,
        "ans": "0"
    }
    # 验证码识别部分
    refresh_image = session.get(f'https://www.aeropres.in/chromeapi/dawn/v1/puzzle/get-puzzle-image?puzzle_id={puzzid}',headers=headers,verify=False).json()
    code = RemixCaptacha(refresh_image['imgBase64'])
    if code :
        logger.success(f'[√] 成功获取验证码结果 {code}',)
        data['ans'] = str(code)
        login_data = json.dumps(data)
        logger.info(f'[2] 登录数据： {login_data}')
        try:
            r = session.post(LoginURL,login_data,headers=headers,verify=False).json()
            logger.debug(r)
            token = r['data']['token']
            logger.success(f'[√] 成功获取AuthToken {token}')
            return token
        except Exception as e:
            logger.error(f'[x] 验证码错误，尝试重新获取...')

def KeepAlive(USERNAME,TOKEN):
    data = {"username": USERNAME,"extensionid":"fpdkjdnhkakefebpekbdhillbhonfjjp","numberoftabs":0,"_v":"1.0.7"}
    json_data = json.dumps(data)
    headers['authorization'] = "Berear " + str(TOKEN)
    r = session.post(KeepAliveURL,data=json_data,headers=headers,verify=False).json()
    logger.info(f'[3] 保持链接中... {r}')


def GetPoint(TOKEN):
    headers['authorization'] = "Berear " + str(TOKEN)
    r = session.get(GetPointURL,headers=headers,verify=False).json()
    logger.success(f'[√] 成功获取Point {r}')


def main(USERANEM, PASSWORD):
    TOKEN = ''
    if TOKEN == '':
        while True:
            TOKEN = login(USERANEM, PASSWORD)
            if TOKEN:
                break
    # 初始化计数器
    count = 0
    max_count = 200  # 每运行 200 次重新获取 TOKEN
    while True:
        try:
            # 执行保持活动和获取点数的操作
            KeepAlive(USERANEM, TOKEN)
            GetPoint(TOKEN)
            # 更新计数器
            count += 1
            # 每达到 max_count 次后重新获取 TOKEN
            if count >= max_count:
                logger.debug(f'[√] 重新登录获取Token...')
                while True:
                    TOKEN = login(USERANEM, PASSWORD)
                    if TOKEN:
                        break
                count = 0  # 重置计数器
        except Exception as e:
            logger.error(e)



if __name__ == '__main__':
    with open('password.txt','r') as f:
        username,password = f.readline().strip().split(':')
    main(username,password)

