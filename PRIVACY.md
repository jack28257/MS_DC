# Ray Skip Privacy Policy

Updated November 23, 2026 · JackJia Studio

This policy describes Ray Skip for iOS.

## Local game data

Ray Skip has no account, advertising, analytics SDK or cross-app tracking. We do not receive your gameplay progress automatically. Campaign progress, scores, achievements, daily challenge records, tutorial history, preferences and full-game access are stored locally. Mirror angles for an active round stay in memory.

Debug builds may write local daily-loading and notification diagnostic status inside the app container. These files are not automatically uploaded.

## Daily challenge downloads

When the game opens or returns to the foreground, it requests the active daily challenge from rayskip.com. While open, it checks for the new challenge day at 08:00 America/Toronto. The requested file path contains the challenge date. No scores, progress, account identifier or advertising identifier are included in the request.

Cloudflare serves the challenge published on GitHub and may process technical information such as the IP address and request time. Older app builds request the file directly from GitHub, which may process this information under its [General Privacy Statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement). Challenge content stays in memory for the current session.

## Notifications

With your permission, a local notification reminds you daily at 08:00 America/Toronto. Ray Skip does not use a remote push notification server. You can disable the reminder in game settings and manage notification permission in iOS Settings.

## Sharing and external links

Tapping Share opens the iOS share sheet with the image shown in the preview, accompanying text and the Ray Skip website link. Your selected destination handles shared content under its own terms. Cloudflare hosts rayskip.com and may process ordinary network information when you visit.

## Full-game access

The current release includes the full campaign. Its access is available on the device from first launch.

## Deleting local data

Settings → Clear play history resets campaign scores, achievements and tutorial history. Select the daily streak option to also clear daily records. This keeps preferences and full-game access.

To remove the complete app container, select **Delete App** in iOS Settings; **Offload App** keeps data. Apple device backups or transfers may retain or copy local data according to your system settings. We cannot access or delete those backups.

## Support and privacy questions

Use **Settings → Support & feedback** in Ray Skip, or the [Ray Skip feedback form](https://rayskip.com/support). No email address or account is required to submit.

Choosing Submit sends your message, a random submission reference, app/iOS versions, language, device model, recent level and up to 60 app-owned diagnostic events to our feedback service. These events describe game actions and results; they do not include system-wide logs, other apps, private identifiers, message drafts or purchase records. Browser submissions provide the message and browser-form version fields without iOS device diagnostics.

Unsubmitted drafts persist locally on the device or in browser storage. Submitted messages are saved locally before transmission; temporary failures are retried while the app or page is running and when it next opens. Retries use the same submission reference to avoid duplicate records. The queue removes confirmed messages. A permanently rejected message can be dealt with separately from later submissions.

Feedback submitted through rayskip.com reaches the same private inbox as feedback sent by older builds using the original support host. The inbox uses OpenAI Sites and Cloudflare hosting/database services. The developer's authenticated account can read and manage feedback. Your device stores a private random key per submission, and the server stores its hash, so you can view your own message, processing status and developer replies without an account or email. A reference number alone does not grant access. Losing app data or browser storage removes access to this anonymous history. Feedback is used to investigate problems, review ideas and improve the game, not for advertising or cross-app tracking. Records remain in the inbox until reviewed or removed by the developer.

The hosting providers receive ordinary technical network information, including IP address and request time. To limit spam, our service uses a daily-changing keyed hash of the network address in a separate rate-limit table. Raw IP addresses are not written to the feedback database. Expired rate-limit entries are cleaned up on subsequent submissions after expiry. See [Cloudflare's privacy policy](https://www.cloudflare.com/privacypolicy/) and [OpenAI's privacy policy](https://openai.com/policies/privacy-policy/) for the providers' practices.

To ask about a submission or request deletion, send a new message with the feedback reference. The developer reviews these requests.

The full policy is also bundled inside Ray Skip under Settings → Privacy policy, in English, French and Chinese. Policy changes will be reflected here and in the app.
