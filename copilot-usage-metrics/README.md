# GitHub Copilot Usage Metrics Reporter

A Python script to fetch and analyze GitHub Copilot usage metrics, including lines of code (LoC) metrics, acceptance rates, and feature-specific breakdowns.

## Features

- ✅ Fetch Copilot usage metrics via GitHub REST API
- 📊 Calculate **Code Acceptance Rate** (code acceptances / code generations)
- 📈 Calculate **LoC Acceptance Rate** (lines added / lines suggested)
- 🎯 Feature-specific metrics (code_completion, chat_panel, chat_panel_agent_mode, agent_edit, etc.)
- 🌍 Language-specific breakdowns
- 📝 Export to CSV or JSON formats
- 🔄 Support for both single-day and 28-day rolling reports
- 🎨 Comprehensive console output with summaries

## Installation

1. Navigate to the script directory:
```bash
cd copilot-usage-metrics
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

### Basic Usage (28-day report, CSV format)

```bash
python copilot_usage_metrics.py YOUR_ENTERPRISE_SLUG
```

This generates two CSV files:
- `copilot_metrics_YOUR_ENTERPRISE_SLUG_TIMESTAMP.csv` - Feature-level metrics
- `copilot_metrics_YOUR_ENTERPRISE_SLUG_TIMESTAMP_by_language.csv` - Language-feature metrics

### JSON Output

```bash
python copilot_usage_metrics.py YOUR_ENTERPRISE_SLUG --format json
```

### Specific Day Report

```bash
python copilot_usage_metrics.py YOUR_ENTERPRISE_SLUG --day 2025-12-01
```

### Custom Output File

```bash
python copilot_usage_metrics.py YOUR_ENTERPRISE_SLUG --output my_metrics.csv
```

### Debug Mode

```bash
python copilot_usage_metrics.py YOUR_ENTERPRISE_SLUG --debug
```

## Output Formats

### CSV Output (Feature Metrics)

| feature | users | loc_suggested_to_add | loc_added | loc_deleted | code_generations | code_acceptances | code_acceptance_rate_% | loc_acceptance_rate_% |
|---------|-------|---------------------|-----------|-------------|------------------|------------------|----------------------|---------------------|
| code_completion | 150 | 50000 | 35000 | 100 | 10000 | 7500 | 75.00 | 70.00 |
| chat_panel_agent_mode | 45 | 8600 | 500 | 0 | 1200 | 0 | 0.00 | 5.81 |
| agent_edit | 30 | 0 | 234200 | 94700 | 34500 | 0 | 0.00 | N/A |

### CSV Output (Language-Feature Metrics)

| language | feature | users | loc_suggested_to_add | loc_added | loc_deleted | code_generations | code_acceptances | code_acceptance_rate_% | loc_acceptance_rate_% |
|----------|---------|-------|---------------------|-----------|-------------|------------------|------------------|----------------------|---------------------|
| python | code_completion | 80 | 25000 | 18000 | 50 | 5000 | 4000 | 80.00 | 72.00 |
| typescript | code_completion | 70 | 20000 | 15000 | 30 | 4500 | 3500 | 77.78 | 75.00 |

### JSON Output Structure

```json
{
  "enterprise": "my-enterprise",
  "report_start_day": "2025-11-10",
  "report_end_day": "2025-12-08",
  "generated_at": "2025-12-08T10:30:00",
  "total_users": 200,
  "feature_metrics": {
    "code_completion": {
      "loc_suggested_to_add_sum": 50000,
      "loc_added_sum": 35000,
      "loc_deleted_sum": 100,
      "code_generation_activity_count": 10000,
      "code_acceptance_activity_count": 7500,
      "user_count": 150,
      "code_acceptance_rate": 75.00,
      "loc_acceptance_rate": 70.00
    },
    "agent_edit": {
      "loc_suggested_to_add_sum": 0,
      "loc_added_sum": 234200,
      "loc_deleted_sum": 94700,
      "code_generation_activity_count": 34500,
      "code_acceptance_activity_count": 0,
      "user_count": 30,
      "code_acceptance_rate": 0.00,
      "loc_acceptance_rate": null
    }
  },
  "language_feature_metrics": {
    "python:code_completion": { ... },
    "typescript:code_completion": { ... }
  }
}
```

## Metrics Explained

### Code Acceptance Rate
**Formula**: `(code_acceptance_activity_count / code_generation_activity_count) × 100`

Measures the percentage of generated code suggestions that users explicitly accepted (via "apply", "insert", "copy" buttons, or Tab key for completions).

### LoC Acceptance Rate
**Formula**: `(loc_added_sum / loc_suggested_to_add_sum) × 100`

Measures the percentage of suggested lines of code that were actually added to files. This provides a volume-based view of acceptance.

**Note**: For `agent_edit` mode, LoC Acceptance Rate shows "N/A" because agents don't follow a suggest-then-accept flow—they directly edit files without generating suggestions first.

### Features Tracked

- **code_completion**: Inline code completions (Tab-accept suggestions)
- **chat_panel**: Chat panel interactions (Ask mode)
- **chat_panel_agent_mode**: Agent mode in chat panel
- **chat_inline**: Inline chat interactions
- **agent_edit**: Direct file edits by Copilot Agent and Edit mode
- **custom**: Custom agent modes

### Raw Data for Agent Edit

The `agent_edit` feature provides direct edit metrics:
- `loc_added_sum`: Lines directly added by agents
- `loc_deleted_sum`: Lines directly deleted by agents
- `code_generation_activity_count`: Number of agent edit operations

These are **not** suggestions—agents perform multi-step tasks and edit files directly.

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
usage: copilot_usage_metrics.py [-h] [--format {csv,json}] [--day DAY] 
                                [--output OUTPUT] [--debug] enterprise

positional arguments:
  enterprise            GitHub Enterprise slug/name

optional arguments:
  -h, --help            show this help message and exit
  --format {csv,json}, -f {csv,json}
                        Output format (default: csv)
  --day DAY, -d DAY     Specific day to fetch metrics for (YYYY-MM-DD format).
                        If not specified, fetches latest 28-day report
  --output OUTPUT, -o OUTPUT
                        Output file path (default: auto-generated with timestamp)
  --debug               Enable debug mode for verbose output
```

