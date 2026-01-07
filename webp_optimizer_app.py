import streamlit as st
import subprocess
import tempfile
import os
from pathlib import Path
import shutil
from PIL import Image
import io

st.set_page_config(
    page_title="Media Optimizer",
    page_icon="🎬",
    layout="wide"
)

def check_cwebp():
    """Check if cwebp is installed (or if Pillow can handle WebP)."""
    # First try command-line tool (for local use)
    try:
        subprocess.run(['cwebp', '-version'], 
                      capture_output=True, check=True)
        return True, 'command_line'
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fall back to Pillow (works on Streamlit Cloud)
        try:
            from PIL import Image
            # Test if WebP is supported
            Image.new('RGB', (1, 1)).save(io.BytesIO(), format='WEBP')
            return True, 'pillow'
        except:
            return False, None

def check_ffmpeg():
    """Check if ffmpeg is installed."""
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def optimize_webp(input_path, output_path, quality=85, method=6):
    """Optimize WebP image using Pillow (works on Streamlit Cloud)."""
    try:
        # Use Pillow for WebP optimization (works everywhere)
        with Image.open(input_path) as img:
            # Convert RGBA to RGB if needed (WebP supports both)
            if img.mode == 'RGBA':
                # Keep alpha channel
                pass
            elif img.mode not in ('RGB', 'RGBA', 'L', 'LA'):
                # Convert to RGB
                img = img.convert('RGB')
            
            # Save as WebP with optimization
            # Pillow's quality parameter maps to WebP quality (0-100)
            # method parameter is not directly supported, but quality works well
            img.save(
                output_path,
                'WEBP',
                quality=quality,
                method=6 if method > 0 else 0,  # Pillow method (0-6)
                lossless=False
            )
        return True, None
    except Exception as e:
        return False, str(e)

def optimize_video(input_path, output_path, crf=35, speed=4, fps=None):
    """Optimize WebM video."""
    try:
        cmd = [
            'ffmpeg', '-i', str(input_path),
            '-c:v', 'libvpx-vp9',
            '-crf', str(crf),
            '-b:v', '0',
            '-speed', str(speed),
            '-row-mt', '1',
            '-tile-columns', '2',
            '-tile-rows', '1',
            '-frame-parallel', '1',
            '-threads', '0',
            '-c:a', 'libopus',
            '-b:a', '96k',
            '-y',
            str(output_path)
        ]
        
        # Add FPS filter if specified
        if fps:
            # Insert fps filter before codec
            cmd.insert(2, '-vf')
            cmd.insert(3, f'fps={fps}')
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True, None
    except subprocess.CalledProcessError as e:
        return False, e.stderr if e.stderr else str(e)

def get_video_info(video_path):
    """Get video information."""
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,r_frame_rate,duration,bit_rate',
            '-of', 'csv=p=0',
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        parts = result.stdout.strip().split(',')
        if len(parts) >= 4:
            return {
                'width': int(parts[0]) if parts[0] else None,
                'height': int(parts[1]) if parts[1] else None,
                'fps': parts[2] if parts[2] else None,
                'duration': float(parts[3]) if len(parts) > 3 and parts[3] else None,
                'bitrate': int(parts[4]) if len(parts) > 4 and parts[4] else None
            }
    except:
        pass
    return None

