# Rezona API Reconstruction

## Scope

This document tracks the reverse-engineering and live reconstruction of the Rezona API surface observed from the iOS app bundle and direct probing.

## Status Legend

- **Confirmed**: live-tested and verified
- **Strongly inferred**: high-confidence from app strings or adjacent verified behavior
- **Unknown**: not yet verified

---

## Base URLs

### Confirmed
- `https://api.rezona.ai`
- `https://web.rezona.ai`

### Confirmed observed supporting URLs
- `https://us.i.posthog.com`
- `https://storage.googleapis.com/rezona-ai-prod/...`

---

## Auth / Header Conventions

### Confirmed
Common working request headers used successfully during probing:

```bash
-H 'Accept: application/json, text/plain, */*'
-H 'Authorization: Bearer <TOKEN>'
-H 'x-os: ios'
```

### Notes
- Bearer auth appears accepted by the API endpoints tested so far.
- `x-os: ios` was included in successful requests and should be treated as part of the standard client shape.
- `User-Agent` did not appear necessary for the confirmed endpoints we tested.

---

## Transport / Network Notes

### Confirmed
Live responses from `api.rezona.ai` advertise HTTP/3 support:

```http
Alt-Svc: h3=":443"; ma=2592000,h3-29=":443"; ma=2592000
```

### Interpretation
- The server supports HTTP/3 at runtime.
- This does **not** necessarily mean the app explicitly implements HTTP/3 itself; it may still be negotiated by the system networking stack.

---

## SSL Pinning Notes

### Current assessment
- No strong static evidence of app-wide SSL pinning was found.
- Some bundled frameworks reference trust APIs.
- `AdjustSigSdk.framework` was the strongest suspicious trust-related signal, but this does not prove general API pinning.

### Confidence
- Moderate
- Dynamic interception resistance may still come from trust handling not obvious in static string inspection.

---

## Confirmed Endpoint Inventory

## Topics / Discovery

### `GET /api/v3/topic/all`
**Status:** Confirmed

#### Working request
```bash
curl 'https://api.rezona.ai/api/v3/topic/all' \
-H 'Accept: application/json, text/plain, */*' \
-H 'Authorization: Bearer <TOKEN>' \
-H 'x-os: ios'
```

#### Confirmed response shape
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "items": [
      { "id": 3, "name": "#Dopamine farming until it hits" }
    ]
  }
}
```

---

### `GET /api/v3/topic/detail`
**Status:** Confirmed

#### Required query parameter
- `topic_id`

#### Working request
```bash
curl 'https://api.rezona.ai/api/v3/topic/detail?topic_id=3' \
-H 'Accept: application/json, text/plain, */*' \
-H 'Authorization: Bearer <TOKEN>' \
-H 'x-os: ios'
```

#### Confirmed validation behavior
Using `id=3` instead of `topic_id=3` returns:

```text
field "topic_id" is not set
```

#### Confirmed response shape
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "id": 3,
    "name": "#Dopamine farming until it hits",
    "description": "😎 Hit that score loop like it’s serotonin-pressing zen",
    "game_count": 21,
    "played_count": 12225,
    "remixed_count": 32
  }
}
```

---

### `GET /api/v3/game/get_by_topic`
**Status:** Confirmed

#### Required query parameter
- `topic_id`

#### Working request
```bash
curl 'https://api.rezona.ai/api/v3/game/get_by_topic?topic_id=3' \
-H 'Accept: application/json, text/plain, */*' \
-H 'Authorization: Bearer <TOKEN>' \
-H 'x-os: ios'
```

