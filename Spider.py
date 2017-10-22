
import requests
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from sqlserver import SqlServer
import time
import uuid
import traceback
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from lxml import etree
from selenium.webdriver.support.wait import WebDriverWait


class SpiderConfig:
    def __init__(self):
        print("调用了父类")
        self.sql_bool = False
        get_host = lambda url: re.search(re.compile("https?://(.*?)/"), url).group(1)
        self.start_url = ''
        self.storeId = ''
        self.product_url = ''
        self.headers = {
            'Host': get_host(self.start_url),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.81 Safari/537.36'
        }
        self.db = SqlServer(
            host='127.0.0.1',
            user='username',
            pwd='pwd',
            db='dbname'
        )
        self.session = requests.session()
        self.session.keep_alive = False

    def get_html(self, url, bool=True, browser=2):
        """
        默认使用requests获取网页源码，bool为Fales时则使用selenium获取源码
        :param url:页面链接
        :param bool:是否启用selenium，默认使用requests
        :param browser:是否显示浏览器，默认使用Chrome
        :return:html
        """
        # 获取单页的html源码
        if bool:
            try:
                reponse = self.session.get(url, headers=self.headers, timeout=30)
            except requests.Timeout:
                print('请求响应超时，重新请求中...')
                reponse = self.session.get(url, headers=self.headers, timeout=30)
            if reponse.status_code == 200:
                html = reponse.content
            else:
                html = ''
                print('返回码为%s,请检查' % str(reponse.status_code))
        else:
            if browser == 1:
                dcap = dict(DesiredCapabilities.PHANTOMJS)
                dcap["phantomjs.page.settings.loadImages"] = False
                driver = webdriver.PhantomJS(desired_capabilities=dcap)
            elif browser == 2:
                driver = webdriver.Chrome()
            else:
                driver = ''
            driver.get(url)
            html = driver.page_source
            driver.quit()
        self.product_url = url
        return html

    def get_or_save_html_file(self, url, save=True):
        """
        默认保存并返回网页源码，save为False时则不保存源码而是在当前html文件获取源码
        :param url:页面链接
        :param save:是否保存页面到本地，默认保存
        :return:从网络或本地返回html
        """
        if save:
            html = self.get_html(url)
            file = open('download.html', 'w', encoding='utf8')
            soup = BeautifulSoup(html, 'lxml')
            file.write(str(soup))
            file.close()
            return html
        else:
            with open('download.html', 'r', encoding='utf8') as f:
                html = f.read()
            return html

    def submit_sql(self, sql):

        if self.sql_bool:
            try:
                self.db.ExecNonQuery(sql)
            except:
                try:
                    print(sql)
                    print("提交sql失败，正在重新提交")
                    self.db.ExecNonQuery(sql)
                except Exception as e:
                    print('提交sql失败，报错原因为%s,请检查sql代码' % e)
        else:
            print('未启用sql提交函数')


