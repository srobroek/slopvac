# Mutual TLS Between Two Docker Compose Services

In this tutorial you'll set up mutual TLS (mTLS) between two containers: an nginx
server and a curl-based client. You'll create your own certificate authority,
issue a certificate for each side, and then watch the handshake succeed — and
fail — so you can tell the difference.

You need Docker with Compose v2 and `openssl`. Plan on about twenty minutes.

## Step 1: Make a project directory

```bash
mkdir mtls-demo && cd mtls-demo
mkdir certs
```

Everything lives here. The `certs` directory will hold keys and certificates,
and you'll mount it into both containers later.

## Step 2: Create your own certificate authority

A CA is just a key plus a self-signed certificate that you decide to trust. Run:

```bash
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout certs/ca.key -out certs/ca.crt \
  -days 365 -subj "/CN=demo-ca"
```

`-nodes` means "no DES", i.e. don't password-protect the key — fine for a local
demo, never for production. You now have `ca.key` (the secret that signs things)
and `ca.crt` (the public certificate both sides will trust).

## Step 3: Issue a server certificate

The server's certificate must match the hostname the client dials. In Compose,
that hostname is the service name, so use `server`.

```bash
openssl req -newkey rsa:2048 -nodes \
  -keyout certs/server.key -out certs/server.csr \
  -subj "/CN=server"

openssl x509 -req -in certs/server.csr \
  -CA certs/ca.crt -CAkey certs/ca.key -CAcreateserial \
  -out certs/server.crt -days 365 \
  -extfile <(printf "subjectAltName=DNS:server")
```

That second command is the CA signing the request. The `subjectAltName` line
matters: modern TLS clients ignore `CN` for hostname checks and look only at the
SAN. Leave it out and you'll get a name-mismatch error later.

## Step 4: Issue a client certificate

This is the "mutual" half — the client proves who it is, too.

```bash
openssl req -newkey rsa:2048 -nodes \
  -keyout certs/client.key -out certs/client.csr \
  -subj "/CN=client"

openssl x509 -req -in certs/client.csr \
  -CA certs/ca.crt -CAkey certs/ca.key -CAcreateserial \
  -out certs/client.crt -days 365
```

No SAN needed here, since nobody resolves the client by hostname.

## Step 5: Configure nginx to demand a client certificate

Create `nginx.conf`:

```nginx
events {}
http {
  server {
    listen 443 ssl;
    server_name server;

    ssl_certificate     /certs/server.crt;
    ssl_certificate_key /certs/server.key;

    ssl_client_certificate /certs/ca.crt;
    ssl_verify_client on;

    location / {
      return 200 "hello $ssl_client_s_dn\n";
      add_header Content-Type text/plain;
    }
  }
}
```

Two directives do the work. `ssl_client_certificate` tells nginx which CA to
trust for clients, and `ssl_verify_client on` makes a valid client certificate
mandatory rather than optional. The response echoes the client's subject so you
can see that nginx really read the certificate.

## Step 6: Write the Compose file

Create `compose.yaml`:

```yaml
services:
  server:
    image: nginx:1.27-alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/certs:ro

  client:
    image: curlimages/curl:8.9.1
    volumes:
      - ./certs:/certs:ro
    depends_on: [server]
    entrypoint: ["sleep", "infinity"]
```

Both services mount the same `certs` directory read-only. The client sleeps so
you can exec into it and run commands by hand instead of racing a one-shot
container.

## Step 7: Start the stack

```bash
docker compose up -d
docker compose logs server
```

If nginx exited, the logs will name the offending directive or a missing file
path. Fix that before moving on — a crashed server looks identical to a TLS
failure from the client's side.

## Step 8: Verify the handshake

```bash
docker compose exec client curl -v https://server/ \
  --cacert /certs/ca.crt \
  --cert /certs/client.crt \
  --key /certs/client.key
```

You should see `hello CN=client`. In the verbose output, look for the line
confirming the negotiated TLS version and cipher, and for `Server certificate:
subject: CN=server`.

## Step 9: Prove that verification is real

A test that can't fail proves nothing. Drop the client certificate:

```bash
docker compose exec client curl -sS https://server/ --cacert /certs/ca.crt
```

nginx returns `400 No required SSL certificate was sent`. Now drop the CA
instead:

```bash
docker compose exec client curl -sS https://server/ \
  --cert /certs/client.crt --key /certs/client.key
```

curl refuses with a self-signed-certificate error, because your CA isn't in its
default trust store.

Two different failures, two different causes — that's your confirmation that
both directions of the handshake are being checked.

## Cleaning up

```bash
docker compose down
```

From here, try issuing a second client certificate from a different CA and
confirm nginx rejects it, or add `ssl_verify_depth` and an intermediate CA.
