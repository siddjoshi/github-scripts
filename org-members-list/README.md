# GitHub Enterprise Organization Members List

A production-ready Python script that generates comprehensive, easy-to-read reports listing all organizations in a GitHub Enterprise along with detailed member information for each organization.

## Features

- 📋 **Multiple Output Formats**: Markdown, HTML, JSON, and plain text
- 👥 **Complete Member Lists**: Shows all members for each organization
- 🎨 **Beautiful HTML Reports**: Interactive, styled HTML with tables and navigation
- 📊 **Comprehensive Data**: Member counts, usernames, types, and profile links
- 🔄 **Automatic Pagination**: Handles large enterprises with many organizations
- ⚡ **Rate Limit Management**: Automatic detection and throttling
- 🐛 **Debug Mode**: Detailed logging for troubleshooting
- 📋 **Environment Variable Support**: Configuration via `.env` files
- ✅ **Production-Ready**: Robust error handling and progress indicators

## Prerequisites

- Python 3.7 or higher
- GitHub Personal Access Token with appropriate permissions
- Access to a GitHub Enterprise instance

## Installation

1. Navigate to the script directory:
```bash
cd org-members-list
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
OUTPUT_FORMAT=markdown
DEBUG=false
```

## GitHub Token Requirements

Your GitHub Personal Access Token must have the following scopes:
- `admin:enterprise` or `read:enterprise` - Required to access enterprise organization data
- `read:org` - Required to read organization member information

### Creating a Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Select the required scopes mentioned above
4. Generate and copy the token
5. Store it securely in your `.env` file or environment variables

## Usage

### Option 1: GitHub Actions (Recommended - No Local Setup Required)

**This is the easiest way to generate member reports automatically without installing anything locally.**

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
2. Click **"Generate Organization Members List"** in the left sidebar
3. Click the **"Run workflow"** dropdown button (top right, green button)
4. Fill in:
   - **Enterprise slug:** Your enterprise name (e.g., `sidlabs`, `acme-corp`)
   - **Output format:** Choose from dropdown:
     - `markdown` - Tables and links (default) 📝
     - `html` - Beautiful web page 🎨
     - `json` - Machine-readable data 💾
     - `text` - Plain text 📄
   - **Enable debug mode:** ☐ (check for detailed logs if needed)
5. Click **"Run workflow"**

**Step 3: View Your Report**
- The workflow will run for a few minutes
- When complete, go to the `results/` folder in your repository
- Your report will be there: `enterprise_members_<enterprise>_<timestamp>.<format>`
- HTML reports can be downloaded and opened in your browser
- Also available as a downloadable artifact in the workflow run

#### What the Workflow Does

✅ Automatically fetches all organizations from your enterprise (uses GraphQL API for GitHub.com)  
✅ Retrieves complete member lists with usernames and profile links  
✅ Generates a beautifully formatted report in your chosen format  
✅ Commits the report to your `results/` folder  
✅ Uploads the report as a workflow artifact (90-day retention)  

#### Report Format Guide

**🎨 HTML** - Best for presentations and easy viewing
- Beautiful styled web page
- Interactive table of contents
- Hover effects and color coding
- Open in any browser

**📝 Markdown** - Best for GitHub and documentation
- Easy to read on GitHub
- Clickable table of contents
- Member tables with links
- Great for version control

**💾 JSON** - Best for automation
- Machine-readable format
- Complete data structure
- Easy to parse and integrate
- Includes all metadata

**📄 Text** - Best for simple viewing
- Plain text format
- No special formatting
- Works in any editor
- Easy to grep/search

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
| Empty member lists | Ensure token has `read:org` scope and member visibility permissions |

---

### Option 2: Run Locally (Command Line)

**Use this if you want to run the script on your local machine.**

#### Prerequisites
- Python 3.7 or higher installed
- GitHub Personal Access Token (from setup above)

#### Installation

1. Clone and navigate to the directory:
```bash
cd org-members-list
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
OUTPUT_FORMAT=markdown
DEBUG=false
EOF
```

**Option B: Environment variable**
```bash
export GITHUB_TOKEN=your_token_here
```

#### Basic Usage (Markdown format)

```bash
python org_members_list.py YOUR_ENTERPRISE_SLUG
```

This generates a Markdown file like: `enterprise_members_YOUR_ENTERPRISE_SLUG_20231117_143022.md`

#### HTML Report (Recommended for easy reading)

```bash
python org_members_list.py my-enterprise --format html
```

Generates a beautiful, interactive HTML page with styled tables and navigation.

#### JSON Report (Machine-readable)

```bash
python org_members_list.py my-enterprise --format json
```

Perfect for programmatic processing or integration with other tools.

#### Plain Text Report

```bash
python org_members_list.py my-enterprise --format text
```

Simple, plain text format for easy viewing in any text editor.

#### Specify Output File

```bash
python org_members_list.py my-enterprise --format html --output my_report.html
```

#### Enable Debug Mode

```bash
python org_members_list.py my-enterprise --debug
```

#### Complete Example

```bash
python org_members_list.py acme-corp \
  --format html \
  --output reports/acme_members.html \
  --debug
```

## Output Formats

### 1. Markdown (Default)

- ✅ Easy to read and edit
- ✅ Works great with GitHub, GitLab, and documentation tools
- ✅ Includes table of contents with clickable links
- ✅ Member tables with usernames and profile links

**Example:**
```markdown
# GitHub Enterprise Organization Members Report

**Enterprise:** acme-corp
**Total Organizations:** 3
**Total Members:** 65

## Table of Contents

1. [engineering](#engineering) (45 members)
2. [product](#product) (12 members)
3. [data-science](#data-science) (8 members)

## engineering

**Member Count:** 45

### Members

| # | Username | Type | Profile |
|---|----------|------|---------|
| 1 | `john.doe` | User | [Profile](https://github.com/john.doe) |
| 2 | `jane.smith` | User | [Profile](https://github.com/jane.smith) |
```

### 2. HTML

- ✅ Beautiful, professional styling
- ✅ Interactive navigation
- ✅ Color-coded sections
- ✅ Hover effects on tables
- ✅ Responsive design
- ✅ Can be opened directly in any browser

**Features:**
- Summary box with key statistics
- Table of contents with jump links
- Styled tables with alternating row colors
- Clean, modern design using GitHub's color scheme

### 3. JSON

- ✅ Machine-readable format
- ✅ Easy to parse programmatically
- ✅ Includes all metadata
- ✅ Perfect for automation and integration

**Example:**
```json
{
  "enterprise": "acme-corp",
  "generated_at": "2023-11-17T14:30:22.123456",
  "summary": {
    "total_organizations": 3,
    "total_members": 65,
    "average_members_per_org": 21.7
  },
  "organizations": [
    {
      "organization_name": "engineering",
      "member_count": 45,
      "members": [
        {
          "login": "john.doe",
          "type": "User",
          "profile_url": "https://github.com/john.doe"
        }
      ]
    }
  ]
}
```

### 4. Plain Text

- ✅ Simple, no formatting
- ✅ Works in any text editor
- ✅ Easy to grep/search
- ✅ Good for terminal viewing

## Configuration Options

### Environment Variables

All configuration can be set via environment variables or a `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub Personal Access Token (required) | None |
| `GITHUB_API_URL` | GitHub API base URL | `https://api.github.com` |
| `OUTPUT_DIR` | Default output directory for reports | `.` (current directory) |
| `OUTPUT_FORMAT` | Default output format | `markdown` |
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
usage: org_members_list.py [-h] [--format {markdown,json,text,html}]
                           [--output OUTPUT] [--debug]
                           enterprise

positional arguments:
  enterprise            GitHub Enterprise slug/name

optional arguments:
  -h, --help            show this help message and exit
  --format {markdown,json,text,html}, -f {markdown,json,text,html}
                        Output format (default: markdown)
  --output OUTPUT, -o OUTPUT
                        Output file path (default: auto-generated with timestamp)
  --debug               Enable debug mode for verbose output
```

## Sample Output

### Console Output

```
📋 Loaded configuration from: /path/to/.env

🔍 Generating members report for GitHub Enterprise: acme-corp
======================================================================

