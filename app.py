import streamlit as st
import pandas as pd
from datetime import datetime
import yt_dlp

# 设置页面配置
st.set_page_config(
    page_title="YouTube 数据爬取工具",
    page_icon="🎥",
    layout="wide"
)

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

def search_videos(query, max_results):
    """搜索视频"""
    try:
        videos_data = []
        
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
            search_query = f"ytsearch{max_results}:{query}"
            results = ydl.extract_info(search_query, download=False)
            
            if results and 'entries' in results:
                entries = [e for e in results.get('entries', []) if e is not None]
                
                # 处理搜索结果
                for i, entry in enumerate(entries):
                    if len(videos_data) >= max_results:
                        break
                        
                    try:
                        # 获取视频信息
                        duration = entry.get('duration', 0)
                        if duration is None:
                            duration = 0
                            
                        video_data = {
                            "视频ID": entry.get('id', 'N/A'),
                            "标题": entry.get('title', 'N/A'),
                            "频道名": entry.get('uploader', 'N/A'),
                            "发布时间": entry.get('upload_date', 'N/A'),
                            "观看次数": format_number(entry.get('view_count', 0)),
                            "时长": format_duration(duration),
                            "缩略图": f"https://i.ytimg.com/vi/{entry.get('id', '')}/hqdefault.jpg",
                            "点赞数": format_number(entry.get('like_count', 0)),
                            "描述": entry.get('description', '')
                        }
                        
                        videos_data.append(video_data)
                        
                        # 更新进度
                        progress = (i + 1) / min(len(entries), max_results)
                        st.progress(progress)
                        
                    except Exception as e:
                        continue
                    
        return videos_data
                
    except Exception as e:
        st.error(f"搜索视频时出错: {str(e)}")
        return None

# 主界面
st.title("🎥 YouTube 数据爬取工具")
st.markdown("这个工具可以帮助你搜索和获取 YouTube 视频的相关数据。")

# 搜索配置
search_query = st.text_input("搜索关键词")
max_results = st.number_input("最大结果数", min_value=1, max_value=50, value=10)
show_preview = st.checkbox("显示视频预览", value=False)

# 搜索按钮
if st.button("开始搜索") and search_query:
    with st.spinner("正在搜索视频数据..."):
        videos = search_videos(search_query, max_results)
        
        if videos:
            st.subheader(f"搜索结果 ({len(videos)} 个视频)")
            
            # 创建DataFrame并确保列顺序与示例文件相同
            columns = ["视频ID", "标题", "频道名", "发布时间", "观看次数", "时长", "缩略图", "点赞数", "描述"]
            df = pd.DataFrame(videos)[columns]
            
            # 显示结果
            if show_preview:
                cols = st.columns(3)
                for idx, video in enumerate(videos):
                    with cols[idx % 3]:
                        st.image(video["缩略图"])
                        st.markdown(f"**{video['标题']}**")
                        st.markdown(f"频道: {video['频道名']}")
                        st.markdown(f"ID: {video['视频ID']}")
                        st.markdown(f"时长: {video['时长']}")
                        st.markdown(f"观看: {video['观看次数']}")
                        if video["描述"]:
                            with st.expander("查看描述"):
                                st.text(video["描述"])
                        st.markdown("---")
            else:
                st.dataframe(df, hide_index=True, use_container_width=True)
            
            # 下载按钮 - 使用与示例相同的格式
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
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("总视频数", len(videos))
                
            with col2:
                total_views = sum([
                    int(str(v['观看次数']).replace(',', ''))
                    for v in videos
                    if str(v['观看次数']).replace(',', '').isdigit()
                ])
                st.metric("总观看次数", format_number(total_views))
else:
    st.info("请输入搜索关键词并点击搜索按钮开始获取数据。") 