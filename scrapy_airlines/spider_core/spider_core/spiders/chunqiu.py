# -*- coding: utf-8 -*-
import scrapy
from spider_core.items import SpiderCoreItem
from copy import deepcopy
from urllib import parse
import datetime
import uuid
import logging
from scrapy.conf import settings
import os, sys
from fake_useragent import UserAgent
import json

from scrapy import Spider, Request
from selenium import webdriver

ua = UserAgent()
to_date = datetime.datetime.now()


# driver = webdriver.PhantomJS(executable_path='/bin/phantomjs/bin/phantomjs')
# 如果不方便配置环境变量。就使用phantomjs的绝对路径也可以


# todo 切换城市
class ChunqiuSpider(scrapy.Spider):
    name = 'chunqiu'
    allowed_domains = ['pages.ch.com']
    start_urls = ['http://pages.ch.com/second-kill/']

    # 初始化函数 ,
    def __init__(self):
        # self.browser = webdriver.Firefox()
        # self.browser.set_page_load_timeout(30)
        pass

    def closed(self, spider):
        # print("spider closed")
        # self.browser.close()
        pass

    def start_requests(self):
        """
        重载start_requests方法 待登录成功后，再进入parse进行数据爬取
            访问登录页面 并调用do_login方法进行登录
        """
        # 春秋通过算法把字符串加密了
        # 17673119082
        # flyfly123
        from_data = {
            'UserNameInput': 'LarvwuAX3KTyBFXtXkCcjcFRLzpSb/Ft6P1r29CxZcOlpn9Le8Q+LCQ3iTeXnW2ZdCKJsmA0tOyn4wF4C92vjs1Tg11lGxaroeAgGmSgZvBqyLQha2UNOM/MDHMroF1m9W5j92oe2jg2QPS4rTsCVRsnMcZCCd3y2iY/2/PBtx0=',
            'undefined': '0',
            'PasswordInput': ' dAaIbU2BmGOtFUVYm/gEM5yaZojqmtjifUJP2N+gkamNFyBqwec5ETXZFcji8orszLywEZPaJ1fQHOvZidQKhWLNtKDqBObcbrXlwgsQuX7ePqYBtP6qAc5JIQ/tfPcPYT6S0s4cCdAWGzyitt/L0jqf27XCael00UjFFLDswAU=',
            'IsKeepLoginState': 'true',
            'loginType': 'PC',
        }
        logging.info("进入start_requests方法")
        yield scrapy.FormRequest(url='https://passport.ch.com/zh_cn/Login/DoLogin',
                                 formdata=from_data,
                                 callback=self.islogin)

    def islogin(self, response):
        logging.info("进入islogin方法")
        logging.info("jsobj:",response.body.decode('utf-8'))
        try:
            jsobj = json.loads(response.body.decode('utf-8'))
            if '0' is not str(jsobj['Code']):
                raise RuntimeError('登陆失败!时间:{}'.format(to_date))
            yield scrapy.Request(url=self.start_urls[0], callback=self.parse)
        except Exception as e:
            # todo 登陆失败
            logging.error('Exception :{}登陆失败!时间:{}'.format(e, to_date))

    def parse(self, response):

        # logging.info('进入解析页面1.....response.content:{}'.format(response.body.decode('utf-8')))
        # 地区  东南亚,日韩,港澳台,境内
        area_list = response.xpath('//h2[@class="red f-cb travel-block"]')
        logging.info('method[parse].....:{}'.format(area_list.getall()))

        for idx, item in enumerate(area_list):
            air_item = {}
            try:
                area_html = response.xpath('//div[@class="m-main g-wp pc-only "]/div')[2:5]
                for item in area_html.xpath('//div[@class="m-sk-area f-cb hot-air"]/div[@class="pic"]'):
                    # 图片
                    air_item['image_url'] = item.xpath('./div[@class="pic1"]/img/@data-src').extract_first()
                    # 获取打折结束时间
                    air_item['discount_start_time'] = item.xpath(
                        '//span[@class="time-span"]/@data-start').extract_first()
                    air_item['discount_end_time'] = item.xpath('//span[@class="time-span"]/@data-end').extract_first()

                    # 创建时间
                    air_item['create_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    air_item['version'] = 1
                    air_item['del_flag'] = 1

                    # air_item['id'] = str(uuid.uuid4())
                    btn_form = item.xpath('./div[@class="pic-bottom"]//form[@class="btn-form"]')
                    detail_url = parse.urljoin(response.url, btn_form.xpath('./@action').extract_first())
                    logging.info('解析详细页面前.....air_item:{}'.format(air_item))
                    yield scrapy.FormRequest(
                        url=detail_url,
                        callback=self.parse_detail,
                        meta={
                            "item": deepcopy(air_item)
                        },
                        formdata={
                            'OriCityCode': btn_form.xpath('./input[@name="OriCityCode"]/@value').extract_first(),
                            'DestCityCode': btn_form.xpath('./input[@name="DestCityCode"]/@value').extract_first(),
                            'FlightDateBegin': btn_form.xpath(
                                './input[@name="FlightDateBegin"]/@value').extract_first(),
                            'FlightDateEnd': btn_form.xpath('./input[@name="FlightDateEnd"]/@value').extract_first(),
                            'ActivitiesStartTime': btn_form.xpath(
                                './input[@name="ActivitiesStartTime"]/@value').extract_first(),
                            'ActivitiesEndTime': btn_form.xpath(
                                './input[@name="ActivitiesEndTime"]/@value').extract_first(),
                        }
                    )
            except Exception as e:
                print("error:", e)

    # 解析详细数据
    def parse_detail(self, response):
        try:
            air_item = response.meta['item']
            logging.info('解析详细页面中.....air_item:{}'.format(air_item))

            currency = response.xpath('//ul[@class="list-ul2 font14"]/li[@class="li10"]/text()').extract_first()
            ul_list = response.xpath('//ul[@class="list-ul3 font14"]')[1:]
            for item in ul_list:
                # 去除已经售罄的
                if item.xpath('./li[@class="li10"]/a/div/@style').extract_first() is None:
                    continue

                air_item['air_No'] = item.xpath('./li/text()').extract()[0]
                date = item.xpath('./li[@class="li2"]/text()').extract_first()
                air_item['f_start_time'] = date + ' ' + item.xpath('./li[@class="li4"]/text()').extract_first()
                air_item['f_end_time'] = date + ' ' + item.xpath('./li[@class="li5"]/text()').extract_first()

                # 开始地点

                city = item.xpath('./li[@class="li6"]/div[@class="start1"]/text()').extract_first()
                site = item.xpath('./li[@class="li6"]/div[@class="start2"]/text()').extract_first()
                air_item['f_source_place'] = city + site

                # 结束地点
                city = item.xpath('./li[@class="li7"]/div[@class="start1"]/text()').extract_first()
                site = item.xpath('./li[@class="li7"]/div[@class="start2"]/text()').extract_first()
                air_item['f_end_place'] = city + site

                air_item['position'] = item.xpath('./li[@class="li9"]/text()').extract_first()
                print("asfasfa:", item.xpath('./li[last()]'))
                price = item.xpath('./li[last()]//span')[0].xpath('./text()')[0]
                print("pring:::", price)
                if price is not None:
                    air_item['price'] = price.replace('¥', '')
                air_item['currency'] = currency

                air_item['detail_url'] = response.url
                # logging.info('解析详细页面后.....air_item:{}'.format(air_item))
            yield air_item
        except Exception as e:
            logging.error("解析详细页面错误:", e)
            pass
