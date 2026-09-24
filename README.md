# VaultWares EPG

Private XMLTV and curated M3U service for `epg.vaultwares.ca`.

The Windows NSSM service `VaultExplorerEPG` runs as `LocalSystem`, uses delayed
automatic startup, and restarts its child process after failure. The
`VaultWaresEPGEnsure` task starts/resumes it at machine boot and user logon.

Endpoints: `/health`, `/epg.xml.gz`, `/epg-fr.xml.gz`, and `/playlist.m3u`.

Operational logs are in `runtime/`, and the French XMLTV backup is in `data/`.
Edit `.env` to change the source URLs, then restart `VaultExplorerEPG`.
`.env.example` documents the supported keys.

The `VaultWaresOnnTiviMateSync` task runs daily at midnight local time while
the Windows user is logged in. It mutes the ONN streamer before performing its
one m3u4u sync, validates the expected 41-channel playlist, uploads the local
M3U fallback to the ONN streamer, and refreshes TiviMate.

`M3U4U_POST_SYNC_WAIT_MS` in `.env` controls how long the browser remains open
after the second m3u4u confirmation; it defaults to 45 seconds.
