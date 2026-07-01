# StoryAlbum Geo CloudBase Deployment

This project is deployed as a pure static StoryAlbum Geo page. The publish directory is `demo-site`, and the CloudBase static hosting target path is `/storyalbum-geo`.

## What Gets Deployed

- `demo-site/index.html`
- `demo-site/styles.css`
- `demo-site/app.js`
- `demo-site/data/geo_album.json`
- `demo-site/data/geo_album.js`
- Local cached photos, AMap static map image, and the local styled SVG route map under `demo-site/assets/geo_album/`

The page does not call AMap APIs in the browser. It first uses local album data and local cached assets. If the AMap static map is unavailable, the local styled route map remains available.

## GitHub Secrets

In the GitHub repository, open:

`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`

Add these secrets:

- `TCB_SECRET_ID`
- `TCB_SECRET_KEY`
- `TCB_ENV_ID`

Do not write these values into source code, HTML, JS, JSON, README, or workflow logs.

## Local Static Check

Run this before pushing:

```powershell
python scripts/check_cloudbase_static.py --site-dir demo-site
```

Expected output includes:

```text
CloudBase static deploy check passed
deploy_dir=demo-site
deploy_path=/storyalbum-geo
```

## GitHub Actions Workflow

The workflow file is:

`.github/workflows/deploy-cloudbase.yml`

It runs on:

- push to `main`
- manual `workflow_dispatch`

The workflow:

1. Checks out the repository.
2. Sets up Python and Node.js.
3. Runs `python scripts/check_cloudbase_static.py --site-dir demo-site`.
4. Verifies `TCB_SECRET_ID`, `TCB_SECRET_KEY`, and `TCB_ENV_ID`.
5. Deploys `demo-site` to `/storyalbum-geo` with CloudBase CLI.

## CloudBase Deploy Command

The CI command is:

```bash
npx --yes --package @cloudbase/cli@latest cloudbase hosting:deploy demo-site /storyalbum-geo -e "$TCB_ENV_ID" --secretId "$TCB_SECRET_ID" --secretKey "$TCB_SECRET_KEY"
```

If CloudBase CLI changes credential flags, keep the same GitHub Secrets and update only the final deploy command in the workflow.

## Access Verification

After the GitHub Action finishes, open your CloudBase static website domain and visit:

```text
https://<your-cloudbase-static-domain>/storyalbum-geo/
```

Verify the page shows:

- Photo GPS / shooting time / POI information
- Original AMap static route map
- Styled SVG route map
- Stop story cards
- Photo wall
- Local fallback route map when remote/API assets are unavailable

## Current Public Reference

Existing Vercel reference:

```text
https://storyalbum-geo.vercel.app/
```

CloudBase deployment is independent from Vercel and keeps this project as a standalone travel photo story map.
