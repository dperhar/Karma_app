from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from app.api.v1.router import api_router as api_v1_router
from app.db.session import engine 
from app.db.base_class import Base

# Load environment variables
load_dotenv()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Karma App API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_v1_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Karma App API is running"} 