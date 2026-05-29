# Telegram Boat Android Shell

This is an Android app shell that opens a WebView and connects to your Telegram downloader backend.

## What it does
- Loads a configured backend URL in a WebView
- Saves the URL across launches
- Allows you to install a native app wrapper for the web dashboard

## How to build
1. Install Android Studio and Android SDK.
2. Open this folder in Android Studio: `android-app`
3. Sync Gradle and build the app.
4. Install on your phone or emulator.

## Important notes
- This app is only a shell. The actual Telegram downloader backend still must run on a server.
- On your phone, set the backend URL to the reachable address of your machine or server, for example:
  `http://192.168.1.100:8000`
- If your phone cannot reach the laptop directly, deploy the backend to a remote host and use that host URL.
