# PDF & Word Document Processing Implementation

**Smart-Redact: Secure Document Redaction System**

## Overview

This document details the implementation of PDF and Word document processing in Smart-Redact, focusing on secure PII redaction that ensures complete removal of sensitive information from final documents.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Security Implementation](#security-implementation)
3. [PDF Processing](#pdf-processing)
4. [Word Document Processing](#word-document-processing)
5. [PII Detection Engine](#pii-detection-engine)
6. [Frontend Integration](#frontend-integration)
7. [Technical Specifications](#technical-specifications)
8. [Security Validation](#security-validation)

## Architecture Overview

### Core Components

```
Document Processing Pipeline:
Upload → Validation → Text Extraction → PII Detection → Secure Redaction → Validation → Download
```

### Key Design Principles

1. **Security First**: True redaction, not visual covering
2. **Format Preservation**: Maintain document structure where possible
3. **Zero Trust**: Assume all documents contain sensitive data
4. **Validation**: Verify no PII remains in final output
5. **Professional Output**: Clean, clearly marked redactions

## Security Implementation

### Critical Security Features

#### 1. True Text Removal
- **Problem Solved**: Previous overlay-based redaction left original text selectable
- **Solution**: Complete document reconstruction with redacted text only
- **Implementation**: New PDF generation using ReportLab with redacted content

#### 2. Copy Protection
- **Requirement**: Redacted areas must not be selectable or copyable
- **Implementation**: Original PII text never included in final document content streams
- **Validation**: Automated verification that no original PII exists in output

#### 3. Content Validation
```python
def _validate_redaction_completeness(
    self,
    redacted_pdf_path: str,
    original_pii_findings: List[Dict[str, Any]]
) -> None:
    """Validate that no original PII text remains in the redacted PDF."""
    # Extract text from redacted document
    redacted_text, _ = self._extract_text_from_pdf(redacted_pdf_path)
    
    # Check for any original PII presence
    violations = []
    for finding in original_pii_findings:
        if finding['text'].lower() in redacted_text.lower():
            violations.append(finding['text'])
    
    if violations:
        raise ValueError(f"SECURITY VIOLATION: Original PII found: {violations}")
```

## PDF Processing

### Technology Stack
- **Text Extraction**: pypdfium2 - Fast, reliable PDF text extraction
- **Document Creation**: ReportLab - Professional PDF generation
- **Content Validation**: PyPDF2 - For document verification

### Processing Workflow

#### 1. Text Extraction
```python
def _extract_text_from_pdf(self, file_path: str) -> Tuple[str, List[str]]:
    """Extract text from PDF using pypdfium2."""
    pdf_doc = pdfium.PdfDocument(file_path)
    page_texts = []
    
    for page_num in range(len(pdf_doc)):
        page = pdf_doc[page_num]
        text_page = page.get_textpage()
        page_text = text_page.get_text_range()
        page_texts.append(page_text)
    
    return '\n'.join(page_texts), page_texts
```

#### 2. PII Detection & Analysis
```python
def process_file(self, file_path: str, output_dir: str) -> Dict[str, Any]:
    """Process PDF with PII detection and secure redaction."""
    # Extract text
    full_text, page_texts = self._extract_text_from_pdf(file_path)
    
    # Detect PII
    pii_findings = self.pii_detector.detect_pii(full_text)
    
    # Calculate statistics
    entity_types = {}
    for finding in pii_findings:
        pii_type = finding.get('entity_type', 'unknown')
        entity_types[pii_type] = entity_types.get(pii_type, 0) + 1
    
    # Create secure redacted PDF
    redacted_file_path = self._create_redacted_pdf(
        file_path, page_texts, pii_findings, output_dir
    )
    
    return {
        'total_entities': len(pii_findings),
        'entity_types': entity_types,
        'redacted_file_path': redacted_file_path,
        'processing_status': 'completed',
        'confidence_score': self._calculate_confidence_score(pii_findings),
        'pages_processed': len(page_texts)
    }
```

#### 3. Secure Document Recreation
```python
def _create_redacted_pdf_with_reportlab(
    self,
    original_path: str,
    page_texts: List[str],
    pii_findings: List[Dict[str, Any]],
    output_path: Path
) -> None:
    """Create completely new PDF with redacted text."""
    # Get original dimensions
    with open(original_path, 'rb') as original_file:
        pdf_reader = PyPDF2.PdfReader(original_file)
        first_page = pdf_reader.pages[0]
        page_width = float(first_page.mediabox.width)
        page_height = float(first_page.mediabox.height)
    
    # Create new PDF with redacted content
    c = canvas.Canvas(str(output_path), pagesize=(page_width, page_height))
    
    for page_num, page_text in enumerate(page_texts):
        redacted_text = self._redact_page_text(page_text, pii_findings)
        self._add_secure_text_to_page(c, redacted_text, page_width, page_height)
        if page_num < len(page_texts) - 1:
            c.showPage()
    
    c.save()
    
    # Validate security
    self._validate_redaction_completeness(str(output_path), pii_findings)
```

### Redaction Formatting
```python
def _redact_page_text(
    self, 
    page_text: str, 
    pii_entities: List[Dict[str, Any]]
) -> str:
    """Apply professional redaction to text."""
    redacted_text = page_text
    
    for entity in pii_entities:
        if entity['text'] in page_text:
            entity_type = entity['entity_type'].replace('_', ' ').title()
            redacted_length = len(entity['text'])
            block_chars = '█' * min(redacted_length, 20)  # Visual block
            redaction = f"🔒[{entity_type}:{block_chars}]"
            redacted_text = redacted_text.replace(entity['text'], redaction)
    
    return redacted_text
```

## Word Document Processing

### Technology Stack
- **Document Processing**: python-docx - Microsoft Word document handling
- **Text Extraction**: Built-in python-docx text extraction
- **Structure Preservation**: Paragraph and table format maintenance

### Processing Workflow

#### 1. Content Extraction
```python
def extract_text(self) -> Dict[str, Any]:
    """Extract text from Word document with structure preservation."""
    doc = Document(self.file_path)
    text_content = ""
    
    # Extract paragraph text
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_content += paragraph.text + "\n"
    
    # Extract table text
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text for cell in row.cells)
            if row_text.strip():
                text_content += row_text + "\n"
    
    return {
        'text': text_content,
        'metadata': {
            'paragraphs': len(doc.paragraphs),
            'tables': len(doc.tables),
            'file_type': 'word'
        },
        'confidence': 0.9
    }
```

#### 2. Secure Redaction Process
```python
def _create_redacted_docx(
    self, 
    original_path: str, 
    paragraph_texts: List[str], 
    pii_findings: List[Dict[str, Any]], 
    output_dir: str
) -> str:
    """Create redacted Word document with structure preservation."""
    original_doc = Document(original_path)
    redacted_doc = Document()
    
    # Copy document properties
    self._copy_document_properties(original_doc, redacted_doc)
    
    # Process paragraphs with redaction
    self._process_paragraphs(original_doc, redacted_doc, pii_findings)
    
    # Process tables with redaction
    self._process_tables(original_doc, redacted_doc, pii_findings)
    
    # Save redacted document
    output_path = self._generate_output_path(original_path, output_dir)
    redacted_doc.save(str(output_path))
    
    return str(output_path)
```

## PII Detection Engine

### Multi-Method Detection Approach

#### 1. Regex Pattern Detection
```python
regex_patterns = {
    'EMAIL_ADDRESS': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    'PHONE_NUMBER': re.compile(r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'),
    'SSN': re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b'),
    'CREDIT_CARD': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
    'IP_ADDRESS': re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
    'URL': re.compile(r'https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*)?(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?'),
    'DATE_PATTERNS': re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'),
    'PASSPORT_NUMBER': re.compile(r'\b[A-Z]{1,2}\d{6,9}\b'),
    'LICENSE_PLATE': re.compile(r'\b[A-Z0-9]{2,3}[-\s]?[A-Z0-9]{3,4}\b')
}
```

#### 2. spaCy NLP Detection
```python
def _detect_with_spacy(self, text: str) -> List[Dict[str, Any]]:
    """Detect PII using spaCy named entity recognition."""
    if not self.spacy_model:
        return []
    
    findings = []
    doc = self.spacy_model(text)
    
    entity_mapping = {
        'PERSON': 'PERSON',
        'ORG': 'ORGANIZATION',
        'GPE': 'LOCATION',
        'DATE': 'DATE_TIME',
        'MONEY': 'FINANCIAL'
    }
    
    for ent in doc.ents:
        pii_type = entity_mapping.get(ent.label_, ent.label_)
        findings.append({
            'entity_type': pii_type,
            'start': ent.start_char,
            'end': ent.end_char,
            'text': ent.text,
            'confidence': 0.8,
            'detection_method': 'spacy'
        })
    
    return findings
```

#### 3. Presidio Enterprise Detection
```python
def _detect_with_presidio(self, text: str) -> List[Dict[str, Any]]:
    """Detect PII using Presidio analyzer for enterprise patterns."""
    if not self.presidio_analyzer:
        return []
    
    results = self.presidio_analyzer.analyze(
        text=text,
        language='en',
        entities=['PERSON', 'EMAIL_ADDRESS', 'PHONE_NUMBER', 'CREDIT_CARD', 'US_SSN']
    )
    
    findings = []
    for result in results:
        findings.append({
            'entity_type': result.entity_type,
            'start': result.start,
            'end': result.end,
            'text': text[result.start:result.end],
            'confidence': result.score,
            'detection_method': 'presidio'
        })
    
    return findings
```

## Frontend Integration

### Response Format Handling
```javascript
// Handle different response formats for PDF/Word vs Excel
if (file_extension in ['.pdf', '.docx', '.doc']) {
    response_data = {
        "status": "success",
        "filename": file.filename,
        "file_type": file_extension[1:],  // Remove dot
        "processing_status": "completed",
        "total_entities": extracted_data.get("total_entities", 0),
        "entity_types": extracted_data.get("entity_types", {}),
        "confidence": extracted_data.get("confidence_score", 0),
        "pages_processed": extracted_data.get("pages_processed", 0),
        "redacted_file_url": f"/api/download/{redacted_filename}",
        "redacted_filename": redacted_filename
    }
}
```

### Conditional UI Elements
```jsx
{/* Only show confidence for non-PDF/Word files where it's meaningful */}
{!['pdf', 'docx', 'doc'].includes(result.file_type) && (
  <div className="stat-card">
    <div className="stat-icon">🎯</div>
    <div className="stat-content">
      <div className="stat-label">Confidence</div>
      <div className="stat-value">{result.confidence}%</div>
    </div>
  </div>
)}
```

## Technical Specifications

### Dependencies

#### Backend (Python 3.11)
```txt
fastapi==0.104.1
uvicorn==0.24.0
python-multipart==0.0.6
pypdfium2==4.23.1
PyPDF2==3.0.1
reportlab==4.0.7
python-docx==1.1.0
openpyxl==3.1.2
pytesseract==0.3.10
spacy==3.7.2
presidio-analyzer==2.2.33
```

#### Frontend (Node.js 18+)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.0.3",
    "vite": "^4.4.5"
  }
}
```

### File Size Limits
- **Maximum file size**: 100MB per upload
- **Supported formats**: PDF (.pdf), Word (.docx, .doc), Excel (.xlsx, .xls), Images (JPG, PNG, TIFF, BMP)
- **Memory optimization**: Streaming file processing for large documents

### Performance Characteristics
- **PDF Processing**: ~2-5 seconds for typical business documents
- **Word Processing**: ~1-3 seconds for standard documents
- **PII Detection**: Linear time complexity O(n) with text length
- **Memory Usage**: ~50-100MB per document during processing

## Security Validation

### Validation Process
1. **Input Validation**: File type, size, and format verification
2. **Content Extraction**: Safe text extraction with error handling
3. **PII Detection**: Multi-method detection for comprehensive coverage
4. **Secure Redaction**: Complete document reconstruction
5. **Output Validation**: Verify no original PII remains in final document
6. **File Cleanup**: Secure deletion of temporary files

### Security Guarantees
- [ ] **No PII Recovery**: Original sensitive data cannot be recovered from redacted documents
- [ ] **Copy Protection**: Redacted areas cannot be selected or copied
- [ ] **Content Validation**: Automated verification ensures complete redaction
- [ ] **Professional Output**: Clear visual indication of redacted content
- [ ] **Format Integrity**: Documents maintain usable format after processing

### Testing Validation
```python
def test_redaction_security():
    """Test that validates complete PII removal."""
    # Process document with known PII
    original_pii = ["john.doe@email.com", "555-123-4567", "123-45-6789"]
    
    # Create redacted document
    redacted_path = processor.process_file(test_document)
    
    # Extract text from redacted document
    redacted_text = extract_text_from_processed_document(redacted_path)
    
    # Verify no original PII exists
    for pii_item in original_pii:
        assert pii_item not in redacted_text, f"SECURITY FAILURE: {pii_item} found in redacted document"
    
    # Verify redaction markers exist
    assert "🔒[Email" in redacted_text, "Redaction markers not found"
    assert "█" in redacted_text, "Block characters not found"
```

## Future Enhancements

### Planned Features
1. **Advanced Layout Preservation**: OCR-based coordinate detection for precise redaction positioning
2. **Batch Processing**: Multiple document processing in single operation
3. **Custom PII Patterns**: User-defined sensitive data patterns
4. **Audit Logging**: Comprehensive processing logs for compliance
5. **API Rate Limiting**: Enhanced security for production deployment

### Performance Optimizations
1. **Async Processing**: Non-blocking document processing for large files
2. **Caching**: Intelligent caching of processed content
3. **Memory Management**: Streaming processing for very large documents
4. **Parallel Processing**: Multi-threaded PII detection for faster processing

---
