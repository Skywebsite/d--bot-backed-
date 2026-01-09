import torch
import re
import json
import spacy
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    # Fallback if model is not downloaded
    nlp = None
print("Torch and spaCy loaded")
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from paddleocr import PaddleOCR
print("PaddleOCR loaded successfully")
import numpy as np
import io
from PIL import Image
import uvicorn
import uuid
from datetime import datetime
import os
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from dotenv import load_dotenv

load_dotenv()


def parse_ocr_text(clean_text: str) -> dict:
    """
    Advanced parsing for Event Posters.
    Extracts: organizer, event_name, event_date, entry_type, highlights, website.
    """
    data = {
        "organizer": "N/A",
        "event_name": "N/A",
        "event_date": "N/A",
        "event_time": "N/A",
        "location": "N/A",
        "entry_type": "Paid", # Default to paid unless "FREE" found
        "highlights": [],
        "website": "N/A",
    }
    
    if not clean_text:
        return data

    lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
    
    # 1. Extract Website
    url_match = re.search(r"(www\.[a-z0-9-]+\.[a-z]{2,}|https?://[^\s]+|ww\.[a-z0-9-]+\.[a-z]{2,})", clean_text, re.IGNORECASE)
    if url_match:
        data["website"] = url_match.group(0)

    # 2. Extract Time
    # More robust time pattern
    time_matches = re.findall(r"(\b\d{1,2}[:.]\d{2}\s*(AM|PM)?\b|\b\d{1,2}\s*(AM|PM)\b)", clean_text, re.IGNORECASE)
    if time_matches:
        # Filter and join unique time strings
        found_times = []
        for tm in time_matches:
            t_str = tm[0] if isinstance(tm, tuple) else tm
            if t_str and t_str.strip() and t_str.strip().upper() not in [ft.upper() for ft in found_times]:
                found_times.append(t_str.strip())
        data["event_time"] = " - ".join(found_times)

    # 3. Extract Entry Type
    if re.search(r"FREE\s*(ENTRY|ADMISSION|TICKET)?", clean_text, re.IGNORECASE):
        data["entry_type"] = "FREE ENTRY"

    # 3. Extract Dates (including days like FRIDAY, ranges like 10TH-18TH, and individual dates)
    date_patterns = [
        r"(\d{1,2}(st|nd|rd|th)?\s*-\s*\d{1,2}(st|nd|rd|th)?\s*\w+)", # 10th-18th October
        r"\b(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)\b", # Days
        r"\b\d{1,2}(st|nd|rd|th)\b", # 24th
        r"\b(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER|OCT|NOV|DEC)\b" # Months
    ]
    
    found_dates = []
    for pattern in date_patterns:
        matches = re.findall(pattern, clean_text, re.IGNORECASE)
        for m in matches:
            d = m if isinstance(m, str) else m[0]
            if d and d.strip() and d.strip().upper() not in [fd.upper() for fd in found_dates]:
                found_dates.append(d.strip())
    
    if found_dates:
        data["event_date"] = ", ".join(found_dates)

    # 4. Organizer and Event Name using NLP and Heuristics
    if nlp:
        doc = nlp(clean_text)
        for ent in doc.ents:
            if ent.label_ == "ORG" and data["organizer"] == "N/A":
                data["organizer"] = ent.text
            if ent.label_ in ["GPE", "LOC", "FAC"] and data["location"] == "N/A":
                data["location"] = ent.text
    
    # Heuristic: If first line contains "PRESENTS", the word before it is the organizer
    for line in lines:
        if "PRESENTS" in line.upper():
            parts = re.split(r"PRESENTS", line, flags=re.IGNORECASE)
            data["organizer"] = parts[0].strip()
            # The part after "PRESENTS" is likely the event name
            if len(parts) > 1 and parts[1].strip():
                data["event_name"] = parts[1].strip()
            break

    # If event_name still N/A, look for big text (usually 2nd or 3rd line if not organizer)
    if data["event_name"] == "N/A" and len(lines) > 0:
        # Avoid picking the organizer or date as the name
        for line in lines:
            if line != data["organizer"] and line != data["event_date"] and "PRESENTS" not in line.upper():
                data["event_name"] = line
                break

    # Heuristic for location if spaCy missed it
    location_keywords = ["ROAD", "STREET", "AVE", "AVENUE", "WAY", "DRIVE", "DR", "LAS VEGAS", "NV", "CHENNAI", "MUMBAI", "CITY", "ST.", "SUITE"]
    if data["location"] == "N/A":
        for line in lines:
            if any(kw in line.upper() for kw in location_keywords):
                # Avoid using the website or date as location
                if line != data["website"] and line != data["event_date"]:
                    data["location"] = line.strip()
                    break

    # 5. Extract Highlights (Bullet points or specific feature items)
    highlights_keywords = ["STUDENT", "SCULPTURE", "SHOWCASE", "ENTERTAINMENT", "REFRESHMENTS", "DAILY", "DJS", "MUSIC"]
    for line in lines:
        # If line contains 2 or more highlight keywords, or is a standalone feature
        if any(kw in line.upper() for kw in highlights_keywords):
            # Clean up: don't add if it's already the event name or organizer
            if line != data["event_name"] and line != data["organizer"]:
                data["highlights"].append(line)

    # Deduced Highlight logic: anything that isn't a date, website, or name
    # is potentially a highlight if it's descriptive
    if not data["highlights"]:
        for line in lines:
            if len(line) > 10 and line != data["event_name"] and line != data["organizer"] and line != data["event_date"] and line != data["website"]:
                data["highlights"].append(line)

    return data


