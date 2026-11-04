# Fake News Detection System

An NLP and Machine Learning application to evaluate news credibility in real-time.

---

## Project Structure

```text
fake-news-detector/
├── data/                  # Raw and cleaned CSV datasets
├── models/                # Serialized trained models (e.g., model.pkl)
├── notebooks/             # Jupyter Notebooks for exploration and training
├── backend/               
│   ├── app.py             # FastAPI server and endpoints
│   ├── scraper.py         # BeautifulSoup logic for article URL parsing
│   └── predictor.py       # Model loading and credibility scoring
├── frontend/              # Web user interface (React)
├── requirements.txt       # Python dependencies
└── README.md              # Project documentation and setup instructions
```

---

## Quickstart: Backend

### 1. Activate the Virtual Environment
- **Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
- **Windows (Command Prompt):**
  ```cmd
  .\.venv\Scripts\activate.bat
  ```
- **macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the FastAPI Development Server
```bash
uvicorn backend.app:app --reload
```

The API will be available at:
- **Root endpoint:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Health check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Interactive API Docs (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
