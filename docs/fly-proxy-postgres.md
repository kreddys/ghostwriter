# Connect to fly.io postgres from local
fly proxy 15432:5432 -a ghostwriter-postgres

# Use 15432 as port while connecting