app = FastAPI()

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Connection
MONGODB_URL = os.getenv("MONGODB_URL")
if not MONGODB_URL:
    raise ValueError("MONGODB_URL not found in environment variables")

client = AsyncIOMotorClient(MONGODB_URL)
db = client.event_database
collection = db.events


# Initialize PaddleOCR
# Using the same config as image scarper.py
ocr = PaddleOCR(
    lang="en",
    use_textline_orientation=True
)


@app.get("/")
async def root():
    return {"message": "PaddleOCR API is running"}

@app.post("/ocr")
async def extract_text(file: UploadFile = File(...)):
    try:
        # Read image contents
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        image_np = np.array(image)
        
        # In PaddleOCR 3.x+, use_angle_cls is set in constructor.
        # predict() is the modern API, but we handle result structure robustly.
        result = ocr.predict(image_np)
        
        extracted = []
        if result:
            # Handle both single image result and batch results
            # PaddleOCR usually returns a list of results (one per image)
            for res_item in result:
                if not res_item:
                    continue
                
                # Format A: Modern Dictionary/Object Format (PaddleOCR 3.3.2 / PaddleX style)
                if hasattr(res_item, 'get') or isinstance(res_item, dict):
                    data = res_item
                    if hasattr(res_item, 'json') and callable(res_item.json):
                        try: data = res_item.json()
                        except: pass
                    
                    # Case 1: user's working format (rec_texts and rec_scores)
                    rec_texts = data.get('rec_texts', [])
                    rec_scores = data.get('rec_scores', [])
                    if rec_texts:
                        for t, s in zip(rec_texts, rec_scores):
                            extracted.append({
                                "text": str(t),
                                "confidence": float(s)
                            })
                    
                    # Case 2: rec_res format [(text, score), ...]
                    else:
                        rec_res = data.get('rec_res', [])
                        for item in rec_res:
                            try:
                                if isinstance(item, (list, tuple)) and len(item) >= 2:
                                    text, score = item[0], item[1]
                                    extracted.append({
                                        "text": str(text),
                                        "confidence": float(score)
                                    })
                                elif isinstance(item, dict):
                                    text = item.get('text', '')
                                    score = item.get('score', 0.0)
                                    extracted.append({
                                        "text": str(text),
                                        "confidence": float(score)
                                    })
                            except (IndexError, TypeError, ValueError):
                                continue
                
                # Format B: Legacy List Format
                # Matches: [ [[box], (text, score)], ... ]
                elif isinstance(res_item, list):
                    for line in res_item:
                        try:
                            # line format: [[box], (text, score)]
                            if isinstance(line, list) and len(line) >= 2:
                                content = line[1]
                                if isinstance(content, (list, tuple)) and len(content) >= 2:
                                    text, score = content[0], content[1]
                                    extracted.append({
                                        "text": str(text),
                                        "confidence": float(score)
                                    })
                        except (IndexError, TypeError, ValueError):
                            continue
        
        # Join all extracted text into a clean block for logical parsing
        full_text_clean = "\n".join([item['text'] for item in extracted])
        structured_data = parse_ocr_text(full_text_clean)
        
        # Prepare MongoDB-style document
        mongo_doc = {
            "timestamp": datetime.now().isoformat(),
            "event_details": structured_data,
            "raw_ocr": extracted,
            "full_text": full_text_clean
        }

        # Store in MongoDB
        try:
            insert_result = await collection.insert_one(mongo_doc)
            mongodb_id = str(insert_result.inserted_id)
        except Exception as mongo_err:
            print(f"MongoDB storage error: {mongo_err}")
            mongodb_id = "error"
        
        return {
            "success": True,
            "data": extracted,
            "full_text": " ".join([item["text"] for item in extracted]),
            "structured": structured_data,
            "mongodb_id": mongodb_id
        }

    except Exception as e:
        import traceback
        print(f"OCR Error: {str(e)}")
        print(traceback.format_exc())
        return {"success": False, "error": str(e)}

@app.get("/events")
async def get_events():
    try:
        events = []
        cursor = collection.find().sort("timestamp", -1)
        async for document in cursor:
            document["_id"] = str(document["_id"]) # Convert ObjectId to string
            events.append(document)
        return {"success": True, "events": events}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


