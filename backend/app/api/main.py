"""
Smart-Redact FastAPI Application
Simple API for handling file uploads from React frontend
"""
import logging
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse

from app.core.config import DELETE_FILES_AFTER_PROCESSING
from app.file_processors.base_processor import ProcessorFactory
from app.utils.file_utils import validate_file, save_uploaded_file, cleanup_file

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Smart-Redact API",
    description="File upload and OCR processing for cybersecurity documents",
    version="1.0.0"
)

# Enable CORS so React can talk to our API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://frontend"],  # React dev server + Docker
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Simple health check - shows API is running"""
    return {
        "message": "Smart-Redact API is running!",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker"""
    return {"status": "healthy", "service": "smart-redact-api"}

@app.post("/api/upload")
async def upload_and_process_file(file: UploadFile = File(...)):
    """
    Main endpoint: Upload file from React and process it
    
    This is what React will call when user uploads a file
    """
    try:
        # Step 1: Validate the uploaded file
        if not validate_file(file):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file. Allowed types: .jpg, .jpeg, .png, .tiff, .bmp, .xlsx, .xls, .pdf, .docx, .doc (max 100MB)"
            )
        
        # Step 2: Save uploaded file temporarily
        file_path = await save_uploaded_file(file)
        
        # Step 3: Get appropriate processor and process file
        processor = ProcessorFactory.get_processor(file_path)
        
        # Handle different processor interfaces
        if hasattr(processor, 'process_file') and callable(processor.process_file):
            # New processors (PDF, Word) use process_file method
            extracted_data = processor.process_file(str(file_path), "data/processed_files")
        else:
            # Legacy processors (Excel, Image) use extract_text method
            extracted_data = processor.extract_text()
        
        # Step 4: Prepare response based on file type and processor output
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension in ['.pdf', '.docx', '.doc']:
            # Handle PDF and Word document responses
            response_data = {
                "status": "success",
                "filename": file.filename,
                "file_type": file_extension[1:],  # Remove the dot
                "processing_status": extracted_data.get("processing_status", "completed"),
                "total_entities": extracted_data.get("total_entities", 0),
                "entity_types": extracted_data.get("entity_types", {}),
                "confidence": extracted_data.get("confidence_score", 0),
                "pages_processed": extracted_data.get("pages_processed", 0),
                "layout_spans_processed": extracted_data.get("layout_spans_processed", 0),
                "message": f"Successfully processed {file.filename}"
            }
            
            # Add download link if redacted file was created
            if extracted_data.get("redacted_file_path"):
                redacted_path = Path(extracted_data["redacted_file_path"])
                redacted_filename = redacted_path.name
                response_data["redacted_file_url"] = f"/api/download/{redacted_filename}"
                response_data["redacted_filename"] = redacted_filename
                
        else:
            # Handle Excel and Image responses (legacy format)
            response_data = {
                "status": "success",
                "filename": file.filename,
                "file_type": processor.file_type,
                "extracted_text": extracted_data.get("text", ""),
                "confidence": extracted_data.get("confidence", 0),
                "metadata": extracted_data.get("metadata", {}),
                "message": f"Successfully processed {file.filename}"
            }
        
        # Add Excel-specific data if available
        if hasattr(processor, 'pii_findings') and processor.pii_findings:
            response_data.update({
                "pii_findings": extracted_data.get("pii_findings", []),
                "pii_summary": extracted_data.get("pii_summary", {}),
                "total_pii_count": extracted_data.get("total_pii_count", 0),
                "worksheets": extracted_data.get("worksheets", [])
            })
            
            # Generate redacted Excel file if PII was found
            if extracted_data.get("total_pii_count", 0) > 0 and processor.file_type == "excel":
                try:
                    # Pass original filename for better naming
                    redacted_file_path = processor.create_redacted_excel(original_filename=file.filename)
                    # Create download URL for the redacted file
                    redacted_filename = redacted_file_path.name
                    response_data["redacted_file_url"] = f"/api/download/{redacted_filename}"
                    response_data["redacted_filename"] = redacted_filename
                except Exception as e:
                    logger.warning(f"Failed to create redacted Excel file: {str(e)}")
        
        # Step 5: Clean up temporary file (but keep redacted file for download)
        if DELETE_FILES_AFTER_PROCESSING:
            cleanup_file(file_path)
        
        return JSONResponse(response_data)
        
    except Exception as e:
        # If anything goes wrong, tell React what happened
        raise HTTPException(
            status_code=500, 
            detail=f"Processing failed: {str(e)}"
        )

@app.get("/api/download/{filename}")
async def download_redacted_file(filename: str):
    """
    Download endpoint for redacted files (Excel, PDF, Word)
    """
    try:
        # Security: Only allow downloads from the data directory
        file_path = Path("data/processed_files") / filename
        
        # Ensure the file exists and is within our allowed directory
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Additional security check to prevent directory traversal
        if not str(file_path.resolve()).startswith(str(Path("data/processed_files").resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Determine media type based on file extension
        file_extension = file_path.suffix.lower()
        media_types = {
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel',
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword'
        }
        
        media_type = media_types.get(file_extension, 'application/octet-stream')
        
        # Return the file for download
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type=media_type
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.get("/api/health")
async def detailed_health_check():
    """Check if all services are working"""
    return {
        "api": "running",
        "ocr": "available", 
        "file_upload": "ready",
        "supported_formats": [".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".xlsx", ".xls", ".pdf", ".docx", ".doc"],
        "pii_detection": "enabled"
    }

# For testing: run with python -m uvicorn app.api.main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000, reload=True)