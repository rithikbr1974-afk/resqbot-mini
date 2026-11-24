# ResQBot Control: phone app with Google AI Studio

Two ways to control the robot from a phone:

| Way | Effort | What you get |
|---|---|---|
| **A. Built-in dashboard** | none | Join Wi-Fi `ResQBot-01` (password `rescue123`), open `http://192.168.4.1` in Chrome. Already in the firmware. |
| **B. ResQBot Control app** | about 1–2 hours | A real Android app built with Google AI Studio from `ai_studio_prompt.txt`: thermal radar, drive pad, camera, sensors, mission log, AI incident report. |

Use A for testing the robot today. Use B when you want a polished app to show the judges.

## Why the app must become an APK

Google AI Studio runs your app on an `https://` web address. A phone browser blocks an `https` page from talking to the robot's
plain `http://192.168.4.1` address (this is called *mixed content*). Packaging the same app as an Android APK with
**Capacitor** fixes this, because the app then runs from the phone itself. The firmware already sends the
`Access-Control-Allow-Origin: *` header that the app needs.

## Step 1: build the app in AI Studio (about 20 minutes)

1. Open **aistudio.google.com** and sign in with your Google account.
2. Click **Build** (the app builder).
3. Open `ai_studio_prompt.txt`, copy **all** of it, paste it in, and press Enter.
4. Wait for it to generate the app. The preview starts in **Demo mode**. Press **Auto search**: within about 20 seconds a survivor
   alert should appear. Try **Acknowledge**, the D-pad (switch to Manual first) and **E-STOP**.
5. If something is missing, ask in the same chat, for example:
   - "The D-pad must keep sending /api/drive every 200 ms while held and send l=0&r=0 on release."
   - "Show DEMO DATA on the Mission screen while the simulator runs."
   - "Make the radar's LEFT side match positive bearings."
6. When you're happy, use **Download** (zip) or **Save to GitHub** to get the code.

## Step 2: turn it into an Android APK (about 30–60 minutes the first time)

You need **Node.js 18+** and **Android Studio** (free) on your computer.

1. Unzip the code and open a terminal in that folder.

```bash
npm install
```

2. Add Capacitor:

```bash
npm install @capacitor/core @capacitor/android
```

```bash
npm install -D @capacitor/cli
```

```bash
npx cap init "ResQBot Control" com.resqbot.control --web-dir dist
```

3. Replace the generated `capacitor.config.ts` (or `.json`) with:

```ts
import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.resqbot.control',
  appName: 'ResQBot Control',
  webDir: 'dist',
  server: { androidScheme: 'http', cleartext: true },   // app runs from http://localhost, so it may call http://192.168.4.1
  plugins: { CapacitorHttp: { enabled: true } },          // native HTTP for fetch(): no CORS or mixed-content blocks
};

export default config;
```

4. Build the web app and add Android:

```bash
npm run build
```

```bash
npx cap add android
```

5. Open `android/app/src/main/AndroidManifest.xml` and make sure the `<application …>` tag has
   `android:usesCleartextTraffic="true"` (add it if missing).
6. Copy the build in and open Android Studio:

```bash
npx cap sync android
```

```bash
npx cap open android
```

7. In Android Studio: **Build → Build App Bundle(s) / APK(s) → Build APK(s)**. The file appears in
   `android/app/build/outputs/apk/debug/app-debug.apk`.
8. Copy the APK to your phone and open it (allow "install unknown apps" for your file manager once).

After every change to the app: `npm run build`, then `npx cap sync android`, then build the APK again.

## Step 3: connect the phone to the robot

1. Switch the robot on and wait for **two short beeps**.
2. On the phone: Wi-Fi → **ResQBot-01** → password `rescue123`.
3. Android will say the Wi-Fi **has no internet**. Tap **Keep connected** (or "Use this network anyway").
4. Open **ResQBot Control** → **Connect** (robot address `http://192.168.4.1`). The pill turns **ONLINE**.
5. If it can't connect: turn **mobile data off** for a moment, check the robot address, and make sure the robot finished starting.
6. The camera is the same board that makes the Wi-Fi, so video is at `http://192.168.4.1:81/stream` and needs no extra setup.

## The AI features (Gemini)

- **AI mission report** and **Analyze photo** need internet. While the phone is on the robot's Wi-Fi it has none, so finish the
  mission, reconnect to normal Wi-Fi or mobile data, then tap **AI mission report**. The mission log stays in the app.
- Get a free key at **aistudio.google.com → Get API key** and paste it in the app's **Settings**. It is stored only on your phone.
  Never put the key in the code or on GitHub.
- Robot control never depends on Gemini: driving, alerts and E-STOP work with no internet at all.

## Checklist before the demo

- [ ] Demo mode: Auto search → alert → Acknowledge works.
- [ ] Real robot: pill shows ONLINE, radar fills after **Thermal scan**.
- [ ] D-pad: robot stops the moment you lift your finger.
- [ ] E-STOP works from every screen.
- [ ] Camera shows video; **Flash light** toggles the LED.
- [ ] AI report works after reconnecting to the internet.
