# EV Charging Receipt Extractor

A comprehensive Home Assistant custom integration that automatically extracts and processes electric vehicle charging receipts from multiple sources including email providers, Tesla PDFs, and EVCC home charging systems.

## ✨ Features

### 📧 Multi-Provider Email Support
- **Automatic Email Processing**: Connects to Gmail to extract charging receipts
- **Supported Providers**: 
  - BP Pulse (Australia)
  - EVIE Networks 
  - Chargefox
  - Ampol (AmpCharge)
  - Tesla Supercharging
  - ChargePoint
  - NRMA
  - Shell Recharge
  - And more Australian EV charging networks

### 🚗 Tesla Integration
- **Tesla PDF Processing**: Automatically processes Tesla Supercharging receipt PDFs
- **Tesla Email Support**: Handles Tesla charging emails with multiple PDF attachments
- **Comprehensive Data Extraction**: Invoice numbers, charging locations, energy consumption, costs

### 🏠 Home Charging Integration
- **EVCC Integration**: Connects to EVCC home charging systems
- **Solar Tracking**: Monitors solar percentage for home charging sessions
- **Cost Calculation**: Automatic cost calculation based on electricity rates

### 📊 Advanced Data Management
- **SQLite Database**: Robust data storage with duplicate prevention
- **Date Correction**: Intelligent date parsing and correction for various formats
- **Export Functions**: CSV export with user-friendly formatting
- **Statistics Tracking**: Comprehensive charging statistics and trends

### 🏡 Home Assistant Integration
- **Sensors**: Real-time charging statistics and session data
- **Services**: Manual processing triggers and debug functions
- **Buttons**: Easy-to-use control interface
- **Configuration Flow**: User-friendly setup process

## 📋 Requirements

### Dependencies
```
beautifulsoup4==4.12.2
PyPDF2==3.0.1
pytz==2023.3
pandas (optional, for enhanced date parsing)
requests (for EVCC integration)
```

### Home Assistant
- Home Assistant 2023.1 or later
- Gmail account with app password enabled
- EVCC installation (optional, for home charging)

## 🚀 Installation

### HACS Installation (Recommended)
1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/your-username/ha-ev-charging-extractor`
6. Select "Integration" as the category
7. Click "Add"
8. Find "EV Charging Receipt Extractor" in HACS and install it
9. Restart Home Assistant

### Manual Installation
1. Download the latest release
2. Copy the `ev_charging_extractor` folder to your `custom_components` directory
3. Restart Home Assistant

## ⚙️ Configuration

### Initial Setup
1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "EV Charging Receipt Extractor"
4. Follow the configuration flow:

#### Required Configuration
- **Gmail Username**: Your Gmail address
- **Gmail App Password**: Generate an app-specific password in your Google account
- **Home Electricity Rate**: Cost per kWh for home charging (e.g., 0.25 for $0.25/kWh)
- **Default Currency**: Currency for cost calculations (default: AUD)

#### Optional Configuration
- **EVCC Integration**: Enable if you have EVCC installed
- **EVCC URL**: URL to your EVCC installation (default: http://homeassistant.local:7070)
- **Email Search Days**: How many days back to search for emails (default: 30)
- **Minimum Cost Threshold**: Minimum cost to process receipts (default: $0.10)
- **Duplicate Prevention**: Enable duplicate receipt detection
- **Auto Export CSV**: Automatically export data to CSV
- **Scheduled Processing**: Enable daily automatic processing
- **Schedule Time**: Time for daily processing (default: 02:00)

### Gmail Setup
1. Enable 2-Factor Authentication on your Google account
2. Generate an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification
   - App passwords → Select app: Mail
   - Copy the generated 16-character password
3. Use this app password in the integration configuration

### Tesla PDF Setup
1. Create a `Tesla` folder in your Home Assistant `www` directory:
   ```
   config/www/Tesla/
   ```
2. Place Tesla Supercharging receipt PDFs in this folder
3. The integration will automatically process new PDFs

### EVCC Setup (Optional)
1. Install and configure [EVCC](https://evcc.io/)
2. Ensure EVCC API is accessible
3. Configure the EVCC URL in the integration settings

## 🎛️ Usage

### Available Sensors
The integration creates multiple sensors to track your charging data:

- **Total Receipts**: Total number of charging sessions
- **Total Cost**: Total amount spent on charging
- **Total Energy**: Total kWh consumed
- **Monthly Cost**: Charging cost for the last 30 days
- **Monthly Energy**: Energy consumed in the last 30 days
- **Average Cost per kWh**: Average rate across all sessions
- **Last Session Provider**: Most recent charging provider
- **Last Session Cost**: Cost of the most recent session
- **Last Session Date**: Date and time of the most recent session
- **Last Session Energy**: Energy consumed in the most recent session
- **Top Provider**: Most frequently used charging provider
- **Home Charging (Monthly)**: Home charging cost for the last 30 days
- **Public Charging (Monthly)**: Public charging cost for the last 30 days

### Control Buttons
- **Run Now**: Process emails with default configuration
- **Clear All Data**: Remove all data and reprocess from scratch
- **Process with Custom Days**: Use custom day setting for processing
- **Debug with Custom Days**: Debug email parsing with custom day setting
- **Process Tesla PDFs**: Process only Tesla PDF receipts
- **Debug Tesla PDFs**: Debug Tesla PDF processing

### Quick Actions Selector
Choose from predefined actions:
- Process Last 7/14/30/60/90 Days
- Debug Last 3/7 Days
- Clear & Reprocess 30/60/200 Days
- Process Tesla PDFs Only
- Debug Tesla PDFs

### Available Services

#### `ev_charging_extractor.trigger_extraction`
Manually trigger email processing
```yaml
service: ev_charging_extractor.trigger_extraction
data:
  email_search_days: 30  # Optional: override default days
