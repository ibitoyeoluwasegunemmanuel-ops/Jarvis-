# JARVIS Mobile (Flutter)

Installable Android and iOS companion for the JARVIS cross-device workspace.

## Build prerequisites

- Flutter stable SDK (Dart SDK constraint is in `pubspec.yaml`)
- Android Studio / Android SDK for Android builds
- Xcode on macOS for iOS builds

## Generate native projects and run

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

For a signed Play Store bundle, configure a private upload keystore and run
`flutter build appbundle --release`. Never commit keystore files or passwords.

## Build iOS

On macOS with Xcode signing configured:

```sh
flutter build ios --release
```

Then archive and distribute through TestFlight using the organisation's Apple
Developer account.

## Connect the app

On first launch, configure:

1. The deployed JARVIS Cloud API HTTPS base URL.
2. The Supabase project HTTPS URL.
3. The Supabase publishable key (or legacy anon public key).

Do not enter a Supabase secret key or service-role key in the mobile app. The
three configuration values and authentication session are stored using
platform secure storage.

## Implemented mobile flow

- Supabase Auth email/password sign-in and account creation.
- Refresh-token rotation and secure persistence of the access/refresh session.
- Authenticated calls to the separate JARVIS Cloud API.
- Workspace discovery and first-workspace creation.
- Current-device registration and per-account device revocation.
- Workspace overview, project list and monitoring-alert list.
- HTTPS-only API URL validation.

Email confirmation behavior follows the Supabase Auth project settings. If
confirmation is enabled, the user must confirm the email before signing in.

## Important release limitations

The cloud API still needs to be deployed and configured with Supabase Auth,
PostgreSQL migrations, a dedicated NOBYPASSRLS runtime role and production
secrets. The mobile app does not yet have push notifications, live updates,
voice, approval execution, offline sync or a Windows desktop cloud-sync client.
The mobile app never connects to the Windows machine's private loopback gateway.

Android/iOS compilation and physical-device installation must pass before this
is treated as an installable release. The current source and CI workflows are
not proof of a signed store-ready build.
