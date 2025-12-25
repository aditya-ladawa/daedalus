# DAEDALUS

**Deep Agent based Exploratory Discovery and Analytical Literature Understanding System**

DAEDALUS is a deep, long-running research agent designed for rigorous, in-depth scientific inquiry. It autonomously conducts large-context literature analysis, identifies research gaps, links and synthesizes evidence across studies, and structures knowledge into coherent graphs and representations. DAEDALUS analyzes PDFs, images, and experimental results, generates visualizations and charts, and produces precise, well-structured reports to support evidence-driven research progress.

_**DAEDALUS** is named after the mythological master craftsman, known for designing complex systems through intellect and precision. The name reflects our agent’s role in systematically constructing knowledge by assembling evidence, linking structures, and navigating complexity through disciplined reasoning._

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- pnpm

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/aditya-ladawa/daedalus.git
   cd daedalus
   ```

2. **Set up the Python environment:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Install Node.js dependencies:**

   ```bash
   pnpm install
   ```

   OR

   ```bash
   npm install
   ```

### Configuration

Create a `.env` file in the root directory and add your Google Gemini API key:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
PROJECTS_DIR=./projects
CHECKPOINTS_DB=./checkpoints.sqlite
```

### Running the Application

Start both the FastAPI backend and the Next.js frontend concurrently:

```bash
pnpm dev
```

OR

```bash
npm run dev
```

The application will be available at `http://localhost:3000`.

## Features

- **Project Management**: Create, rename, and delete research projects.
- **File Management**: Upload and preview research papers (PDFs), images, and data files.
- **Dynamic Interface**: Modern, responsive UI with real-time chat and file viewing.
