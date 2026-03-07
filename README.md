# Smart-Google: Control your custom devices with Google Home using Python and Flask

![GitHub license](https://img.shields.io/github/license/DaTiC0/smart-google)

## How to integrate Google Home to your custom devices by Google action and Python with Flask Framework

If you are looking for a way to control your custom devices with Google Home, you might be interested in Smart-Google, a project that allows you to create your own Google actions and connect them to your devices using Python and Flask. In this blog post, I will show you how to set up the environment, create a simple Google action, and use MQTT to communicate with your device.

## Environment

To run this project, you will need the following:

- A Google account and a Google Home device
- A custom device that can connect to the internet and use MQTT protocol (I used a ESP 8266 board with micropython firmware)
- A Heroku or Google Cloud or AWS or any other cloud platform which supports Python apps
- A Firebase account and the Firebase CLI installed
- Python 3.8 or higher and pip installed

## Installation

The first step is to clone the Smart-Google repository from GitHub:

```bash
git clone https://github.com/DaTiC0/smart-google.git
cd Smart-Google
```

Next, you need to create a virtual environment and install the required packages:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Then, you need to export some environment variables that will be used by the application. You can either set them manually or use a .env file. The variables are:

- `SECRET_KEY`
- `SQLALCHEMY_DATABASE_URI`
- `MQTT_BROKER_URL`
- `MQTT_USERNAME`
- `MQTT_PASSWORD`
- `API_KEY`
- `AGENT_USER_ID`
- `SERVICE_ACCOUNT_FILE`
- `FIREBASE_ADMINSDK_FILE`
- `DATABASEURL`

### Google Service Account

To use Google actions and Firebase, you need to create a service account and download the JSON credentials file. Run the helper script to generate `service_account_file.json`:

```bash
python generate_service_account_file.py
```

The following variables are extracted automatically from that file and must also be present in your environment or `.env`:

- `PROJECT_ID`
- `PRIVATE_KEY_ID`
- `PRIVATE_KEY`
- `CLIENT_EMAIL`
- `CLIENT_X509_CERT_URL`

### Testing Locally

To expose your Flask server to the internet during local testing, use either **ngrok**:

```bash
./ngrok http 5000
```

or **Cloudflare Tunnel**:

```bash
cloudflared tunnel --url http://localhost:5000
```

### Health Check

The app exposes a `/health` endpoint:

```bash
curl -i http://127.0.0.1:5000/health
# or
make health
```

Example response:

```json
{"mqtt_connected":true,"service":"smart-google","status":"ok"}
```

Returns `200` when MQTT is connected (`status: ok`) and `503` when it is not (`status: degraded`).

### Collaboration Workflow

Recommended workflow is branch + pull request + merge to `main`.

Quick steps:

```bash
git checkout main
git pull --rebase origin main
git checkout -b feat/my-change
make install-hooks
```

Before opening a PR:

```bash
make test
make health
make check-paths
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full details and AI-assisted code review policy.
