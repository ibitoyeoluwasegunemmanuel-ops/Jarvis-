# JARVIS Mobile (Flutter)

This is the installable Android/iOS companion application.

## Build prerequisites
- Flutter stable SDK (Dart SDK constraint is in pubspec.yaml)
- Android Studio / Android SDK for APK builds
- Xcode on macOS for iOS builds

## Run
```sh
cd apps/mobile
flutter create --project-name jarvis_mobile --org com.ceoglobal --platforms android,ios --no-pub .
flutter pub get
flutter run
```

## Build Android APK
```sh
flutter build apk --debug
```

For a signed Play Store bundle, configure a private upload keystore and build:
```sh
flutter build appbundle --release
```

Never commit keystore files, passwords, API tokens, or signing credentials.

## Build iOS
On macOS with Xcode signing configured:
```sh
flutter build ios --release
```
Then archive and distribute through TestFlight using the organisation's Apple Developer account.

## Backend connection
The app accepts only an HTTPS cloud API base URL and stores that URL using platform secure storage. It intentionally does not connect to the Windows desktop's loopback gateway. At this stage it can test the public `GET /health` endpoint only. Cloud owner authentication, device registration, project sync, approvals, push notifications and voice are not yet wired; they must be implemented server-side before this app can be used as a fully connected companion.

The interface labels those capabilities as pending rather than displaying fabricated project or monitoring data.
