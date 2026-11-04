# Fake News Detection System: Project Specification

## Project Overview
A Fake News Detection System evaluates the credibility of news by using Natural Language Processing (NLP) to extract linguistic patterns and machine learning classifiers to predict whether the text is legitimate or fabricated.

## Languages and Frameworks
* **Python:** The core programming language for data manipulation, NLP, and model training.
* **Scikit-Learn:** Used to build the machine learning pipeline, specifically for TF-IDF vectorization (converting text to numbers) and training a lightweight model like a PassiveAggressive or Logistic Regression classifier.
* **spaCy:** Essential for text preprocessing, such as removing noise, filtering stop words, and reducing words to their root forms.
* **FastAPI:** A lightweight Python backend framework to serve your trained machine learning model as a real-time API endpoint.
* **React** For building a clean frontend interface where users can input data and visualize the credibility results.

## Standout CV Features (High Impact, Low Complexity)
* **URL Parsing:** Instead of forcing users to copy-paste text, allow them to submit a news link. You can use the `BeautifulSoup` library to automatically extract the main article text from the URL.
* **Confidence Scoring:** Display a probability percentage alongside the final "Real" or "Fake" verdict so the user understands the model's certainty.
* **Word Highlighting (Explainability):** Use the classifier's feature weights to highlight specific sensationalist words or phrases in the text that contributed most to a "fake" classification.
* **User Feedback Loop:** Add a "Flag as Incorrect" button on the results page to show recruiters you understand real-world model deployment and continuous data collection.

## Team Roles & Responsibilities
This divides the work evenly between data science and software engineering for a two-person team.

* **Person A (Machine Learning & Data):** Focuses entirely on the AI. They will clean the datasets using **NLTK** (removing useless words like "the" or "and"), train the model using **Scikit-Learn**, and figure out which text features are most important for the confidence score.
* **Person B (Full-Stack & Integration):** Focuses on the application. They will build the **FastAPI** backend, write the **BeautifulSoup** script to scrape articles from URLs, and create the frontend interface where users see the results.

## Project Structure
Keep your files organized from day one. Here is the standard architecture for an ML-powered web app:

```text
fake-news-detector/
├── data/                  # Store your raw and cleaned CSV datasets here
├── models/                # Save your trained models here (e.g., model.pkl)
├── notebooks/             # Jupyter Notebooks for data exploration and testing
├── backend/               
│   ├── app.py             # The main FastAPI server file
│   ├── scraper.py         # BeautifulSoup logic for extracting text from links
│   └── predictor.py       # Script that loads your model and predicts credibility
├── frontend/              # HTML/CSS/JS or React files for the user interface
├── requirements.txt       # List of Python dependencies (pip freeze)
└── README.md              # Instructions on how to run the project
```

*(Note: `.pkl` is Python's format for saving a trained machine learning model. You train it once in your notebook, save it as a `.pkl`, and load it instantly in your backend without needing to retrain).*

## Implementation Plan & Milestones

**Milestone 1: Project Setup & Data (Days 1-3)**
* **Both:** Create a GitHub repository and a Python **Virtual Environment** (an isolated folder that keeps your project's libraries separate from your computer's global settings).
* **Person A:** Download a dataset (like the ISOT Fake News dataset from Kaggle) and place it in the `data/` folder.
* **Person B:** Create the basic file structure and a simple "Hello World" FastAPI endpoint in `app.py`.

**Milestone 2: The Core Model (Days 4-7)**
* **Person A:** Write a Jupyter Notebook to clean the text data and convert words into numbers (TF-IDF Vectorization).
* **Person A:** Train a classifier, test its accuracy, and export it as a `model.pkl` file into the `models/` folder.
* **Person B:** Build a basic HTML/CSS frontend with a search bar and a "Check News" button.

**Milestone 3: URL Scraping & API Logic (Days 8-11)**
* **Person B:** Write `scraper.py` using BeautifulSoup to automatically download and extract the paragraph text when a user pastes a URL.
* **Person A:** Write `predictor.py` to load the `.pkl` model and create a function that takes a raw string of text and returns a "Real" or "Fake" prediction.

**Milestone 4: Assembly & Polish (Days 12-14)**
* **Person B:** Connect the frontend button to the FastAPI backend.
* **Person A:** Add the confidence score percentage to the API response.
* **Both:** Test the full pipeline: Paste a live URL -> Scraper grabs text -> Model predicts -> UI shows the final score.