def format_size(size_bytes):
    """Format file size in human readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

# Main app
st.title("🎬 Media Optimizer")
st.markdown("Optimize images and videos for smaller file sizes without losing quality.")

# Create tabs
tab1, tab2 = st.tabs(["🖼️ Image Optimizer", "🎥 Video Optimizer"])

# ========== IMAGE TAB ==========
with tab1:
    st.markdown("Upload an image to optimize it for smaller file size without losing visual quality.")
    st.markdown("**Supports:** WebP, PNG, JPG, JPEG → Optimized WebP output")
    
    # Check if WebP optimization is available
    webp_available, method = check_cwebp()
    if not webp_available:
        st.error("⚠️ WebP support is not available. Please install Pillow:")
        st.code("pip install Pillow", language="bash")
    else:
        # Sidebar for image settings
        with st.sidebar:
            st.header("⚙️ Image Settings")
            
            quality = st.slider(
                "Quality",
                min_value=50,
                max_value=100,
                value=85,
                help="Higher quality = larger file size. 85 is a good balance."
            )
            
            method = st.slider(
                "Compression Method",
                min_value=0,
                max_value=6,
                value=6,
                help="Higher method = better compression but slower. 6 is best compression."
            )
        
        # File upload
        uploaded_file = st.file_uploader(
            "Upload an image to optimize",
            type=['webp', 'png', 'jpg', 'jpeg'],
            help="Drag and drop or click to upload. Supports WebP, PNG, JPG, JPEG",
            key="image_upload"
        )
        
        if uploaded_file is not None:
            # Create temporary files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_input = Path(temp_dir) / uploaded_file.name
                temp_output = Path(temp_dir) / f"optimized_{uploaded_file.name}"
                
                # Save uploaded file
                with open(temp_input, 'wb') as f:
                    f.write(uploaded_file.getbuffer())
                
                # Get original file size
                original_size = temp_input.stat().st_size
                
                # Display original image info
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📤 Original Image")
                    st.image(uploaded_file)
                    st.info(f"**Size:** {format_size(original_size)}")
                
                # Optimize button
                if st.button("🚀 Optimize Image", type="primary", key="optimize_img"):
                    with st.spinner("Optimizing image... This may take a moment."):
                        success, error = optimize_webp(temp_input, temp_output, quality=quality, method=method)
                        
                        if success and temp_output.exists():
                            optimized_size = temp_output.stat().st_size
                            reduction = ((1 - optimized_size / original_size) * 100) if original_size > 0 else 0
                            
                            with col2:
                                st.subheader("📥 Optimized Image")
                                
                                # Read and display optimized image
                                with open(temp_output, 'rb') as f:
                                    optimized_bytes = f.read()
                                st.image(optimized_bytes)
                                
                                st.success(f"**Size:** {format_size(optimized_size)}")
                                
                                # Size reduction info
                                if optimized_size < original_size:
                                    st.success(f"✅ **Reduction:** {reduction:.1f}% smaller")
                                    st.metric(
                                        "Size Saved",
                                        f"-{format_size(original_size - optimized_size)}",
                                        f"{reduction:.1f}%"
                                    )
                                else:
                                    st.warning("⚠️ File size increased. Try lower quality settings.")
                            
                            # Download button
                            st.markdown("---")
                            output_filename = f"optimized_{Path(uploaded_file.name).stem}.webp"
                            st.download_button(
                                label="⬇️ Download Optimized Image",
                                data=optimized_bytes,
                                file_name=output_filename,
                                mime="image/webp",
                                key="download_img"
                            )
                            
                            # Comparison chart
                            st.markdown("---")
                            st.subheader("📊 Size Comparison")
                            
                            comparison_data = {
                                'Original': original_size,
                                'Optimized': optimized_size
                            }
                            st.bar_chart(comparison_data)
                            
                            # Detailed stats
                            with st.expander("📈 Detailed Statistics"):
                                col_a, col_b, col_c = st.columns(3)
                                with col_a:
                                    st.metric("Original Size", format_size(original_size))
                                with col_b:
                                    st.metric("Optimized Size", format_size(optimized_size))
                                with col_c:
                                    st.metric("Reduction", f"{reduction:.1f}%")
                                
                                st.markdown(f"""
                                - **Quality Setting:** {quality}
                                - **Compression Method:** {method}
                                - **Size Saved:** {format_size(original_size - optimized_size)}
                                - **Compression Ratio:** {optimized_size / original_size:.2%}
                                """)
                        else:
                            st.error(f"❌ Optimization failed: {error}")
                            if error:
                                st.code(error)

# ========== VIDEO TAB ==========
with tab2:
    st.markdown("Upload a video to optimize it for smaller file size.")
    st.markdown("**Supports:** WebM, MP4, MOV → Optimized WebM output")
    
    # Check if ffmpeg is installed
    ffmpeg_available = check_ffmpeg()
    if not ffmpeg_available:
        st.warning("⚠️ **Video optimization is not available on this platform.**")
        st.info("""
        **Why?** Video optimization requires `ffmpeg`, which is not available on Streamlit Cloud.
        
        **Solutions:**
        - ✅ **Image optimization** works perfectly - use the Image Optimizer tab!
        - 💻 **For video optimization:** Run the app locally on your Mac/Windows machine
        - 🌐 **Alternative:** Use online video compression tools
        
        **To use video optimization locally:**
        1. Install ffmpeg: `brew install ffmpeg` (Mac) or download from ffmpeg.org (Windows)
        2. Run the app locally using the launcher scripts
        """)
        st.markdown("---")
        st.markdown("### 📥 Download for Local Use")
        st.markdown("""
        You can download the app and run it locally on your computer where ffmpeg is installed.
        Check the README.md file in the repository for local setup instructions.
        """)
    else:
        # Sidebar for video settings
        with st.sidebar:
            st.header("⚙️ Video Settings")
            
            crf = st.slider(
                "CRF (Quality)",
                min_value=28,
                max_value=40,
                value=35,
                help="Lower CRF = higher quality but larger file. 35 is good for compression."
            )
            
            speed = st.slider(
                "Encoding Speed",
                min_value=0,
                max_value=5,
                value=4,
                help="Higher speed = faster encoding but slightly less efficient. 4 is a good balance."
            )
            
            fps_limit = st.checkbox("Limit FPS to 30", value=False, help="Reduce frame rate to 30 FPS for smaller file size")
            target_fps = 30 if fps_limit else None
            
            st.markdown("---")
            st.markdown("**Tips:**")
            st.markdown("- CRF 30-35: Good balance")
            st.markdown("- Speed 4: Fast encoding")
            st.markdown("- Limit FPS: Reduces size significantly")
        
        # File upload
        uploaded_video = st.file_uploader(
            "Upload a video to optimize",
            type=['webm', 'mp4', 'mov'],
            help="Drag and drop or click to upload. Supports WebM, MP4, MOV",
            key="video_upload"
        )
        
        if uploaded_video is not None:
            # Create temporary files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_input = Path(temp_dir) / uploaded_video.name
                temp_output = Path(temp_dir) / f"optimized_{uploaded_video.name}"
                
                # Save uploaded file
                with open(temp_input, 'wb') as f:
                    f.write(uploaded_video.getbuffer())
                
                # Get original file size
                original_size = temp_input.stat().st_size
                
                # Get video info
                video_info = get_video_info(temp_input)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📤 Original Video")
                    st.video(uploaded_video)
                    st.info(f"**Size:** {format_size(original_size)}")
                    
                    if video_info:
                        st.info(f"""
                        **Video Info:**
                        - Resolution: {video_info.get('width', '?')}x{video_info.get('height', '?')}
                        - FPS: {video_info.get('fps', '?')}
                        - Duration: {video_info.get('duration', 0):.1f}s
                        """)
                
                # Optimize button
                if st.button("🚀 Optimize Video", type="primary", key="optimize_vid"):
                    with st.spinner("Optimizing video... This may take several minutes depending on video length."):
                        success, error = optimize_video(temp_input, temp_output, crf=crf, speed=speed, fps=target_fps)
                        
                        if success and temp_output.exists():
                            optimized_size = temp_output.stat().st_size
                            reduction = ((1 - optimized_size / original_size) * 100) if original_size > 0 else 0
                            
                            with col2:
                                st.subheader("📥 Optimized Video")
                                
                                # Read and display optimized video
                                with open(temp_output, 'rb') as f:
                                    optimized_bytes = f.read()
                                
                                # Save to temp file for video display
                                temp_video_display = Path(temp_dir) / "display_video.webm"
                                with open(temp_video_display, 'wb') as f:
                                    f.write(optimized_bytes)
                                
                                st.video(str(temp_video_display))
                                
                                st.success(f"**Size:** {format_size(optimized_size)}")
                                
                                # Size reduction info
                                if optimized_size < original_size:
                                    st.success(f"✅ **Reduction:** {reduction:.1f}% smaller")
                                    st.metric(
                                        "Size Saved",
                                        f"-{format_size(original_size - optimized_size)}",
                                        f"{reduction:.1f}%"
                                    )
                                else:
                                    st.warning("⚠️ File size increased. Try higher CRF or enable FPS limit.")
                            
                            # Download button
                            st.markdown("---")
                            output_filename = f"optimized_{Path(uploaded_video.name).stem}.webm"
                            st.download_button(
                                label="⬇️ Download Optimized Video",
                                data=optimized_bytes,
                                file_name=output_filename,
                                mime="video/webm",
                                key="download_vid"
                            )
                            
                            # Comparison chart
                            st.markdown("---")
                            st.subheader("📊 Size Comparison")
                            
                            comparison_data = {
                                'Original': original_size,
                                'Optimized': optimized_size
                            }
                            st.bar_chart(comparison_data)
                            
                            # Detailed stats
                            with st.expander("📈 Detailed Statistics"):
                                col_a, col_b, col_c = st.columns(3)
                                with col_a:
                                    st.metric("Original Size", format_size(original_size))
                                with col_b:
                                    st.metric("Optimized Size", format_size(optimized_size))
                                with col_c:
                                    st.metric("Reduction", f"{reduction:.1f}%")
                                
                                st.markdown(f"""
                                - **CRF Setting:** {crf}
                                - **Encoding Speed:** {speed}
                                - **FPS Limit:** {target_fps if target_fps else 'None'}
                                - **Size Saved:** {format_size(original_size - optimized_size)}
                                - **Compression Ratio:** {optimized_size / original_size:.2%}
                                """)
                        else:
                            st.error(f"❌ Optimization failed: {error}")
                            if error:
                                st.code(error)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>Powered by WebP & VP9 compression • Optimize media without losing quality</p>
    </div>
    """,
    unsafe_allow_html=True
)