#### Confirmed response shape
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "page": 1,
    "pages": 2,
    "size": 20,
    "total": 21,
    "items": [
      {
        "game_id": 42381,
        "game_version": 86643,
        "name": "simpsons hide and seek",
        "description": "",
        "cover_url": "https://storage.googleapis.com/...",
        "dynamic_cover_url": "",
        "screen_orientation": "portrait",
        "is_public": true,
        "stats": {
          "played_count": 4827,
          "liked_count": 15,
          "shared_count": 5,
          "comment_count": 16
        },
        "creator": {
          "id": 15873,
          "name": "CARLOGIAN GAPOY",
          "avatar": "https://...",
          "follow_status": "none"
        },
        "url": "https://storage.googleapis.com/.../index.html",
        "topic": {
          "id": 3,
          "name": "#Dopamine farming until it hits"
        },
        "created_at": 1767428126,
        "updated_at": 1773826799,
        "is_liked": false,
        "remixable": true,
        "remixed_games": 2
      }
    ]
  }
}
```

#### Important note
This endpoint leaks actual playable content URLs through the `url` field, including:
- direct GCS-hosted HTML
- `web.rezona.ai/bridge?...` wrapper URLs for some items

---

## Explore Theme Endpoints

### `GET /api/v3/game/explore-theme/list`
**Status:** Confirmed

#### Working request
```bash
curl 'https://api.rezona.ai/api/v3/game/explore-theme/list' \
-H 'Accept: application/json, text/plain, */*' \
-H 'Authorization: Bearer <TOKEN>' \
-H 'x-os: ios'
```

#### Confirmed response shape
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "items": [
      { "name": "Brainrot" },
      { "name": "Casual" },
      { "name": "67 Energy" },
      { "name": "Meme" },
      { "name": "NPC Core" },
      { "name": "Satisfying" },
      { "name": "TikTok Viral" }
    ]
  }
}
```

---

### `GET /api/v3/game/explore-theme/games`
**Status:** Confirmed

#### Required query parameter
- `name`

#### Confirmed validation behavior
Using `topic_id=3` returns:

```text
field "name" is not set
```

#### Working requests
```bash
curl 'https://api.rezona.ai/api/v3/game/explore-theme/games?name=Brainrot' \
-H 'Accept: application/json, text/plain, */*' \
-H 'Authorization: Bearer <TOKEN>' \
-H 'x-os: ios'
```

```bash
curl 'https://api.rezona.ai/api/v3/game/explore-theme/games?name=TikTok%20Viral' \
-H 'Accept: application/json, text/plain, */*' \
-H 'Authorization: Bearer <TOKEN>' \
-H 'x-os: ios'
```

#### Confirmed response shape
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "items": [],
    "next_cursor": "",
    "has_more": false
  }
}
```

#### Pagination model
- This endpoint is **cursor-based**, not page-based.
- Relevant fields:
  - `next_cursor`
  - `has_more`

---

## Search

### `GET /api/v3/search`
**Status:** Confirmed

#### Required query parameter
- `type`

#### Confirmed validation behavior
Calling without `type` returns:

```text
field "type" is not set
```

#### Confirmed valid enum options for `type`
Server leaked the full allowed set:

```text
[user game audio bgm sfx image meme video]
```

#### Confirmed text search parameter
- `q`

#### Confirmed non-working / ignored alternatives
These did **not** produce populated search results during probing:
- `keyword`
- `query`
- `name`
- `search`
- `text`
- `title`

#### Confirmed working request
```bash
curl 'https://api.rezona.ai/api/v3/search?type=game&q=minecraft' \
-H 'Accept: application/json, text/plain, */*' \
-H 'Authorization: Bearer <TOKEN>' \
-H 'x-os: ios'
```

#### Confirmed response shape
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "page": 1,
    "pages": 10,
    "size": 20,
    "total": 200,
    "items": [
      {
        "type": "game",
        "game": {
          "game_id": 310748,
          "game_version": 614811,
          "name": "minecraft",
          "description": "",
          "cover_url": "https://storage.googleapis.com/...",
          "dynamic_cover_url": "",
          "screen_orientation": "portrait",
          "is_public": true,
          "stats": {
            "played_count": 45833,
            "liked_count": 598,
            "shared_count": 119,
            "comment_count": 418
          },
          "creator": {
            "id": 115455,
            "name": "KLN_ZKN",
            "avatar": "https://storage.googleapis.com/...",
            "follow_status": "none"
          },
          "url": "https://storage.googleapis.com/rezona-ai-prod/minigame/92fa921e-1df7-47a0-9f45-36dc0706f907/index.html",
          "topic": {
            "id": 0,
            "name": ""
          },
          "created_at": 1768091437,
          "updated_at": 1768092183,
          "is_liked": false,
          "remixable": true,
          "remixed_games": 71,
          "exact_match": true
        }
      }
    ]
  }
}
```

#### Pagination model
Search is **page-based**.

