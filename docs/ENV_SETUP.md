# Environment Variable Setup

This project uses python-dotenv to manage environment variables through a `.env` file.

## Setup Instructions

### 1. Copy the Sample File

```bash
cp .env.sample .env
```

### 2. Edit the .env File

Open `.env` in your text editor and add your API keys:

```bash
# Anthropic API (for LLM-powered WONDER query builder)
ANTHROPIC_API_KEY="your-anthropic-api-key"
```

### 3. Verify Setup

The `.env` file will be automatically loaded when you import modules that use these environment variables.

Test with:

```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API Key loaded:', 'Yes' if os.getenv('ANTHROPIC_API_KEY') else 'No')"
```

## Security Notes

- The `.env` file is already listed in `.gitignore` and will NOT be committed to version control
- Never commit API keys or secrets to Git
- Each developer should have their own `.env` file with their own API keys
- For production deployments, use proper secret management (environment variables, secret managers, etc.)

## Getting API Keys

### Anthropic API Key

1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy and paste into your `.env` file

## Troubleshooting

**Error: Module 'dotenv' not found**

```bash
uv sync  # Install dependencies
```

**Error: API key not found**

- Make sure you copied `.env.sample` to `.env`
- Make sure you edited the `.env` file and added your actual API key (remove quotes if copied with them)
- Make sure the `.env` file is in the project root directory

**Alternative: Environment Variables**

If you prefer not to use a `.env` file, you can export environment variables directly:

```bash
export ANTHROPIC_API_KEY='your-key-here'
```

Add these to your shell profile (`.bashrc`, `.zshrc`, etc.) to make them persistent.
