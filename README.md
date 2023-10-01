# RSS Server for Mirantis Software Releases

This is a simple Flask-based RSS server that provides information about the latest Mirantis software releases. It periodically fetches release information for different Mirantis products, caches the data, and serves it as an RSS feed.

## Features

- Automatically updates release information every 24 hours.
- Caches release data to minimize external requests.
- Supports multiple Mirantis products.
- Exposes basic Prometheus metrics to monitor application performance.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [License](#license)

## Installation

Make sure you have python3 installed as a pre-requisite.

Clone the repository:
```shell
git clone https://github.com/yourusername/rss-server.git
cd rss-server
```

Set up a virtual environment and activate it:

```shell
python -m venv venv
# For Windows
.\venv\Scripts\activate
# For Unix or MacOS
source venv/bin/activate
```

Install the required Python packages:
```shell
pip install -r requirements.txt
```

## Usage

Start the RSS server:

```shell
python app.py
```

Access the RSS feed in your web browser or through an RSS reader:
RSS Feed URL: http://localhost:4000/rss

## Configuration

You can customize the behavior of the RSS server by modifying the config.py file. Some configurable options include:

- List of Mirantis products and their repository information.
- Cache expiration time.
- Port and host settings.

## Contributing

Contributions are welcome! If you'd like to contribute to this project, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and test them.
4. Commit your changes with clear and concise messages.
5. Push your changes to your fork.
6. Create a pull request to the main repository.

## License

This project is licensed under the MIT License.