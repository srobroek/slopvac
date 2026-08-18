# Postgres Failover Runbook

## Overview

This runbook walks you through the process of failing over a Postgres primary to its replica. It's a critical procedure that should be approached with care, but don't worry — if you follow the steps below carefully, you'll be fine.

## Before You Begin

Make sure you have:
- Admin access to both database hosts
- Access to the connection pooler configuration
- A colleague on the call if possible (highly recommended!)

## Step 1: Check Replication Lag

First, you'll want to verify that the replica is sufficiently caught up. If the lag is too high, promoting could potentially result in data loss.

```sql
SELECT now() - pg_last_xact_replay_timestamp() AS lag;
```

Generally speaking, a lag of under a few seconds is considered acceptable, though your tolerance may vary depending on your requirements.

## Step 2: Fence the Old Primary

This is arguably the most important step. You need to make absolutely sure the old primary cannot accept writes, otherwise you may end up in a split-brain scenario which is extremely difficult to recover from.

```bash
sudo systemctl stop postgresql
sudo iptables -A INPUT -p tcp --dport 5432 -j DROP
```

## Step 3: Promote the Replica

Now for the moment of truth. Promoting the replica is irreversible — once you do this, the old primary can no longer be reattached without a full rebuild.

```bash
pg_ctl promote -D /var/lib/postgresql/data
```

## Step 4: Repoint the Pooler

Update the pooler to point at the newly promoted host and reload.

```bash
vim /etc/pgbouncer/pgbouncer.ini
systemctl reload pgbouncer
```

## Step 5: Verify Writes

Finally, confirm that writes are landing:

```sql
CREATE TABLE failover_check (id int);
DROP TABLE failover_check;
```

## Wrapping Up

And that's it! You've successfully failed over. Remember to update the incident channel and consider scheduling a rebuild of the old primary when you get a chance.

If anything goes wrong, don't panic — escalate to the on-call DBA.
