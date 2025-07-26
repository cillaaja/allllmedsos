import sys
import subprocess
import threading
import os
import time
import datetime
import streamlit.components.v1 as components

try:
    import streamlit as st
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
    import streamlit as st


# ==================== FUNGSI STREAMING ====================
def run_ffmpeg(video_path, output_urls, is_shorts, log_callback, status_callback):
    tee_urls = "|".join([f"[f=flv]{url}" for url in output_urls])
    scale = "-vf scale=720:1280" if is_shorts else ""

    cmd = [
        "ffmpeg", "-re", "-stream_loop", "-1", "-i", video_path,
        "-c:v", "libx264", "-preset", "veryfast", "-b:v", "2500k",
        "-maxrate", "2500k", "-bufsize", "5000k",
        "-g", "60", "-keyint_min", "60",
        "-c:a", "aac", "-b:a", "128k"
    ]
    if scale:
        cmd += scale.split()
    cmd += ["-f", "tee", tee_urls]

    log_callback(f"🎥 Menjalankan streaming...")
    status_callback("🟢 LIVE")

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        start_time = time.time()
        for line in process.stdout:
            duration = int(time.time() - start_time)
            log_callback(f"[{duration}s] {line.strip()}")
        process.wait()
    except Exception as e:
        log_callback(f"❌ Error: {e}")
    finally:
        log_callback("⚠️ Streaming dihentikan.")
        status_callback("🔴 OFFLINE")


# ==================== FUNGSI JADWAL ====================
def schedule_stream(start_datetime, video_path, output_urls, is_shorts, log_callback, status_callback):
    now = datetime.datetime.now()
    delay = (start_datetime - now).total_seconds()
    if delay <= 0:
        log_callback("⚠️ Waktu sudah lewat, streaming dimulai sekarang!")
        run_ffmpeg(video_path, output_urls, is_shorts, log_callback, status_callback)
    else:
        log_callback(f"⏳ Streaming akan dimulai otomatis pada {start_datetime.strftime('%d-%m-%Y %H:%M:%S')}")
        time.sleep(delay)
        run_ffmpeg(video_path, output_urls, is_shorts, log_callback, status_callback)