## Examples

### Generate 28-day CSV report
```bash
python copilot_usage_metrics.py acme-corp
```

### Generate JSON report for specific day
```bash
python copilot_usage_metrics.py acme-corp --day 2025-12-01 --format json
```

### Save to specific location with debug output
```bash
python copilot_usage_metrics.py acme-corp --output /reports/metrics.csv --debug
```

### Use with custom API endpoint
```bash
GITHUB_API_URL=https://github.mycompany.com/api/v3 python copilot_usage_metrics.py myorg
```

## Data Availability

- Reports are available starting from **October 10, 2025**
- Historical data can be accessed for up to **1 year** from the current date
- Reports are generated daily and become available within 24 hours

## Version Requirements

LoC metrics require minimum IDE and plugin versions. Users on older versions won't contribute LoC data:

| IDE | Feature | Min IDE Version | Min Plugin Version |
|-----|---------|----------------|-------------------|
| VS Code | code_completion | 1.104.0 | 0.31.0 |
| VS Code | chat_panel (Agent) | 1.102.0 | 0.29.0 |
| VS Code | agent_edit | 1.103.0 | 0.30.0 |
| IntelliJ | All features | 2024.2.6 | 1.5.52-241 |
| Visual Studio | code_completion, chat_panel | 17.14.13 | 18.0.471.29466 |

## Understanding Agent Mode Metrics

Agent mode differs from other features:

1. **No Suggestion Flow**: Agents plan and execute multi-step tasks without showing suggestions
2. **Direct Edits**: `agent_edit` captures lines added/deleted directly in files
3. **Multi-file Operations**: One agent task can edit multiple files
4. **Zero Suggestions**: `loc_suggested_to_add_sum` is always 0 for `agent_edit`

Example metrics for agent:
```
chat_panel_agent_mode:
  - loc_suggested_to_add_sum: 86 (code blocks shown in chat)
  - loc_added_sum: 5 (code blocks copied/applied from chat)
  
agent_edit:
  - loc_suggested_to_add_sum: 0 (no suggestions)
  - loc_added_sum: 2342 (direct edits to files)
  - loc_deleted_sum: 947 (direct deletions from files)
```

## Error Handling

The script handles various error scenarios:

- **Missing Token**: Clear error message with setup instructions
- **Invalid Enterprise**: Detects if enterprise doesn't exist or is inaccessible
- **Permission Issues**: Identifies if token lacks required scopes
- **Rate Limiting**: Automatically waits when approaching rate limits
- **Network Errors**: Graceful handling with informative messages
- **API Errors**: Detailed error reporting with status codes

## Performance Considerations

- **Large Enterprises**: Reports may contain multiple NDJSON files; all are downloaded and aggregated
- **Rate Limits**: GitHub API has rate limits (5000 requests/hour for authenticated requests)
- **API Delay**: Default 0.1s delay between requests can be adjusted via `API_DELAY` environment variable
- **Report Size**: Large enterprises may have multi-megabyte reports; download times vary

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
- Try using a more recent date or omit `--day` for latest 28-day report

### LoC metrics showing zeros
- Check if users are on required IDE/plugin versions (see Version Requirements)
- Verify that `last_known_ide_version` and `last_known_plugin_version` in raw data meet minimums
- Some features may not have LoC data if not used during the reporting period

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
