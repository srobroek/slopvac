# Runbook: fail Postgres over to the replica

Promoting the replica cannot be undone. After step 4 the old primary can never rejoin as a primary; you rebuild it from a base backup.

Read the whole runbook before you run anything. Expect 10 to 15 minutes of write downtime.

## When to run this

Run this when the primary `db-primary-1` is unreachable or unrecoverable, or when a maintainer asks for a planned failover.

Do not run this when the primary is reachable and only slow. A promotion on a live primary gives you two primaries accepting writes.

## Before you start

- Open a second terminal. You need `db-primary-1`, `db-replica-1`, and `pgbouncer-1` at the same time.
- Post in `#incident` that you are starting a failover on `db-primary-1`.
- Confirm you can `sudo -u postgres psql` on `db-replica-1`.

If any check below fails and this runbook does not say what to do, stop and page the database owner (`@db-oncall` in PagerDuty).

## Step 1. Check replication lag

On `db-replica-1`:

```bash
sudo -u postgres psql -Atc "
  SELECT pg_last_wal_receive_lsn(),
         pg_last_wal_replay_lsn(),
         EXTRACT(EPOCH FROM now() - pg_last_xact_replay_timestamp()) AS lag_seconds;"
```

Read `lag_seconds`:

- Under 5 seconds: continue to step 2.
- 5 to 60 seconds: wait 60 seconds and run the query again. Continue when it drops under 5.
- Over 60 seconds, or the value keeps rising: stop and page `@db-oncall`. Promoting now loses every transaction the replica has not replayed.
- `NULL` with the primary down: the replica has replayed everything it received. Continue to step 2.

Record the two LSN values in the incident channel. You need them to state the data loss window afterwards.

## Step 2. Fence the old primary

Fencing stops the old primary from accepting writes. Skipping it gives you split-brain: two servers accepting writes, with no automatic way to merge them.

On `pgbouncer-1`, block client traffic to the old primary:

```bash
sudo -u postgres psql -p 6432 -U pgbouncer -c "PAUSE app_db;"
```

Then on `db-primary-1`, stop Postgres:

```bash
sudo systemctl stop postgresql@16-main
sudo systemctl mask postgresql@16-main
```

`mask` stops a reboot from restarting the old primary.

If `db-primary-1` does not respond to SSH, fence it at the infrastructure layer instead. Detach its network interface or stop the instance in the cloud console. Do not continue until the host is confirmed down or detached; a host that answers on its data port is not fenced.

Verify the fence from any application host:

```bash
psql "host=db-primary-1 port=5432 dbname=app_db connect_timeout=3" -c "SELECT 1"
```

Expect a connection refused or a timeout. A successful `SELECT 1` means the host is not fenced. Return to the start of this step.

## Step 3. Confirm the replica is a replica

On `db-replica-1`:

```bash
sudo -u postgres psql -Atc "SELECT pg_is_in_recovery();"
```

`t` means it is still a standby; continue to step 4. `f` means it was already promoted; skip to step 5.

## Step 4. Promote the replica

This is the destructive step. The promotion writes a new timeline; `db-primary-1` can no longer stream from or to `db-replica-1`.

State in `#incident` that you are promoting, then run on `db-replica-1`:

```bash
sudo -u postgres pg_ctl promote -D /var/lib/postgresql/16/main
```

Wait for recovery to end:

```bash
sudo -u postgres psql -Atc "SELECT pg_is_in_recovery();"
```

Expect `f` within 30 seconds. If it still returns `t` after 60 seconds, read the log and page `@db-oncall`:

```bash
sudo tail -n 50 /var/log/postgresql/postgresql-16-main.log
```

## Step 5. Repoint the connection pooler

On `pgbouncer-1`, edit the database line in `/etc/pgbouncer/pgbouncer.ini`:

```ini
[databases]
app_db = host=db-replica-1 port=5432 dbname=app_db
```

Reload and resume:

```bash
sudo pgbouncer -R -d /etc/pgbouncer/pgbouncer.ini
sudo -u postgres psql -p 6432 -U pgbouncer -c "RESUME app_db;"
```

Confirm the pooler points at the new host:

```bash
sudo -u postgres psql -p 6432 -U pgbouncer -c "SHOW databases;" | grep app_db
```

The `host` column must read `db-replica-1`.

## Step 6. Verify writes

Through the pooler, on any application host:

```bash
psql "host=pgbouncer-1 port=6432 dbname=app_db" -c "
  CREATE TABLE IF NOT EXISTS failover_check (at timestamptz);
  INSERT INTO failover_check VALUES (now()) RETURNING at;"
```

A returned timestamp means writes work. `ERROR: cannot execute INSERT in a read-only transaction` means the pooler still points at a standby; return to step 5.

Then check the application:

```bash
curl -fsS https://app.example.com/healthz
```

Expect `{"db":"ok"}`. Watch the application error rate for 5 minutes in Grafana, dashboard `app-overview`.

Drop the marker table when you are done:

```bash
psql "host=pgbouncer-1 port=6432 dbname=app_db" -c "DROP TABLE failover_check;"
```

## Step 7. Close out

- Post in `#incident`: the promotion time, the LSN values from step 1, and the write downtime.
- Update the PagerDuty incident with a link to this runbook.
- File a ticket to rebuild `db-primary-1` as a standby of `db-replica-1` with `pg_basebackup`. Do not unmask its service unit until that ticket is worked.
- Update monitoring so `db-replica-1` is alerted as the primary.

## Rollback

There is no rollback after step 4. To return service to `db-primary-1`, rebuild it as a standby of `db-replica-1`, then run this runbook again in the other direction.
