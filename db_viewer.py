#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库查看器 - 使用Rich库美观展示MediaCrawler数据库内容
"""

import asyncio
import sys
from datetime import datetime

import aiomysql
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

# 导入项目配置
sys.path.append('.')
from config import db_config

# 创建Rich控制台
console = Console()


async def connect_to_db():
    """连接到数据库"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]正在连接到数据库..."),
        transient=True,
    ) as progress:
        progress.add_task("连接", total=None)
        try:
            # 创建数据库连接
            conn = await aiomysql.connect(
                host=db_config.RELATION_DB_HOST,
                port=db_config.RELATION_DB_PORT,
                user=db_config.RELATION_DB_USER,
                password=db_config.RELATION_DB_PWD,
                db=db_config.RELATION_DB_NAME,
                charset='utf8mb4'  # 确保使用utf8mb4字符集以支持中文和表情符号
            )
            console.print("[bold green]✓[/] 数据库连接成功！")
            return conn
        except Exception as e:
            console.print(f"[bold red]✗[/] 数据库连接失败: {str(e)}")
            return None


async def show_db_info(conn):
    """显示数据库基本信息"""
    console.print(Panel.fit(
        "[bold]数据库基本信息[/]",
        border_style="blue"
    ))
    
    async with conn.cursor() as cursor:
        # 获取数据库版本
        await cursor.execute("SELECT VERSION()")
        version = await cursor.fetchone()
        
        # 获取数据库表列表
        await cursor.execute("SHOW TABLES")
        tables = await cursor.fetchall()
        
        # 获取数据库大小
        await cursor.execute("""
            SELECT 
                table_schema AS '数据库',
                ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS '大小(MB)'
            FROM information_schema.tables
            WHERE table_schema = %s
            GROUP BY table_schema
        """, (db_config.RELATION_DB_NAME,))
        db_size = await cursor.fetchone()
    
    info_table = Table(show_header=False, box=None)
    info_table.add_column("属性", style="cyan")
    info_table.add_column("值", style="green")
    
    info_table.add_row("数据库名称", db_config.RELATION_DB_NAME)
    info_table.add_row("数据库主机", db_config.RELATION_DB_HOST)
    info_table.add_row("MySQL版本", version[0] if version else "未知")
    info_table.add_row("表数量", str(len(tables)))
    info_table.add_row("数据库大小", f"{db_size[1] if db_size else 0} MB")
    info_table.add_row("当前时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    console.print(info_table)


async def show_table_info(conn):
    """显示表结构信息"""
    console.print(Panel.fit(
        "[bold]数据表信息[/]",
        border_style="blue"
    ))
    
    async with conn.cursor() as cursor:
        # 获取数据库表列表
        await cursor.execute("SHOW TABLES")
        tables = await cursor.fetchall()
        
        # 创建表格
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("表名")
        table.add_column("记录数")
        table.add_column("创建时间")
        table.add_column("更新时间")
        
        for table_name in tables:
            # 获取表记录数
            await cursor.execute(f"SELECT COUNT(*) FROM `{table_name[0]}`")
            count = await cursor.fetchone()
            
            # 获取表创建时间和更新时间
            await cursor.execute(f"""
                SELECT 
                    CREATE_TIME, 
                    UPDATE_TIME
                FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = %s
            """, (db_config.RELATION_DB_NAME, table_name[0]))
            
            times = await cursor.fetchone()
            create_time = times[0].strftime("%Y-%m-%d %H:%M:%S") if times and times[0] else "未知"
            update_time = times[1].strftime("%Y-%m-%d %H:%M:%S") if times and times[1] else "未知"
            
            table.add_row(
                table_name[0],
                str(count[0]),
                create_time,
                update_time
            )
    
    console.print(table)


async def show_xhs_notes(conn, limit=10, batch_id=None):
    """显示小红书笔记数据"""
    title_text = f"小红书笔记数据 (前{limit}条)"
    if batch_id:
        title_text = f"小红书笔记数据 (批次ID: {batch_id})"
    
    console.print(Panel.fit(
        f"[bold]{title_text}[/]",
        border_style="red"
    ))
    
    async with conn.cursor(aiomysql.DictCursor) as cursor:
        # 构建查询条件
        query_condition = ""
        query_params = []
        
        if batch_id:
            query_condition = "WHERE batch_id = %s"
            query_params = [batch_id]
        
        # 获取小红书笔记数据
        query = f"""
            SELECT 
                note_id, 
                title, 
                `desc`, 
                liked_count, 
                collected_count, 
                comment_count,
                share_count,
                nickname,
                time,
                image_list,
                local_image_paths,
                batch_id
            FROM xhs_note 
            {query_condition}
            ORDER BY time DESC
            LIMIT {limit}
        """
        
        await cursor.execute(query, query_params)
        
        notes = await cursor.fetchall()
        
        if not notes:
            console.print("[yellow]暂无小红书笔记数据[/]")
            return
        
        # 创建表格
        table = Table(show_header=True, header_style="bold red")
        table.add_column("笔记ID", style="dim", width=12)
        table.add_column("标题", style="green")
        table.add_column("内容摘要", width=30)
        table.add_column("点赞", justify="right")
        table.add_column("收藏", justify="right")
        table.add_column("评论", justify="right")
        table.add_column("分享", justify="right")
        table.add_column("作者", style="blue")
        table.add_column("创建时间", style="magenta")
        table.add_column("图片数量", justify="right")
        table.add_column("已下载", justify="right")
        table.add_column("批次ID", style="cyan")
        
        for note in notes:
            # 处理内容摘要（截取前30个字符）
            desc = note['desc'] if note['desc'] else ""
            desc_summary = (desc[:27] + "...") if len(desc) > 30 else desc
            
            # 格式化创建时间 (time是Unix时间戳，需要转换)
            from datetime import datetime
            create_time = datetime.fromtimestamp(note['time']/1000).strftime("%Y-%m-%d %H:%M") if note['time'] else "未知"
            
            # 处理图片列表
            image_count = 0
            downloaded_count = 0
            if note['image_list']:
                try:
                    # 图片URL是以逗号分隔的字符串
                    image_urls = note['image_list'].split(',')
                    image_count = len(image_urls)
                    
                    # 处理本地图片路径
                    if note['local_image_paths']:
                        local_paths = note['local_image_paths'].split(',')
                        downloaded_count = len(local_paths)
                except:
                    pass
            
            # 获取批次ID
            batch_id_display = note.get('batch_id', '未知')
            if batch_id_display and batch_id_display.startswith('batch_'):
                batch_id_display = batch_id_display[6:]  # 移除 'batch_' 前缀以简化显示
            
            table.add_row(
                note['note_id'],
                note['title'] or "无标题",
                desc_summary,
                str(note['liked_count']),
                str(note['collected_count']),
                str(note['comment_count']),
                str(note['share_count']),
                note['nickname'] or "未知",
                create_time,
                str(image_count),
                f"{downloaded_count}/{image_count}" if image_count > 0 else "0/0",
                batch_id_display or "未知"
            )
        
        console.print(table)


async def show_batch_ids(conn):
    """显示所有批次ID及其包含的笔记数量"""
    console.print(Panel.fit(
        "[bold]批次ID统计[/]",
        border_style="cyan"
    ))
    
    async with conn.cursor(aiomysql.DictCursor) as cursor:
        # 获取所有批次ID及其笔记数量
        await cursor.execute("""
            SELECT 
                batch_id, 
                COUNT(*) as note_count,
                MIN(time) as first_note_time,
                MAX(time) as last_note_time
            FROM xhs_note 
            WHERE batch_id IS NOT NULL AND batch_id != ''
            GROUP BY batch_id
            ORDER BY last_note_time DESC
        """)
        
        batches = await cursor.fetchall()
        
        if not batches:
            console.print("[yellow]暂无批次ID数据[/]")
            return
        
        # 创建表格
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("批次ID", style="green")
        table.add_column("笔记数量", justify="right", style="blue")
        table.add_column("开始时间", style="magenta")
        table.add_column("结束时间", style="magenta")
        table.add_column("持续时间", style="yellow")
        
        for batch in batches:
            batch_id = batch['batch_id']
            # 如果批次ID以 'batch_' 开头，则移除前缀以简化显示
            if batch_id and batch_id.startswith('batch_'):
                display_id = batch_id[6:]
            else:
                display_id = batch_id or "未知"
            
            # 格式化时间
            first_time = datetime.fromtimestamp(batch['first_note_time']/1000).strftime("%Y-%m-%d %H:%M") if batch['first_note_time'] else "未知"
            last_time = datetime.fromtimestamp(batch['last_note_time']/1000).strftime("%Y-%m-%d %H:%M") if batch['last_note_time'] else "未知"
            
            # 计算持续时间
            duration = "未知"
            if batch['first_note_time'] and batch['last_note_time']:
                duration_seconds = (batch['last_note_time'] - batch['first_note_time']) / 1000
                if duration_seconds < 60:
                    duration = f"{int(duration_seconds)}秒"
                elif duration_seconds < 3600:
                    duration = f"{int(duration_seconds/60)}分钟"
                else:
                    duration = f"{duration_seconds/3600:.1f}小时"
            
            table.add_row(
                display_id,
                str(batch['note_count']),
                first_time,
                last_time,
                duration
            )
        
        console.print(table)


async def show_statistics(conn):
    """显示统计信息"""
    console.print(Panel.fit(
        "[bold]数据统计[/]",
        border_style="green"
    ))
    
    async with conn.cursor() as cursor:
        # 获取笔记总数
        await cursor.execute("SELECT COUNT(*) FROM xhs_note")
        result = await cursor.fetchone()
        note_count = result[0] if result else 0
        
        # 获取用户总数
        await cursor.execute("SELECT COUNT(DISTINCT user_id) FROM xhs_note")
        result = await cursor.fetchone()
        user_count = result[0] if result else 0
        
        # 获取平均点赞数
        await cursor.execute("SELECT AVG(liked_count) FROM xhs_note")
        result = await cursor.fetchone()
        avg_likes = result[0] if result and result[0] is not None else 0
        
        # 获取平均收藏数
        await cursor.execute("SELECT AVG(collected_count) FROM xhs_note")
        result = await cursor.fetchone()
        avg_collects = result[0] if result and result[0] is not None else 0
        
        # 获取平均评论数
        await cursor.execute("SELECT AVG(comment_count) FROM xhs_note")
        result = await cursor.fetchone()
        avg_comments = result[0] if result and result[0] is not None else 0
    
    stats_table = Table(title="数据统计概览", show_header=True, header_style="bold green")
    stats_table.add_column("指标", style="cyan")
    stats_table.add_column("数值", style="yellow", justify="right")
    
    stats_table.add_row("笔记总数", f"{note_count:,}")
    stats_table.add_row("用户总数", f"{user_count:,}")
    stats_table.add_row("平均点赞数", f"{avg_likes:.2f}" if avg_likes else "0")
    stats_table.add_row("平均收藏数", f"{avg_collects:.2f}" if avg_collects else "0")
    stats_table.add_row("平均评论数", f"{avg_comments:.2f}" if avg_comments else "0")
    
    console.print(stats_table)


async def show_top_notes(conn, limit=5):
    """显示最受欢迎的笔记"""
    console.print(Panel.fit(
        f"[bold]最受欢迎的{limit}条笔记[/]",
        border_style="yellow"
    ))
    
    async with conn.cursor(aiomysql.DictCursor) as cursor:
        # 获取点赞最多的笔记
        await cursor.execute(f"""
            SELECT 
                note_id, 
                title, 
                liked_count, 
                collected_count,
                nickname
            FROM xhs_note 
            ORDER BY liked_count DESC
            LIMIT {limit}
        """)
        
        top_notes = await cursor.fetchall()
        
        if not top_notes:
            console.print("[yellow]暂无笔记数据[/]")
            return
        
        # 创建表格
        table = Table(show_header=True, header_style="bold yellow")
        table.add_column("笔记ID", style="dim", width=12)
        table.add_column("标题", style="green")
        table.add_column("点赞", justify="right", style="red")
        table.add_column("收藏", justify="right", style="blue")
        table.add_column("作者", style="magenta")
        
        for note in top_notes:
            table.add_row(
                note['note_id'],
                note['title'] or "无标题",
                str(note['liked_count']),
                str(note['collected_count']),
                note['nickname'] or "未知"
            )
        
        console.print(table)


async def show_note_images(conn, note_id):
    """显示指定笔记的图片URL列表和本地图片路径"""
    console.print(Panel.fit(
        f"[bold]笔记 {note_id} 的图片信息[/]",
        border_style="blue"
    ))
    
    async with conn.cursor(aiomysql.DictCursor) as cursor:
        # 获取笔记数据
        await cursor.execute("""
            SELECT note_id, title, image_list, local_image_paths 
            FROM xhs_note 
            WHERE note_id = %s
        """, (note_id,))
        
        note = await cursor.fetchone()
        
        if not note:
            console.print(f"[yellow]未找到ID为 {note_id} 的笔记[/]")
            return
        
        console.print(f"笔记标题: [green]{note['title'] or '无标题'}[/]")
        
        # 解析图片列表
        if not note['image_list']:
            console.print("[yellow]该笔记没有图片[/]")
            return
            
        try:
            # 图片URL是以逗号分隔的字符串
            image_urls = note['image_list'].split(',')
            
            if not image_urls:
                console.print("[yellow]该笔记没有图片[/]")
                return
            
            # 解析本地图片路径列表（如果有）
            local_paths = []
            if note['local_image_paths']:
                local_paths = note['local_image_paths'].split(',')
            
            # 创建表格
            table = Table(show_header=True, header_style="bold blue")
            table.add_column("序号", style="dim", justify="right")
            table.add_column("图片URL", style="green", width=60)
            table.add_column("本地路径", style="cyan", width=40)
            table.add_column("状态", style="magenta", width=10)
            
            for i, img_url in enumerate(image_urls, 1):
                # 获取对应的本地路径（如果存在）
                local_path = "未下载"
                status = "❌ 未下载"
                
                if i <= len(local_paths) and local_paths[i-1].strip():
                    local_path = local_paths[i-1].strip()
                    status = "✅ 已下载"
                
                table.add_row(str(i), img_url.strip(), local_path, status)
            
            # 显示下载统计
            downloaded_count = sum(1 for path in local_paths if path.strip())
            console.print(f"\n总图片数: [bold]{len(image_urls)}[/] | 已下载: [bold green]{downloaded_count}[/] | 未下载: [bold red]{len(image_urls) - downloaded_count}[/]")
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]解析图片列表时出错: {str(e)}[/]")

async def show_download_status(conn, show_downloaded=True, show_paths=False):
    """显示已下载或未下载图片的笔记"""
    status_text = "已下载" if show_downloaded else "未下载"
    path_text = "（包含本地路径）" if show_paths else ""
    console.print(Panel.fit(
        f"[bold]小红书笔记 - {status_text}图片状态{path_text}[/]",
        border_style="green" if show_downloaded else "red"
    ))
    
    async with conn.cursor(aiomysql.DictCursor) as cursor:
        # 构建查询条件
        query_condition = "local_image_paths IS NOT NULL AND local_image_paths != ''" if show_downloaded else "local_image_paths IS NULL OR local_image_paths = ''"
        
        # 获取笔记数据
        await cursor.execute(f"""
            SELECT 
                note_id, 
                title, 
                image_list,
                local_image_paths,
                nickname,
                time
            FROM xhs_note 
            WHERE {query_condition}
            ORDER BY time DESC
        """)
        
        notes = await cursor.fetchall()
        
        if not notes:
            console.print(f"[yellow]暂无{status_text}图片的笔记[/]")
            return
        
        # 创建表格
        table = Table(show_header=True, header_style="bold green" if show_downloaded else "bold red")
        table.add_column("笔记ID", style="dim", width=12)
        table.add_column("标题", style="green")
        table.add_column("作者", style="blue")
        table.add_column("创建时间", style="magenta")
        table.add_column("图片总数", justify="right")
        table.add_column("已下载数", justify="right")
        table.add_column("下载比例", justify="right")
        
        for note in notes:
            # 处理图片列表
            image_count = 0
            downloaded_count = 0
            
            if note['image_list']:
                try:
                    # 图片URL是以逗号分隔的字符串
                    image_urls = note['image_list'].split(',')
                    image_count = len(image_urls)
                    
                    # 处理本地图片路径
                    if note['local_image_paths']:
                        local_paths = note['local_image_paths'].split(',')
                        downloaded_count = sum(1 for path in local_paths if path.strip())
                except Exception as e:
                    console.print(f"[red]解析图片列表时出错: {str(e)}[/]")
            
            # 格式化创建时间
            create_time = datetime.fromtimestamp(note['time']/1000).strftime("%Y-%m-%d %H:%M") if note['time'] else "未知"
            
            # 计算下载比例
            download_ratio = f"{downloaded_count}/{image_count}"
            percentage = f"{(downloaded_count/image_count)*100:.1f}%" if image_count > 0 else "0%"
            
            table.add_row(
                note['note_id'],
                note['title'] or "无标题",
                note['nickname'] or "未知",
                create_time,
                str(image_count),
                str(downloaded_count),
                f"{download_ratio} ({percentage})"
            )
        
        console.print(table)
        console.print(f"\n总计: [bold]{len(notes)}[/] 条{status_text}图片的笔记")
        
        # 如果需要显示路径信息，并且是已下载的笔记
        if show_paths and show_downloaded:
            console.print("\n")
            console.print(Panel.fit(
                "[bold]本地图片路径详情[/]",
                border_style="cyan"
            ))
            
            for note in notes:
                console.print(f"\n[bold cyan]笔记ID:[/] [green]{note['note_id']}[/] - [bold]标题:[/] {note['title'] or '无标题'}")
                
                if note['image_list'] and note['local_image_paths']:
                    try:
                        image_urls = note['image_list'].split(',')
                        local_paths = note['local_image_paths'].split(',')
                        
                        path_table = Table(show_header=True, header_style="bold blue")
                        path_table.add_column("序号", style="dim", justify="right")
                        path_table.add_column("本地路径", style="green")
                        
                        for i, path in enumerate(local_paths, 1):
                            if path.strip():
                                path_table.add_row(str(i), path.strip())
                        
                        console.print(path_table)
                    except Exception as e:
                        console.print(f"[red]解析路径时出错: {str(e)}[/]")


async def main():
    """主函数"""
    console.print(Text("MediaCrawler 数据库查看器", style="bold cyan underline"), justify="center")
    console.print("使用Rich库美观展示数据库内容\n", style="italic", justify="center")
    
    # 检查命令行参数
    show_images_only = False
    show_downloaded = False
    show_not_downloaded = False
    show_paths = False
    show_batch_info = False
    batch_id = None
    note_id = None
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--images' and len(sys.argv) > 2:
            show_images_only = True
            note_id = sys.argv[2]
        elif sys.argv[1] == '--downloaded':
            show_downloaded = True
            # 检查是否还有--paths参数
            if len(sys.argv) > 2 and sys.argv[2] == '--paths':
                show_paths = True
        elif sys.argv[1] == '--not-downloaded':
            show_not_downloaded = True
        elif sys.argv[1] == '--batches':
            show_batch_info = True
        elif sys.argv[1] == '--batch' and len(sys.argv) > 2:
            batch_id = sys.argv[2]
    
    # 连接数据库
    conn = await connect_to_db()
    if not conn:
        return
    
    try:
        if show_images_only:
            # 只显示指定笔记的图片URL列表
            await show_note_images(conn, note_id)
        elif show_downloaded:
            # 显示已下载图片的笔记
            await show_download_status(conn, show_downloaded=True, show_paths=show_paths)
        elif show_not_downloaded:
            # 显示未下载图片的笔记
            await show_download_status(conn, show_downloaded=False)
        elif show_batch_info:
            # 显示批次ID信息
            await show_batch_ids(conn)
        elif batch_id:
            # 显示指定批次ID的笔记
            await show_xhs_notes(conn, limit=100, batch_id=batch_id)
        else:
            # 显示完整的数据库信息
            # 显示数据库基本信息
            await show_db_info(conn)
            console.print()
            
            # 显示表结构信息
            await show_table_info(conn)
            console.print()
            
            # 显示统计信息
            await show_statistics(conn)
            console.print()
            
            # 显示最受欢迎的笔记
            await show_top_notes(conn)
            console.print()
            
            # 显示小红书笔记数据
            await show_xhs_notes(conn)
        
    except Exception as e:
        console.print(f"[bold red]发生错误:[/] {str(e)}")
    finally:
        # 关闭数据库连接
        conn.close()
        console.print("\n[bold green]数据库连接已关闭[/]")


if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main())
