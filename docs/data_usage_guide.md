# MediaCrawler 数据使用指南

本文档提供了关于如何访问、查询和利用MediaCrawler抓取的数据的详细指南。MediaCrawler是一个多平台媒体内容抓取工具，支持小红书、抖音、B站等多个平台的数据抓取。

## 目录

- [数据存储概述](#数据存储概述)
- [数据库结构](#数据库结构)
- [数据访问方法](#数据访问方法)
  - [使用Python直接访问](#使用python直接访问)
  - [使用数据库查看器](#使用数据库查看器)
  - [使用SQL命令行](#使用sql命令行)
- [数据分析示例](#数据分析示例)
- [常见问题解答](#常见问题解答)
- [最佳实践](#最佳实践)

## 数据存储概述

MediaCrawler支持三种数据存储方式：

1. **数据库存储（推荐）**：数据存储在MySQL数据库中，支持高效查询和数据去重。
2. **CSV文件存储**：数据保存为CSV文件，方便导入到Excel等工具中分析。
3. **JSON文件存储**：数据保存为JSON文件，适合需要保留完整数据结构的场景。

默认配置使用数据库存储，可在`config/base_config.py`中通过`SAVE_DATA_OPTION`参数修改：

```python
# 数据保存类型选项配置,支持三种类型：csv、db、json, 最好保存到DB，有排重的功能。
SAVE_DATA_OPTION = "db"  # csv or db or json
```

## 数据库结构

MediaCrawler使用MySQL数据库存储抓取的数据。数据库名称默认为`media_crawler`，可在`config/db_config.py`中配置。

### 主要数据表

数据库包含多个表，每个表对应不同平台的不同数据类型：

| 表名 | 描述 | 主要字段 |
|------|------|---------|
| xhs_note | 小红书笔记 | note_id, title, desc, liked_count, collected_count, comment_count, share_count, nickname |
| xhs_note_comment | 小红书笔记评论 | comment_id, note_id, content, nickname, liked_count |
| xhs_creator | 小红书创作者 | user_id, nickname, avatar, desc, gender, location |
| douyin_aweme | 抖音视频 | aweme_id, desc, liked_count, comment_count, share_count, nickname |
| douyin_aweme_comment | 抖音视频评论 | comment_id, aweme_id, content, nickname, liked_count |
| dy_creator | 抖音创作者 | user_id, nickname, avatar, desc, gender, location |
| bilibili_video | B站视频 | video_id, title, desc, liked_count, video_play_count, video_comment, nickname |
| bilibili_video_comment | B站视频评论 | comment_id, video_id, content, nickname, sub_comment_count |
| bilibili_up_info | B站UP主信息 | user_id, nickname, avatar, total_fans, total_liked, user_rank |

### 字段说明

以小红书笔记表（xhs_note）为例：

| 字段名 | 类型 | 描述 |
|--------|------|------|
| id | int | 自增ID，主键 |
| user_id | varchar(64) | 用户ID |
| nickname | varchar(64) | 用户昵称 |
| avatar | varchar(255) | 用户头像URL |
| note_id | varchar(64) | 笔记ID |
| title | varchar(255) | 笔记标题 |
| desc | longtext | 笔记内容 |
| time | bigint | 发布时间（Unix时间戳，毫秒） |
| liked_count | varchar(16) | 点赞数 |
| collected_count | varchar(16) | 收藏数 |
| comment_count | varchar(16) | 评论数 |
| share_count | varchar(16) | 分享数 |
| image_list | longtext | 图片列表（JSON格式） |
| tag_list | longtext | 标签列表（JSON格式） |
| note_url | varchar(255) | 笔记URL |
| source_keyword | varchar(255) | 搜索来源关键词 |

## 数据访问方法

### 使用Python直接访问

#### 1. 异步方式（推荐）

MediaCrawler使用aiomysql进行异步数据库操作，以下是一个基本示例：

```python
import asyncio
import aiomysql
from config import db_config

async def fetch_notes():
    # 创建数据库连接
    conn = await aiomysql.connect(
        host=db_config.RELATION_DB_HOST,
        port=db_config.RELATION_DB_PORT,
        user=db_config.RELATION_DB_USER,
        password=db_config.RELATION_DB_PWD,
        db=db_config.RELATION_DB_NAME,
        charset='utf8mb4'  # 确保使用utf8mb4字符集以支持中文和表情符号
    )
    
    try:
        # 创建游标
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            # 执行查询
            await cursor.execute("SELECT note_id, title, `desc`, liked_count FROM xhs_note LIMIT 10")
            # 获取结果
            results = await cursor.fetchall()
            
            # 处理结果
            for row in results:
                print(f"笔记ID: {row['note_id']}")
                print(f"标题: {row['title']}")
                print(f"内容: {row['desc']}")
                print(f"点赞数: {row['liked_count']}")
                print("-" * 50)
                
    finally:
        # 关闭连接
        conn.close()

# 运行异步函数
asyncio.run(fetch_notes())
```

#### 2. 使用项目封装的数据库访问方法

MediaCrawler项目封装了数据库访问方法，可以直接使用：

```python
import asyncio
from db import async_db_obj

async def fetch_notes():
    # 执行查询
    results = await async_db_obj.fetch_all(
        "SELECT note_id, title, `desc`, liked_count FROM xhs_note LIMIT 10"
    )
    
    # 处理结果
    for row in results:
        print(f"笔记ID: {row['note_id']}")
        print(f"标题: {row['title']}")
        print(f"内容: {row['desc']}")
        print(f"点赞数: {row['liked_count']}")
        print("-" * 50)

# 运行异步函数
if __name__ == "__main__":
    asyncio.run(fetch_notes())
```

#### 3. 使用pandas进行数据分析

对于数据分析场景，推荐使用pandas库：

```python
import asyncio
import pandas as pd
import aiomysql
from config import db_config

async def export_to_pandas():
    # 创建数据库连接
    conn = await aiomysql.connect(
        host=db_config.RELATION_DB_HOST,
        port=db_config.RELATION_DB_PORT,
        user=db_config.RELATION_DB_USER,
        password=db_config.RELATION_DB_PWD,
        db=db_config.RELATION_DB_NAME,
        charset='utf8mb4'
    )
    
    try:
        # 使用pandas读取SQL查询结果
        query = "SELECT * FROM xhs_note WHERE source_keyword = '改色膜'"
        df = pd.read_sql(query, conn._connection)
        
        # 数据处理示例
        print(f"数据总量: {len(df)}")
        print(f"平均点赞数: {pd.to_numeric(df['liked_count']).mean()}")
        
        # 按点赞数排序
        df['liked_count_num'] = pd.to_numeric(df['liked_count'])
        top_notes = df.sort_values(by='liked_count_num', ascending=False).head(5)
        print("点赞最多的5条笔记:")
        print(top_notes[['note_id', 'title', 'liked_count_num']])
        
        # 保存为CSV文件
        df.to_csv('xhs_notes_analysis.csv', index=False, encoding='utf-8-sig')
        
    finally:
        # 关闭连接
        conn.close()

# 运行异步函数
if __name__ == "__main__":
    asyncio.run(export_to_pandas())
```

### 使用数据库查看器

项目提供了一个基于Rich库的数据库查看器（`db_viewer.py`），可以直观地查看数据库内容：

```bash
# 在项目根目录下运行显示完整数据库信息
python db_viewer.py

# 查看指定笔记的图片URL列表
python db_viewer.py --images <note_id>

# 例如
python db_viewer.py --images 643a637d000000000800ecfe
```

数据库查看器提供以下功能：

1. 显示数据库基本信息（表数量、大小等）
2. 显示表结构信息（记录数、创建时间等）
3. 显示数据统计信息（笔记总数、平均点赞数等）
4. 显示最受欢迎的笔记
5. 显示最新的笔记数据
6. 显示指定笔记的图片URL列表

您也可以根据需要修改`db_viewer.py`文件，添加自定义查询和展示逻辑。

### 使用SQL命令行

如果您熟悉SQL，可以直接使用MySQL命令行工具查询数据：

```bash
# 连接到Docker中的MySQL容器
docker exec -it media-crawler-mysql mysql -uroot -p123456 media_crawler

# 或者使用本地MySQL客户端
mysql -h localhost -u root -p123456 media_crawler
```

常用SQL查询示例：

```sql
-- 查询点赞数最多的10条小红书笔记
SELECT note_id, title, liked_count, nickname 
FROM xhs_note 
ORDER BY CAST(liked_count AS UNSIGNED) DESC 
LIMIT 10;

-- 按关键词查询笔记
SELECT note_id, title, `desc` 
FROM xhs_note 
WHERE title LIKE '%改色膜%' OR `desc` LIKE '%改色膜%';

-- 统计每个用户的笔记数量
SELECT nickname, COUNT(*) as note_count 
FROM xhs_note 
GROUP BY nickname 
ORDER BY note_count DESC;

-- 查询评论数最多的笔记及其评论
SELECT n.note_id, n.title, n.comment_count, c.content 
FROM xhs_note n 
JOIN xhs_note_comment c ON n.note_id = c.note_id 
ORDER BY CAST(n.comment_count AS UNSIGNED) DESC 
LIMIT 20;
```

## 图片数据处理

MediaCrawler抓取的小红书笔记包含图片URL列表，存储在`xhs_note`表的`image_list`字段中。这些图片URL是以逗号分隔的字符串形式存储的。

### 查看图片URL

您可以使用`db_viewer.py`脚本查看指定笔记的图片URL列表：

```bash
python db_viewer.py --images <note_id>
```

### 下载图片

以下是一个简单的Python脚本，用于下载指定笔记的所有图片：

```python
import asyncio
import aiohttp
import aiomysql
import os
from config import db_config

async def download_note_images(note_id):
    # 创建数据库连接
    conn = await aiomysql.connect(
        host=db_config.RELATION_DB_HOST,
        port=db_config.RELATION_DB_PORT,
        user=db_config.RELATION_DB_USER,
        password=db_config.RELATION_DB_PWD,
        db=db_config.RELATION_DB_NAME,
        charset='utf8mb4'
    )
    
    try:
        # 获取笔记数据
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("""
                SELECT note_id, title, image_list 
                FROM xhs_note 
                WHERE note_id = %s
            """, (note_id,))
            
            note = await cursor.fetchone()
            
            if not note or not note['image_list']:
                print(f"\u672a找到ID为 {note_id} 的笔记或该笔记没有图片")
                return
            
            # 创建保存目录
            save_dir = f"images/{note_id}"
            os.makedirs(save_dir, exist_ok=True)
            
            # 解析图片URL
            image_urls = note['image_list'].split(',')
            
            # 下载图片
            async with aiohttp.ClientSession() as session:
                for i, img_url in enumerate(image_urls, 1):
                    img_url = img_url.strip()
                    filename = f"{save_dir}/image_{i}.jpg"
                    
                    try:
                        async with session.get(img_url) as response:
                            if response.status == 200:
                                with open(filename, 'wb') as f:
                                    f.write(await response.read())
                                print(f"\u4e0b载图片 {i}/{len(image_urls)} 成功: {filename}")
                            else:
                                print(f"\u4e0b载图片 {i}/{len(image_urls)} 失败: HTTP状态码 {response.status}")
                    except Exception as e:
                        print(f"\u4e0b载图片 {i}/{len(image_urls)} 失败: {str(e)}")
            
            print(f"\u5df2完成笔记 '{note['title']}' 的图片下载")
    
    finally:
        # 关闭数据库连接
        conn.close()

# 使用示例
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        note_id = sys.argv[1]
        asyncio.run(download_note_images(note_id))
    else:
        print("\u8bf7提供笔记ID，例如: python download_images.py 643a637d000000000800ecfe")
```

将上述代码保存为`download_images.py`，然后运行：

```bash
python download_images.py <note_id>
```

### 图片分析

下载的图片可以用于各种分析目的，例如：

1. **内容识别**：使用计算机视觉库（如OpenCV、TensorFlow或PyTorch）识别图片中的对象、场景或文本。

2. **颜色分析**：分析图片的主要颜色和颜色分布。

3. **图像聚类**：根据图像特征将相似的图片分组。

4. **品牌标识识别**：识别图片中的品牌标识或商标。

以下是一个使用PIL和matplotlib分析图片主要颜色的简单示例：

```python
import os
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans

def analyze_image_colors(image_path, num_colors=5):
    # 打开图片
    img = Image.open(image_path)
    # 调整图片大小以加快处理
    img = img.resize((150, 150))
    # 转换为数组
    img_array = np.array(img)
    # 重塑数组为2D（像素数，3）
    pixels = img_array.reshape(-1, 3)
    
    # 使用K-means聚类找出主要颜色
    kmeans = KMeans(n_clusters=num_colors)
    kmeans.fit(pixels)
    
    # 获取颜色中心
    colors = kmeans.cluster_centers_.astype(int)
    # 获取每个颜色的像素数量
    counts = np.bincount(kmeans.labels_)
    # 按频率排序
    sorted_indices = np.argsort(counts)[::-1]
    sorted_colors = colors[sorted_indices]
    sorted_counts = counts[sorted_indices]
    total_pixels = sum(sorted_counts)
    
    # 显示结果
    plt.figure(figsize=(12, 6))
    
    # 显示原始图片
    plt.subplot(1, 2, 1)
    plt.imshow(img)
    plt.title("原始图片")
    plt.axis('off')
    
    # 显示颜色分布
    plt.subplot(1, 2, 2)
    color_bars = np.zeros((100, num_colors*50, 3), dtype=np.uint8)
    for i in range(num_colors):
        color_bars[:, i*50:(i+1)*50] = sorted_colors[i]
    plt.imshow(color_bars)
    plt.title("主要颜色分布")
    plt.axis('off')
    
    # 显示每个颜色的百分比
    for i in range(num_colors):
        percentage = sorted_counts[i] / total_pixels * 100
        color_rgb = sorted_colors[i]
        plt.text(i*50 + 25, 120, f"RGB: {color_rgb}\n{percentage:.1f}%", 
                ha='center', va='top', fontsize=8)
    
    plt.tight_layout()
    plt.savefig(f"{os.path.splitext(image_path)[0]}_analysis.png")
    plt.close()
    
    print(f"图片 {os.path.basename(image_path)} 的主要颜色分析完成")
    return sorted_colors, sorted_counts / total_pixels

# 分析指定笔记的所有图片
 def analyze_note_images(note_id):
    image_dir = f"images/{note_id}"
    if not os.path.exists(image_dir):
        print(f"目录 {image_dir} 不存在，请先下载图片")
        return
    
    image_files = [f for f in os.listdir(image_dir) if f.endswith('.jpg')]
    if not image_files:
        print(f"没有找到图片文件")
        return
    
    for image_file in image_files:
        image_path = os.path.join(image_dir, image_file)
        analyze_image_colors(image_path)

# 使用示例
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        note_id = sys.argv[1]
        analyze_note_images(note_id)
    else:
        print("\u8bf7提供笔记ID，例如: python analyze_colors.py 643a637d000000000800ecfe")
```

## 数据分析示例

### 1. 热门话题分析

```python
import asyncio
import pandas as pd
import re
import jieba
import jieba.analyse
from collections import Counter
from db import async_db_obj

async def analyze_hot_topics():
    # 获取所有笔记内容
    results = await async_db_obj.fetch_all(
        "SELECT `desc` FROM xhs_note WHERE `desc` IS NOT NULL AND `desc` != ''"
    )
    
    # 提取所有文本
    all_text = " ".join([row['desc'] for row in results])
    
    # 提取话题标签 (#话题#)
    topics = re.findall(r'#(.*?)#', all_text)
    topic_counter = Counter(topics)
    
    print("热门话题TOP10:")
    for topic, count in topic_counter.most_common(10):
        print(f"{topic}: {count}次")
    
    # 提取关键词
    keywords = jieba.analyse.extract_tags(all_text, topK=20, withWeight=True)
    
    print("\n热门关键词TOP20:")
    for keyword, weight in keywords:
        print(f"{keyword}: {weight:.4f}")

# 运行分析
if __name__ == "__main__":
    asyncio.run(analyze_hot_topics())
```

### 2. 用户互动分析

```python
import asyncio
import pandas as pd
import matplotlib.pyplot as plt
from db import async_db_obj

async def analyze_user_engagement():
    # 获取笔记互动数据
    results = await async_db_obj.fetch_all("""
        SELECT 
            note_id, 
            liked_count, 
            collected_count, 
            comment_count, 
            share_count,
            time
        FROM xhs_note
    """)
    
    # 转换为DataFrame
    df = pd.DataFrame(results)
    
    # 转换数值类型
    for col in ['liked_count', 'collected_count', 'comment_count', 'share_count']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 转换时间
    df['date'] = pd.to_datetime(df['time'], unit='ms')
    df['date'] = df['date'].dt.date
    
    # 按日期分组计算平均互动
    daily_engagement = df.groupby('date').agg({
        'liked_count': 'mean',
        'collected_count': 'mean',
        'comment_count': 'mean',
        'share_count': 'mean'
    }).reset_index()
    
    print("每日平均互动数据:")
    print(daily_engagement)
    
    # 计算互动比率
    df['save_rate'] = df['collected_count'] / df['liked_count']
    df['comment_rate'] = df['comment_count'] / df['liked_count']
    
    print("\n互动比率统计:")
    print(f"平均收藏/点赞比: {df['save_rate'].mean():.2f}")
    print(f"平均评论/点赞比: {df['comment_rate'].mean():.2f}")
    
    # 导出分析结果
    daily_engagement.to_csv('daily_engagement.csv', index=False, encoding='utf-8-sig')

# 运行分析
if __name__ == "__main__":
    asyncio.run(analyze_user_engagement())
```

### 3. 内容情感分析

使用第三方NLP库进行情感分析：

```python
import asyncio
import pandas as pd
from snownlp import SnowNLP
from db import async_db_obj

async def sentiment_analysis():
    # 获取评论数据
    results = await async_db_obj.fetch_all(
        "SELECT comment_id, content FROM xhs_note_comment WHERE content IS NOT NULL LIMIT 1000"
    )
    
    # 分析情感
    sentiments = []
    for row in results:
        try:
            # SnowNLP情感分析，返回值在0-1之间，越接近1越正面
            sentiment = SnowNLP(row['content']).sentiments
            sentiments.append({
                'comment_id': row['comment_id'],
                'content': row['content'],
                'sentiment': sentiment,
                'attitude': 'positive' if sentiment > 0.6 else ('negative' if sentiment < 0.4 else 'neutral')
            })
        except:
            continue
    
    # 转换为DataFrame
    df = pd.DataFrame(sentiments)
    
    # 统计情感分布
    sentiment_counts = df['attitude'].value_counts()
    print("评论情感分布:")
    print(sentiment_counts)
    
    # 导出分析结果
    df.to_csv('comment_sentiment.csv', index=False, encoding='utf-8-sig')

# 运行分析
if __name__ == "__main__":
    asyncio.run(sentiment_analysis())
```

## 常见问题解答

### 1. 如何处理中文乱码问题？

确保在连接数据库时指定正确的字符集：

```python
conn = await aiomysql.connect(
    # 其他参数...
    charset='utf8mb4'  # 支持中文和表情符号
)
```

在导出CSV文件时，使用`utf-8-sig`编码：

```python
df.to_csv('output.csv', encoding='utf-8-sig')
```

### 2. 如何优化查询性能？

- 使用索引字段进行查询（如`note_id`, `user_id`等）
- 限制查询结果数量（使用`LIMIT`）
- 只选择需要的字段，避免`SELECT *`
- 对于大数据量查询，考虑分批处理

### 3. 如何处理数值类型字段？

数据库中的点赞数、收藏数等字段存储为字符串类型，在分析时需要转换为数值类型：

```python
df['liked_count'] = pd.to_numeric(df['liked_count'], errors='coerce')
```

### 4. 如何处理时间戳字段？

数据库中的时间字段存储为Unix时间戳（毫秒），需要转换为日期时间：

```python
from datetime import datetime

# Python原生转换
timestamp_ms = 1679468400000  # 示例时间戳
datetime_obj = datetime.fromtimestamp(timestamp_ms / 1000)
formatted_date = datetime_obj.strftime("%Y-%m-%d %H:%M:%S")

# 使用pandas转换
df['datetime'] = pd.to_datetime(df['time'], unit='ms')
```

## 最佳实践

### 数据访问

1. **使用连接池**：对于频繁的数据库操作，使用连接池可以提高性能。
2. **异步操作**：使用异步方式进行数据库操作，避免阻塞主线程。
3. **参数化查询**：使用参数化查询防止SQL注入。

```python
await cursor.execute(
    "SELECT * FROM xhs_note WHERE source_keyword = %s", 
    (keyword,)
)
```

### 数据处理

1. **数据清洗**：处理缺失值、异常值和重复数据。
2. **数据转换**：将字符串转换为适当的数据类型（数值、日期等）。
3. **数据规范化**：标准化数据格式，便于比较和分析。

### 数据分析

1. **使用专业工具**：利用pandas、numpy等库进行数据分析。
2. **可视化**：使用matplotlib、seaborn或plotly等库进行数据可视化。
3. **导出结果**：将分析结果导出为CSV、Excel或JSON格式，便于共享和进一步处理。

### 数据安全

1. **敏感信息保护**：避免在代码中硬编码数据库凭证。
2. **最小权限原则**：使用只有必要权限的数据库用户。
3. **数据备份**：定期备份重要数据。

---

本文档提供了MediaCrawler数据使用的基本指南。随着项目的发展，可能会有新的数据表和字段添加，请定期查看最新的数据库结构。如有任何问题，请参考项目文档或联系项目维护者。