Confirmed pagination fields:
- `page`
- `pages`
- `size`
- `total`

#### Best reconstructed shape
```http
GET /api/v3/search?type=<user|game|audio|bgm|sfx|image|meme|video>&q=<term>
```

#### Confirmed pagination parameters
- `page`
- `size`

#### Verified working requests
```bash
curl 'https://api.rezona.ai/api/v3/search?type=game&q=minecraft&page=2' ...
curl 'https://api.rezona.ai/api/v3/search?type=game&q=minecraft&page=1&size=5' ...
```

#### Observed behavior
- `page=2` returned a different result slice and `page: 2`
- `size=5` changed the response to:
  - `size: 5`
  - `pages: 40`
  - `items.length: 5`

---

## Other Endpoint Inventory from Static Strings

These endpoints were recovered from the app bundle but are not all live-verified yet.

### User / Auth
- `/api/v3/user/login`
- `/api/v3/user/login_as_tourist`
- `/api/v3/user/logout`
- `/api/v3/user/stats`
- `/api/v3/user/update-registration-token`
- `/api/v3/user/event`
- `/api/v3/user/delete`

### Game
- `/api/v3/game/detail`
- `/api/v3/game/status`
- `/api/v3/game/generate`
- `/api/v3/game/publish`
- `/api/v3/game/preview`
- `/api/v3/game/get_by_topic`
- `/api/v3/game/creation-templates`
- `/api/v3/game/explore-theme/list`
- `/api/v3/game/explore-theme/games`
- `/api/v3/game/update_version_file`
- `/api/v3/game/drafts/delete`
- `/api/v3/game/remixed`

---

## Additional Verified Game Endpoints

### `GET /api/v3/game/detail`
**Status:** Confirmed

#### What worked
```bash
curl 'https://api.rezona.ai/api/v3/game/detail?game_id=6190648' \
-H 'Accept: application/json, text/plain, */*' \
-H 'Authorization: Bearer <TOKEN>' \
-H 'x-os: ios'
```

```bash
curl 'https://api.rezona.ai/api/v3/game/detail?game_id=6190648&game_version=13475911' \
-H 'Accept: application/json, text/plain, */*' \
-H 'Authorization: Bearer <TOKEN>' \
-H 'x-os: ios'
```

#### What did not work
```bash
curl 'https://api.rezona.ai/api/v3/game/detail?id=6190648' ...
curl 'https://api.rezona.ai/api/v3/game/detail?game_version=13475911' ...
curl 'https://api.rezona.ai/api/v3/game/detail?version_id=13475911' ...
```

These failed with:
```text
field "game_id" is not set
```

#### Confirmed request behavior
- `game_id` is required
- `game_version` is optional or ignored when `game_id` is sufficient

#### Confirmed response shape
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "game_id": 6190648,
    "game_version": 13475911,
    "name": "Whisker Quest",
    "description": "",
    "cover_url": "https://storage.googleapis.com/rezona-ai-prod/games/cover-default/fallback-pixel-meme_003.webp",
    "dynamic_cover_url": "",
    "screen_orientation": "portrait",
    "is_public": true,
    "stats": {
      "played_count": 0,
      "liked_count": 0,
      "shared_count": 0,
      "comment_count": 0
    },
    "creator": {
      "id": 8361332,
      "name": "Warm Rezonian 91282",
      "avatar": "https://storage.googleapis.com/rezona-ai-prod/user/avatar/Mummy.webp",
      "follow_status": "none"
    },
    "url": "https://storage.googleapis.com/rezona-ai-prod/agent-jobs/dist/6190648/13475911/index.html",
    "topic": {
      "id": 0,
      "name": ""
    },
    "created_at": 1776231432,
    "updated_at": 1776231444,
    "is_liked": false,
    "remixable": true,
    "remixed_games": 0
  }
}
```

#### Conclusion
- `game/detail` is the canonical single-game metadata fetch.
- It is keyed by `game_id`.

---

### `GET /api/v3/game/creation-templates`
**Status:** Confirmed

#### What worked
```bash
curl 'https://api.rezona.ai/api/v3/game/creation-templates' ...
curl 'https://api.rezona.ai/api/v3/game/creation-templates?lang=en' ...
curl 'https://api.rezona.ai/api/v3/game/creation-templates?mode=advance' ...
```

#### What did not fail
- no tested variants failed so far

#### Confirmed response shape
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "items": [
      {
        "display_image": "https://storage.googleapis.com/...",
        "name": "Bald Androgenic",
        "user_input": "Create a game based on ...",
        "assets": [
          {
            "type": "meme",
            "url": "https://storage.googleapis.com/...",
            "usage": "meme"
          }
        ]
      }
    ]
  }
}
```