class Spider(SpiderConfig):
    def __init__(self):
        super().__init__()
        # 常量，需要手动获取
        self.CAT2_URLS = [
            ''
        ]

        self.error_num = 0

        # 要在外部获取并保存的字段
        self.cat1Name = ''
        self.cat2Name = ''
        self.cat1Url = ''
        self.cat2Url = ''

        # 转换并全部大写
        self.conversion = lambda str1: ' '.join(map(lambda x: x.capitalize(), str1.split('-')))
        # 去重并保持原有顺序
        self.deduplication_sorting = lambda list1: sorted(set(list1), key=list1.index)

    def get_cat2_urls(self, cat1_url=""):
        cat1_url = self.start_url
        html = self.get_html(cat1_url)
        html = etree.HTML(str(html))
        result = html.xpath('/html/body/header/nav/div/ul/li[7]/ul/li/a/@href')
        for i in result:
            print('"%s",' % i)

    def get_product_urls(self, cat2_url=""):
        cat2_url = ''
        # 通过规范的列表链接获取分类信息
        # self.cat1Url = re.search(re.compile('https://.+?/.+?/.+?/'), cat2_url).group()
        # self.cat1Name = self.conversion(re.search(re.compile('https://.+?/.+?/(.+?)/'), cat2_url).group(1))
        # self.cat2Url = cat2_url
        # self.cat2Name = self.conversion(re.search(re.compile('https://.+?/.+?/.+?/(.+?)/'), cat2_url).group(1))

        page_urls = []
        # 用Beautifulsoup获取
        html = self.get_html(cat2_url)
        soup = BeautifulSoup(html, 'lxml')

        # 翻页功能
        # num = 0
        # for page_num in range(1, 50):
        #     print(page_num)
        #     tmp_url = cat2_url + '?p=' + str(page_num)
        #     html = self.get_html(tmp_url, False, 1)
        #     soup = BeautifulSoup(html, 'lxml')
        #     try:
        #         urls = [url['href'] for url in soup.find('section', id="category-main").findAll('a')]
        #         for url in urls:
        #             page_urls.append(url)
        #         if num <= len(urls):
        #             num = len(urls)
        #         else:
        #             #
        #             html = self.get_html(tmp_url)
        #             soup = BeautifulSoup(html, 'lxml')
        #             urls = [url['href'] for url in soup.find('section', id="category-main").findAll('a')]
        #             for url in urls:
        #                 page_urls.append(url)
        #             print(len(page_urls))
        #             break
        #     except:
        #         print(cat2_url)
        #         print("获取商品列表出错")
        #     print(len(page_urls))

        # 用xpath获取
        # html = self.get_html(cat2_url)
        # html = etree.HTML(str(html))
        # result = html.xpath('//*[@id="main"]/ul/li/a[1]/@href')
        # urls = [url for url in result]
        # for url in urls:
        #     print(url)

        # # 翻页功能
        # num = 0
        # for page_num in range(1, 4):
        #     print(page_num)
        #     tmp_url = cat2_url + '?page=' + str(page_num)
        #     print(tmp_url)
        #     try:
        #         html = self.get_html(tmp_url)
        #         html = etree.HTML(str(html))
        #         result = html.xpath('//*[@id="product-loop"]/div/a/@href')
        #         urls = [self.start_url + url.replace('/', '', 1) for url in result]
        #         for url in urls:
        #             page_urls.append(url)
        #         if num <= len(urls):
        #             num = len(urls)
        #         else:
        #             html = self.get_html(cat2_url)
        #             html = etree.HTML(str(html))
        #             result = html.xpath('//*[@id="product-loop"]/div/a/@href')
        #             urls = [self.start_url + url.replace('/', '', 1) for url in result]
        #             for url in urls:
        #                 page_urls.append(url)
        #             print(len(page_urls))
        #             break
        #     except:
        #         print(cat2_url)
        #         print("获取商品列表出错")
        assert isinstance(page_urls, list)
        # 清除重复数据并保持原来的顺序
        page_urls = self.deduplication_sorting(page_urls)
        print(len(page_urls))
        return page_urls

    def get_data(self, html=''):
        html = self.get_or_save_html_file('')
        soup = BeautifulSoup(html, 'lxml')
        self.sql_bool = False
        self.save_error = False
        try:
            provider = 'byb'
            # 网站id
            storeId = self.storeId
            # 货币id
            currencyId = '1'

            name = soup.find('h1').text
            print(name)
            # 副标题
            caption = ''
            # 商品简介
            description = ''
            # 商品详情
            introduction = soup.find()
            url = self.product_url
            images = soup.find()
            price = soup.find()
            # 优惠价格
            promotionPrice = soup.find()
            # 获取优惠价格
            # tmp_price = soup.find('p', class_="price").text.split('£')[1::]
            # try:
            #     if float(tmp_price[0].replace("£", '')) < float(tmp_price[1].replace("£", '')):
            #         promotionPrice = tmp_price[0].replace("£", '')
            #         price = tmp_price[1].replace("£", '')
            #     else:
            #         promotionPrice = tmp_price[1].replace("£", '')
            #         price = tmp_price[0].replace("£", '')
            # except IndexError:
            #     promotionPrice = ''
            #     price = tmp_price[0]
            try:
                specName1 = ''
                specValue1 = soup.find()
            except AttributeError:
                specName1 = ''
                specValue1 = ''
            try:
                specName2 = ''
                specValue2 = ''
            except AttributeError:
                specName2 = ''
                specValue2 = ''
            create_at = time.strftime('%Y-%m-%d %H:%M:%S')
            cat1Name = ''
            cat2Name = ''
            cat3Name = ''
            cat1Url = ''
            cat2Url = ''
            cat3Url = ''
            # 在商品详情页获取分类信息
            # tmp_name = [tname.text for tname in soup.find('div', class_="breadcrumbs").findAll('a')[1::]]
            # tmp_url = [turl['href'] for turl in soup.find('div', class_="breadcrumbs").findAll('a')[1::]]
            # cat1Name = tmp_name[0].replace("'", "''")
            # cat2Name = tmp_name[1].replace("'", "''")
            # cat3Name = tmp_name[2].replace("'", "''")
            # cat1Url = tmp_url[0]
            # cat2Url = tmp_url[1]
            # cat3Url = tmp_url[2]

            # 最后一级的分类名称
            categoryName = ''
            categoryUuid = str(uuid.uuid3(uuid.NAMESPACE_DNS, str(categoryName.lower().strip())))

            # print('一级链接为：'+cat1Name, cat1Url)
            # print('二级链接为：'+cat2Name, cat2Url)
            # print('三级链接为：'+cat3Name, cat3Url)
            # print('规格1为:' + specName1, specValue1)
            # print('规格2为:' + specName2, specValue2)
            # print("图片为:" + images)
            # print("价格为:" + price)
            # print('名称为：'+name, url, categoryName)

            sql = "INSERT INTO data(provider,storeId,currencyId,categoryName,categoryUuid,name,caption,description,introduction" \
                  ",url,images,price,promotionPrice,specName1,specValue1,specName2,specValue2,create_at,cat1Name," \
                  "cat2Name,cat3Name,cat1Url,cat2Url,cat3Url) VALUES(" \
                  "'{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')".format(
                provider, storeId, currencyId, categoryName, categoryUuid, name, caption, description, introduction,
                url, images, price, promotionPrice, specName1, specValue1, specName2, specValue2, create_at, cat1Name,
                cat2Name, cat3Name, cat1Url, cat2Url, cat3Url

            )

            self.submit_sql(sql)

            pass
        except Exception as e:
            if self.error_num <= 10:
                if self.save_error:
                    with open('error.txt', 'a', encoding='utf8') as file:
                        file.write(self.product_url + '\n')
                        file.write('报错原因为：' + str(e) + '\n')
                        file.write('详细原报错原因为：' + traceback.format_exc() + '\n')
                        print('本次运行已报错%d次，已保存错误信息到本地' % (self.error_num + 1))
                print(self.product_url)
                print(traceback.format_exc())
                print('本次运行已报错%d次，未保存错误信息到本地' % (self.error_num + 1))
                self.error_num += 1
            else:
                exit()


