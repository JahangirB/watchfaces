# Install Almanac on a OnePlus Watch 3

Almanac is sideloaded: you copy the APK onto the watch yourself over Wi-Fi.
It takes about 10 minutes the first time. After that, updating is a single command.

**You need:**
- a OnePlus Watch 3, or any watch on **Wear OS 5 or newer**;
- the file [`dist/almanac-1.0.0.apk`](../dist/almanac-1.0.0.apk);
- a computer (Windows, macOS or Linux) **or** an Android phone. Both routes are below;
- the watch and the computer or phone on the **same Wi-Fi network**.

> SHA-256 of `almanac-1.0.0.apk`:
> `35bfa3f814d226309c12ab14c2e8c9ed2bf1b14b8667a606666014e6dfbe9303`

---

## Step 1: Turn on developer options on the watch

1. On the watch, open **Settings → System → About**. On some versions this is
   **About watch → Versions**.
2. Tap **Build number** seven times, until it says you're a developer.
3. Go back to **Settings → System → Developer options** (on some versions it's
   at the bottom of **Settings**).
4. Turn on **ADB debugging**.
5. Turn on **Wireless debugging**. Make sure the watch is connected to Wi-Fi.
   Bluetooth-only isn't enough.

---

## Step 2a: Install from a computer

1. Install Google's **platform-tools**, which include `adb`:
   https://developer.android.com/tools/releases/platform-tools
   On macOS you can use `brew install android-platform-tools` instead.
2. On the watch, open **Wireless debugging → Pair new device**. The watch shows
   an address such as `192.168.1.23:37123` and a 6-digit code.
3. On the computer, pair using the address and port from the pairing screen,
   then type the code when asked:

```bash
adb pair 192.168.1.23:37123
```

4. Go back one screen on the watch. The **Wireless debugging** screen shows a
   second address with a **different port**, for example `192.168.1.23:41234`.
   Connect to that one:

```bash
adb connect 192.168.1.23:41234
```

5. Install the face, from the folder where you downloaded the APK:

```bash
adb install almanac-1.0.0.apk
```

   You should see `Success`.

## Step 2b: Install from an Android phone (no computer)

1. On your phone, install an ADB installer app such as **Bugjaeger** or
   **Wear Installer 2** from the Play Store.
2. Download `almanac-1.0.0.apk` to the phone.
3. In the app, choose to pair with a watch over wireless debugging, and enter the
   pairing address and code from **Wireless debugging → Pair new device** on the
   watch. Then connect with the address on the main **Wireless debugging** screen.
4. Choose **Install APK** and pick `almanac-1.0.0.apk`.

---

## Step 3: Select the face

1. On the watch, **press and hold** the current watch face.
2. Swipe to the end of the list and tap **+ Add**, or **Add watch face**.
3. Choose **Almanac**.

**Customise it:** press and hold the face, then tap **Edit** or **Customize**:

| Option | Choices |
|---|---|
| Day schedule | Early 06–21 · **Standard 07–22** · Late 08–23. This sets when morning, day, evening and night begin, and the step pace |
| Light scale | On / off: hatching on the 24 h ring for the hours of darkness ahead |
| Bottom | Any complication, with **Steps** as the default |

For security, turn **ADB debugging** off again when you're done.

---

## Updating to a new version

```bash
adb install -r almanac-1.0.1.apk
```

If you see `INSTALL_FAILED_UPDATE_INCOMPATIBLE`, the new APK was signed with a
different key. Remove the old one first:

```bash
adb uninstall io.github.jahangirb.watchface.almanac
```

## Removing it

```bash
adb uninstall io.github.jahangirb.watchface.almanac
```

You can also remove it from the watch's app list, like any other app.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `INSTALL_FAILED_OLDER_SDK` | The watch is older than Wear OS 5. Weather data in watch faces needs Wear OS 5. |
| "No forecast yet / Check connection" | The watch has no weather data yet. Open the watch's Weather app once, and allow location in the OnePlus OHealth app. |
| The face is replaced by a simple OnePlus face | That's the Watch 3's power-saver (RTOS) mode. Custom faces only show while Wear OS is running. |
| `adb pair` fails | Use the address and port from the **Pair new device** screen. They change each time it opens. |
| `adb connect` fails | Use the address from the main **Wireless debugging** screen, which is different from the pairing address. Check that both devices are on the same Wi-Fi. |
| Something looks wrong on the face | Take a screenshot with the command below and open an issue with it. |

To take a screenshot from the watch:

```bash
adb exec-out screencap -p > almanac.png
```

To capture the watch face's error log for a bug report:

```bash
adb logcat --pid=$(adb shell pidof -s com.google.wear.watchface.runtime) > almanac-log.txt
```
