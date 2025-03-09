import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import yt_dlp
import json
from io import BytesIO
import requests

# 设置页面配置
st.set_page_config(
    page_title="YouTube 数据爬取工具",
    page_icon="🎥",
    layout="wide"
)

# 初始化会话状态
if 'stop_search' not in st.session_state:
    st.session_state.stop_search = False
if 'current_results' not in st.session_state:
    st.session_state.current_results = None

# 添加标题和说明
st.title("🎥 YouTube 数据爬取工具")
st.markdown("""
这个工具可以帮助你搜索和获取 YouTube 视频的相关数据。
请在下方输入搜索关键词和筛选条件来开始搜索。
""")

# 侧边栏配置
with st.sidebar:
    st.header("搜索配置")
    search_query = st.text_input("搜索关键词")
    
    # 高级筛选条件
    st.subheader("高级筛选")
    
    # 结果数量
    max_results = st.number_input("最大结果数", min_value=1, max_value=500, value=30)
    
    # 视频时长筛选
    st.write("视频时长筛选")
    duration_filter = st.selectbox(
        "时长范围",
        ["全部", "短视频 (< 4分钟)", "中等 (4-20分钟)", "长视频 (> 20分钟)"]
    )
    
    # 上传时间筛选
    st.write("上传时间筛选")
    upload_date_filter = st.selectbox(
        "上传时间",
        ["全部", "今天", "本周", "本月", "今年"]
    )
    
    # 排序方式
    sort_by = st.selectbox(
        "排序方式",
        ["相关度", "上传时间", "观看次数", "评分"]
    )
    
    # 显示选项
    st.subheader("显示选项")
    show_preview = st.checkbox("显示视频预览", value=False)
    include_description = st.checkbox("获取视频描述", value=True)
    
    search_button = st.button("开始搜索")
    
    # 添加停止按钮
    if st.session_state.current_results is not None:
        if st.button("停止搜索"):
            st.session_state.stop_search = True

