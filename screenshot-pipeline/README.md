# Screenshot Tracker                                                                     
                                                                                           
I take a lot of screenshots of things I send to ChatGPT — error messages, code snippets, 
documentation, UI bugs. I realised this is basically a log of everything I struggle with.
So I built a pipeline to analyse those screenshots and surface patterns in what I ask   
for help with the most, so I can focus on improving in those areas.

## How it works

1. **Screenshots land in S3** — raw screenshots are uploaded to an S3 bucket             
2. **OCR extracts text** — Tesseract runs on each image to pull out readable content
3. **Confidence routing** — OCR results are scored and routed: high-confidence text goes 
straight to enrichment, low-confidence results are flagged                               
4. **LLM enrichment** — Claude analyses the extracted text and classifies each screenshot
(screen type, application, key content, entities)                                       
5. **Storage** — enriched results are stored in a PostgreSQL database on AWS RDS
                                                                                        
## Tech stack   
                                                                                        
- **Dagster** — orchestration                                                            
- **Tesseract** — OCR
- **Claude API** — LLM enrichment                                                        
- **AWS S3** — screenshot storage
- **AWS RDS (PostgreSQL)** — structured data storage                                     
- **Terraform** — infrastructure as code
                                                                                        
## Setup        

1. Clone the repo                                                                        
2. Create a virtual environment and install dependencies:
    ```bash                                                                               
    python -m venv venv
    source venv/bin/activate
    pip install -e ".[dev]"                                                               
3. Create a .env file with your credentials (see .env.example)
4. Run the Dagster UI:                                                                   
dagster dev     
                                                                                        
What's next
                                                                                        
- dbt transformation layer to aggregate patterns over time                               
- Dashboard to visualise weak areas and track improvement
- Neo4j graph to map relationships between topics        