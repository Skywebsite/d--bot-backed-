# D-BOT: VisionText OCR & Event Parser

A high-precision OCR and event parsing application using PaddleOCR, FastAPI, and React.

## Project Structure
- **/backend**: FastAPI server, PaddleOCR logic, and MongoDB integration.
- **/frontend**: React application with a dynamic dashboard and event history.

## Deployment Preparation

### Backend
The backend is prepared for deployment (Heroku, Render, etc.).
- **Requirements**: `backend/requirements.txt` contains all dependencies.
- **Port**: The application listens on the port defined by the `PORT` environment variable (defaults to 8000).
- **Environment Variables**:
  - `MONGODB_URL`: Your MongoDB connection string.

### Git Instructions
1. Initialize Git: `git init`
2. Add files: `git add .`
3. Commit: `git commit -m "Prepare for cloud deployment"`
4. Push to your repository.

**Note**: The `.env` file and `node_modules` are ignored by `.gitignore` to keep the repository secure and clean.
