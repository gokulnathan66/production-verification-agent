all-server:
cd src && docker compose --env-file ../.env up --build

all-server-spin:
cd src && docker compose --env-file ../.env up 