# ==================== UI DASHBOARD ====================
def main():
    # ==================== PAGE CONFIG ====================
    st.set_page_config(page_title="KarinDev Multi Streaming", page_icon="📡", layout="wide")

    # ==================== CSS DARK MODE ====================
    st.markdown("""
        <style>
        body { background: #1b1b1b; color: #eaeaea; }
        .stButton>button {
            background: linear-gradient(90deg, #ff416c, #ff4b2b);
            color: white; font-weight: bold; padding: 0.6rem 1.4rem;
            border-radius: 10px; border: none; font-size: 16px;
        }
        .stTextInput>div>input, .stFileUploader>div>div {
            background: #2a2a2a; color: white; border-radius: 10px !important;
        }
        .card {
            background: #2b2b2b; border-radius: 12px; padding: 15px;
            text-align: center; border: 1px solid #444;
        }
        .footer { text-align:center; color:#aaa; font-size:13px; margin-top:15px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("## 📡 **Multi Live Streaming Dashboard**")
    st.markdown("#### Dibuat oleh **KarinDev**")

    # ==================== IKLAN ====================
    show_ads = st.checkbox("Tampilkan Iklan", value=False)
    if show_ads:
        components.html(
            "<div style='background:#2a2a2a;padding:10px;border-radius:10px;text-align:center'>🔥 Sponsor: Pasang iklan Anda di sini!</div>",
            height=50
        )

    # ==================== VIDEO INPUT ====================
    st.markdown("### 🎬 Pilih atau Upload Video")
    col1, col2 = st.columns([2, 1])
    video_files = [f for f in os.listdir('.') if f.endswith(('.mp4', '.flv'))]

    with col1:
        selected_video = st.selectbox("📁 Pilih video yang ada", video_files) if video_files else None
    with col2:
        uploaded_file = st.file_uploader("📤 Upload video baru", type=['mp4', 'flv'])

    video_path = None
    if uploaded_file:
        with open(uploaded_file.name, "wb") as f:
            f.write(uploaded_file.read())
        video_path = uploaded_file.name
    elif selected_video:
        video_path = selected_video

    # Preview video
    if video_path:
        st.video(video_path)

    # ==================== STREAM KEY INPUT ====================
    st.markdown("### 🔑 Masukkan Stream Key")
    col1, col2 = st.columns(2)
    with col1:
        fb_key = st.text_input("🌐 Facebook Stream Key", type="password")
        yt_key = st.text_input("▶️ YouTube Stream Key", type="password")
    with col2:
        twitch_key = st.text_input("🎮 Twitch Stream Key", type="password")
        tiktok_key = st.text_input("🎵 TikTok Stream Key", type="password")

    output_urls = []
    if fb_key:
        output_urls.append(f"rtmps://live-api-s.facebook.com:443/rtmp/{fb_key}")
    if yt_key:
        output_urls.append(f"rtmp://a.rtmp.youtube.com/live2/{yt_key}")
    if twitch_key:
        output_urls.append(f"rtmp://live.twitch.tv/app/{twitch_key}")
    if tiktok_key:
        output_urls.append(f"rtmp://global-live.musical.ly:80/live/{tiktok_key}")

    # Mode Shorts
    is_shorts = st.checkbox("📱 Mode Shorts (720x1280)")

    # ==================== STATUS & LOG ====================
    status_placeholder = st.empty()
    log_placeholder = st.empty()
    logs = []

    def log_callback(msg):
        logs.append(msg)
        log_placeholder.code("\n".join(logs[-15:]), language="bash")

    def status_callback(status):
        status_placeholder.markdown(f"### Status: **{status}**")

    if 'ffmpeg_thread' not in st.session_state:
        st.session_state['ffmpeg_thread'] = None

    # ==================== JADWAL ====================
    st.markdown("### ⏰ Jadwal Tayang Otomatis")
    col_date, col_time = st.columns(2)
    with col_date:
        schedule_date = st.date_input("Tanggal Mulai")
    with col_time:
        schedule_time = st.time_input("Jam Mulai")

    start_datetime = datetime.datetime.combine(schedule_date, schedule_time)

    # ==================== KONTROL ====================
    col_run, col_stop = st.columns(2)
    with col_run:
        if st.button("🚀 Jalankan Streaming (Langsung)"):
            if not video_path or not output_urls:
                st.error("⚠️ Harus pilih video dan minimal 1 stream key!")
            else:
                st.session_state['ffmpeg_thread'] = threading.Thread(
                    target=run_ffmpeg, args=(video_path, output_urls, is_shorts, log_callback, status_callback), daemon=True)
                st.session_state['ffmpeg_thread'].start()
                st.success(f"Streaming dimulai ke {len(output_urls)} platform! 📡")

        if st.button("📅 Jadwalkan Streaming Otomatis"):
            if not video_path or not output_urls:
                st.error("⚠️ Harus pilih video dan minimal 1 stream key!")
            else:
                st.session_state['ffmpeg_thread'] = threading.Thread(
                    target=schedule_stream, args=(start_datetime, video_path, output_urls, is_shorts, log_callback, status_callback), daemon=True)
                st.session_state['ffmpeg_thread'].start()
                st.success(f"Streaming terjadwal pada {start_datetime.strftime('%d-%m-%Y %H:%M:%S')}")

    with col_stop:
        if st.button("⛔ Stop Streaming"):
            os.system("pkill ffmpeg")
            status_callback("🔴 OFFLINE")
            st.warning("Streaming dihentikan!")

    # Footer
    st.markdown("<div class='footer'>© 2025 KarinDev - All Rights Reserved</div>", unsafe_allow_html=True)


if __name__ == '__main__':
    main()
