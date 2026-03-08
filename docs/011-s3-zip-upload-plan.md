# S3-Based ZIP Upload & Multi-Agent Analysis Plan

## Overview
Enable production verification of entire codebases via S3 ZIP upload, where the orchestrator coordinates all agents to analyze the extracted project.

## Architecture

```
User → Upload ZIP → S3 → Orchestrator → Extract → Agents → Results
                     ↓
              s3://uploads/{session-id}/codebase.zip
                     ↓
              /tmp/{session-id}/extracted/
                     ↓
         ┌───────────┴───────────┐
         ↓                       ↓
    Code Files              Config Files
         ↓                       ↓
    All Agents              Metadata
```

---

## Phase 1: S3 Upload & Storage

### 1.1 S3 Bucket Structure

```
s3://a2a-analysis/
├── uploads/{session-id}/
│   └── codebase.zip                    # Original upload
├── extracted/{session-id}/
│   └── {project-files}                 # Extracted (optional)
├── results/{session-id}/
│   ├── code-analysis.json
│   ├── research.json
│   ├── validation.json
│   ├── tests.json
│   └── final-report.json
└── artifacts/{session-id}/
    ├── generated-tests/
    └── research-docs/
```

### 1.2 Upload API Endpoint

```python
# src/orchestorator_agent/agent.py

from fastapi import UploadFile, File, Form
import boto3
import zipfile
import tempfile
from pathlib import Path

# S3 Client
s3_client = boto3.client('s3',
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)

S3_BUCKET = os.getenv('S3_BUCKET', 'a2a-analysis')

@app.post("/upload")
async def upload_codebase(
    file: UploadFile = File(...),
    project_name: str = Form(None),
    language: str = Form("auto")
):
    """
    Upload ZIP file to S3 and trigger analysis
    """
    session_id = str(uuid.uuid4())
    
    # 1. Upload to S3
    s3_key = f"uploads/{session_id}/codebase.zip"
    
    try:
        # Upload file to S3
        s3_client.upload_fileobj(
            file.file,
            S3_BUCKET,
            s3_key,
            ExtraArgs={'ContentType': 'application/zip'}
        )
        
        # 2. Create analysis session
        session_metadata = {
            "session_id": session_id,
            "project_name": project_name or file.filename,
            "s3_uri": f"s3://{S3_BUCKET}/{s3_key}",
            "language": language,
            "status": "uploaded",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Save to Redis
        await redis_store.create_session(session_id, session_metadata)
        
        # 3. Trigger async analysis
        background_tasks.add_task(
            process_codebase_analysis,
            session_id,
            s3_key
        )
        
        return {
            "session_id": session_id,
            "status": "processing",
            "s3_uri": f"s3://{S3_BUCKET}/{s3_key}",
            "message": "Analysis started. Use /status/{session_id} to check progress"
        }
        
    except Exception as e:
        return {"error": str(e)}, 500


@app.get("/status/{session_id}")
async def get_analysis_status(session_id: str):
    """Get analysis progress"""
    status = await redis_store.get_session_status(session_id)
    metadata = await redis_store.client.get(f"session:{session_id}:metadata")
    
    return {
        "session_id": session_id,
        "metadata": json.loads(metadata) if metadata else {},
        "agents": status,
        "overall_progress": calculate_progress(status)
    }


@app.get("/results/{session_id}")
async def get_analysis_results(session_id: str):
    """Get final analysis results"""
    # Fetch from S3
    result_key = f"results/{session_id}/final-report.json"
    
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=result_key)
        results = json.loads(response['Body'].read())
        return results
    except s3_client.exceptions.NoSuchKey:
        return {"error": "Results not ready yet"}, 404
```

---

## Phase 2: ZIP Extraction & File Discovery

### 2.1 Extraction Service

