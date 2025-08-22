# Deployment Guide for NutriTeen-Analyzer

This guide explains how to deploy the NutriTeen-Analyzer app.

---

## 1. Prerequisites
- Python 3.9+
- Git installed
- Heroku account (for deployment)

---

## 2. Local Setup
```bash
# Clone the repo
git clone https://github.com/cmkarthik2004/NutriTeen-Analyzer.git
cd NutriTeen-Analyzer

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py
