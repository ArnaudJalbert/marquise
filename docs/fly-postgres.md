# Private catalog database on Fly

Issue [#341](https://github.com/ArnaudJalbert/marquise/issues/341) prepares an
empty catalog with the schema merged in PR #330. Import jobs are covered by
[#342](https://github.com/ArnaudJalbert/marquise/issues/342), and import review
and API cutover by [#343](https://github.com/ArnaudJalbert/marquise/issues/343).
The API, nightly imports, and Supabase Auth still use their existing configuration.

## Resources and cost

[deploy/postgres/fly.toml](../deploy/postgres/fly.toml) runs the official PostgreSQL
17.11 image, pinned by digest. It is an ordinary self-managed Machine, without
Fly Managed Postgres or a replication manager.

- App `marquise-db`, organization `personal`, region `yyz`, matching `marquise-api`.
- One shared CPU, 512 MB RAM, 30 database connections maximum. Fly stops the
  Machine after idle time and starts it when a connection arrives.
- One encrypted 1 GB `pg_data` volume mounted at `/data`. PostgreSQL files live
  in `/data/pgdata`, including across Machine restarts.
- Private Flycast hostname `marquise-db.flycast:5432` routes PostgreSQL through
  Fly Proxy on a private IPv6 address, with no public IP. Same-organization
  network access and SCRAM password authentication are required. Fly's WireGuard
  network encrypts traffic; PostgreSQL itself does not terminate TLS in this setup.

Estimated recurring cost, checked October 30, 2026, is approximately **USD 4.30
per 30 days**, excluding taxes, existing services, and operator time. The public
[pricing calculator](https://fly.io/pricing/) gives a Toronto multiplier of
1.115384615 over the base CPU/RAM rates. One shared CPU with 512 MB is about
$4.12, plus $0.15 for the 1 GB volume. Same-region private traffic is free.
Rates and billing-month length can change the bill. See
[resource pricing](https://fly.io/docs/about/pricing/).

## Fresh setup

From the repository root, with authenticated `flyctl` and `uv sync` completed:

```bash
flyctl config validate --strict --config deploy/postgres/fly.toml
flyctl apps create marquise-db --org personal --yes
flyctl volumes create pg_data --app marquise-db --region yyz --size 1 \
  --vm-size shared-cpu-1x --vm-memory 512 --scheduled-snapshots=false --yes
```

Generate credentials directly into Fly's encrypted secret storage. This does not
write the password to disk, shell arguments, or terminal output:

```bash
uv run python - <<'PY'
import secrets
import subprocess

password = secrets.token_urlsafe(36)
result = subprocess.run(
    ['flyctl', 'secrets', 'import', '--app', 'marquise-db', '--stage'],
    input=(f'POSTGRES_PASSWORD={password}\n'
           f'DATABASE_URL=postgresql://marquise:{password}'
           '@marquise-db.flycast:5432/marquise\n'),
    text=True, capture_output=True,
)
if result.returncode:
    raise SystemExit('Secret import failed; credential-bearing output suppressed')
PY
flyctl ips allocate-v6 --private --app marquise-db
flyctl deploy --config deploy/postgres/fly.toml --ha=false --yes
flyctl checks list --app marquise-db
flyctl ips list --app marquise-db
```

The PostgreSQL service enables autostop, autostart, and zero minimum Machines.
Its TCP check prevents Fly Proxy from routing connections before PostgreSQL is
ready. A new connection to `marquise-db.flycast` wakes PostgreSQL after an idle
stop. Direct `marquise-db.internal` connections bypass Fly Proxy and cannot wake
the stopped Machine. Set the API's `DATABASE_URL` host to `marquise-db.flycast`
when performing the later cutover. The API already stops and starts with HTTP
traffic.

Keep exactly one Machine and one volume. The explicit `--ha=false` prevents
creation of a spare Machine. Do not run `fly postgres attach` or replace the API's
`DATABASE_URL` during preparation. The database app's `DATABASE_URL` secret is
reserved for database operations and later import jobs. `marquise` is the trusted
database owner created by the image; these credentials must never reach clients.

`POSTGRES_PASSWORD` initializes a new data directory only. Changing this Fly
secret later does not rotate the existing database password. Coordinate an
`ALTER ROLE` password change with updates to both secrets and all consumers.
Keep using PostgreSQL 17 for an existing volume; a major-version image change
requires a PostgreSQL upgrade procedure, not a normal image deployment.

## Configuration transfer

The command [transfer_cinema_configuration.py](../scripts/transfer_cinema_configuration.py)
reads only `SOURCE_DATABASE_URL` and `TARGET_DATABASE_URL`. Supply percent-encoded
PostgreSQL URLs from secret storage. It never loads `.env` or falls back to
`DATABASE_URL`. The source schema is `marquise`.

Open a loopback-only tunnel in a separate terminal:

```bash
flyctl proxy 55432:5432 --app marquise-db --bind-addr 127.0.0.1
```

With `SOURCE_DATABASE_URL` set to the retained Supabase database, run this to
retrieve the target secret in memory, change only its host/port for the tunnel,
and invoke the transfer command:

```bash
uv run python - <<'PY'
import os
import subprocess
import sys
from urllib.parse import urlsplit, urlunsplit

result = subprocess.run(
    ['flyctl', 'ssh', 'console', '--app', 'marquise-db', '--quiet',
     '--command', 'printenv DATABASE_URL'],
    capture_output=True, text=True, timeout=30,
)
urls = [line for line in result.stdout.splitlines()
        if line.startswith('postgresql://')]
if result.returncode or len(urls) != 1:
    raise SystemExit('Cannot read database secret; output suppressed')
parts = urlsplit(urls[0])
target = urlunsplit(parts._replace(
    netloc=parts.netloc.rsplit('@', 1)[0] + '@127.0.0.1:55432'))
raise SystemExit(subprocess.run(
    [sys.executable, 'scripts/transfer_cinema_configuration.py'],
    env={**os.environ, 'TARGET_DATABASE_URL': target},
).returncode)
PY
```

The source is read in a read-only repeatable-read transaction. The destination
bootstrap, empty-table check, inserts, and verification commit in one transaction.
All five destination tables are locked through commit. Any preexisting
configuration, Movie, or Screening row causes refusal.
Successful output reports exact verified configuration counts and zero excluded
rows. Foreign keys enforce the assignments. No source writes, catalog copy,
overwrite, or deletion occur. Repeating a completed transfer fails safely.
A failed transfer rolls back; investigate the cause before retrying. Never
truncate an existing catalog to bypass the guard. Close the tunnel afterward.

## Verification receipt

On October 30, 2026, the deployed Machine `8695e4b60974e8` in `yyz` used encrypted
volume `vol_4m3dzmmj7dp262gv`, size 1 GB. Its TCP check passed and its public IP
list was empty. An authenticated connection through the private tunnel confirmed
PostgreSQL 17.11 and the merged schema, including `movies.tmdb_id`. This receipt
predates enabling Flycast autostop. The Flycast TCP health check is now passing,
and the service has autostop, autostart, and zero minimum Machines configured.
Flycast wake-on-connect and an idle stop remain to be confirmed when #343 switches
the API connection to `marquise-db.flycast`.

The transfer compared all configuration values and preserved the original IDs:

| Table | Supabase before and after | Fly after transfer |
|---|---:|---:|
| `cinemas` | 14 | 14 |
| `source_definitions` | 7 | 7 |
| `cinema_source_assignments` | 14 | 14 |
| `movies` | 73 | 0 |
| `screenings` | 294 | 0 |

There were zero dangling assignments. Comparing every row in all five source
tables before and after confirmed that Supabase was unchanged. These are setup
counts, not a live status report. No catalog ingestion or API cutover was run.

## Imports before API cutover

The scheduled GitHub Actions import continues to use the existing Supabase
`DATABASE_URL`. A manual `workflow_dispatch` run builds the production CLI image
and runs it on a temporary Machine in `yyz` under the `marquise-db` Fly app.
That Machine inherits the encrypted `DATABASE_URL` and `TMDB_API_KEY` Fly
secrets. The workflow disables PostgreSQL autostop during the import, starts
the Machine, and waits for its health checks. It restores autostop and stops
PostgreSQL afterward. A shared Actions concurrency group queues scheduled and
manual runs so they cannot write the catalog at the same time.

The manual run accepts `days`, defaulting to 7. Its CLI result is streamed to the
Actions log, and a failed cinema makes the CLI exit nonzero, failing the job.
Since `fly machine run` returns after startup and does not propagate the
container's exit status, [run_fly_import.sh](../scripts/run_fly_import.sh) waits
for the stopped state, reads the recorded exit code, prints the Machine logs,
and destroys the temporary Machine on success, failure, or timeout. The CLI
image is pushed to the private Fly registry and is not deployed as the database
app's running process.

Before using the manual trigger, configure `TMDB_API_KEY` as a Fly app secret on
`marquise-db`, and confirm `FLY_API_TOKEN` is a GitHub Actions secret. The app's
`DATABASE_URL` must remain a Fly secret pointed at the Fly catalog. The
scheduled job continues to read its GitHub `DATABASE_URL` and `TMDB_API_KEY`
secrets, so it remains on Supabase until the separately reviewed cutover in
#343.

The first Fly import and its review belong to #342. Record provider coverage
and failures, representative catalog rows, and any duplicate TMDB identities
before changing the API connection.

### First Fly import report

The first seven-day import ran on October 30, 2026. It exited 1 after importing
four of 14 assigned cinemas. It wrote 57 movies and 831 screenings. Beaubien,
Cineplex Forum et VIP, Cineplex Royalmount, and du Parc produced screenings.
Those records came from the `cinemacinema` and `cineplex` providers. The other
five configured providers had no completed cinema import in this run.

The CLI reported ten failures. One Cineplex request for Quartier Latin timed
out. Cinéma du Musée failed on a TMDB identity conflict for `Sense and
Sensibility`. The other eight failures were database connection errors after
Fly stopped PostgreSQL: Moderne had a closed connection, and Public, Starcité,
the Cinémathèque, both Ciné Starz cinemas, Scotiabank, and Théâtre Outremont
received connection refusals.

Fly Proxy's log at 18:51:29 UTC says it stopped the only PostgreSQL Machine
because the app had excess capacity. PostgreSQL received SIGINT and shut down
normally. The importer used the private `.internal` hostname, so its idle period
while fetching provider data did not keep Fly Proxy traffic active. This was an
autostop event, not a PostgreSQL crash. The database Machine is stopped again,
its encrypted 1 GB volume remains attached, and the partial catalog still has 57
movies and 831 screenings.

No duplicate `tmdb_id` values exist in the partial catalog. The existing `Sense
and Sensibility` row is year 2026 with TMDB ID `1503762`; the failed import
encountered a different TMDB identity for the same title. The incoming ID was
not included in the CLI error. Representative imported rows include `Pauline
Julien : Femme pays` (TMDB `1232113`) and `Fjord` (TMDB `1401459`) at Beaubien,
and `Fjord` at du Parc. `Le monde de Wishy` at Beaubien has no TMDB ID.

A second attempt was interrupted before any catalog changes. Counts remained
57 movies and 831 screenings. It is not a completed import and does not change
the first-run report above. Provider coverage and the TMDB conflict remain for
review in #342 before any API cutover.

Disposable PostgreSQL integration tests exercise the operator command, exact
configuration preservation, exclusion of nonempty source catalog/history,
refusal of populated destinations and replay, and rollback on an insert failure.
They bootstrap the actual SQL on a blank database and also apply the TMDB
migration twice to the previous schema while preserving a legacy Movie.
The test user needs `CREATEDB`; the tests create and drop uniquely named databases.

```bash
uv run pytest packages/marquise-core/tests/integration_tests/infrastructure/test_configuration_transfer.py -q
```

## Operations and recovery limits

Check Machine health, volume usage, and database size regularly:

```bash
flyctl status --app marquise-db
flyctl checks list --app marquise-db
flyctl volumes list --app marquise-db
flyctl ssh console --app marquise-db --command 'df -h /data'
flyctl ssh console --app marquise-db --command \
  'psql -U marquise -d marquise -c "SELECT pg_size_pretty(pg_database_size(current_database()));"'
```

One GB is the provisioned capacity, not free database space. WAL and PostgreSQL
files also consume it. Expand the volume before it fills; investigate connection
pressure or OOM events before increasing connections or importing concurrently.
The single Machine has no automatic failover and incurs downtime on restart,
deployment, host failure, or network failure. Apply minor PostgreSQL security
updates deliberately by updating the pinned digest and testing it first.

Backups are explicitly deferred. Scheduled volume snapshots are disabled for
this volume, and there is no WAL archive, PITR, replica, off-host logical dump,
or tested restore. A persistent volume survives ordinary restarts, but a lost
volume or failed host can lose the Fly catalog. See
[Fly volume limitations](https://fly.io/docs/volumes/overview/).

If only the Machine is lost, preserve the volume and secrets and redeploy against
the existing volume. Confirm it attaches to the replacement Machine in `yyz`.
Do not create a new volume or initialize a new cluster over the old data directory.
If the volume is lost, provision a replacement with the fresh-setup procedure,
reuse the stored credentials or coordinate their replacement, transfer Cinema
and source configuration from the retained Supabase database, then reimport and
review the catalog through #342/#343. Post-transfer configuration changes and
authenticated writes on Fly cannot be recovered from the retained Supabase copy.

Supabase remains intact for Auth and the old catalog. It is a fallback copy,
not a synchronized replica or backup of subsequent Fly writes. API/import
cutover and fallback secret changes belong to #343. Until that cutover, stopping
the new database does not change the serving catalog.