#### Current interpretation
- returns preset creation prompts/templates
- includes attached assets
- `lang` and `mode` appear accepted, though they did not change the payload in the tested responses

#### Conclusion
- likely used to power generation presets in the UI before `game/generate`

---

## Additional Verified Notification Endpoints

### `GET /api/v3/notification/list`
**Status:** Confirmed

#### What worked
```bash
curl 'https://api.rezona.ai/api/v3/notification/list' \
-H 'Accept: application/json, text/plain, */*' \
-H 'Authorization: Bearer <TOKEN>' \
-H 'x-os: ios'
```

#### Confirmed response shape
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "items": [
      {
        "id": 111506832,
        "notification_type": "game_played_count",
        "sender_user_id": 51283,
        "sender_user_name": "Laser Lemonade",
        "sender_user_avatar": "https://storage.googleapis.com/...",
        "follow_status": "none",
        "entity_id": 5501393,
        "entity_type": "game",
        "entity_info": {
          "game_id": 5501393,
          "game_version": 11874206,
          "name": "NEW GAME",
          "cover_url": "https://storage.googleapis.com/...",
          "screen_orientation": "portrait",
          "is_public": true,
          "creator": {
            "id": 8361332,
            "name": "Warm Rezonian 91282",
            "avatar": "https://storage.googleapis.com/..."
          }
        },
        "target_type": "",
        "content": "",
        "message": "Laser Lemonade played your game!",
        "created_at": 1776223716,
        "read_at": 0
      }
    ],
    "next_cursor": "1775872356945658000:108213303",
    "has_more": true
  }
}
```

#### Pagination model
- cursor-based
- uses:
  - `next_cursor`
  - `has_more`

#### Conclusion
- notification list is a feed endpoint, not page-based

### `GET /api/v3/notification/list?cursor=<next_cursor>`
**Status:** Confirmed

#### What worked
```bash
curl 'https://api.rezona.ai/api/v3/notification/list?cursor=1775872356945658000:108213303' \
-H 'Accept: application/json, text/plain, */*' \
-H 'Authorization: Bearer <TOKEN>' \
-H 'x-os: ios'
```

#### Confirmed behavior
- returned the next page of older notifications
- returned a new `next_cursor`
- `has_more` remained `true`

#### Conclusion
- `next_cursor` values are opaque
- cursor values should be replayed exactly as returned by the previous response

### `GET /api/v3/notification/unread/count`
**Status:** Confirmed

#### What worked
```bash
curl 'https://api.rezona.ai/api/v3/notification/unread/count' \
-H 'Accept: application/json, text/plain, */*' \
-H 'Authorization: Bearer <TOKEN>' \
-H 'x-os: ios'
```

#### Confirmed response shape
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "count": 55
  }
}
```

#### Conclusion
- helper endpoint for unread badge/count
- auth-required

---

### `POST /api/v3/notification/read/all`
**Status:** Confirmed

#### What worked
```bash
curl 'https://api.rezona.ai/api/v3/notification/read/all' \
-X POST \
-H 'Accept: application/json, text/plain, */*' \
-H 'Content-Type: application/json' \
-H 'Authorization: Bearer <TOKEN>' \
-H 'x-os: ios' \
--data-raw '{}'
```

#### Confirmed response
```json
{
  "code": 0,
  "msg": "success"
}
```

#### Conclusion
- bulk mark-as-read endpoint
- empty JSON body is sufficient
- auth-required

### Comment
- `/api/v3/comment/detail`
- `/api/v3/comment/replies`
- `/api/v3/comment/vote`
- `/api/v3/comment/mention-candidates`

### Notification
- `/api/v3/notification/list`
- `/api/v3/notification/unread/count`
- `/api/v3/notification/read/all`

### Topic / Discovery
- `/api/v3/topic/all`
- `/api/v3/topic/detail`
- `/api/v3/search`

