# MirrorShot Privacy Policy

Updated October 20, 2026 · Lumilo Studio

This policy describes MirrorShot for iOS.

## Local game data

MirrorShot has no account, advertising, analytics SDK or cross-app tracking. We do not receive your gameplay progress automatically. Campaign progress, scores, achievements, daily challenge records, tutorial history, saved mirror layouts, preferences and full-game access are stored locally using app-scoped UserDefaults. Older builds may also have saved a local gem balance; it is retained but gems are not used or sold.

Debug builds may write local daily-loading and notification diagnostic status inside the app container. These files are not automatically uploaded.

## Daily challenge downloads

When the game opens or returns to the foreground, it requests the active daily challenge from `raw.githubusercontent.com`. While open, it checks for the new challenge day at 08:00 America/Toronto. The requested file path contains the challenge date. No scores, progress, account identifier or advertising identifier are included in the request.

GitHub receives the network request and may process technical information such as the IP address and request time under its [General Privacy Statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement). The developer does not receive player progress through this download. Challenge content is held in memory for the current session, without an app-managed persistent content cache.

## Notifications

With your permission, a local notification reminds you daily at 08:00 America/Toronto. MirrorShot does not use a remote push notification server. You can disable the reminder in game settings and manage notification permission in iOS Settings.

## Sharing and external links

Sharing starts only when you tap Share and uses the iOS share sheet. The image contains the game result shown in its preview. Your selected destination handles shared content under its own terms. Opening an external privacy or support website uses your browser and that website's privacy practices.

## Purchases

Full-game access and purchase records are stored on your device. Restore purchases reads the purchase record saved on this device. MirrorShot does not collect payment card details or send purchase records to the feedback service. There are no gem purchases.

## Deleting local data

Settings → Clear play history resets campaign scores, achievements and tutorial history. Select the daily streak option to also clear daily records. This keeps preferences, full-game access and any legacy local gem balance.

To remove the complete app container, select **Delete App** in iOS Settings; **Offload App** keeps data. Apple device backups or transfers may retain or copy local data according to your system settings. We cannot access or delete those backups.

## Support and privacy questions

Use **Settings → Support & feedback** in MirrorShot, or the [MirrorShot feedback form](https://mirrorshot-feedback.groovy-clove-2264.chatgpt.site/). No email address or account is required to submit.

Choosing Submit sends your message, a random submission reference, app/iOS versions, language, device model, recent level and up to 60 app-owned diagnostic events to our feedback service. These events describe game actions and results; they do not include system-wide logs, other apps, private identifiers, message drafts or purchase records. Browser submissions provide the message and browser-form version fields without iOS device diagnostics.

Unsubmitted drafts persist locally on the device or in browser storage. Submitted messages are saved locally before transmission; unconfirmed messages retry automatically while the app or page is running and when it next opens. The same submission reference prevents duplicate records. Confirmed messages are removed from the local queue.

Feedback is stored in the developer's private inbox using OpenAI Sites and Cloudflare hosting/database services. The developer's authenticated account can read and manage feedback. Your device stores a private random key per submission, and the server stores its hash, so you can view your own message, processing status and developer replies without an account or email. A reference number alone does not grant access. Losing app data or browser storage removes access to this anonymous history. Feedback is used to investigate problems, review ideas and improve the game, not for advertising or cross-app tracking. Records remain in the inbox until reviewed or removed by the developer.

The hosting providers receive ordinary technical network information, including IP address and request time. To limit spam, our service uses a daily-changing keyed hash of the network address in a separate rate-limit table. Raw IP addresses are not written to the feedback database. Expired rate-limit entries are cleaned up on subsequent submissions after expiry. See [Cloudflare's privacy policy](https://www.cloudflare.com/privacypolicy/) and [OpenAI's privacy policy](https://openai.com/policies/privacy-policy/) for the providers' practices.

To ask about a submission or request deletion, send a new message with the feedback reference. The developer reviews these requests.

The full policy is also bundled inside MirrorShot under Settings → Privacy policy, in English, French and Chinese. Policy changes will be reflected here and in the app.
