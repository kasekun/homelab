# Plex deep links on the NVIDIA SHIELD

Goal: an NFC tag should start a specific movie on the SHIELD, either at 0:00 or at that item's saved resume point. The same mechanism should later cover episodes and playlists.

Tested with Plex Android TV `com.plexapp.android` 2026.20.0 (`tv.plex.app.MainActivity`) on SHIELD `192.168.1.126`, against PMS `http://192.168.1.123:32400` (machine id `${MACHINE_ID}`). Movies used: Antz `35417`, James and the Giant Peach `49423`.

Current implementation lives in `jplex`: it builds the same watch links, opens Plex first, leaves any active/paused player, quotes the URL for `adb shell`, and supports movies, shows, and playlists. The old `plex_play.py` spike was removed.

note, throughout we reference `MACHINE_ID="<plex-server-id>"` this is the plex server id that you can get from visiting `app.plex.tv` and navigating to a movie in your library. e.g., the url `https://app.plex.tv/desktop/#!/server/abcd1234/details?...` reveals a `MACHINE_ID="abcd1234"`

## What plays a movie

The desktop URL does not. `https://app.plex.tv/desktop/#!/server/.../details?key=...` is not an intent filter on this build, so the app opens and stays on Home.

The player route is `watch/video`. The app's link prefixes are `plex://`, `https://watch.plex.tv`, and `https://watch.plextv.dev`. A working link:

```
https://watch.plex.tv/watch/video?uri=server%3A%2F%2F{machineId}%2Fcom.plexapp.plugins.library%2Flibrary%2Fmetadata%2F{ratingKey}&offset={seconds}
```

`uri` is the content URI, not a URL-encoded metadata path by itself:

```
server://{machineId}/com.plexapp.plugins.library/library/metadata/{ratingKey}
```

`offset` is seconds. The player does `parseInt(offset, 10) * 1000` and passes that as `startOffsetMs`. PMS `viewOffset` is milliseconds, so resume seconds are `viewOffset // 1000`.

Checked against `/status/sessions` for this SHIELD (`Player@address` `192.168.1.126`, `state=playing`):

| Link | Player already running? | Result |
| --- | --- | --- |
| `offset=20` after the player had been left | no | Antz at 20000 ms |
| `offset=12` after Back | no | James at 12000 ms |
| `offset=0` after Back | no | Antz at 0, then James at 0 |
| `offset=5`, `30`, `50`, `90` while another movie was playing | yes | Title changed. Clock did not. The new movie continued at the previous movie's position. |

`offset` is honored only when nothing is already playing. A link delivered to a live player (`am start` reports the intent was delivered to the current instance) swaps the metadata and keeps the existing clock. The decision builder uses the engine's `windowStartMs` when it does not receive a new start offset. `0` is also falsy in that builder (`if (startOffset)`), and the autoplay redirect drops a falsy `offset`, so do not rely on `offset=0` to seek backward inside a live session.

The start-at-0:00 sequence that worked:

1. If this SHIELD has a playing session, `input keyevent KEYCODE_BACK` and wait until `/status/sessions` no longer shows it playing. One Back left the player.
2. Then `am start` the watch link with `offset=0`.

Quote the URL in the device shell. `&` is a background operator, so an unquoted link loses `offset` and `-n`.

```
am start -a android.intent.action.VIEW \
  -d 'https://watch.plex.tv/watch/video?uri=...&offset=0' \
  -n com.plexapp.android/tv.plex.app.MainActivity
```

Cold start and "Plex is open but not playing" both land at 0:00 when `offset` is omitted, because there is no clock to reuse. That is not resume. Resume has to pass the item's own seconds.

## Resume

Read the item, do not trust the live player position:

```
GET /library/metadata/{ratingKey}
```

`viewOffset` is milliseconds of progress for that item. Absent or `0` means start at the beginning. Resume link:

```
offset = int(viewOffset or 0) // 1000
```

Then the same two steps: leave the current player, then open the watch link with that `offset`. An NFC tag can store the rating key and a mode (`restart` or `resume`). The handler looks up `viewOffset` at scan time so the tag does not go stale.

Earlier experiments wrote the inherited clock back onto James and Antz, so their saved `viewOffset` may be wrong until the next real watch.

## NFC handler

For each tag:

1. Map the tag to a rating key and a mode, `restart` or `resume`.
2. `GET /library/metadata/{ratingKey}`.
3. `offset = 0` for restart, otherwise `int(viewOffset or 0) // 1000`.
4. If `/status/sessions` shows this SHIELD `playing`, send Back and wait until that session is gone.
5. `am start` the watch link. Quote it.

`jplex play` does these steps for movies, shows, and playlists. Movie resume reads the movie `viewOffset`; show resume reads On Deck. Movies and shows resume by default; playlists start at the first item unless shuffled.

ADB over the network is enough for a first automation. Home Assistant can send the same Back and `am start` once the SHIELD is paired. The link itself does not need Home Assistant.

## TV shows