### Follow
- `/api/v3/follow/followers`
- `/api/v3/follow/unread_count`

### Assets / Reporting
- `/api/v3/asset/page`
- `/api/v3/report/create`

---

## Additional Verified Asset Endpoints

### `GET /api/v3/asset/page`
**Status:** Confirmed

#### What worked
```bash
curl 'https://api.rezona.ai/api/v3/asset/page' ...
curl 'https://api.rezona.ai/api/v3/asset/page?page=1&size=20' ...
curl 'https://api.rezona.ai/api/v3/asset/page?type=image&page=1&size=5' ...
```

#### Confirmed response shape
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "page": 1,
    "pages": 56,
    "size": 20,
    "total": 1103,
    "items": [
      {
        "id": 7669,
        "name": "TuffPigeon_pigeon_avatar",
        "usage": "",
        "type": "image",
        "use_count": 0,
        "url": "https://storage.googleapis.com/rezona-ai-prod/games/assets/image/0006/TuffPigeon/pigeon_avatar.png"
      }
    ]
  }
}
```

#### Confirmed request behavior
- no params works
- `page` is accepted
- `size` is accepted
- `type` is accepted

#### Confirmed filter examples
```http
GET /api/v3/asset/page?type=image&page=1&size=5
GET /api/v3/asset/page?type=audio&page=1&size=1
GET /api/v3/asset/page?type=bgm&page=1&size=3
GET /api/v3/asset/page?type=sfx&page=1&size=3
GET /api/v3/asset/page?type=video&page=1&size=3
GET /api/v3/asset/page?type=meme&page=1&size=3
```

#### Additional confirmed type behavior
- `type=image` returns image assets
- `type=bgm` returns background music assets
- `type=sfx` returns sound effect assets
- `type=video` returns video assets and includes `cover_url`
- `type=meme` returns meme/gif-style assets
- `type=audio` works, but returns audio-family assets whose item `type` may still be `sfx`

#### Conclusion
- `asset/page` is page-based
- confirmed accepted filters:
  - `type=image`
  - `type=audio`
  - `type=bgm`
  - `type=sfx`
  - `type=video`
  - `type=meme`
- `audio` appears to behave as a broad umbrella category, while `bgm` and `sfx` are narrower subtypes

---

## Additional Verified Comment / User Endpoints

### `GET /api/v3/comment/detail`
**Status:** Partially confirmed

#### What did not work
```bash
curl 'https://api.rezona.ai/api/v3/comment/detail' ...
```

#### Validation leak
```text
field "comment_id" is not set
```

#### Current conclusion
- `comment_id` is required

---

### `GET /api/v3/comment/replies`
**Status:** Partially confirmed

#### What did not work
```bash
curl 'https://api.rezona.ai/api/v3/comment/replies' ...
```

#### Validation leak
```text
field "root_id" is not set
```

#### Current conclusion
- `root_id` is required

---

### `GET /api/v3/comment/mention-candidates`
**Status:** Confirmed

#### What worked
```bash
curl 'https://api.rezona.ai/api/v3/comment/mention-candidates' \
-H 'Accept: application/json, text/plain, */*' \
-H 'Authorization: Bearer <TOKEN>' \
-H 'x-os: ios'
```

#### Confirmed response shape
```json
{
  "code": 0,
  "msg": "success",
  "data": [
    {
      "id": 51143,
      "name": "Indigo Impulse",
      "avatar": "https://storage.googleapis.com/rezona-ai-dev/user/avatar/16.webp",
      "i_follow": false,
      "follow_me": true
    }
  ]
}
```

---

### `POST /api/v3/user/login_as_tourist`
**Status:** Confirmed

#### What did not work
1. no body
   - HTTP `411 Length Required`
2. body:
```json
{"platform":"ios"}
```
   returned:
```text
field "device_id" is not set
```

#### What worked
```bash
curl 'https://api.rezona.ai/api/v3/user/login_as_tourist' \
-X POST \
-H 'Accept: application/json, text/plain, */*' \
-H 'Content-Type: application/json' \
-H 'Authorization: Bearer <TOKEN>' \
-H 'x-os: ios' \
--data-raw '{"device_id":"test-device-id","platform":"ios"}'
```

#### Confirmed response shape
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "access_token": "<jwt>",
    "access_exp_at": "2026-04-30T05:50:47Z",
    "refresh_token": "<jwt>",
    "refresh_exp_at": "2026-04-30T05:50:47Z",
    "user_id": 10450354,
    "username": "Tourist_Sw4IL",
    "avatar": "https://storage.googleapis.com/rezona-ai-prod/user/avatar/King.webp"
  }
}
```

