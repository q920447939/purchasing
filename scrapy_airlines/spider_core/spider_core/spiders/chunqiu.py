# -*- coding: utf-8 -*-
import scrapy
from scrapy_airlines.spider_core.spider_core.items import SpiderCoreItem
from copy import deepcopy
from urllib import parse
import datetime
import uuid


class ChunqiuSpider(scrapy.Spider):
    name = 'chunqiu'
    allowed_domains = ['pages.ch.com']
    start_urls = ['http://pages.ch.com/second-kill/']

    # todo 切换城市

    def parse(self, response):
        # 地区  东南亚,日韩,港澳台,境内
        area_list = response.xpath('//h2[@class="red f-cb travel-block"]')
        for idx, item in enumerate(area_list):
            air_item = SpiderCoreItem()
            self.parse_item(int(idx), deepcopy(air_item), response)
            pass

    def parse_item(self, idx, air_item, response):
        area_html = response.xpath('//div[@class="m-main g-wp pc-only "]/div[2-5]')
        for item in area_html.xpath('//div[@class="m-sk-area f-cb hot-air"]/div[@class="pic"]'):
            # 图片
            air_item['image_url'] = item.xpath('./div[@class="pic1"]/img/src').extract_first()

            # 获取打折结束时间
            air_item['discount_start_time'] = response.xpath(
                '//span[@class="fr time bg-noChange time-parent"]/@data-start').extract_first()
            air_item['discount_end_time'] = response.xpath(
                '//span[@class="fr time bg-noChange time-parent"]/@data-end').extract_first()

            # 创建时间
            air_item['discount_start_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            air_item['version'] = 1
            air_item['del_flag'] = 1

            air_item['id'] = uuid.uuid1()
            btn_form = item.xpath('./div[@class="pic-bottom"]//form[@class="btn-form"]')
            detail_url = parse.urljoin(response.url, btn_form.xpath('./@action').extract_first())
            yield scrapy.FormRequest(
                url=detail_url,
                callback=self.parse_detail,
                meta={
                    "item": deepcopy(air_item)
                },
                formdata={
                    'OriCityCode': btn_form.xpath('./input[@name="OriCityCode"]/@value'),
                    'DestCityCode': btn_form.xpath('./input[@name="DestCityCode"]/@value'),
                    'FlightDateBegin': btn_form.xpath('./input[@name="FlightDateBegin"]/@value'),
                    'FlightDateEnd': btn_form.xpath('./input[@name="FlightDateEnd"]/@value'),
                    'ActivitiesStartTime': btn_form.xpath('./input[@name="ActivitiesStartTime"]/@value'),
                    'ActivitiesEndTime': btn_form.xpath('./input[@name="ActivitiesEndTime"]/@value')
                }
            )

    # 解析详细数据
    def parse_detail(self, response):
        air_item = response.meta['item']

        currency = response.xpath('//ul[@class="list-ul2 font14"]/li[@class="li10"]').extract_first()

        ul_list = response.xpath('//ul[@class="list-ul3 font14"]')[3:]
        for item in ul_list:
            # 去除已经售罄的
            if item.xpath('./li[@class="li10"]/a/div/@style').extract_first() is None:
                continue
            air_item['air_No'] = item.xpath('./li').extract()[1]

            date = item.xpath('./li').extract()[2]
            air_item['f_start_time'] = date + item.xpath('./li').extract()[3]
            air_item['f_end_time'] = date + item.xpath('./li').extract()[4]


            f_source_place = item.xpath('./li[@class="li6"]').extract()
            if not f_source_place:
                if not f_source_place[1] and not f_source_place[2]:
                    f_source_place = f_source_place[1] + f_source_place[2]
                elif not f_source_place[1]:
                    f_source_place = f_source_place[1]
                else:
                    f_source_place = ""

            air_item['f_source_place'] = f_source_place

            f_end_place = item.xpath('./li[@class="li7"]').extract()
            if not f_end_place:
                if not f_end_place[1] and not f_end_place[2]:
                    f_end_place = f_end_place[1] + f_end_place[2]
                elif not f_end_place[1]:
                    f_end_place = f_end_place[1]
                else:
                    f_end_place = ""
            air_item['f_end_place'] = f_end_place

            air_item['position'] = item.xpath('./li[@class="li9"]').extract_first()
            air_item['price'] = item.xpath('./li[@class="li10"]//span').extract_first().replace('¥', '')
            air_item['currency'] = currency
        pass
