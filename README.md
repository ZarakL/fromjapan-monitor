# FromJapan Monitor

A web scraping application that monitors Japanese e-commerce platforms (Mercari, Rakuten, Rakuma) for specific fashion items and collectibles, sending real-time notifications to Discord webhooks when matching products are found.

## Features

- **Multi-Platform Monitoring**: Scrapes Mercari, Rakuten, and Rakuma through FromJapan's proxy service
- **Brand-Specific Search**: Monitors specific Japanese fashion brands including LizLisa, Axes Femme, Baby The Stars Shine Bright, h.naoto, and Angelic Pretty
- **Intelligent Filtering**: Advanced keyword filtering by color, style, and price ranges
- **Discord Integration**: Real-time notifications with product details, images, and direct links
- **Duplicate Prevention**: URL caching system prevents duplicate notifications
- **Price Conversion**: Automatic JPY to USD conversion for easy price assessment
- **Headless Operation**: Runs silently in the background using Chrome/Chromium WebDriver
- **Error Recovery**: Robust error handling with exponential backoff retry logic

## Target Brands & Items

### Fashion Brands
- **LizLisa**: Skirts and culottes in brown tones
- **Axes Femme**: Blouses, dresses, and tops with specific style filters
- **Baby The Stars Shine Bright (BTSSB)**: Items under $50 USD
- **h.naoto**: Gothic fashion items under $50 USD
- **Angelic Pretty**: Sweet Lolita items under $50 USD

### Collectibles
- **My Melody**: Vintage plushies, mascots, and character goods
- **Blind boxes and figures**: Various kawaii collectibles

## Technical Requirements

### Dependencies
- Python 3.7+
- Selenium WebDriver
- BeautifulSoup4
- Google Translate API (deep-translator)
- Requests library
- Chrome/Chromium browser
- ChromeDriver

### Installation
```bash
pip install selenium beautifulsoup4 deep-translator requests
```

## Configuration

The script requires several configuration elements:

1. **ChromeDriver**: Download from [ChromeDriver Downloads](https://chromedriver.chromium.org/downloads)
2. **Discord Webhooks**: Set up Discord webhook URLs for notifications
3. **Search Terms**: Customize Japanese search terms for your target items

## Usage

### Running the Script
```bash
python fromjapan.py
```

### Building Executable
```bash
pyinstaller fromjapan.spec
```

The executable will be created in the `dist/` directory and can run independently without Python installed.

## How It Works

1. **Initialization**: Sets up Chrome WebDriver with headless configuration
2. **Search Execution**: Iterates through predefined search terms across all platforms
3. **Content Extraction**: Parses product pages for titles, descriptions, prices, and images
4. **Filtering Logic**: Applies brand-specific filters (color, keywords, price ranges)
5. **Translation**: Converts Japanese text to English for notifications
6. **Duplicate Check**: Compares URLs against cached history to prevent repeats
7. **Discord Notification**: Sends formatted messages with product details
8. **Continuous Monitoring**: Repeats the cycle every 10 minutes

## Architecture

### Core Components
- **WebDriver Management**: Handles browser automation with stability optimizations
- **Search Processing**: Manages multi-site, multi-term search combinations
- **Content Parsing**: Extracts and processes product information
- **Filter Engine**: Applies sophisticated filtering logic per brand
- **Cache System**: Maintains persistent URL history with automatic cleanup
- **Notification System**: Formats and sends Discord messages with rich formatting

### Memory Optimization
- Periodic WebDriver refreshes to prevent memory leaks
- Garbage collection after processing cycles
- Resource cleanup on exit
- Chrome process management

## File Structure

```
fromjapan/
├── fromjapan.py          # Main application script
├── fromjapan.spec        # PyInstaller build configuration
├── update.bat            # Windows build automation script
└── dist/
    └── fromjapan.exe     # Compiled executable
```

## Monitoring Output

The application generates:
- `fromjapan_monitor.log`: Detailed operation logs
- `seen_urls.json`: URL cache for duplicate prevention
- Real-time Discord notifications with product details

## Development Notes

This project demonstrates:
- Advanced web scraping techniques with Selenium
- Multi-site data aggregation and processing
- Robust error handling and recovery mechanisms
- International e-commerce platform integration
- Real-time notification systems
- Memory-efficient long-running automation

## Disclaimer

This tool is for personal monitoring purposes only. Please respect the terms of service of the websites being monitored and use reasonable request intervals to avoid overwhelming servers.