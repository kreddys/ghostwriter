# Deploying Custom PostgreSQL with pgvector on Fly.io

This guide walks through the steps to build, tag, push, and deploy a custom **PostgreSQL with pgvector** Docker image on **Fly.io**.

## Prerequisites

- **Docker** installed and running
- **Fly.io CLI** installed ([Install Fly.io CLI](https://fly.io/docs/hands-on/install-flyctl/))
- **Fly.io account** with an active app

---

## 1. Build the Docker Image

Run the following command to build your custom PostgreSQL image:

```sh
docker build -f Dockerfile.postgres -t kreddy/fly-pg-pgvector --platform "linux/amd64" .
```

- `-f Dockerfile.postgres` → Specifies the custom Dockerfile.
- `-t kreddy/fly-pg-pgvector` → Tags the built image.
- `--platform "linux/amd64"` → Ensures compatibility with Fly.io.

---

## 2. Tag the Image for Fly.io Registry

Tag the built image so it can be pushed to Fly.io’s container registry:

```sh
docker tag kreddy/fly-pg-pgvector registry.fly.io/ghostwriter-postgres:latest
```

- `registry.fly.io/ghostwriter-postgres:latest` → Uses the Fly.io app name (`ghostwriter-postgres`).

---

## 3. Authenticate Docker with Fly.io

Before pushing the image, authenticate with Fly.io’s container registry:

```sh
fly auth docker
```

This command ensures Docker can push images to Fly.io.

---

## 4. Push the Image to Fly.io

Once authenticated, push the image to the Fly.io registry:

```sh
docker push registry.fly.io/ghostwriter-postgres:latest
```

This uploads your locally built image to Fly.io’s private container registry.

---

## 5. Deploy the Custom PostgreSQL Image

Deploy the pushed image to Fly.io:

```sh
fly deploy --image registry.fly.io/ghostwriter-postgres:latest -a ghostwriter-postgres
```

This updates your Fly.io PostgreSQL instance with the new Docker image.

---

## 6. Verify Deployment

Check the status of your app:

```sh
fly status
```

View logs to confirm the database is running correctly:

```sh
fly logs
```

---

## 7. Rollback (If Needed)

If something goes wrong, you can roll back to a previous version:

```sh
fly releases -a ghostwriter-postgres
fly rollback -a ghostwriter-postgres
```

---

## Conclusion

This guide covered:
✅ Building a PostgreSQL with pgvector Docker image
✅ Tagging and pushing the image to Fly.io
✅ Deploying and verifying the database update
✅ Rolling back if needed

Now your Fly.io PostgreSQL instance is running a **custom-built Docker image with pgvector**! 🚀

