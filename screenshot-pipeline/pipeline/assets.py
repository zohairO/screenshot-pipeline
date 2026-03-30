from dagster import asset, AssetExecutionContext
import pytesseract
from PIL import Image
import anthropic 
import json
import boto3
import tempfile
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

@asset                                                                               
def raw_screenshots() -> list[dict]:
    """Pull only unprocessed screenshots from S3."""                                 
    s3 = boto3.client("s3")
    bucket = os.environ["S3_BUCKET_NAME"]                                            
                
    conn = psycopg2.connect(                                                         
        host=os.environ["DB_HOST"],
        database=os.environ["DB_NAME"],                                              
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],                                          
    )           
    cursor = conn.cursor()
    cursor.execute("SELECT s3_key FROM processed_screenshots")
    already_processed = {row[0] for row in cursor.fetchall()}                        
    cursor.close()                                                                   
    conn.close()                                                                     
                                                                                    
    response = s3.list_objects_v2(Bucket=bucket)

    temp_dir = tempfile.mkdtemp()                                                    
    results = []
                                                                                    
    for obj in response.get("Contents", []):
        key = obj["Key"]
        if key in already_processed:
            continue
        if key.lower().endswith((".png", ".jpg", ".jpeg")):
            local_path = os.path.join(temp_dir, key.replace("/", "_"))               
            s3.download_file(bucket, key, local_path)                                
            results.append({"path": local_path, "s3_key": key})                      
                                                                                    
    return results


@asset
def ocr_results(raw_screenshots: list[dict]) -> list[dict]:
    """Run OCR on each screenshot and return text with confidence scores."""         
    results = []                                                                     
                                                                                    
    for item in raw_screenshots:                                                     
        image = Image.open(item["path"])
        text = pytesseract.image_to_string(image)
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT) 
                                                                                    
        confidence = [int(c) for c in data["conf"] if int(c) > 0]                    
        avg_confidence = sum(confidence) / len(confidence) if confidence else 0      
                                                                                    
        results.append({
            "source": item["path"],                                                  
            "s3_key": item["s3_key"],
            "text": text,
            "confidence": avg_confidence                                             
        })
                                                                                    
    return results

@asset
def confidence_routing(context: AssetExecutionContext, ocr_results: list[dict]) -> dict:      
    """Route OCR results based on confidence scores."""
    high_confidence = []
    low_confidence = []
    failed = []

    for result in ocr_results:
        if result["confidence"] >= 80:
            high_confidence.append(result)
        elif result["confidence"] >= 40:
            low_confidence.append(result)
        else:
            failed.append(result)

    context.log.info(f"High: {len(high_confidence)}, Low: {len(low_confidence)}, Failed: {len(failed)}")  
  
    return {
        "high": high_confidence,
        "low": low_confidence,
        "failed": failed,
    }


@asset
def llm_enrichment(confidence_routing: dict) -> list[dict]:
    """Send high-confidence OCR text to Claude for structured extraction."""
    client = anthropic.Anthropic()
    enriched = []

    for result in confidence_routing["high"]:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": f"""Analyze this OCR text from a screenshot. Return JSON only with
                                these fields:
                                - screen_type: what kind of screen this is (e.g. email_inbox, search_results, form, document)
                                - application: which app is shown (e.g. Gmail, Google Search, Google Forms)
                                - key_content: the main meaningful content, ignoring browser chrome and UI elements
                                - entities: any notable names, dates, numbers, or organizations found

                                OCR text:
                                {result['text']}"""
            }]
        )

        try:
            response_text = message.content[0].text
            response_text = response_text.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("\n", 1)[1]
                response_text = response_text.rsplit("```", 1)[0]
            analysis = json.loads(response_text)
        except json.JSONDecodeError:
            analysis = {"raw_response": message.content[0].text}

        enriched.append({
            "source": result["source"],
            "s3_key": result["s3_key"],
            "confidence": result["confidence"],
            "analysis": analysis,
            
        })

    return enriched

@asset
def store_enriched_results(context: AssetExecutionContext, llm_enrichment: list[dict]) -> None:
    """Store enriched OCR results in PostgreSQL."""       

    context.log.info(f"Received {len(llm_enrichment)} enriched results")                                                     
    conn = psycopg2.connect(
        host=os.environ["DB_HOST"],                                                                               
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )                                                                                                       
    cursor = conn.cursor()
                                                                                                            
    for item in llm_enrichment:
        analysis = item["analysis"]
        try:
            cursor.execute(
                """INSERT INTO enriched_screenshots
                    (source, confidence, screen_type, application, key_content, entities) VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    item["source"],
                    item["confidence"],
                    analysis.get("screen_type"),
                    analysis.get("application"),
                    analysis.get("key_content"),
                    json.dumps(analysis.get("entities", [])),
                )
            )
        except Exception as e:
            context.log.error(f"Insert failed: {e}")
            conn.rollback()    

    # Mark as processed
    for item in llm_enrichment:                                                      
        cursor.execute(
            "INSERT INTO processed_screenshots (s3_key) VALUES (%s) ON CONFLICT DO NOTHING",                                                                            
            (item["s3_key"],)
        )

    conn.commit()
    cursor.close()
    conn.close()

@asset(deps=[store_enriched_results])                                                
def run_dbt(context: AssetExecutionContext) -> None:
    """Run dbt transformations after enriched data is stored."""                     
    import subprocess                                                                
    result = subprocess.run(
        ["dbt", "run"],                                                              
                                                                                    
    cwd="/Users/zohairoomatia/Desktop/projects/screenshot-tracker/screenshot_analytics",
        capture_output=True,                                                         
        text=True,
    )                                                                                
    context.log.info(result.stdout)
    if result.returncode != 0:                                                       
        context.log.error(result.stderr)
        raise Exception("dbt run failed") 