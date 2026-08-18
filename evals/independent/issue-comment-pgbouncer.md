Thanks for the detailed report — the stack trace helped a lot.

So, the short version: this isn't really a regression, it's the opposite. 1.21 is the release where we *added* protocol-level prepared statement support in transaction mode, and I'm fairly sure what you're hitting is that support being half-enabled rather than absent.

Here's the background. In transaction pooling, your client gets a different server connection basically every transaction. A prepared statement lives on the server connection, so `PREPARE`/`Parse` on one backend and then `EXECUTE`/`Bind` on another and you get exactly the `prepared statement "lrupsc_1_0" does not exist` style error you pasted. That's been the case forever, and the historical advice was "turn prepared statements off in your driver."

1.21 added `max_prepared_statements`, which makes pgbouncer track named prepared statements itself and transparently re-prepare them on whatever backend your transaction lands on. Great — except **the default is 0, which means disabled.** So on upgrade you get the new code path only if you opt in. What I suspect happened on your side is that your driver noticed the new server version / capabilities and started using named statements again (some pool libraries and ORMs do feature-detect here, and a few people have reported their driver flipping behaviour after the upgrade), while pgbouncer is still configured to not track them. Worst of both worlds.

What to do:

1. Set `max_prepared_statements` in your `[pgbouncer]` section. Something like `max_prepared_statements = 200` is a reasonable start. It's a per-client-connection cap, and pgbouncer keeps an LRU, so it isn't unbounded memory. Reload and retry.
2. If you're on 1.21.0 specifically, please go to 1.21.1 or later first. There were a couple of genuine bugs in the initial implementation around `DEALLOCATE`/`DISCARD ALL` handling and statement name collisions that we fixed shortly after. Chasing this on .0 is not a good use of your afternoon.
3. Only unnamed/protocol-level statements are handled transparently regardless of the setting. If your app issues literal `PREPARE foo AS ...` SQL text, that is *not* tracked — pgbouncer only intercepts the extended query protocol messages. You'd need to keep that inside an explicit transaction, or move to session pooling for that pool.

One caveat worth knowing: `DISCARD ALL` from your app will still nuke the tracked statements, and some connection poolers send it as a reset query. Check whether yours does.

If setting `max_prepared_statements` doesn't fix it, can you reply with your full config (minus credentials), the driver plus version, and a `pgbouncer` log at `verbose = 1` covering one failing request? That'll tell me whether it's the driver or us.
