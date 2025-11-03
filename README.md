# MedAlign Visualization Tool

An interactive Streamlit web application for exploring and analyzing the **MedAlign** dataset — a structured XML-based electronic health record (EHR) dataset developed by Stanford University.  
This tool allows you to visualize patient encounter timelines, inspect clinical notes, and perform global keyword searches across the dataset.


## Features
- **Patient-Level Visualization**  
  Browse individual XML EHR files and view encounter timelines, entry summaries, and clinical notes.
- **Entry-Level Summaries**  
  View total note counts, event types, and codes for each encounter entry.
- **Note-Level Explorer**  
  Inspect detailed metadata (type, code, timestamp) and full text of any note.
- **Global Keyword Search**  
  Perform full-dataset searches across all patients and attributes (`#text`, `@type`, `@code`, etc.).
- **Rich Interface**  
  Powered by [Streamlit](https://streamlit.io), with intuitive layout and dynamic controls.

---

## Dataset
The **MedAlign** dataset can be downloaded from the Stanford Shah Lab repository:
🔗 [Stanford Redivis Dataset – ShahLab / MedAlign](https://stanford.redivis.com/ShahLab/datasets)

## Installation
### 1. Clone this Repository
```bash
git clone https://github.com/jennycs0830/I-DocAssist.git
cd I-DocAssist
```

### 2. Create an Environment
```bash
conda create -n MedAlign python=3.10 -y
conda activate MedAlign
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

## Run the App
Launch the streamlit app locally
```bash
streamlit run app.py
```
Once started, open the URL shown in your terminal (usually http://localhost:8501￼).