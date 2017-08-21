# -*- coding: utf-8 -*-

import scrapy
import re
import os
from urllib import parse
from scrapy.http import Request
from amz_crawl.items import AmazonOrdersItem
from amz_crawl.tool.file_deal import regularize_filename

BSR = 'https://www.amazon.com/Best-Sellers/zgbs/ref=zg_bs_unv_auto_0_15718271_2'


# HNR = 'https://www.amazon.com/gp/new-releases/fashion/1040660/ref=zg_bsnr_unv_3_2368343011_1'


class OrdersSpider(scrapy.Spider):
    name = 'all_orders'
    allowed_domains = ['amazon.com']
    start_urls = [BSR]
    project_dir = os.path.abspath(os.path.curdir)

    def parse(self, response):
        links = response.css('#zg_browseRoot li:not(.zg_browseUp)>a::attr(href)').extract()

        # 不是主页

        if response.url is not BSR:
            yield Request(url=response.url,
                          callback=self.parse_list)

        # 当前link 不在 子links 才可以继续遍历
        if response.url not in links:
            for i, link_sel in enumerate(links):
                link = link_sel.css('a::attr(href)').extract()[0]
                print(link)
                yield Request(url=parse.urljoin(response.url, link),
                              callback=self.parse)

    def parse_list(self, response):
        items_node = response.css('#zg_centerListWrapper  .zg_itemImmersion')
        for item in items_node:
            front_image_url = item.css(' a > div.a-section.a-spacing-mini img::attr(src)').extract_first()
            front_image_url = re.sub(r'_SL500_SR.*_.jpg', '_SL500_SR400,400.jpg', front_image_url)
            # Windows下冒号会错误
            des = item.css(' a > div.a-section.a-spacing-mini img::attr(alt)').extract_first()
            des = regularize_filename(des)
            rate = item.css('div > div.a-icon-row.a-spacing-none > a > i .a-icon-alt::text').extract_first()
            if rate:
                rate_num = re.match(r'\d.\d', rate).group()
            else:
                rate_num = '0.0'

            reviews = item.css(
                'div > div.a-icon-row.a-spacing-none > a.a-size-small.a-link-normal::text').extract_first()

            if not reviews:
                reviews = '0.0'

            price = item.css('div > div.a-row > span .p13n-sc-price::text').extract_first()

            if not price:
                price = '$0.0'
            # 类目
            category = None
            sub_category = None
            browse_ups = response.css('.zg_browseUp a::text').extract()
            browse_ups = [b for b in browse_ups if b != 'Any Department']
            if len(browse_ups) > 0:
                category = browse_ups[0]
                category = regularize_filename(category)
                sub_category = '/'.join(browse_ups)

            rank = item.css('.zg_rankNumber::text').extract_first()
            rank = re.search(r'\d+', rank).group()

            # 是new-releases 还是 top seller
            belong = 'BSR'
            if "new-releases" in response.url:
                belong = 'HNR'

            order_item = AmazonOrdersItem()
            order_item["front_image_url"] = [front_image_url]
            order_item["des"] = des
            order_item["rate_num"] = rate_num
            order_item["reviews"] = reviews
            order_item["price"] = price
            order_item['rank'] = rank
            order_item['belong'] = belong

            if category:
                order_item["category"] = category
            if sub_category:
                order_item["sub_category"] = sub_category
            # 详情页
            detail_link = item.css('.zg_itemWrapper >div > a::attr(href)').extract_first()
            yield Request(url=parse.urljoin(response.url, detail_link), callback=self.parse_page)
            # 下一页
            next_page = int(response.css('.zg_selected').css('a::attr(page)').extract_first()) + 1

            if next_page <= 5:
                next_url = response.css('#zg_page' + str(next_page) + ' > a::attr(href)').extract_first()
                if next_url:
                    yield Request(url=parse.urljoin(response.url, next_url), callback=self.parse_list)

    def parse_page(self, response):

        order_item = response.meta['AmazonOrdersItem']
        # q & a
        qanum = response.css('#askATFLink > span::text').extract_first().strip()
        if qanum:
            qanum = re.match(r'\d+', qanum).group()
        else:
            qanum = '0.0'

        order_item['question_num'] = qanum

        yield order_item