Played on the same SHIELD after leaving the movie player. Shows from `links.json`: Final Space `39010`. The Joy of Painting with Nicholas Hankins `39818` is the watched show used for resume (not in `links.json`). Its On Deck item is S1E2 Mt. McKinley `39821`.

A show rating key is a directory, not a video. The player is still `/watch/video`. PMS builds the episode queue from the content URI.

**Any implementation that starts media with adb must leave any item already playing before it sends the new watch link.** This applies to movies, episodes, shows, and playlists. A link delivered to a live player swaps the title and keeps the old clock, so `offset`, `key`, and `shuffle` do not take effect. If `/status/sessions` shows this SHIELD `playing`, send Back and wait until that session is gone, then `am start` the quoted link. One Back left the player in these tests. Plex can stay open.

```
adb -s 192.168.1.126:5555 shell input keyevent KEYCODE_BACK
```

A watch link sent while Plex has not yet connected to the server can stop on "server not available". Sending that same link again then works, because the first attempt opened the app. Implementations should open Plex with a plain launch, then send the watch link:

```
adb -s 192.168.1.126:5555 shell am start -n com.plexapp.android/tv.plex.app.MainActivity
```

`pmsUri(machineId, path)` is `server://{machineId}/com.plexapp.plugins.library` plus the library path. The route reads `uri`, `key`, `offset`, and `shuffle`. `offset` is `parseInt(offset, 10) * 1000` milliseconds. `shuffle` is on only when the query value is `1` or `true`. The player then `POST /playQueues` with that `uri`, the `key` as the starting item, and `shuffle` 0 or 1.

### Start from the beginning

Show URI and `offset=0`. No `shuffle`, no `key`. The queue starts at the first episode and ignores On Deck. Final Space played S1E1 Chapter One `39121` at 0. A Joy of Painting queue built the same way also starts at S1E1, even though On Deck is S1E2.

```
export MACHINE_ID="<plex-server-id>"
adb -s 192.168.1.126:5555 shell "am start -a android.intent.action.VIEW -d 'https://watch.plex.tv/watch/video?uri=server%3A%2F%2F${MACHINE_ID}%2Fcom.plexapp.plugins.library%2Flibrary%2Fmetadata%2F39010&offset=0' -n com.plexapp.android/tv.plex.app.MainActivity"
```

### Removed next-unwatched experiment

The show URI does not do this. It restarts at the first episode.

Unwatched means no `viewCount`. `GET /library/metadata/{showRatingKey}/allLeaves?unwatched=1` and take the first `Video`. For Joy of Painting that is S1E3 Ebony Sunset `39822`. S1E2 is On Deck and still has `viewOffset`, but it also has `viewCount` 2, so it is not the next unwatched episode.

Play that episode with the show URI and `key` set to the episode path, `offset=0`. `key` is the play-queue start item. `playlistPlaybackLink` appends the same `&key=`. This played Ebony Sunset at 0.

`jplex` no longer exposes this as `--mode next`; default show playback follows Plex's Play action by using On Deck instead.

```
export MACHINE_ID="<plex-server-id>"
adb -s 192.168.1.126:5555 shell "am start -a android.intent.action.VIEW -d 'https://watch.plex.tv/watch/video?uri=server%3A%2F%2F${MACHINE_ID}%2Fcom.plexapp.plugins.library%2Flibrary%2Fmetadata%2F39818&key=%2Flibrary%2Fmetadata%2F39822&offset=0' -n com.plexapp.android/tv.plex.app.MainActivity"
```

An episode URI (`.../library/metadata/{episodeRatingKey}`) also starts the show queue on that episode. If the in-progress episode has `viewOffset` but no `viewCount` yet, it is the first unwatched leaf. This mode still passes `offset=0`. Resume is the next section.

### Resume a partially watched episode

Read On Deck, not the show:

```
GET /library/metadata/{showRatingKey}?includeOnDeck=1
```

`OnDeck/Video` is the continue item. `viewOffset` is milliseconds. The link offset is `int(viewOffset) // 1000`. The show URI does not seek to that point. The episode does. Mt. McKinley with `offset=90` played at 90000 ms. That test moved its saved `viewOffset` from 90000 to 92047, so the command below uses 92 seconds.

```
export MACHINE_ID="<plex-server-id>"
adb -s 192.168.1.126:5555 shell "am start -a android.intent.action.VIEW -d 'https://watch.plex.tv/watch/video?uri=server%3A%2F%2F${MACHINE_ID}%2Fcom.plexapp.plugins.library%2Flibrary%2Fmetadata%2F39821&offset=92' -n com.plexapp.android/tv.plex.app.MainActivity"
```

The in-app Play action (`pmsWatchAction`) is this case when `viewOffset` is set, and the next-episode case when it is not: the target is `OnDeck.Metadata.key`, and the offset is `floor(viewOffset / 1000)` only when `viewOffset` is present. `pmsWatchFromStartAction` is the Restart action. On a show it plays the show key at offset 0, which is the first episode.

