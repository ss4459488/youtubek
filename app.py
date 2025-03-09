import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import yt_dlp
import json
from io import BytesIO

# 设置页面配置
st.set_page_config(
    page_title="YouTube 数据爬取工具",
    page_icon="🎥",
    layout="wide"
)

# 初始化会话状态
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'is_searching' not in st.session_state:
    st.session_state.is_searching = False

# 工具函数
def format_number(num):
    """格式化数字"""
    if not num:
        return '0'
    return f"{num:,}"

def format_duration(seconds):
    """格式化时长"""
    if not seconds:
        return "0:00"
    try:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"
    except:
        return "0:00"

def get_thumbnail_url(video_info):
    """获取缩略图URL"""
    if not video_info:
        return ""
    video_id = video_info.get('id', '')
    if not video_id:
        return ""
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

def filter_video(video, duration_filter, upload_date_filter):
    """筛选视频"""
    try:
        # 时长筛选
        if duration_filter != "全部":
            duration = video.get('原始时长(秒)', 0)
            if duration:
                duration = int(duration)
                if duration_filter == "短视频 (< 4分钟)" and duration >= 240:
                    return False
                elif duration_filter == "中等 (4-20分钟)" and (duration < 240 or duration > 1200):
                    return False
                elif duration_filter == "长视频 (> 20分钟)" and duration <= 1200:
                    return False

        # 上传时间筛选
        if upload_date_filter != "全部":
            upload_date = video.get('发布时间', '')
            if upload_date:
                try:
                    upload_date = datetime.strptime(upload_date, '%Y%m%d')
                    now = datetime.now()
                    days_diff = (now - upload_date).days
                    
                    if upload_date_filter == "今天" and days_diff > 1:
                        return False
                    elif upload_date_filter == "本周" and days_diff > 7:
                        return False
                    elif upload_date_filter == "本月" and days_diff > 30:
                        return False
                    elif upload_date_filter == "今年" and days_diff > 365:
                        return False
                except:
                    pass

        return True
    except:
        return True

def process_video(entry):
    """处理视频数据"""
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
            
        # 基本信息处理
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
    """搜索视频"""
    try:
        videos_data = []
        processed_ids = set()
        
        # yt-dlp 配置
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': False,
            'no_warnings': True,
            'ignoreerrors': True,
            'no_color': True,
            'skip_download': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 搜索视频
            search_query = f"ytsearch{max_results * 2}:{query}"
            results = ydl.extract_info(search_query, download=False)
            
            if results and 'entries' in results:
                entries = [e for e in results.get('entries', []) if e is not None]
                
                # 处理搜索结果
                for entry in entries:
                    if len(videos_data) >= max_results:
                        break
                        
                    video_id = entry.get('id')
                    if not video_id or video_id in processed_ids:
                        continue
                        
                    video_data = process_video(entry)
                    if video_data and filter_video(video_data, duration_filter, upload_date_filter):
                        videos_data.append(video_data)
                        processed_ids.add(video_id)
                        
                    # 更新进度
                    progress = min((len(videos_data) / max_results), 1.0)
                    st.progress(progress)
                    
        return videos_data[:max_results]
                
    except Exception as e:
        st.error(f"搜索视频时出错: {str(e)}")
        return None

# 主界面
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
    max_results = st.number_input("最大结果数", min_value=1, max_value=100, value=30)
    
    duration_filter = st.selectbox(
        "时长范围",
        ["全部", "短视频 (< 4分钟)", "中等 (4-20分钟)", "长视频 (> 20分钟)"]
    )
    
    upload_date_filter = st.selectbox(
        "上传时间",
        ["全部", "今天", "本周", "本月", "今年"]
    )
    
    sort_by = st.selectbox(
        "排序方式",
        ["相关度", "上传时间", "观看次数", "评分"]
    )
    
    include_description = st.checkbox("获取视频描述", value=True)
    show_preview = st.checkbox("显示视频预览", value=False)
    
    if st.button("开始搜索"):
        st.session_state.is_searching = True

# 搜索和显示结果
if st.session_state.is_searching and search_query:
    with st.spinner("正在搜索视频数据..."):
        videos = search_videos(search_query, max_results)
        st.session_state.search_results = videos
        st.session_state.is_searching = False

# 显示结果
if st.session_state.search_results:
    videos = st.session_state.search_results
    
    # 创建数据表格
    if videos:
        st.subheader(f"搜索结果 ({len(videos)} 个视频)")
        
        # 显示方式
        if show_preview:
            cols = st.columns(3)
            for idx, video in enumerate(videos):
                with cols[idx % 3]:
                    st.image(video["缩略图"])
                    st.markdown(f"**{video['标题']}**")
                    st.markdown(f"频道: {video['频道名']}")
                    st.markdown(f"时长: {video['时长']}")
                    st.markdown(f"观看: {video['观看次数']}")
                    if video["描述"]:
                        with st.expander("查看描述"):
                            st.text(video["描述"])
                    st.markdown("---")
        else:
            # 表格视图
            df = pd.DataFrame(videos)
            st.dataframe(
                df[["标题", "频道名", "时长", "观看次数", "发布时间"]],
                hide_index=True,
                use_container_width=True
            )
        
        # 下载按钮
        df = pd.DataFrame(videos)
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            "下载数据为CSV",
            csv,
            f"youtube_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "text/csv",
            key='download-csv'
        )
        
        # 数据统计
        st.subheader("数据统计")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("总视频数", len(videos))
            
        with col2:
            total_views = sum([
                int(str(v['观看次数']).replace(',', ''))
                for v in videos
                if str(v['观看次数']).replace(',', '').isdigit()
            ])
            st.metric("总观看次数", format_number(total_views))
            
        with col3:
            valid_durations = [
                int(v['原始时长(秒)'])
                for v in videos
                if v['原始时长(秒)'] is not None
            ]
            if valid_durations:
                avg_duration = sum(valid_durations) / len(valid_durations)
                st.metric("平均时长", format_duration(avg_duration))
else:
    st.info("请输入搜索关键词并点击搜索按钮开始获取数据。") 