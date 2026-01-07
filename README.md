# Media Optimizer

A Streamlit app to optimize images and videos for smaller file sizes without losing quality.

## Features

- 🖼️ **Image Optimizer**: Optimize WebP, PNG, JPG images
- 🎥 **Video Optimizer**: Optimize WebM, MP4, MOV videos
- ⚙️ Adjustable quality and compression settings
- 📊 Size reduction statistics
- ⬇️ Download optimized files

## Requirements

- Python 3.8+
- Streamlit
- ffmpeg (for video optimization)
- webp tools (for image optimization)

## Local Setup

```bash
pip install -r requirements.txt
streamlit run webp_optimizer_app.py
```

## Deployment

This app can be deployed to Streamlit Community Cloud.

Note: Video optimization requires ffmpeg, which may not be available on Streamlit Cloud. Image optimization should work fine.