`jplex play` and `jplex plan` use that Play action by default for movies and shows. `--from-start` (`--mode restart`) is Restart. `--shuffle` (`--mode shuffle`) is the shuffle link above.

## When Plex calls it finished

Play does not decide that an item is finished. PMS does, while the player reports `/:/timeline`, and Play only reads the result.

On this server, `GET /:/prefs`:

| Setting | Value | Meaning |
| --- | --- | --- |
| `LibraryVideoPlayedThreshold` | `90` | Mark played at this percent of `duration` when no earlier rule applies. Choices are 70, 75, 80, 85, 90, 95. |
| `LibraryVideoPlayedAtBehaviour` | `3` | `0` threshold only. `1` final credits marker. `2` first credits marker. `3` earliest of the threshold and the first credits marker. `3` is the default. |
| `GenerateCreditsMarkerBehavior` | `asap` | Credits markers are detected. |
| `OnDeckWindow` | `16` weeks | Continue Watching drops media not watched in this long. |

A credits marker is a `Marker` on `GET /library/metadata/{ratingKey}?includeMarkers=1` with `type="credits"` and `startTimeOffset` in milliseconds. `final="1"` is the last credits block, not the one behaviour `3` uses. Behaviour `3` uses the earliest `startTimeOffset`.

James and the Giant Peach `49423`, duration `4761840`:

- 90% is `4285656` ms.
- First credits marker starts at `4381657` ms (92%). A second, `final="1"`, starts at `4751657`.
- Played position is `min(4285656, 4381657) = 4285656`. The credits are after the threshold, so the threshold wins.
- If the first credits marker started at 82%, played position would be that marker instead, and the credits would not count as unfinished.

Crossing that position clears `viewOffset`, increments `viewCount`, and moves the show's On Deck to the next episode. Checked against the live library: the only item within 15% of its end was Tarzan `33312` at `4763493 / 5311339` (89.7%). Its played position is `4780205` (90%; credits start later, at `4944205`), so it is still On Deck. Nothing in Continue Watching or the movie libraries was stored past its played position.

On Deck is the show's resume point, not "any episode with a `viewOffset`". The Joy of Painting `39818` has S1E2 Mt. McKinley `39821` at `viewCount=2` and `viewOffset=107903`, and On Deck is S1E3 Ebony Sunset `39822` at `viewOffset=112861`. Show resume follows Ebony Sunset. A movie has no On Deck child; its own `viewOffset` is the resume point, including a rewatch (`viewCount` set and `viewOffset` still set, as with Dune `36472`).

`jplex` does not recompute the 90% or credits rule. Resume reads the `viewOffset` and On Deck that PMS has already updated. That is how Play skips the credits.

### Random episode

`shuffle=1` on the show URI. A playlist is not required. Final Space with `shuffle=1` and `offset=0` played S1E7 Chapter Seven `39090`, not S1E1. PMS confirmed the same flag: three shuffled Final Space queues each started on a different episode (`playQueueShuffled=1`).

```
export MACHINE_ID="<plex-server-id>"
adb -s 192.168.1.126:5555 shell "am start -a android.intent.action.VIEW -d 'https://watch.plex.tv/watch/video?uri=server%3A%2F%2F${MACHINE_ID}%2Fcom.plexapp.plugins.library%2Flibrary%2Fmetadata%2F39010&shuffle=1&offset=0' -n com.plexapp.android/tv.plex.app.MainActivity"
```

A playlist uses the same player and the same `shuffle` values. Its path is `/playlists/{playlistRatingKey}` (Futurama `49444`, Bob Ross `49446` in `links.json`). The playlist record's own `key` is `/playlists/{playlistRatingKey}/items`; both paths build a queue. After Back, a Futurama watch link played S10E1 Destroy Tall Monsters `28273` at 0. The first playlist item is Bender's Big Score, so this was a shuffle. Bob Ross `49446` uses the same watch link with that rating key.

Open Plex, then send the playlist. Leave any current player first.

```
export MACHINE_ID="<plex-server-id>"
adb -s 192.168.1.126:5555 shell am start -n com.plexapp.android/tv.plex.app.MainActivity && sleep 10 && adb -s 192.168.1.126:5555 shell "am start -a android.intent.action.VIEW -d 'https://watch.plex.tv/watch/video?uri=server%3A%2F%2F${MACHINE_ID}%2Fcom.plexapp.plugins.library%2Fplaylists%2F49444&shuffle=1&offset=0' -n com.plexapp.android/tv.plex.app.MainActivity"
```

`shuffle=true` is the other value the route accepts. `playbackLink` stringifies a boolean `true` into that. Other values are off.

## Rejected

- `https://app.plex.tv/desktop/#!/server/.../details?key=...` opens the app, not the movie.
- `plex://play/?metadataKey=/library/metadata/{id}&server={machineId}` matches the `plex` scheme and is ignored. This build does not use the Apple TV play link.
- `offset` on a link sent while a movie is already playing does not seek.
