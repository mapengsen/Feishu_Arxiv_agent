# 使用方法
### 1、创建群里机器人
进入群组，点击右上角的...图标 > 设置，找到 群机器人，并点击 添加机器人。
![alt text](image.png)
添加自定义机器人：在添加机器人页面点击 自定义机器人。设置机器人头像、名称、描述，点击 添加 即可。

###2、新建飞书卡片
https://open.feishu.cn/cardkit
![alt text](image.png)


将代码库中的ArXivToday.card 直接导入。
![alt text](image-1.png)


将id和version记住，一般version都是'1.0.0'


### 3、克隆仓库并修改代码
```
git clone https://github.com/mapengsen/Feishu_Arxiv_agent.git
conda create -n arxiv
conda activate arxiv
pip install -r requirements.txt
```


### 4、修改config.yaml中的代码:







