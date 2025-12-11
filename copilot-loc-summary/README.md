# GitHub Copilot Lines of Code Summary Reporter

A Python script to calculate total lines of code added and deleted by GitHub Copilot across the enterprise, providing both 28-day aggregated data and weekly breakdowns (4 rolling weeks).

## Features

- ✅ Fetch Copilot usage metrics via GitHub REST API
- 📊 Calculate total lines of code added across all features
- 📊 Calculate total lines of code deleted across all features
- 📅 28-day aggregated totals
- 📅 Weekly breakdowns (4 rolling weeks: Week 1: days 1-7, Week 2: days 8-14, Week 3: days 15-21, Week 4: days 22-28)
- 🎯 Per-feature breakdown for both 28-day and weekly periods
- 📝 Export to CSV format

## Installation

1. Navigate to the script directory:
```bash
cd copilot-loc-summary
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

Your GitHub Personal Access Token must have one of the following scopes:
- `manage_billing:copilot` - For managing Copilot billing and viewing metrics
- `read:enterprise` - For reading enterprise data including Copilot metrics

### Creating a Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Select the required scopes mentioned above
4. Generate and copy the token
5. Store it securely in your `.env` file or environment variables

**Note**: Only enterprise owners, billing managers, and users with "View Enterprise Copilot Metrics" permission can access these metrics.

## Usage

### Basic Usage

```bash
python copilot_loc_summary.py YOUR_ENTERPRISE_SLUG
```

This generates two CSV files:
- `copilot_loc_summary_YOUR_ENTERPRISE_SLUG_TIMESTAMP.csv` - Summary with 28-day and weekly totals
- `copilot_loc_summary_YOUR_ENTERPRISE_SLUG_TIMESTAMP_features.csv` - Per-feature breakdown

### Custom Output File

```bash
python copilot_loc_summary.py YOUR_ENTERPRISE_SLUG --output my_summary.csv
```

### Debug Mode

```bash
python copilot_loc_summary.py YOUR_ENTERPRISE_SLUG --debug
```

## Output Format

### Summary CSV

The summary CSV contains aggregated totals for all features combined:

| period | loc_added | loc_deleted | net_change |
|--------|-----------|-------------|------------|
| 28-Day Total | 1250000 | 450000 | 800000 |
| Week 1 | 320000 | 115000 | 205000 |
| Week 2 | 310000 | 110000 | 200000 |
| Week 3 | 310000 | 112000 | 198000 |
| Week 4 | 310000 | 113000 | 197000 |

### Features CSV

The features CSV contains per-feature breakdowns for both 28-day and weekly periods:

| feature | period | loc_added | loc_deleted | net_change |
|---------|--------|-----------|-------------|------------|
| code_completion | 28-Day Total | 850000 | 300000 | 550000 |
| code_completion | Week 1 | 215000 | 75000 | 140000 |
| code_completion | Week 2 | 210000 | 73000 | 137000 |
| agent_edit | 28-Day Total | 400000 | 150000 | 250000 |
| agent_edit | Week 1 | 105000 | 40000 | 65000 |
| chat_panel | 28-Day Total | 0 | 0 | 0 |

## How It Works

1. **28-Day Aggregation**: Fetches the latest 28-day aggregated report from GitHub API
2. **Weekly Breakdown**: Fetches daily reports for each day in the 28-day period and aggregates them into 4 rolling weeks:
   - Week 1: Days 1-7
   - Week 2: Days 8-14
   - Week 3: Days 15-21
   - Week 4: Days 22-28
3. **Feature Aggregation**: Aggregates lines of code added and deleted across all features and languages

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

## Command Line Arguments

```
usage: copilot_loc_summary.py [-h] [--output OUTPUT] [--debug] enterprise

positional arguments:
  enterprise            GitHub Enterprise slug/name

optional arguments:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        Output file path (default: auto-generated with timestamp)
  --debug               Enable debug mode for verbose output
```

## Examples

### Generate summary report

```bash
python copilot_loc_summary.py acme-corp
```

### Save to specific location

```bash
python copilot_loc_summary.py acme-corp --output /reports/loc_summary.csv
```

### Use with custom API endpoint

```bash
GITHUB_API_URL=https://github.mycompany.com/api/v3 python copilot_loc_summary.py myorg
```

## Performance Considerations

- **API Calls**: The script makes 28 API calls (one per day) to generate weekly breakdowns, which may take several minutes
- **Rate Limits**: GitHub API has rate limits (5000 requests/hour for authenticated requests)
- **API Delay**: Default 0.1s delay between requests can be adjusted via `API_DELAY` environment variable
- **Large Enterprises**: Reports may contain multiple NDJSON files; all are downloaded and aggregated

## Data Availability

- Reports are available starting from **October 10, 2025**
- Historical data can be accessed for up to **1 year** from the current date
- Reports are generated daily and become available within 24 hours

## Features Tracked

The script aggregates data across all Copilot features:

- **code_completion**: Inline code completions (Tab-accept suggestions)
- **chat_panel**: Chat panel interactions (Ask mode)
- **chat_panel_agent_mode**: Agent mode in chat panel
- **chat_inline**: Inline chat interactions
- **agent_edit**: Direct file edits by Copilot Agent and Edit mode
- **custom**: Custom agent modes

## Error Handling

The script handles various error scenarios:

- **Missing Token**: Clear error message with setup instructions
- **Invalid Enterprise**: Detects if enterprise doesn't exist or is inaccessible
- **Permission Issues**: Identifies if token lacks required scopes
- **Rate Limiting**: Automatically waits when approaching rate limits
- **Network Errors**: Graceful handling with informative messages
- **API Errors**: Detailed error reporting with status codes

## Troubleshooting

### "Enterprise not found" error
- Verify the enterprise slug is correct (use the slug from your enterprise URL)
- Ensure your token has `read:enterprise` or `manage_billing:copilot` scope
- Confirm you have permission to view Copilot metrics

### "Access forbidden" error
- Your token needs `manage_billing:copilot` or `read:enterprise` scope
- Contact your enterprise owner to grant "View Enterprise Copilot Metrics" permission

### "No download links available"
- Metrics may not be available for the requested date
- Historical data only available for past year
- Try running again later if data is still being generated

### Script taking too long
- The script fetches 28 daily reports for weekly breakdowns
- This is expected behavior and may take 5-10 minutes depending on API response times
- Consider increasing `API_DELAY` if you encounter rate limit issues

## Security Best Practices

1. **Never commit tokens**: Add `.env` to `.gitignore`
2. **Use minimal scopes**: Only grant necessary permissions
3. **Rotate tokens**: Regularly update your access tokens
4. **Store securely**: Use environment variables or secure secret management

## Related Documentation

- [GitHub Copilot Usage Metrics](https://docs.github.com/en/copilot/reference/copilot-usage-metrics/copilot-usage-metrics)
- [Lines of Code Metrics](https://docs.github.com/en/copilot/reference/copilot-usage-metrics/lines-of-code-metrics)
- [REST API for Copilot Metrics](https://docs.github.com/en/rest/copilot/copilot-usage-metrics)

## Contributing

Feel free to submit issues or pull requests to improve this script.

## License

This script is provided as-is for use with GitHub Enterprise and Copilot instances.

