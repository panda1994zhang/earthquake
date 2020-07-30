import json
from pprint import pprint
from time import time

import asks
import moment
import requests
import trio
from django.db import IntegrityError
from pyquery import PyQuery as jq

from Common.CompanyWeChat import WechatReports
from Common.Config import WechatConf
from Website.models import EarthquakeCase

asks.init("trio")


class worker:
    def __init__(self, *args, **kwargs):
        self.robot = WechatReports(WechatConf)
        self.max_num = 1

    async def init_session(self):
        self.session = asks.Session()
        self.session.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Host": "www.ceic.ac.cn",
            "Pragma": "no-cache",
            "Proxy-Connection": "keep-alive",
            "Referer": "http://news.ceic.ac.cn/index.html",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36",
        }  # 定义访问类header

    async def item(self, page, send=False):
        """
            新数据截取
        """
        key = "jQuery"
        url = f"http://www.ceic.ac.cn/ajax/speedsearch?num=6&&page={page}&&callback={key}&_={int(time())}"
        try:
            resp = await self.session.get(url)
            jsondata = json.loads(resp.text.replace(f"{key}(", "")[:-1])
            self.save(jsondata["shuju"], send)
            self.max_num = jsondata["num"]
        except Exception as e:
            print(e)

    def save(self, datas, send=False):
        """数据留存并根据可否成功存储发送推送信息

            Args:
                datas: 数据集
                send: 是否发送
        """
        for data in datas:
            res = dict(
                zip(
                    ["Level", "Time", "Latitede", "Longitude", "Deep", "Address"],
                    [
                        data[key]
                        for key in [
                            "M",
                            "O_TIME",
                            "EPI_LAT",
                            "EPI_LON",
                            "EPI_DEPTH",
                            "LOCATION_C",
                        ]
                    ],
                )
            )
            print(res)
            try:
                EarthquakeCase.objects.create(**res)
                if send:
                    Location = f"{res.get('Latitede','')},{res.get('Longitude','')}"
                    self.robot.Data_send(
                        MsgType="textcard",
                        Content={
                            "title": f"{res.get('Address','')}",
                            "description": f"""<div class="gray">{res.get('Time',moment.now())}</div><br/><div class="info">Level:  {res.get('Level')}</div><br/><div class="info">Deep:  {res.get('Deep','')}km</div><br/><br/><div class="highlight">Location:  {Location}</div>""",
                            "url": f"https://www.google.com/maps/search/{Location}",
                        },
                        SendNow=True,
                        AppId="1000004",
                    )
            except IntegrityError:
                pass
            except Exception:
                raise

    async def init(self):
        """初始化运行
            
        """
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.item, self.max_num)

        async with trio.open_nursery() as nursery:
            for page in range(1, self.max_num + 1):
                nursery.start_soon(self.item, page)

    async def update(self):
        """
            更新数据方法

        """
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.item, 1, True)


def getUpdateData():
    """定时更新

    """
    w = worker()
    trio.run(w.init_session)
    trio.run(w.update)


def getBaseData():
    """初始化
    
    """
    w = worker()
    trio.run(w.init_session)
    trio.run(w.init)


# from Website.tasks import getBaseData;getBaseData()
# from Website.tasks import getUpdateData;getUpdateData()

# getBaseData()
