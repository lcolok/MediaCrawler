# MediaCrawler 图片路径获取指南

本文档简要介绍如何从 MediaCrawler 数据库中获取小红书笔记图片的本地路径。

## 查看图片路径的方法

### 方法一：使用 db_viewer.py 命令行工具

我们提供了几种便捷的命令行选项来查看图片路径：

```bash
# 查看特定笔记的图片信息（包括URL和本地路径）
python db_viewer.py --images <笔记ID>

# 查看所有已下载图片的笔记
python db_viewer.py --downloaded

# 查看所有已下载图片的笔记及其详细本地路径
python db_viewer.py --downloaded --paths

# 查看所有未下载图片的笔记
python db_viewer.py --not-downloaded
```

### 方法二：直接查询数据库

如果需要在自己的代码中获取图片路径，可以使用以下 SQL 查询：

```python
import aiomysql
from config import db_config

async def get_image_paths(note_id):
    """获取指定笔记的本地图片路径"""
    conn = await aiomysql.connect(
        host=db_config.RELATION_DB_HOST,
        port=db_config.RELATION_DB_PORT,
        user=db_config.RELATION_DB_USER,
        password=db_config.RELATION_DB_PWD,
        db=db_config.RELATION_DB_NAME,
        charset='utf8mb4'
    )
    
    async with conn.cursor(aiomysql.DictCursor) as cursor:
        await cursor.execute("""
            SELECT note_id, title, image_list, local_image_paths 
            FROM xhs_note 
            WHERE note_id = %s
        """, (note_id,))
        
        note = await cursor.fetchone()
        
        if note and note['local_image_paths']:
            # 解析本地路径列表
            local_paths = note['local_image_paths'].split(',')
            return local_paths
        
        return []
    
    # 别忘了关闭连接
    conn.close()
```

## 图片路径格式

本地图片路径的默认格式为：

```
/Users/lco/GitHub/MediaCrawler/data/xhs/images/<笔记ID>/<序号>.jpg
```

例如：
```
/Users/lco/GitHub/MediaCrawler/data/xhs/images/643a637d000000000800ecfe/0.jpg
```

## 批量处理图片的示例代码

```python
import asyncio
import os
from PIL import Image

async def process_note_images(note_id):
    """处理指定笔记的所有图片"""
    paths = await get_image_paths(note_id)
    
    for path in paths:
        if os.path.exists(path):
            # 这里可以添加您的图片处理代码
            # 例如：调整大小、添加水印、提取特征等
            img = Image.open(path)
            print(f"处理图片: {path}, 尺寸: {img.size}")
            
            # 示例：调整图片大小
            # resized_img = img.resize((800, 600))
            # resized_img.save(path.replace('.jpg', '_resized.jpg'))

# 使用示例
if __name__ == "__main__":
    note_id = "643a637d000000000800ecfe"  # 替换为您需要处理的笔记ID
    asyncio.run(process_note_images(note_id))
```

## 注意事项

1. 确保在使用图片路径前检查文件是否存在
2. 图片路径字段 `local_image_paths` 可能为空，表示图片尚未下载
3. 如果需要下载图片，可以使用 `download_images.py` 脚本
4. 图片路径是以逗号分隔的字符串，需要使用 `split(',')` 方法解析

希望这份指南对您的开发工作有所帮助！
