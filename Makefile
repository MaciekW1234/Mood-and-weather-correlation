COMPOSE_BASE = docker/docker-compose.base.yml
COMPOSE_DEV  = docker/docker-compose.dev.yml
COMPOSE_TEST = docker/docker-compose.test.yml
COMPOSE_PROD = docker/docker-compose.prod.yml

DC_DEV  = docker compose -f $(COMPOSE_BASE) -f $(COMPOSE_DEV)
DC_TEST = docker compose -f $(COMPOSE_BASE) -f $(COMPOSE_TEST)
DC_PROD = docker compose -f $(COMPOSE_BASE) -f $(COMPOSE_PROD)

# dev
dev-up:        ## Uruchom środowisko dev w tle
	$(DC_DEV) up -d

dev-down:      ## Zatrzymaj środowisko dev
	$(DC_DEV) down

dev-logs:      ## Pokaż logi środowiska dev
	$(DC_DEV) logs -f

dev-ps:        ## Status kontenerów dev
	$(DC_DEV) ps

# test
test-up:       ## Uruchom środowisko test w tle
	$(DC_TEST) up -d

test-down:     ## Zatrzymaj środowisko test
	$(DC_TEST) down

test-ps:       ## Status kontenerów test
	$(DC_TEST) ps

# prod
prod-up:       ## Uruchom środowisko prod w tle
	$(DC_PROD) up -d

prod-down:     ## Zatrzymaj środowisko prod
	$(DC_PROD) down

prod-ps:       ## Status kontenerów prod (z healthcheck)
	$(DC_PROD) ps

# narzedzia
clean:         ## Usuń wszystkie kontenery i wolumeny (UWAGA: utrata danych)
	$(DC_DEV) down -v
	$(DC_TEST) down -v
	$(DC_PROD) down -v

help:
	@echo Dostepne komendy:
	@echo   dev-up      Uruchom srodowisko dev w tle
	@echo   dev-down    Zatrzymaj srodowisko dev
	@echo   dev-logs    Pokaz logi srodowiska dev
	@echo   dev-ps      Status kontenerow dev
	@echo   test-up     Uruchom srodowisko test w tle
	@echo   test-down   Zatrzymaj srodowisko test
	@echo   test-ps     Status kontenerow test
	@echo   prod-up     Uruchom srodowisko prod w tle
	@echo   prod-down   Zatrzymaj srodowisko prod
	@echo   prod-ps     Status kontenerow prod (z healthcheck)
	@echo   clean       Usun wszystkie kontenery i wolumeny

.PHONY: dev-up dev-down dev-logs dev-ps test-up test-down test-ps prod-up prod-down prod-ps clean help