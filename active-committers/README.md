# GitHub Active Committers Analyzer

A Python script to analyze and identify active committers in a GitHub organization. This tool helps you understand who has been actively contributing to your organization's repositories within a specified time period.

## Features

- ✅ **Comprehensive Analysis**: Analyzes all repositories in an organization
- ✅ **Time-based Filtering**: Configurable time period for "active" contributors
- ✅ **Rate Limit Handling**: Automatically handles GitHub API rate limits
- ✅ **Detailed Statistics**: Optional detailed contributor statistics
- ✅ **Export Results**: Save results to JSON file
- ✅ **Error Handling**: Robust error handling for network issues and API errors
- ✅ **Progress Tracking**: Real-time progress updates during analysis

## Prerequisites

1. **Python 3.7+**
2. **GitHub Personal Access Token** with appropriate permissions:
   - `repo` (for private repositories)
   - `read:org` (to read organization data)

## Installation

1. Clone or download this script
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. **Set up your configuration using one of these methods:**

### Method 1: Using .env file (Recommended)
1. Copy the example environment file:
   ```bash
   copy .env.example .env
   ```
2. Edit `.env` and add your GitHub token:
   ```bash
   GITHUB_TOKEN=your_actual_token_here
   DEFAULT_ORG=your_default_org_name
   ```

### Method 2: Using environment variables
   ```bash
   # Windows PowerShell
   $env:GITHUB_TOKEN="your_token_here"
   
   # Windows CMD
   set GITHUB_TOKEN=your_token_here
   
   # Linux/Mac
   export GITHUB_TOKEN="your_token_here"
   ```

**🔐 Get your GitHub token from: https://github.com/settings/tokens**

Required scopes:
- `repo` (for private repositories)
- `read:org` (to read organization data)

## Usage

### Basic Usage
```bash
python active-commiters.py <organization_name>
```

### Using .env file (if DEFAULT_ORG is set)
```bash
# Will use DEFAULT_ORG from .env file
python active-commiters.py

# Or override the default org
python active-commiters.py different-org
```

### Advanced Usage
```bash
# Analyze last 90 days with detailed statistics
python active-commiters.py myorg --days 90 --stats

# Save results to a JSON file
python active-commiters.py myorg --output results.json

# Enable debug mode for troubleshooting
python active-commiters.py myorg --debug

# Combine options
python active-commiters.py myorg --days 180 --stats --output analysis.json --debug
```

### Configuration Options

You can configure the script using a `.env` file or environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_TOKEN` | **Required** GitHub personal access token | None |
| `DEFAULT_ORG` | Default organization to analyze | None |
| `DEFAULT_DAYS` | Default number of days to look back | 365 |
| `GITHUB_API_URL` | GitHub API base URL | https://api.github.com |
| `OUTPUT_DIR` | Default output directory for reports | . (current dir) |
| `DEBUG` | Enable debug mode (true/false) | false |
| `RATE_LIMIT_THRESHOLD` | Rate limit threshold | 10 |
| `API_DELAY` | Delay between API requests (seconds) | 0.1 |

### Command Line Options

- `organization`: GitHub organization name to analyze (optional if `DEFAULT_ORG` is set in .env)
- `--days, -d`: Number of days to look back for activity (default from .env or 365)
- `--stats, -s`: Include detailed contributor statistics
- `--output, -o`: Output file to save results in JSON format
- `--debug`: Enable debug mode for verbose output

## Examples

### Example 1: Quick Setup and Analysis
```bash
# 1. Copy and configure environment file
copy .env.example .env
# Edit .env and set your GITHUB_TOKEN and DEFAULT_ORG

# 2. Run analysis
python active-commiters.py
```

### Example 2: Analyze Specific Organization
```bash
python active-commiters.py microsoft
```

### Example 3: Detailed Quarterly Analysis
```bash
python active-commiters.py mycompany --days 90 --stats --output quarterly-report.json
```

### Example 4: Debug Mode for Troubleshooting
```bash
python active-commiters.py myorg --debug
```

## Output

The script provides:

1. **Console Output**: Real-time progress and summary
2. **JSON Export** (optional): Detailed results including:
   - List of active committers
   - Repository-wise statistics
   - Analysis metadata

### Sample Output
```
🔍 Analyzing GitHub organization: myorg
📅 Looking for activity since: 2024-07-10
============================================================

📚 Found 25 repositories

[1/25] 🔍 Analyzing repository: main-app
  ✅ Found 8 active contributors

[2/25] 🔍 Analyzing repository: utils-lib
  ✅ Found 3 active contributors

...

============================================================
📊 ANALYSIS SUMMARY
============================================================
Organization: myorg
Total repositories: 25
Repositories with activity: 18
Total active committers: 42
Analysis period: Last 365 days

👥 Active committers:
  • alice-dev
  • bob-engineer
  • charlie-ops
  ...
```

## Best Practices

1. **Token Security**: 
   - Use a `.env` file to store your GitHub token securely
   - Never commit your `.env` file to version control
   - The `.gitignore` file is configured to exclude `.env` files

2. **Rate Limits**: The script automatically handles rate limits, but large organizations may take time to analyze

3. **Regular Analysis**: Run periodic analyses to track contributor trends

4. **Data Export**: Use the JSON export for further analysis or reporting

5. **Configuration Management**: Use the `.env` file to set default values for your organization

## Error Handling

The script handles common scenarios:
- Invalid organization names
- Network connectivity issues
- API rate limit exceeded
- Empty repositories
- Permission denied errors

## Contributing

Feel free to submit issues and enhancement requests!

## License

This script is provided as-is for educational and organizational analysis purposes.
