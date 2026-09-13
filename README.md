# Kahani Video AI - Backend

This is the Python backend for the Kahani Video AI application. It is fully compatible with the Android application.

## Prerequisites
- **FFmpeg**: Required for rendering video and audio.
- **Python 3.11+**

## Render Deployment Instructions

The absolute easiest way to deploy this to Render is using the provided Dockerfile, because Render's native Python environment does not come with `ffmpeg` installed. By using Docker, we ensure `ffmpeg` is properly bundled.

1. Create a new GitHub repository and upload this entire `backend/` folder to the root of your repository.
2. Sign in to [Render](https://render.com).
3. Click **New +** and select **Web Service**.
4. Connect your GitHub repository.
5. In the settings:
   - **Environment**: Select `Docker` (Render will automatically detect the `Dockerfile`).
   - **Region**: Choose the region closest to you.
   - **Plan**: Free or Starter.
6. Scroll down to **Environment Variables**:
   - Add a new variable with Key: `GEMINI_API_KEY` and Value: `(Your actual Gemini API Key)`.
     *(Never hardcode this in your code!)*
7. Click **Create Web Service**.

Render will build the Docker container (which installs FFmpeg and your Python libraries) and deploy the API.

## Verifying Deployment

Once deployed, Render will provide a URL (e.g., `https://kahani-video-api.onrender.com`).

Test the health check endpoint:
```bash
curl https://kahani-video-api.onrender.com/health
```
If it returns `{"status": "ok"}`, your server is successfully running!

## Updating the Android App

Once deployed, copy your Render URL and place it in your Android app's `.env` file:
```
API_BASE_URL=https://kahani-video-api.onrender.com/
```
Recompile the Android app, and it will now send all video generation jobs to your real deployed server.
