# MissionSpec AI

MissionSpec AI is a Python Flask app and CLI that turns a plain-text technical requirement into:

- Parsed sub-requirements
- A generated Python scaffold
- Generated pytest tests
- A compliance checklist in markdown

## Files Included

- `app.py`: Flask web UI entry point
- `missionspec.py`: Core generation logic and CLI
- `requirements.txt`: Python dependencies for deployment
- `vercel.json`: Vercel routing configuration

## Deploy To Vercel

### Option 1: Upload with the Vercel Dashboard

1. Sign in to [Vercel](https://vercel.com/).
2. Create a new project.
3. Upload the contents of this bundle as the project source.
4. Make sure the root directory contains:
   - `app.py`
   - `missionspec.py`
   - `requirements.txt`
   - `vercel.json`
5. Deploy the project.

Vercel should detect the Python app automatically and route all traffic to `app.py`.

### Option 2: Deploy with the Vercel CLI

1. Install the Vercel CLI:

```bash
npm install -g vercel
```

2. In the project directory, run:

```bash
vercel login
vercel deploy
```

3. For a production deployment, run:

```bash
vercel --prod
```

## Run Locally

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start the Flask app:

```bash
python app.py
```

3. Open:

```text
http://127.0.0.1:5000/
```

## Notes

- The web UI loads with a default sample requirement already filled in.
- The Download Report button exports a markdown file named `missionspec_report.md`.
- The CLI is still available through `missionspec.py` if you want terminal-based use.
