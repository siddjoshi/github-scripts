# GitHub Enterprise Organization Report Generator

A production-ready Python script that generates a CSV report listing all organizations in a GitHub Enterprise along with their member counts and repository counts.

## Features

- 📊 Generates comprehensive CSV reports with organization statistics
- 🔄 Handles pagination automatically for large enterprises
- ⚡ Rate limit detection and automatic throttling
- 🐛 Debug mode for troubleshooting
- 📋 Environment variable support via `.env` files
- ✅ Production-ready error handling and logging
- 🎯 Configurable output directory and file naming

## Prerequisites

- Python 3.7 or higher
- GitHub Personal Access Token with appropriate permissions
- Access to a GitHub Enterprise instance

## Installation

1. Navigate to the script directory:
```bash
cd enterprise-org-report
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your GitHub token:

**Option 1: Environment variable**
```bash
export GITHUB_TOKEN=your_github_token_here
```

**Option 2: .env file (recommended)**
Create a `.env` file in the script directory:
```bash
GITHUB_TOKEN=your_github_token_here
GITHUB_API_URL=https://api.github.com
OUTPUT_DIR=./reports
DEBUG=false
```

## GitHub Token Requirements

Your GitHub Personal Access Token must have the following scope:
- `admin:enterprise` or `read:enterprise` - Required to access enterprise organization data
- `read:org` - Required to read organization member and repository information

### Creating a Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Select the required scopes mentioned above
4. Generate and copy the token
5. Store it securely in your `.env` file or environment variables

## Usage

### Option 1: GitHub Actions (Recommended - No Local Setup Required)

**This is the easiest way to generate reports automatically without installing anything locally.**

#### Quick Start Guide

**Step 1: Add Your Token to Repository Secrets**
1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. Enter:
   - **Name:** `ENTERPRISE_GITHUB_TOKEN` *(must be exactly this)*
   - **Secret:** Your GitHub Personal Access Token (from above)
5. Click **"Add secret"**

**Step 2: Run the Workflow**
1. Go to the **Actions** tab in your GitHub repository
2. Click **"Generate Enterprise Organization Report"** in the left sidebar
3. Click the **"Run workflow"** dropdown button (top right, green button)
4. Fill in:
   - **Enterprise slug:** Your enterprise name (e.g., `sidlabs`, `acme-corp`)
   - **Enable debug mode:** ☐ (check for detailed logs if needed)
5. Click **"Run workflow"**

**Step 3: View Your Report**
- The workflow will run for a few minutes
- When complete, go to the `results/` folder in your repository
- Your CSV report will be there: `enterprise_org_report_<enterprise>_<timestamp>.csv`
- Also available as a downloadable artifact in the workflow run

#### What the Workflow Does

✅ Automatically fetches all organizations from your enterprise (uses GraphQL API for GitHub.com)  
✅ Counts all members and repositories for each organization  
✅ Generates a timestamped CSV report  
✅ Commits the report to your `results/` folder  
✅ Uploads the report as a workflow artifact (90-day retention)  

#### Optional: For GitHub Enterprise Server Users

If you're using self-hosted GitHub Enterprise Server (not GitHub.com):

1. Go to **Settings** → **Secrets and variables** → **Actions** → **Variables** tab
2. Click **"New repository variable"**
3. Enter:
   - **Name:** `GITHUB_API_URL`
   - **Value:** Your server's API URL (e.g., `https://github.your-company.com/api/v3`)
4. Click **"Add variable"**

#### Troubleshooting the Workflow

| Problem | Solution |
|---------|----------|
| "ENTERPRISE_GITHUB_TOKEN not found" | Make sure the secret name is exactly `ENTERPRISE_GITHUB_TOKEN` |
| "Enterprise not found" | Verify enterprise slug is correct and token has `admin:enterprise` scope |
| "No organizations found" | Enable debug mode and check token permissions |
| Shows 0 members/repos | Ensure token has `read:org` scope |

---

### Option 2: Run Locally (Command Line)

**Use this if you want to run the script on your local machine.**

#### Prerequisites
- Python 3.7 or higher installed
- GitHub Personal Access Token (from setup above)

#### Installation

1. Clone and navigate to the directory:
```bash
cd enterprise-org-report
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your token (choose one):

**Option A: .env file (Recommended)**
```bash
# Create .env file
cat > .env << EOF
GITHUB_TOKEN=your_token_here
GITHUB_API_URL=https://api.github.com
OUTPUT_DIR=./reports
DEBUG=false
EOF
```

**Option B: Environment variable**
```bash
export GITHUB_TOKEN=your_token_here
```

#### Basic Usage

```bash
python enterprise_org_report.py YOUR_ENTERPRISE_SLUG
```

This will:
- Fetch all organizations from the enterprise
- Count members and repositories for each organization
- Generate a CSV file with timestamp: `enterprise_org_report_YOUR_ENTERPRISE_SLUG_20231117_143022.csv`

#### Specify Output File

```bash
python enterprise_org_report.py my-enterprise --output my_report.csv
```

#### Enable Debug Mode

```bash
python enterprise_org_report.py my-enterprise --debug
```

#### Complete Example

```bash
python enterprise_org_report.py acme-corp \
  --output reports/acme_org_report.csv \
  --debug