#### Confirmed required fields
- `device_id`
- `platform`

---

### `POST /api/v3/game/publish`
**Status:** Confirmed

#### What did not work
Body:
```json
{
  "game_id": 6190648,
  "game_version": 13475911,
  "name": "Whisker Quest",
  "description": ""
}
```

Returned:
```text
field "is_public" is not set
```

#### What worked
```bash
curl 'https://api.rezona.ai/api/v3/game/publish' \
-X POST \
-H 'Accept: application/json, text/plain, */*' \
-H 'Content-Type: application/json' \
-H 'Authorization: Bearer <TOKEN>' \
-H 'x-os: ios' \
--data-raw '{"game_id":6190648,"game_version":13475911,"name":"Whisker Quest","description":"","is_public":true}'
```

#### Confirmed required fields
- `game_id`
- `game_version`
- `name`
- `description`
- `is_public`

#### Confirmed response behavior
- returns the same rich game object shape as `game/detail`

## WebView / Content URL Findings

### Strongest WebView candidates
- `https://web.rezona.ai/create`
- `https://web.rezona.ai/share/game/`

### Related findings
Returned content URLs sometimes use direct HTML files:
- `https://storage.googleapis.com/rezona-ai-prod/minigame/<uuid>/index.html`

Other items use bridge wrappers:
- `https://web.rezona.ai/bridge?src=...&mask=...`

This suggests the app may load:
- raw game HTML directly
- or wrapped content through a Rezona bridge page depending on content type / overlay requirements

---

## Static Reverse-Engineering Notes

### App-level networking clues
- Flutter app likely uses **Dio**
- Evidence:
  - `ApiException.fromDioException`
- App appears to use the normal iOS HTTPS stack under Flutter

### WebView-related clues
- `webview_flutter_wkwebview`
- `WKWebView`
- `LoadRequestParams`
- `active_webview`
- `openUrlInSafariViewController`

---

## Legacy Web vs V3 Endpoint Comparison

### Overview
We compared the legacy web routes under `https://web.rezona.ai/game/...` with the reconstructed v3 routes under `https://api.rezona.ai/api/v3/game/...`.

### `generate`
**Legacy**
- `POST /game/generate`

**V3**
- `POST /api/v3/game/generate`

**Status:** Confirmed for both

#### Shared request body
```json
{
  "prompt": "cat",
  "mode": "advance",
  "features": {}
}
```

#### Legacy response
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "game_id": 6190646,
    "game_version": 13475909,
    "assistant_msg": "Begin Generate Game"
  }
}
```

#### V3 response
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "game_id": 6190648,
    "game_version": 13475911,
    "assistant_msg": "Begin Generate Game"
  }
}
```

#### Conclusion
- The request shape is the same.
- The response shape is the same.
- Legacy and v3 both work.
- They appear to trigger separate generation jobs rather than returning the exact same IDs.

---

### `preview`
**Legacy**
- `GET /game/preview?game_id=...&game_version=...`

**V3**
- `GET /api/v3/game/preview?game_id=...&game_version=...`

**Status:** Confirmed for both

#### Legacy response
```json
{
  "code": 0,
  "msg": "success",
  "data": "https://storage.googleapis.com/rezona-ai-prod/agent-jobs/dist/5389918/11595618/index.html"
}
```

#### V3 response
```json
{
  "code": 0,
  "msg": "success",
  "data": "https://storage.googleapis.com/rezona-ai-prod/agent-jobs/dist/5389918/11595618/index.html"
}
```

#### Conclusion
- The request shape is the same.
- The response shape is the same.
- Legacy and v3 preview appear functionally equivalent for the tested pair.

---

### `status`
**Legacy**
- `GET /game/status?game_id=...&game_version=...`

**V3**
- `GET /api/v3/game/status?game_id=...&game_version=...`

**Status:** Confirmed for both

#### Working request shape
- query parameters:
  - `game_id`
  - `game_version`