def format_duration(duration_seconds):
    """将秒数格式化为可读时间"""
    try:
        if not duration_seconds:
            return "未知"
        minutes, seconds = divmod(int(duration_seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    except:
        return str(duration_seconds)

def format_number(number):
    """格式化数字（添加千位分隔符）"""
    try:
        return "{:,}".format(int(number))
    except:
        return str(number)

def get_thumbnail_url(entry):
    """获取最佳质量的缩略图URL"""
    try:
        if 'id' in entry:
            return f"https://i.ytimg.com/vi/{entry['id']}/hqdefault.jpg"
    except:
        pass
    return None

def filter_video(video, duration_filter, upload_date_filter):
    """根据条件筛选视频"""
    try:
        if duration_filter != "全部":
            duration = int(video.get('原始时长(秒)', 0))
            if duration == 0:  # 如果无法获取时长，则不过滤
                return True
            if duration_filter == "短视频 (< 4分钟)" and duration >= 240:
                return False
            elif duration_filter == "中等 (4-20分钟)" and (duration < 240 or duration > 1200):
                return False
            elif duration_filter == "长视频 (> 20分钟)" and duration <= 1200:
                return False

        if upload_date_filter != "全部":
            upload_date = video.get('发布时间', '')
            if not upload_date or upload_date == 'N/A':  # 如果无法获取日期，则不过滤
                return True
            try:
                upload_date = datetime.strptime(upload_date, '%Y%m%d')
                now = datetime.now()
                if upload_date_filter == "今天" and upload_date.date() != now.date():
                    return False
                elif upload_date_filter == "本周" and (now - upload_date).days > 7:
                    return False
                elif upload_date_filter == "本月" and (now - upload_date).days > 30:
                    return False
                elif upload_date_filter == "今年" and upload_date.year != now.year:
                    return False
            except:
                return True  # 如果日期格式错误，则不过滤

        return True
    except:
        return True

def process_video(entry):
    """处理单个视频数据"""
    try:
        if not entry:
            return None
            
        # 处理时长
        duration = entry.get('duration')
        if duration is None:
            duration = 0
        try:
            duration = int(duration)
        except:
            duration = 0
            
        video_data = {
            "视频ID": entry.get('id', 'N/A'),
            "标题": entry.get('title', 'N/A'),
            "频道名": entry.get('uploader', 'N/A'),
            "发布时间": entry.get('upload_date', 'N/A'),
            "观看次数": format_number(entry.get('view_count', 0)),
            "时长": format_duration(duration),
            "原始时长(秒)": duration,
            "缩略图": get_thumbnail_url(entry),
            "点赞数": format_number(entry.get('like_count', 0)),
            "描述": entry.get('description', '') if include_description else ''
        }
        
        return video_data
    except Exception as e:
        st.error(f"处理视频信息时出错: {str(e)}")
        return None

def search_videos(query, max_results):
    """使用 yt-dlp 搜索视频"""
    try:
        # 重置停止标志
        st.session_state.stop_search = False
        st.session_state.current_results = None
        
        # 创建固定的进度显示容器
        progress_container = st.empty()
        progress_text = progress_container.empty()
        progress_bar = progress_container.empty()
        status_text = progress_container.empty()
        
        # 初始化进度显示
        progress_text.text("准备开始搜索...")
        progress_bar.progress(0)
        status_text.text("初始化中...")

        # yt-dlp 基础配置
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': False,
            'no_warnings': True,
            'ignoreerrors': True,
            'no_color': True,
            'skip_download': True,
            'format': 'best',
            'default_search': 'ytsearch',
            'extract_flat': True,
            'dump_single_json': True,
            'simulate': True,
            'playlistend': max_results * 2
        }
        
        videos_data = []
        processed_ids = set()
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # 搜索视频
                status_text.text("正在搜索视频...")
                search_query = f"ytsearch{max_results * 2}:{query}"
                
                try:
                    # 直接获取搜索结果
                    results = ydl.extract_info(search_query, download=False)
                    
                    if not results or 'entries' not in results:
                        status_text.text("搜索结果为空，请尝试其他关键词")
                        return None
                        
                    entries = [e for e in results.get('entries', []) if e is not None]
                    if not entries:
                        status_text.text("未找到有效的视频结果")
                        return None
                        
                    total_entries = len(entries)
                    status_text.text(f"找到 {total_entries} 个视频，正在处理...")
                    
                    # 处理每个视频
                    for i, entry in enumerate(entries):
                        if st.session_state.stop_search:
                            break
                            
                        try:
                            if len(videos_data) >= max_results:
                                break
                                
                            # 基本信息处理
                            video_data = {
                                "视频ID": entry.get('id', 'N/A'),
                                "标题": entry.get('title', 'N/A'),
                                "频道名": entry.get('uploader', 'N/A'),
                                "发布时间": entry.get('upload_date', 'N/A'),
                                "观看次数": format_number(entry.get('view_count', 0)),
                                "时长": format_duration(entry.get('duration')),
                                "原始时长(秒)": entry.get('duration', 0),
                                "缩略图": f"https://i.ytimg.com/vi/{entry.get('id', '')}/hqdefault.jpg",
                                "点赞数": format_number(entry.get('like_count', 0)),
                                "描述": entry.get('description', '') if include_description else ''
                            }
                            
                            # 检查是否符合筛选条件
                            if filter_video(video_data, duration_filter, upload_date_filter):
                                videos_data.append(video_data)
                                processed_ids.add(entry.get('id'))
                                st.session_state.current_results = videos_data.copy()
                                
                                # 更新进度
                                progress = min((len(videos_data) / max_results), 1.0)
                                progress_text.text(f"已获取: {len(videos_data)}/{max_results} 个视频")
                                progress_bar.progress(progress)
                                status_text.text(f"正在处理第 {i+1}/{total_entries} 个视频...")
                                
                        except Exception as e:
                            st.warning(f"处理视频时出错: {str(e)}")
                            continue
                            
                except Exception as e:
                    st.error(f"搜索出错: {str(e)}")
                    return None
                    
            finally:
                # 更新最终状态
                if len(videos_data) == 0:
                    status_text.text("未找到符合条件的视频")
                    return None
                elif st.session_state.stop_search:
                    status_text.text(f"搜索已手动停止。已获取 {len(videos_data)} 个视频。")
                else:
                    status_text.text(f"搜索完成，共获取 {len(videos_data)} 个视频。")
                
                return videos_data[:max_results]
                
    except Exception as e:
        st.error(f"搜索视频时出错: {str(e)}")
        return st.session_state.current_results if st.session_state.current_results else None

def display_video_table(videos):
    """以表格形式显示视频数据"""
    # 创建简化的数据表格
    table_data = []
    for video in videos:
        table_data.append({
            "标题": video["标题"],
            "频道名": video["频道名"],
            "时长": video["时长"],
            "观看次数": video["观看次数"],
            "发布时间": video["发布时间"],
            "链接": f"[观看](https://youtube.com/watch?v={video['视频ID']})"
        })
    
    # 使用 st.table 显示数据
    st.table(pd.DataFrame(table_data))

if search_button and search_query:
    with st.spinner("正在搜索视频数据..."):
        videos = search_videos(search_query, max_results)
        
        if videos:
            # 创建数据表格，确保列顺序与示例文件相同
            columns = ["视频ID", "标题", "频道名", "发布时间", "观看次数", "时长", "缩略图", "点赞数", "描述"]
            df = pd.DataFrame(videos)[columns]
            
            # 显示结果
            st.subheader(f"搜索结果 ({len(videos)} 个视频)")
            
            if show_preview:
                # 使用列显示视频信息（带预览）
                cols = st.columns(3)
                for idx, video in enumerate(videos):
                    with cols[idx % 3]:
                        st.image(video["缩略图"], use_column_width=True)
                        st.markdown(f"**{video['标题']}**")
                        st.markdown(f"频道: {video['频道名']}")
                        st.markdown(f"发布时间: {video['发布时间']}")
                        st.markdown(f"观看次数: {video['观看次数']}")
                        st.markdown(f"时长: {video['时长']}")
                        st.markdown(f"点赞数: {video['点赞数']}")
                        if video["描述"]:
                            with st.expander("查看描述"):
                                st.text(video["描述"])
                        video_url = f"https://youtube.com/watch?v={video['视频ID']}"
                        st.markdown(f"[在 YouTube 上观看]({video_url})")
                        st.markdown("---")
            else:
                # 显示简洁的表格视图
                display_video_table(videos)
            
            # 添加下载按钮
            st.download_button(
                label="下载数据为 CSV",
                data=df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'),
                file_name=f'youtube_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                mime='text/csv'
            )
            
            # 显示数据统计
            st.subheader("数据统计")
            st.write(f"总视频数: {len(videos)}")
            if len(videos) > 0:
                try:
                    # 处理观看次数统计
                    view_counts = []
                    for v in videos:
                        try:
                            count = str(v['观看次数']).replace(',', '')
                            if count and count.isdigit():
                                view_counts.append(int(count))
                        except:
                            continue
                    if view_counts:
                        total_views = sum(view_counts)
                        st.write(f"总观看次数: {format_number(total_views)}")
                    
                    # 处理时长统计
                    durations = []
                    for v in videos:
                        try:
                            duration = v['原始时长(秒)']
                            if duration is not None and str(duration).isdigit():
                                durations.append(int(duration))
                        except:
                            continue
                    if durations:
                        avg_duration = sum(durations) / len(durations)
                        st.write(f"平均视频时长: {format_duration(avg_duration)}")
                except Exception as e:
                    st.warning(f"计算统计信息时出错: {str(e)}")
else:
    st.info("请输入搜索关键词并点击搜索按钮开始获取数据。") 