## EV Charging Receipt Extractor

**Automatically extract and track EV charging receipts from emails, Tesla PDFs, and home charging systems.**

### ✨ Features

- **📧 Multi-Provider Email Support** - Automatically processes charging receipts from Gmail
- **🚗 Tesla Integration** - Handles Tesla Supercharging PDFs and email receipts  
- **🏠 EVCC Home Charging** - Integrates with EVCC systems for complete charging data
- **📊 Comprehensive Analytics** - Real-time sensors and detailed charging statistics
- **🛡️ Smart Duplicate Prevention** - Automatically prevents duplicate entries
- **📁 CSV Export** - Export data with user-friendly formatting
- **🕐 Automated Processing** - Scheduled daily processing with manual controls
- **🔧 Advanced Debugging** - Built-in tools for troubleshooting parsing issues

### 🌏 Supported Providers

**Australian Providers:**
- BP Pulse
- EVIE Networks  
- Chargefox
- Ampol (AmpCharge)
- NRMA
- Shell Recharge

**International:**
- Tesla Supercharging (Global)
- ChargePoint

**Home Charging:**
- EVCC (Complete integration)

### 📋 Requirements

- **Home Assistant** 2023.1 or later
- **Gmail Account** with app password enabled
- **Python Dependencies** (auto-installed):
  - `beautifulsoup4` - HTML email processing
  - `PyPDF2` - Tesla PDF processing  
  - `pandas` - Enhanced date parsing
  - `requests` - EVCC integration

### 🚀 Quick Start

1. **Install via HACS**
   - Add this repository to HACS
   - Install "EV Charging Receipt Extractor"
   - Restart Home Assistant

2. **Add Integration**
   - Go to Settings → Devices & Services
   - Click "Add Integration"
   - Search for "EV Charging Receipt Extractor"

3. **Configure Gmail**
   - Enable 2-Factor Authentication on Google Account
   - Generate App Password (not your regular password)
   - Enter Gmail address and app password

4. **Optional: Tesla Setup**
   - Create folder: `config/www/Tesla/`
   - Place Tesla receipt PDFs in this folder
   - Integration will auto-process new PDFs

5. **Optional: EVCC Setup**
   - Configure EVCC URL (default: `http://homeassistant.local:7070`)
   - Enable EVCC integration in settings

### 🎛️ What You Get

**Sensors Created:**
- Total/Monthly cost and energy consumption
- Last session details (provider, cost, energy, date)
- Home vs Public charging breakdown
- Average cost per kWh
- Top provider statistics

**Controls:**
- Manual processing buttons
- Quick action selector (7/14/30/60/90 day processing)
- Debug tools for troubleshooting
- CSV export functions

**Services:**
- `trigger_extraction` - Manual email processing
- `export_to_csv` - Export all data
- `debug_email_parsing` - Troubleshoot parsing issues
- `process_tesla_pdfs` - Tesla PDF processing
- `clear_and_reprocess` - Fresh start option

### 💡 Pro Tips

- **Gmail App Password**: Use Google's app-specific password, not your regular password
- **Tesla PDFs**: Drag and drop Tesla receipts into `config/www/Tesla/` folder
- **Scheduling**: Enable daily processing at 2 AM for automatic updates
- **Debugging**: Use debug services if receipts aren't being detected
- **CSV Export**: Access exported data at `/local/ev_charging_receipts.csv`

### 🛠️ Troubleshooting

**Gmail Issues:**
- Verify 2-Factor Authentication is enabled
- Generate new app password if authentication fails
- Check IMAP is enabled in Gmail settings

**Tesla PDFs Not Processing:**
- Ensure PDFs are in `config/www/Tesla/` directory
- Check PDFs are valid Tesla Supercharging receipts
- Use "Debug Tesla PDFs" service for analysis

**EVCC Connection Issues:**
- Verify EVCC URL is accessible from Home Assistant
- Check EVCC API is enabled
- Test with "Debug EVCC Connection" service

**Missing Receipts:**
- Use "Debug Email Parsing" service
- Check email search days setting
- Verify provider emails aren't filtered/blocked

### 📊 Dashboard Integration

The integration creates sensors perfect for Energy Dashboard and custom cards:

```yaml
# Example Lovelace card
type: entities
title: EV Charging
entities:
  - sensor.ev_charging_monthly_cost
  - sensor.ev_charging_monthly_energy  
  - sensor.ev_charging_last_session_provider
  - sensor.ev_charging_average_cost_per_kwh
```

### 🔒 Privacy & Security

- Gmail credentials stored securely in Home Assistant
- Email content processed locally (never sent externally)
- PDF processing happens locally on your system
- No data transmitted to third parties
- Database stored locally in your Home Assistant config

### 🤝 Support

- **Issues**: [GitHub Issues](https://github.com/stevelea/EV-Charging-Extracter-2/issues)
- **Discussions**: [GitHub Discussions](https://github.com/stevelea/EV-Charging-Extracter-2/discussions)
- **Documentation**: [Full Documentation](https://github.com/stevelea/EV-Charging-Extracter-2)

### ⚡ Perfect for EV Owners Who Want To:

- Track charging costs across multiple providers
- Monitor home vs public charging ratios
- Export data for tax/business purposes
- Analyze charging patterns and optimize costs
- Integrate charging data with home energy management

---

**Made with ❤️ for the EV community in Australia and beyond**