```

## Output Format

The script generates a CSV file with three columns:

| organization_name | member_count | repository_count |
|------------------|--------------|------------------|
| org-alpha        | 25           | 150              |
| org-beta         | 10           | 75               |
| org-gamma        | 50           | 300              |

### CSV Example

```csv
organization_name,member_count,repository_count
engineering-team,45,230
product-team,12,45
data-science,8,67
```

## Configuration Options

### Environment Variables

All configuration can be set via environment variables or a `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub Personal Access Token (required) | None |
| `GITHUB_API_URL` | GitHub API base URL | `https://api.github.com` |
| `OUTPUT_DIR` | Default output directory for reports | `.` (current directory) |
| `DEBUG` | Enable debug logging (`true`/`false`) | `false` |
| `RATE_LIMIT_THRESHOLD` | Remaining requests before throttling | `10` |
| `API_DELAY` | Delay between API requests (seconds) | `0.1` |

### For GitHub Enterprise Server

If using GitHub Enterprise Server (self-hosted), set the API URL:

```bash
GITHUB_API_URL=https://github.your-company.com/api/v3
```

## Command Line Options

```
usage: enterprise_org_report.py [-h] [--output OUTPUT] [--debug] enterprise

positional arguments:
  enterprise            GitHub Enterprise slug/name

optional arguments:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        Output CSV file path (default: auto-generated with timestamp)
  --debug               Enable debug mode for verbose output
```

## Error Handling

The script handles various error scenarios:

- **Missing Token**: Clear error message with instructions
- **Invalid Enterprise**: Detects if enterprise doesn't exist or is inaccessible
- **Permission Issues**: Identifies if token lacks required scopes
- **Rate Limiting**: Automatically waits when approaching rate limits
- **Network Errors**: Graceful handling with informative messages
- **API Errors**: Detailed error reporting with status codes

## Sample Output

```
📋 Loaded configuration from: /path/to/.env

🔍 Generating report for GitHub Enterprise: acme-corp
======================================================================

🏢 Fetching organizations for enterprise: acme-corp
   📄 Fetched page 1, total organizations so far: 3

📊 Found 3 organizations
🔄 Fetching member and repository counts for each organization...

[1/3] Processing: engineering
   👥 Members: 45
   📚 Repositories: 230

[2/3] Processing: product
   👥 Members: 12
   📚 Repositories: 45

[3/3] Processing: data-science
   👥 Members: 8
   📚 Repositories: 67

======================================================================
📈 REPORT SUMMARY
======================================================================
Enterprise: acme-corp
Total Organizations: 3
Total Members: 65
Total Repositories: 342

✅ Report saved to: ./enterprise_org_report_acme-corp_20231117_143022.csv

✨ Report generation completed successfully!
```

## Troubleshooting

### "GITHUB_TOKEN not found" Error

Make sure you've set the token as an environment variable or in a `.env` file:
```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
```

### "Enterprise not found or not accessible"

1. Verify the enterprise slug is correct
2. Ensure your token has `admin:enterprise` or `read:enterprise` scope
3. Check if you have access to the enterprise

### "Access forbidden" Error

Your token needs the `admin:enterprise` or `read:enterprise` scope. Generate a new token with the correct permissions.

### Rate Limiting

The script automatically handles rate limiting. If you're consistently hitting limits:
- Increase `API_DELAY` in your `.env` file
- Use a token with higher rate limits
- Process fewer organizations at once

### Debug Mode

Enable debug mode for detailed troubleshooting:
```bash
python enterprise_org_report.py my-enterprise --debug
```

## Performance Considerations

- **Large Enterprises**: For enterprises with many organizations, the script may take several minutes
- **Rate Limits**: GitHub API has rate limits (typically 5000 requests/hour for authenticated requests)
- **API Delay**: Default 0.1s delay between requests can be adjusted via `API_DELAY` environment variable

## Security Best Practices

1. **Never commit tokens**: Add `.env` to `.gitignore`
2. **Use minimal scopes**: Only grant necessary permissions
3. **Rotate tokens**: Regularly update your access tokens
4. **Store securely**: Use environment variables or secure secret management

## Contributing

Feel free to submit issues or pull requests to improve this script.

## License

This script is provided as-is for use with GitHub Enterprise instances.
