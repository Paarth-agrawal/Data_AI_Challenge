# Data & AI Challenge — Candidate Ranking System

## What this does
Ranks 100,000 candidates for a Senior AI Engineer role using a 
multi-signal scoring system that evaluates skills, experience, 
career quality, and behavioral signals.

## Team
- Paarth Agrawal
- Piyush Jakhar

## Setup
1. Install Python 3.12
2. Install dependencies:
pip install -r requirements.txt

3. Place candidates.jsonl in this folder

## Single command to reproduce submission
python main.py

This processes all 100,000 candidates and outputs submission.csv

## How it works
- scorer.py — scores each candidate 0-100 based on 5 signals
- job_description.py — defines the role requirements
- main.py — runs the pipeline and generates submission CSV

## Compute environment
Windows 11, Python 3.12, 16GB RAM, CPU only
Runs in under 3 minutes on 100K candidates

## AI Tools Used
Claude (Anthropic) — used for code assistance and debugging