#### Legacy response
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "game_id": 6190648,
    "game_version": 13475911,
    "status": "generating",
    "assistant_msg": "We're polishing sound and feedback so every action feels satisfying."
  }
}
```

#### V3 response
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "game_id": 6190648,
    "game_version": 13475911,
    "status": "generating",
    "assistant_msg": "We're polishing sound and feedback so every action feels satisfying."
  }
}
```

#### Conclusion
- The request shape is the same.
- The response shape is the same.
- Legacy and v3 status are functionally equivalent for the tested pair.

---

### Current comparison summary

| Legacy route | V3 route | Works | Same shape |
|---|---|---:|---:|
| `/game/generate` | `/api/v3/game/generate` | Yes | Yes |
| `/game/preview` | `/api/v3/game/preview` | Yes | Yes |
| `/game/status` | `/api/v3/game/status` | Yes | Yes |

---

## Auth Sensitivity Snapshot

### Confirmed works without bearer auth
- `GET /api/v3/topic/all`
- `GET /api/v3/search?type=game&q=minecraft&page=1&size=3`
- `GET /api/v3/asset/page?type=image&page=1&size=3`

### Confirmed auth-required or auth-coupled
- `GET /api/v3/notification/list`
- `GET /api/v3/notification/unread/count`
- `POST /api/v3/notification/read/all`
- `POST /api/v3/user/login_as_tourist`
- `POST /api/v3/game/publish`
- game generation flow was probed with auth and should still be treated as auth-coupled until proven otherwise

---

## Open Questions

### High-priority next probes
1. Probe `comment/detail` with a real `comment_id`
2. Probe `comment/replies` with a real `root_id`
3. Determine auth sensitivity of additional endpoints:
   - `topic/detail`
   - `game/get_by_topic`
   - `game/detail`
   - `game/creation-templates`
4. Determine whether any endpoints use POST with JSON bodies beyond the obvious auth/generation flows

---

## Reproduction Notes

Use this general header template for probing:

```bash
-H 'Accept: application/json, text/plain, */*' \
-H 'Authorization: Bearer <TOKEN>' \
-H 'x-os: ios'
```

Example search request:

```bash
curl 'https://api.rezona.ai/api/v3/search?type=game&q=minecraft' \
-H 'Accept: application/json, text/plain, */*' \
-H 'Authorization: Bearer <TOKEN>' \
-H 'x-os: ios'
```

Example topic detail request:

```bash
curl 'https://api.rezona.ai/api/v3/topic/detail?topic_id=3' \
-H 'Accept: application/json, text/plain, */*' \
-H 'Authorization: Bearer <TOKEN>' \
-H 'x-os: ios'
```

Example games-by-topic request:

```bash
curl 'https://api.rezona.ai/api/v3/game/get_by_topic?topic_id=3' \
-H 'Accept: application/json, text/plain, */*' \
-H 'Authorization: Bearer <TOKEN>' \
-H 'x-os: ios'
```

---

## Progress Summary

### Confirmed live
- topic/discovery endpoint family
- explore-theme endpoint family
- search `type` enum and `q` parameter
- search uses page-based response metadata
- search `page` and `size` parameters are confirmed
- server advertises HTTP/3
- direct playable game URLs are exposed through API responses
- legacy/v3 generation flow equivalence for generate, preview, status
- `game/detail` keyed by `game_id`
- `game/creation-templates` returns template items with attached assets
- `notification/list` uses cursor pagination
- `notification/list?cursor=...` is confirmed
- `notification/unread/count` is confirmed
- `notification/read/all` is confirmed
- `asset/page` is page-based and accepts `page`, `size`, and `type`
- additional asset type filters confirmed: `audio`, `bgm`, `sfx`, `video`, `meme`
- `comment/detail` leaks required `comment_id`
- `comment/replies` leaks required `root_id`
- `comment/mention-candidates` works with no params
- `user/login_as_tourist` is confirmed with `device_id` + `platform`
- `game/publish` is confirmed with `game_id`, `game_version`, `name`, `description`, and `is_public`
- `topic/all`, `search`, and `asset/page` are confirmed to work without bearer auth

### Still in progress
- obtaining a real `comment_id` / `root_id`
- auth sensitivity of the rest of the endpoint families