def main():
    s = Spider()
    s.get_data()
    # s.get_cat2_urls()
    # s.get_page_urls()

    # 二个层级,二个for循环抓取


    # cat2_num, cat2_print_num = 1, 1
    # page_num, page_print_num = 1, 1
    #
    # for cat2_url in s.CAT2_URLS[cat2_num - 1::]:
    #     page_urls = s.get_product_urls(cat2_url)
    #     for page_url in page_urls[page_num - 1::]:
    #         html = s.get_html(page_url)
    #         print('正在采集第{}个二级链接下第{}个商品，还剩{}个商品未采集'.format(
    #             str(cat2_print_num), str(page_print_num), str(len(page_urls[page_num - 1::]) - page_print_num)))
    #         s.get_data(html)
    #         page_print_num += 1
    #     page_num = 1
    #     page_print_num = 1
    #     cat2_print_num += 1



    # 三个层级,三个for循环抓取

    # cat1_num, cat1_print_num = 1, 1
    # cat2_num, cat2_print_num = 1, 1
    # page_num, page_print_num = 1, 1
    # for cat1url in s.CAT1_URLS[cat1_num-1::]:
    #     cat2Urls = s.get_cat2_urls(cat1url)
    #     for cat2Url in cat2Urls[cat2_num-1::]:
    #         page_urls = s.get_product_urls(cat2Url)
    #         for page_url in page_urls[page_num-1::]:
    #             html = s.get_html(page_url,False,2)
    #             print("正在采集第{}个一级类别下的第{}个二级类别下的第{}个商品".format(
    #                 str(cat1_print_num), str(cat2_print_num), str(page_print_num)))
    #             s.get_data(html)
    #             print('还剩%s个商品未采集' % str(len(page_urls[page_num - 1::]) - page_print_num))
    #             page_print_num += 1
    #         page_print_num = 1
    #         page_num = 1
    #         cat2_print_num += 1
    #     cat2_num = 1
    #     cat2_print_num = 1
    #     cat1_print_num += 1


if __name__ == '__main__':
    main()
