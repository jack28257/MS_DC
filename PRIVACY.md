# MirrorShot Privacy Policy

Updated October 17, 2026 · Lumilo Studio

This policy describes the current free playtest of MirrorShot for iOS.

## Local game data

MirrorShot has no account, advertising, analytics SDK or cross-app tracking. We do not receive your gameplay progress. Campaign progress, scores, achievements, daily challenge records, tutorial history and preferences are stored locally using app-scoped UserDefaults. Older builds may also have saved a local gem balance; it is retained but is not used or sold in this playtest.

Debug builds may write local daily-loading and notification diagnostic status inside the app container. These files are not automatically uploaded.

## Daily challenge downloads

When the game opens or returns to the foreground, it requests the active daily challenge from `raw.githubusercontent.com`. While open, it checks for the new challenge day at 08:00 America/Toronto. The requested file path contains the challenge date. No scores, progress, account identifier or advertising identifier are included in the request.

GitHub receives the network request and may process technical information such as the IP address and request time under its [General Privacy Statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement). The developer does not receive player progress through this download. Challenge content is held in memory for the current session, without an app-managed persistent content cache.

## Notifications

With your permission, a local notification reminds you daily at 08:00 America/Toronto. MirrorShot does not use a remote push notification server. You can disable the reminder in game settings and manage notification permission in iOS Settings.

## Sharing and external links

Sharing starts only when you tap Share and uses the iOS share sheet. The image contains the game result shown in its preview. Your selected destination handles shared content under its own terms. Opening an external privacy or support link uses your browser and that website's privacy practices.

## Purchases

The current playtest does not process payments or offer in-app purchases. All current levels are available through normal progression, with unlimited trajectory previews. There are no gem purchases. A future paid release will require an updated policy before payment features are enabled.

## Deleting local data

Settings → Clear play history resets campaign scores, achievements and tutorial history. Select the daily streak option to also clear daily records. This keeps preferences and any legacy local gem balance.

To remove the complete app container, select **Delete App** in iOS Settings; **Offload App** keeps data. Apple device backups or transfers may retain or copy local data according to your system settings. We cannot access or delete those backups.

## Support and privacy questions

Contact the developer through [MirrorShot support on GitHub](https://github.com/jack28257/MS_DC/issues). This is a public issue tracker; do not include passwords, personal details or private screenshots. A GitHub account may be required to submit an issue.

The policy is also available inside MirrorShot under Settings → Privacy policy, including English, French and Chinese text. Policy changes will be reflected here and in the app.
