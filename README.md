DoubanFM2Xiami
==============

将豆瓣电台的[加心曲目](http://douban.fm/mine?type=liked)导入到虾米收藏

### Requirements
* PyQuery
* PIL

### DirtyPart
* 豆瓣在登录的时候很可能需要验证码，此时验证码会弹出显示，需要手工输入（PIL 只在此时用到...）
* 由于虾米没有提供公开搜索接口，直接把搜索页面命中的第一个记录认定为匹配曲目，因此很可能无法 100% 匹配
* 整个流程根据曲目数量会发起多次请求，耗时较长，曲目信息列表、匹配到的曲目 ID 都会序列化保存，可更改 transfer() 函数分步执行提升成功率

Example
===

```python
\# 账户信息
douban = ('Douban Username', 'Douban password')
xiami = ('Xiami Username', 'Douban password')

db2xm = DB2XM(douban, xiami)
db2xm.transfer()
```