```

#### `ev_charging_extractor.debug_email_parsing`
Debug email parsing issues
```yaml
service: ev_charging_extractor.debug_email_parsing
data:
  email_search_days: 7  # Optional: days to debug
```

#### `ev_charging_extractor.process_tesla_pdfs`
Process Tesla PDFs only
```yaml
service: ev_charging_extractor.process_tesla_pdfs
```

#### `ev_charging_extractor.fix_receipt_dates`
Correct incorrect receipt dates
```yaml
service: ev_charging_extractor.fix_receipt_dates
```

#### `ev_charging_extractor.export_to_csv`
Export all data to CSV
```yaml
service: ev_charging_extractor.export_to_csv
```

#### `ev_charging_extractor.get_database_stats`
Get detailed statistics
```yaml
service: ev_charging_extractor.get_database_stats
```

#### `ev_charging_extractor.clear_and_reprocess`
Clear all data and reprocess
```yaml
service: ev_charging_extractor.clear_and_reprocess
data:
  email_search_days: 200  # Optional: days to reprocess
```

## 📁 Data Storage

### Database
- **Location**: `config/ev_charging_data.db`
- **Type**: SQLite database
- **Tables**: Charging receipts, processed emails, processed Tesla PDFs, processed EVCC sessions

### CSV Export
- **Location**: `config/www/ev_charging_receipts.csv`
- **Format**: User-friendly with formatted dates (DD-MM-YY HH:MM)
- **Columns**: Session Date & Time, Provider, Location, Energy (kWh), Duration, Cost, Currency, Source, Added to Database

### Tesla PDFs
- **Location**: `config/www/Tesla/`
- **Supported**: Any Tesla Supercharging receipt PDFs
- **Processing**: Automatic when placed in directory

## 🔧 Troubleshooting

### Common Issues

#### Gmail Connection Errors
- Verify Gmail app password is correct
- Ensure 2-Factor Authentication is enabled
- Check Gmail IMAP is enabled
- Try generating a new app password

#### Tesla PDFs Not Processing
- Ensure PDFs are in `config/www/Tesla/` directory
- Check PDF format is valid Tesla receipt
- Look for errors in Home Assistant logs
- Use "Debug Tesla PDFs" service for detailed analysis

#### EVCC Connection Issues
- Verify EVCC URL is correct and accessible
- Check EVCC API is enabled
- Ensure network connectivity between Home Assistant and EVCC
- Use "Debug EVCC Connection" service

#### Date Parsing Issues
- Use "Fix Receipt Dates" service to correct dates
- Use "Analyze Date Issues" service to identify problems
- Check logs for date parsing errors

### Debug Services
Use the debug services to troubleshoot issues:
- `debug_email_parsing`: Analyze email content and parsing
- `debug_evcc_connection`: Test EVCC connectivity and data
- `debug_tesla_pdfs`: Analyze Tesla PDF structure and parsing
- `analyze_date_issues`: Identify receipts with date problems

### Logs
Enable debug logging for detailed troubleshooting:
```yaml
logger:
  default: info
  logs:
    custom_components.ev_charging_extractor: debug
```

## 🌏 Supported Providers

### Australian Providers
- **BP Pulse**: Full support including receipt parsing
- **EVIE Networks**: Complete integration with tax invoices
- **Chargefox**: Advanced parsing with multiple receipt formats
- **Ampol (AmpCharge)**: Full support including Foodary locations
- **NRMA**: Basic support
- **Shell Recharge**: Basic support
- **ChargePoint**: Basic support

### International Providers
- **Tesla Supercharging**: Global support with PDF processing
- **ChargePoint**: International locations

### Home Charging
- **EVCC**: Complete integration with solar tracking
- **Manual Entry**: Through custom sensors (planned)

## 🔮 Roadmap

### Planned Features
- [ ] Grafana dashboard integration
- [ ] InfluxDB export support
- [ ] Mobile app notifications
- [ ] Cost prediction and budgeting
- [ ] Carbon footprint tracking
- [ ] Integration with energy tariff APIs
- [ ] Multi-vehicle tracking
- [ ] Charging session analytics
- [ ] Automatic route planning integration

### Provider Expansion
- [ ] Additional Australian providers
- [ ] European charging networks
- [ ] North American providers
- [ ] Asian charging networks

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Adding New Providers
To add support for a new charging provider:

1. Create a new parser in `parsers/` directory
2. Extend the `BaseParser` class
3. Implement provider-specific extraction methods
4. Add provider detection logic
5. Update `ProviderMapping` class
6. Add tests for the new provider

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Home Assistant community for the excellent platform
- EVCC project for home charging integration
- Tesla for providing detailed PDF receipts
- Australian EV charging providers for consistent receipt formats

## 📞 Support

- **Issues**: Report bugs and feature requests on [GitHub Issues](https://github.com/your-username/ha-ev-charging-extractor/issues)
- **Discussions**: Join the conversation in [GitHub Discussions](https://github.com/your-username/ha-ev-charging-extractor/discussions)
- **Community**: Find help in the Home Assistant community forums

## 🏷️ Version History

### v1.0.0
- Initial release with email processing
- Tesla PDF support
- EVCC integration
- Basic provider support (BP Pulse, EVIE, Chargefox, Ampol)
- Date correction functionality
- CSV export capabilities
- Comprehensive Home Assistant integration

---

**Made with ❤️ for the EV community in Australia and beyond**