```python
# src/shared/file_processor.py

import zipfile
import tempfile
from pathlib import Path
from typing import Dict, List, Any
import os

class CodebaseProcessor:
    """Extract and analyze codebase structure"""
    
    def __init__(self, s3_client, bucket: str):
        self.s3 = s3_client
        self.bucket = bucket
    
    async def download_and_extract(self, s3_key: str, session_id: str) -> str:
        """Download ZIP from S3 and extract"""
        
        # Create temp directory
        temp_dir = f"/tmp/analysis-{session_id}"
        os.makedirs(temp_dir, exist_ok=True)
        
        zip_path = f"{temp_dir}/codebase.zip"
        extract_path = f"{temp_dir}/extracted"
        
        # Download from S3
        self.s3.download_file(self.bucket, s3_key, zip_path)
        
        # Extract ZIP
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_path)
        
        return extract_path
    
    def discover_files(self, base_path: str) -> Dict[str, List[str]]:
        """Discover all code files by language"""
        
        files_by_language = {
            "python": [],
            "javascript": [],
            "java": [],
            "go": [],
            "rust": [],
            "other": []
        }
        
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "javascript",
            ".tsx": "javascript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust"
        }
        
        # Walk directory
        for root, dirs, files in os.walk(base_path):
            # Skip common ignore patterns
            dirs[:] = [d for d in dirs if d not in {
                'node_modules', '.git', '__pycache__', 'venv', 
                'dist', 'build', 'target', '.next'
            }]
            
            for file in files:
                ext = Path(file).suffix
                if ext in language_map:
                    lang = language_map[ext]
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, base_path)
                    files_by_language[lang].append(rel_path)
        
        return files_by_language
    
    def get_project_metadata(self, base_path: str) -> Dict[str, Any]:
        """Extract project metadata"""
        
        metadata = {
            "has_package_json": os.path.exists(f"{base_path}/package.json"),
            "has_requirements_txt": os.path.exists(f"{base_path}/requirements.txt"),
            "has_pom_xml": os.path.exists(f"{base_path}/pom.xml"),
            "has_cargo_toml": os.path.exists(f"{base_path}/Cargo.toml"),
            "has_go_mod": os.path.exists(f"{base_path}/go.mod"),
        }
        
        # Detect primary language
        if metadata["has_package_json"]:
            metadata["primary_language"] = "javascript"
        elif metadata["has_requirements_txt"]:
            metadata["primary_language"] = "python"
        elif metadata["has_pom_xml"]:
            metadata["primary_language"] = "java"
        elif metadata["has_cargo_toml"]:
            metadata["primary_language"] = "rust"
        elif metadata["has_go_mod"]:
            metadata["primary_language"] = "go"
        else:
            metadata["primary_language"] = "unknown"
        
        return metadata
    
    async def cleanup(self, session_id: str):
        """Remove temporary files"""
        temp_dir = f"/tmp/analysis-{session_id}"
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
```

---

## Phase 3: Orchestrator Workflow

### 3.1 Multi-File Analysis Workflow

