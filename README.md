# GitLean: Token-Efficient Git Pull Explainer & Reviewer

[![Built with Paritok](https://img.shields.io/badge/Built%20with-Paritok-1f2d3d)](https://github.com/Paritok-official/paritok-4b-v1)

GitLean is a developer tool and dashboard specifically designed for developers working in teams who pull updates from colleagues and ask an AI agent (like Antigravity or Claude Code) to explain, summarize, or review what was just pulled. 

By sitting as a smart proxy between your IDE assistant and upstream LLMs, GitLean intercepts requests about pulled changes, automatically isolates the exact modified files (using `git diff HEAD@{1} HEAD`), and compresses them via Paritok. This reduces prompt token usage, latency, and costs by **75%+** while providing clean, concise code explanations directly in your editor.

---

## ⚡ Core Features

1. **Git Pull Interceptor**: Automatically compares your branch's state before and after you run `git pull` (comparing `HEAD@{1}` to `HEAD`), isolating only the changes introduced by your team.
2. **Context Compression Visualizer**: A split-screen visual diff that shows original source files side-by-side with Paritok's compressed representation (collapsing boilerplate imports and helpers, highlighting active logic).
3. **Savings Analytics**: Dynamic interactive charts mapping token reduction percentages, cost savings in USD, and latency metrics across your reviews.
4. **Automated Diagnostic Suite**: A built-in security and integration auditor that probes the Paritok hosted API and generates a detailed bug and feedback report, writing results directly to `feedback.md`.

---

## 🛠️ Tech Stack

- **Backend**: Python standard library `http.server` (zero external dependencies, runs out-of-the-box).
- **Frontend**: React, Vite, glassmorphism dark-mode vanilla CSS.
- **Integration**: Direct connection to Paritok Hosted GPU API (with pre-configured shared key), Anthropic Claude API (Upstream LLM).

---

## 🚀 Quick Start

### 1. Prerequisities
Ensure Python 3.9+ and Node.js are installed on your system.

### 2. Run the Backend
1. Navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the backend server:
   ```bash
   python run_backend.py
   ```
   *The backend will start running on `http://127.0.0.1:8000` (no external dependencies required!).*


### 3. Run the Frontend
1. In a separate terminal, navigate to the frontend folder:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Start the Vite dev server:
   ```bash
   npm run dev
   ```
   *Open `http://localhost:5173` in your browser to view the GitLean dashboard.*

---

## 📦 Production Distribution (SDK & VS Code Extension)

To remove cloning and manual setup friction, GitLean is distributed in two developer-friendly formats:

### 1. The GitLean CLI SDK (PyPI / npm package)
Instead of cloning the repo, teams install GitLean globally:
```bash
# Install the SDK
pip install gitlean-cli

# Start the compression proxy in any workspace
gitlean up --port 8000
```
This instantly fires up the background server and points your local terminal's agent context to GitLean.

### 2. The VS Code / Cursor Extension
For the ultimate zero-friction workflow, developers install the GitLean extension from the Marketplace:
1. Open the [vscode-extension/](file:///C:/Users/user/Desktop/gitlean/vscode-extension) folder.
2. In your terminal, run `vsce package` to compile the extension into a `.vsix` installer.
3. Drag-and-drop the `.vsix` into VS Code.
*   **What it does**: The extension automatically spawns the proxy server on startup, binds `ANTHROPIC_BASE_URL` to your terminals, and provides a **split-screen visual diff panel directly inside VS Code** (no external browser tab needed!).

---

### 4. Run the Local CLI Reviewer
You can also run GitLean directly in your terminal without starting any servers:
```bash
# Run a review on your active local changes
python gitlean_cli.py --review

# Run a review in Demo Mode using mock repositories
python gitlean_cli.py --review --demo
```
This prints the full token reduction analysis and code review comments directly to your terminal.

---

## 🤖 CI/CD Production Integration (GitHub Action)

GitLean can be deployed to production as a GitHub Actions workflow that automatically reviews pull requests and posts comments.

1. Create a file `.github/workflows/gitlean.yml` in your repo (already provided in this directory).
2. Configure secrets in your repository settings:
   - `PARITOK_API_KEY`: Your key from the paritok.com dashboard.
   - `ANTHROPIC_API_KEY`: Your Anthropic Claude API Key.
3. Every time a PR is opened or synchronized, the GitLean review bot will:
   - Extract PR diffs and modified files.
   - Compress the context via the Paritok API.
   - Post an automated review directly as a PR comment, along with a token-savings badge!

---

## 📝 Configuration (`paritok.yaml`)

GitLean reads configuration from `paritok.yaml` in the root folder. You can configure settings directly in the web dashboard or edit the YAML manually:

```yaml
use_gpu_server: true
gpu_server:
  api_key: "pk_live_..." # Replace with your API key from paritok.com
```

---

## 🏆 Hackathon Credits & Submissions

- **Built with**: [Paritok](https://github.com/Paritok-official/paritok-4b-v1) - The open-source model layer routing only context that matters.
- **License**: Apache 2.0 (See [LICENSE](file:///C:/Users/user/.gemini/antigravity/scratch/gitlean/LICENSE))
- **Valuable Feedback**: Formatted report of API and proxy bugs discovered during development is exported to [feedback.md](file:///C:/Users/user/.gemini/antigravity/scratch/gitlean/feedback.md).
- **Social Posts**: Marketing tweets and campaign notes are tracked in [social_media.md](file:///C:/Users/user/.gemini/antigravity/scratch/gitlean/social_media.md).