🏢 Fetching organizations for enterprise: acme-corp
   📄 Fetched page 1, total organizations so far: 3

📊 Found 3 organizations
🔄 Fetching member lists for each organization...

[1/3] Processing: engineering
   👥 Found 45 members

[2/3] Processing: product
   👥 Found 12 members

[3/3] Processing: data-science
   👥 Found 8 members

======================================================================
📝 Generating MARKDOWN report...

======================================================================
📈 REPORT SUMMARY
======================================================================
Enterprise: acme-corp
Total Organizations: 3
Total Members: 65
Average Members per Organization: 21.7

✅ Report saved to: ./enterprise_members_acme-corp_20231117_143022.md

✨ Report generation completed successfully!
```

## Report Contents

Each report includes:

1. **Header Section**
   - Enterprise name
   - Generation timestamp
   - Total statistics

2. **Table of Contents** (Markdown/HTML)
   - Quick links to each organization
   - Member counts at a glance

3. **Organization Sections**
   - Organization name
   - Member count
   - Complete member list with:
     - Sequential numbering
     - Username
     - User type (User/Bot)
     - Profile link

4. **Summary Section**
   - Total organizations
   - Total members across all orgs
   - Average members per organization

## Use Cases

### 1. Audit and Compliance
Generate reports to track organization membership for compliance purposes.

```bash
python org_members_list.py my-enterprise --format json --output audit_report.json
```

### 2. Documentation
Create Markdown reports to document your enterprise structure.

```bash
python org_members_list.py my-enterprise --format markdown --output docs/org_structure.md
```

### 3. Presentations
Generate HTML reports for stakeholder presentations.

```bash
python org_members_list.py my-enterprise --format html --output presentation.html
```

### 4. Automation
Use JSON output for automated processing or integration.

```bash
python org_members_list.py my-enterprise --format json | jq '.summary'
```

## Error Handling

The script handles various error scenarios:

- **Missing Token**: Clear error message with instructions
- **Invalid Enterprise**: Detects if enterprise doesn't exist or is inaccessible
- **Permission Issues**: Identifies if token lacks required scopes
- **Rate Limiting**: Automatically waits when approaching rate limits
- **Network Errors**: Graceful handling with informative messages
- **API Errors**: Detailed error reporting with status codes

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

### Empty Member Lists

Some organizations may restrict member visibility. Ensure your token has appropriate permissions.

### Rate Limiting

The script automatically handles rate limiting. For faster processing:
- Reduce `API_DELAY` (may hit limits faster)
- Use a token with higher rate limits

### Debug Mode

Enable debug mode for detailed troubleshooting:
```bash
python org_members_list.py my-enterprise --debug
```

## Performance Considerations

- **Large Enterprises**: May take several minutes for enterprises with many organizations
- **Rate Limits**: GitHub API has rate limits (typically 5000 requests/hour)
- **Member Counts**: Organizations with many members require additional API calls
- **API Delay**: Default 0.1s delay between requests (adjustable)

## Security Best Practices

1. **Never commit tokens**: Add `.env` to `.gitignore`
2. **Use minimal scopes**: Only grant necessary permissions
3. **Rotate tokens**: Regularly update your access tokens
4. **Store securely**: Use environment variables or secure secret management
5. **Audit access**: Regularly review who has access to generated reports

## Advanced Usage

### Scheduled Reports

Create a cron job to generate daily reports:

```bash
0 9 * * * cd /path/to/org-members-list && python org_members_list.py my-enterprise --format html --output /var/www/html/daily_report.html
```

### Email Reports

Combine with email tools to send reports:

```bash
python org_members_list.py my-enterprise --format html --output report.html
mail -s "Daily Org Report" team@company.com < report.html
```

### Compare Reports

Use JSON format to compare membership changes over time:

```bash
# Generate today's report
python org_members_list.py my-enterprise --format json --output today.json

# Compare with yesterday's report
diff <(jq '.organizations[].members[].login' yesterday.json | sort) \
     <(jq '.organizations[].members[].login' today.json | sort)
```

## Contributing

Feel free to submit issues or pull requests to improve this script.

## License

This script is provided as-is for use with GitHub Enterprise instances.