```python
# src/orchestorator_agent/agent.py

async def process_codebase_analysis(session_id: str, s3_key: str):
    """
    Main workflow for analyzing entire codebase
    """
    
    processor = CodebaseProcessor(s3_client, S3_BUCKET)
    
    try:
        # 1. Download and extract
        await redis_store.update_session_agent_status(session_id, "orchestrator", {
            "status": "extracting",
            "message": "Downloading and extracting codebase"
        })
        
        extract_path = await processor.download_and_extract(s3_key, session_id)
        
        # 2. Discover files
        files_by_language = processor.discover_files(extract_path)
        project_metadata = processor.get_project_metadata(extract_path)
        
        total_files = sum(len(files) for files in files_by_language.values())
        
        await redis_store.update_session_agent_status(session_id, "orchestrator", {
            "status": "discovered",
            "message": f"Found {total_files} files",
            "files_by_language": files_by_language,
            "metadata": project_metadata
        })
        
        # 3. Run agents on each file
        all_results = {
            "code_analysis": [],
            "research": [],
            "validation": [],
            "tests": []
        }
        
        # Process files by language
        for language, file_list in files_by_language.items():
            if not file_list or language == "other":
                continue
            
            print(f"Processing {len(file_list)} {language} files...")
            
            for file_path in file_list[:50]:  # Limit to 50 files per language
                full_path = os.path.join(extract_path, file_path)
                
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        code_content = f.read()
                    
                    # Run all agents on this file
                    file_results = await analyze_single_file(
                        session_id,
                        file_path,
                        code_content,
                        language
                    )
                    
                    # Aggregate results
                    for agent_type, result in file_results.items():
                        all_results[agent_type].append({
                            "file": file_path,
                            "result": result
                        })
                    
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    continue
        
        # 4. Generate final report
        final_report = generate_final_report(
            session_id,
            all_results,
            project_metadata,
            files_by_language
        )
        
        # 5. Upload results to S3
        result_key = f"results/{session_id}/final-report.json"
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=result_key,
            Body=json.dumps(final_report, indent=2),
            ContentType='application/json'
        )
        
        # 6. Update session status
        await redis_store.update_session_agent_status(session_id, "orchestrator", {
            "status": "completed",
            "message": "Analysis complete",
            "result_uri": f"s3://{S3_BUCKET}/{result_key}"
        })
        
        # 7. Cleanup
        await processor.cleanup(session_id)
        
    except Exception as e:
        await redis_store.update_session_agent_status(session_id, "orchestrator", {
            "status": "failed",
            "error": str(e)
        })
        raise


async def analyze_single_file(
    session_id: str,
    file_path: str,
    code_content: str,
    language: str
) -> Dict[str, Any]:
    """Run all agents on a single file"""
    
    message_parts = [
        {"kind": "text", "text": code_content},
        {"kind": "data", "data": {
            "code": code_content,
            "language": language,
            "file_path": file_path,
            "session_id": session_id
        }}
    ]
    
    results = {}
    
    # Run agents in parallel
    tasks = [
        call_agent("code-logic-agent", message_parts, {"file": file_path}),
        call_agent("research-agent", message_parts, {"file": file_path}),
        call_agent("validation-agent", message_parts, {"file": file_path}),
        call_agent("test-run-agent", message_parts, {"file": file_path})
    ]
    
    agent_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    results["code_analysis"] = agent_results[0] if not isinstance(agent_results[0], Exception) else {"error": str(agent_results[0])}
    results["research"] = agent_results[1] if not isinstance(agent_results[1], Exception) else {"error": str(agent_results[1])}
    results["validation"] = agent_results[2] if not isinstance(agent_results[2], Exception) else {"error": str(agent_results[2])}
    results["tests"] = agent_results[3] if not isinstance(agent_results[3], Exception) else {"error": str(agent_results[3])}
    
    return results


def generate_final_report(
    session_id: str,
    all_results: Dict[str, List],
    project_metadata: Dict,
    files_by_language: Dict
) -> Dict[str, Any]:
    """Generate comprehensive analysis report"""
    
    # Aggregate statistics
    total_files = sum(len(files) for files in files_by_language.values())
    total_vulnerabilities = sum(
        len(r["result"].get("messages", [{}])[1].get("parts", [{}])[1].get("data", {}).get("issues", {}).get("security", []))
        for r in all_results.get("validation", [])
        if "result" in r
    )
    
    # Calculate average quality score
    quality_scores = []
    for r in all_results.get("code_analysis", []):
        if "result" in r:
            messages = r["result"].get("messages", [])
            if len(messages) > 1:
                data = messages[1].get("parts", [{}])[1].get("data", {})
                if "quality_score" in data:
                    quality_scores.append(data["quality_score"])
    
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    
    return {
        "session_id": session_id,
        "generated_at": datetime.utcnow().isoformat(),
        "project_metadata": project_metadata,
        "summary": {
            "total_files_analyzed": total_files,
            "files_by_language": {k: len(v) for k, v in files_by_language.items()},
            "total_vulnerabilities": total_vulnerabilities,
            "average_quality_score": round(avg_quality, 2),
            "critical_issues": total_vulnerabilities  # Simplified
        },
        "detailed_results": {
            "code_analysis": all_results["code_analysis"],
            "research": all_results["research"],
            "validation": all_results["validation"],
            "tests": all_results["tests"]
        },
        "recommendations": generate_recommendations(all_results)
    }


def generate_recommendations(all_results: Dict) -> List[str]:
    """Generate actionable recommendations"""
    recommendations = []
    
    # Check validation results
    validation_results = all_results.get("validation", [])
    if validation_results:
        high_severity = sum(
            1 for r in validation_results
            if "result" in r and "security" in str(r["result"])
        )
        if high_severity > 5:
            recommendations.append("⚠️ Multiple security vulnerabilities detected. Review and fix critical issues.")
    
    # Check code quality
    code_results = all_results.get("code_analysis", [])
    if code_results:
        low_quality = sum(
            1 for r in code_results
            if "result" in r and "quality_score" in str(r["result"])
        )
        if low_quality > 10:
            recommendations.append("📝 Code quality improvements needed. Add documentation and reduce complexity.")
    
    if not recommendations:
        recommendations.append("✅ Codebase looks good! Minor improvements suggested.")
    
    return recommendations
```

