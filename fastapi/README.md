# Chat Application with FastAPI Backend and Streamlit Frontend

This is a simple chat application that uses a FastAPI backend (`app.py`) and a Streamlit frontend (`chat.py`). The backend processes user messages, and the frontend provides an interactive chat interface.

## Prerequisites

- Python 3.7 or higher
- `pip` package manager

## Setup Instructions

### 0. Set up an .env file

Create an .env file with `touch .env` and replace the contents below with your actual API keys

```bash
PINECONE_API_KEY=XXXX
OPENAI_API_KEY=XXXX
```

### 1. Install Dependencies

Navigate to the project directory in your terminal and install the required packages using the provided `requirements.txt` file:

```bash
pip install -r requirements.txt
```

### 2. Start the FastAPI Backend

Run the FastAPI app (`app.py`) using Uvicorn:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

- This will start the backend server on `http://localhost:8000`.
- Keep this terminal window open to maintain the running server.

### 3. Run the Streamlit Frontend

In a new terminal window, start the Streamlit app (`chat.py`):

```bash
streamlit run chat.py
```

- This will launch the frontend interface in your default web browser.
- If it doesn't open automatically, navigate to `http://localhost:8501` in your browser.

## Usage

- **Chat with the Bot**: Use the input box in the Streamlit app to send messages to the bot.
- **Conversation Continuity**: The conversation history and context are maintained throughout the session.

## Notes

- **Ensure Backend is Running**: The FastAPI backend must be running before starting the Streamlit frontend.
- **Dependencies**: All necessary Python packages are listed in `requirements.txt`.
- **Port Configuration**: Default ports are `8000` for the backend and `8501` for the frontend. Adjust if necessary.