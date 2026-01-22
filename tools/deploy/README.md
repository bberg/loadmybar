# Audio Tools Network - Deployment Scripts

Automated deployment scripts for the Audio Tools Network.

## Quick Start

```bash
cd shared/tools/deploy

# Install dependencies
pip install -r requirements.txt

# Check prerequisites
python deploy_all.py --check

# Show deployment plan
python deploy_all.py --plan

# Run deployment (dry-run first!)
python deploy_all.py --dry-run
python deploy_all.py --deploy
```

## Required Environment Variables

Set these before running deployment:

```bash
export RAILWAY_TOKEN="your_railway_api_token"
export CLOUDFLARE_TOKEN="your_cloudflare_api_token"
export GOOGLE_CREDENTIALS_PATH="/path/to/service-account.json"
export GA_ACCOUNT_ID="your_ga_account_id"
```

## Scripts

### `deploy_all.py` - Master Orchestration
Coordinates all deployment steps in the correct order.

```bash
python deploy_all.py --check     # Verify prerequisites
python deploy_all.py --plan      # Show what will be deployed
python deploy_all.py --dry-run   # Simulate deployment
python deploy_all.py --deploy    # Run full deployment
```

### `railway_setup.py` - Railway Hosting
Creates Railway projects and links to GitHub repos.

```bash
python railway_setup.py --token TOKEN --dry-run
python railway_setup.py --token TOKEN --list
```

### `cloudflare_setup.py` - DNS Configuration
Configures Cloudflare DNS records pointing to Railway.

```bash
python cloudflare_setup.py --token TOKEN --list-zones
python cloudflare_setup.py --token TOKEN --domain focushum.com --railway-url noise-gen.railway.app
```

### `google_analytics_setup.py` - GA4 Properties
Creates Google Analytics 4 properties and data streams.

```bash
python google_analytics_setup.py --credentials creds.json --account-id 123 --list-accounts
python google_analytics_setup.py --credentials creds.json --account-id 123 --dry-run
python google_analytics_setup.py --generate-code G-XXXXXXX  # Generate tracking snippet
```

### `search_console_setup.py` - Search Console
Adds sites to Google Search Console and submits sitemaps.

```bash
python search_console_setup.py --credentials creds.json --list-sites
python search_console_setup.py --credentials creds.json --dry-run
python search_console_setup.py --generate-dns  # Show DNS verification records needed
```

### `inject_analytics.py` - Code Injection
Injects GA4 tracking code into site templates.

```bash
python inject_analytics.py --measurement-ids ga_ids.json --dry-run
python inject_analytics.py --measurement-ids ga_ids.json --site noise-generator
```

### `generate_seo_files.py` - SEO Files
Generates sitemaps and robots.txt for all sites.

```bash
python generate_seo_files.py --dry-run
python generate_seo_files.py --site noise-generator
python generate_seo_files.py --show-sitemap focushum.com
python generate_seo_files.py --show-robots focushum.com
```

## Configuration

Edit `config.py` to modify:
- Site definitions (domains, paths, repos)
- GitHub organization name
- Network-wide settings

## Deployment Order

1. **Manual**: Purchase domains on Cloudflare
2. **Manual**: Generate API tokens (Railway, Cloudflare, Google)
3. **Auto**: Generate SEO files (sitemaps, robots.txt)
4. **Auto**: Create Railway projects linked to GitHub
5. **Auto**: Configure Cloudflare DNS → Railway
6. **Auto**: Create GA4 properties
7. **Auto**: Inject analytics code
8. **Auto**: Add sites to Search Console
9. **Auto**: Submit sitemaps

## Sites

| Site | Domain | Description |
|------|--------|-------------|
| NoiseGenerator | focushum.com | White/pink/brown noise |
| ToneGenerator | tonesynth.com | Frequency tone generator |
| BinauralBeats | binauralhq.com | Binaural beats for focus |
| DroneGenerator | omtones.com | Ambient drone generator |
| FrequencyGenerator | testtones.com | Speaker testing tones |
| Metronome | metronomely.com | Online metronome |