---

## Phase 4: Agent Updates

### 4.1 Update Agents to Handle File Context

```python
# All agents need to accept file_path in metadata

async def create_task(params: Dict[str, Any]) -> Dict[str, Any]:
    metadata = params.get("metadata", {})
    file_path = metadata.get("file")  # ← New
    session_id = metadata.get("session_id")  # ← New
    
    # Include file context in results
    task["metadata"]["file_path"] = file_path
    task["metadata"]["session_id"] = session_id
    
    return task
```

---

## Phase 5: Deployment Configuration

### 5.1 Environment Variables

```bash
# .env
AWS_REGION=us-east-1
S3_BUCKET=a2a-analysis
REDIS_URL=redis://localhost:6379
```

### 5.2 IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::a2a-analysis/*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::a2a-analysis"
    }
  ]
}
```

### 5.3 Requirements Update

```txt
# requirements.txt
fastapi
uvicorn
httpx
redis
boto3
python-multipart  # For file uploads
```

---

## Usage Flow

### 1. Upload ZIP

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@codebase.zip" \
  -F "project_name=MyProject" \
  -F "language=python"

Response:
{
  "session_id": "abc-123",
  "status": "processing",
  "s3_uri": "s3://a2a-analysis/uploads/abc-123/codebase.zip"
}
```

### 2. Check Status

```bash
curl http://localhost:8000/status/abc-123

Response:
{
  "session_id": "abc-123",
  "agents": {
    "orchestrator": {"status": "processing", "progress": 45},
    "code-logic-agent": {"status": "completed"},
    "validation-agent": {"status": "running"}
  },
  "overall_progress": 60
}
```

### 3. Get Results

```bash
curl http://localhost:8000/results/abc-123

Response:
{
  "session_id": "abc-123",
  "summary": {
    "total_files_analyzed": 150,
    "total_vulnerabilities": 3,
    "average_quality_score": 85.5
  },
  "detailed_results": {...}
}
```

---

## Implementation Timeline

| Phase | Task | Effort |
|-------|------|--------|
| 1 | S3 upload endpoint | 4h |
| 2 | ZIP extraction service | 4h |
| 3 | Multi-file orchestration | 8h |
| 4 | Agent updates | 4h |
| 5 | Testing & deployment | 6h |

**Total**: ~26 hours

---

## Benefits

✅ **Scalable** - S3 handles large files
✅ **Persistent** - Results stored in S3
✅ **Async** - Non-blocking analysis
✅ **Complete** - Analyzes entire projects
✅ **Traceable** - Session-based tracking
✅ **Production-Ready** - Real-world usage
