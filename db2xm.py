#coding=utf-8
'''
Created on 2013-3-17

@author: Newton
'''
import sys
import urllib
import urllib2
import cookielib
from PIL import Image
import pickle as p
from pyquery import PyQuery as pq
import json


class DB2XM(object):
    # HTTP 头
    header = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) \
                AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.58 Safari/537.36'}

    # 豆瓣相关 URL
    db_loginUrl = 'https://www.douban.com/accounts/login'
    db_refererUrl = 'http://douban.fm/mine'
    db_favUrl = 'http://douban.fm/j/play_record?type=liked'

    # 虾米相关 URL
    xm_loginUrl = 'http://www.xiami.com/member/login'
    xm_searchUrl = 'http://www.xiami.com/search?key='
    xm_favUrl = 'http://www.xiami.com/ajax/addtag'

    def __init__(self, douban, xiami):
        self.db_username = douban[0]
        self.db_password = douban[1]
        self.xm_username = xiami[0]
        self.xm_password = xiami[1]

        self.cj = cookielib.CookieJar()
        self.cookieProcessor = urllib2.HTTPCookieProcessor(self.cj)
        self.opener = urllib2.build_opener(self.cookieProcessor,
                                           urllib2.HTTPHandler)
        urllib2.install_opener(self.opener)

    # 登录豆瓣
    def loginDb(self):
        header = self.header
        header['Referer'] = 'http://www.douban.com/'
        loginData = {'source': 'index_nav',
                     'form_email': self.db_username,
                     'form_password': self.db_password,
                     'remember': 'on'}
        req = urllib2.Request(self.db_loginUrl, urllib.urlencode(loginData), header)
        resp = urllib2.urlopen(req).read()
        doc = pq(resp)
        captcha = doc('.item-captcha')
        # 需要验证码
        if captcha:
            # 获取验证码图像并显示
            captImg = pq(captcha('#captcha_image'))
            captImg = captImg.attr['src']
            captId = pq(captcha('input[name="captcha-id"]'))
            captId = captId.attr['value']
            imgBin = urllib2.urlopen(captImg).read()
            captFile = open('captcha', 'wb')
            captFile.write(imgBin)
            captFile.close()
            img = Image.open('captcha')
            img.show()
            # 输入显示的验证码
            captCode = raw_input('Input the captcha: ')
            # 完成登录
            loginData['captcha-solution'] = captCode
            loginData['captcha-id'] = captId
            loginData['user_login'] = urllib.quote('登录')
            req = urllib2.Request(self.db_loginUrl, urllib.urlencode(loginData),
                                  header)
            urllib2.urlopen(req)

    # 获取豆瓣电台加心曲目
    def getDbFavs(self):
        self.loginDb()
        start = 0
        songsList = []

        # 生成曲目列表 JSON 数据请求 URL
        cookies = self.loadCookies()
        db_favUrl = '%s&%s' % (self.db_favUrl,
                 urllib.urlencode({'ck': cookies['ck'], 'spbid': '::%s' % (cookies['bid'])}))
        # 设置 Header
        header = self.header
        header['X-Requested-With'] = 'XMLHttpRequest'
        header['Referer'] = self.db_refererUrl

        print u'豆瓣：开始获取电台加心曲目...'
        while True:
            favUrl = '%s&%s' % (db_favUrl,
                                urllib.urlencode({'start': start}))
            print favUrl
            req = urllib2.Request(favUrl, '', header)
            resp = urllib2.urlopen(req).read()
            try:
                jsonData = json.loads(resp)
            except Exception:
                print u'!没有获取到曲目列表!'
                raise
            if not jsonData['songs']:
                break
            songs = jsonData['songs']
            for song in songs:
                songsList.append('%s %s' % (song['title'], song['artist']))
            start = start + jsonData['per_page']
        self.saveData('songs', songsList)
        print u'豆瓣：获取电台加心曲目 %s 首' % len(songsList)

    # 登录虾米
    def loginXm(self):
        loginData = {'email': self.xm_username,
                     'password': self.xm_password,
                     'autologin': 1,
                     'submit': urllib.quote('登 录'),
                     'done': '/',
                     'type': ''
                     }
        loginData = urllib.urlencode(loginData)
        header = self.header
        header['Referer'] = self.xm_loginUrl
        req = urllib2.Request(self.xm_loginUrl, loginData, header)
        resp = urllib2.urlopen(req)
        return resp

    # 在虾米匹配曲目并保存曲目 ID
    def getXmSongsId(self):
        header = self.header
        header['Referer'] = 'http://www.xiami.com/'
        songs = self.loadData('songs')
        songsId = []
        nomatch = []
        print u'虾米：开始匹配加心曲目，耗时较长...'
        for searchKey in songs:
            searchUrl = '%s%s' % (self.xm_searchUrl, urllib.quote(searchKey.encode('utf-8')))
            req = urllib2.Request(searchUrl, '', header)
            resp = urllib2.urlopen(req).read()
            page = pq(resp)('tbody:first')
            if page:
                song = page('.song_name:first').find('a[target="_blank"]')
                songLink = song.attr('href')
                songId = filter(str.isdigit, songLink.encode('utf-8'))
                songsId.append(songId)
                print u'匹配到 "%s"' % (searchKey)
            else:
                nomatch.append(searchKey)
                print u'未匹配 "%s"' % (searchKey)
        self.saveData('songsid', songsId)
        self.saveData('nomatch', nomatch)
        print u'虾米：匹配到 %s 首，未匹配 %s 首' % (len(songsId), len(nomatch))

    # 将匹配到的曲目添加收藏
    def addXmFav(self):
        self.loginXm()
        cookies = self.loadCookies()
        songsId = self.loadData('songsid')
        favData = {'type': 3, 'share': 0, 'shareTo': 'all', '_xiamitoken': cookies['_xiamitoken']}
        header = self.header
        header['Referer'] = 'http://www.xiami.com/'
        print u'虾米：开始收藏匹配曲目...'
        count = 0
        for songId in songsId:
            favData['id'] = songId
            req = urllib2.Request(self.xm_favUrl, urllib.urlencode(favData), header)
            resp = urllib2.urlopen(req).read()
            jsonData = json.loads(resp)
            if jsonData['status'] == 'ok':
                count = count + 1
        print u'虾米：收藏成功 %s 首，失败 %s 首' % (count, len(songsId) - count)

    # 载入 Cookies
    def loadCookies(self):
        cookies = {}
        for c in self.cj:
            try:
                cookies[c.name] = eval(c.value,{},{})
            except Exception, e:
                cookies[c.name] = c.value
        return cookies

    # 保存序列化数据
    def saveData(self, filename, data):
        f = open(filename, 'w')
        p.dump(data, f)
        return True

    # 载入序列化数据
    def loadData(self, filename):
        try:
            f = open(filename, 'r')
            data = p.load(f)
            return data
        except Exception:
            raise u'载入 %s 失败' % (filename)

    # 从序列化数据输出可读列表
    def data2lst(self, filename):
        log = ''
        items = self.loadData(filename)
        for item in items:
            log = '%s%s\n' % (log, item)
        f = open('%s.lst' % (filename), 'w')
        f.write(log.encode('utf-8'))

    # 执行流程
    def transfer(self):
        self.getDbFavs()
        self.data2lst('songs')
        self.getXmSongsId()
        self.data2lst('nomatch')
        self.addXmFav()

if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf-8')

    # 账户信息
    douban = ('Douban Username', 'Douban password')
    xiami = ('Xiami Username', 'Xiami password')

    db2xm = DB2XM(douban, xiami)
    db2xm.transfer()
