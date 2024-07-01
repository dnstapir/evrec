CONTAINER=		ghcr.io/dnstapir/evrec:latest
CONTAINER_BASE=		evrec:latest
BUILDINFO=		evrec/buildinfo.py

DEPENDS=		$(BUILDINFO)


all: $(DEPENDS)

$(BUILDINFO):
	printf "__commit__ = \"`git rev-parse HEAD`\"\n__timestamp__ = \"`date +'%Y-%m-%d %H:%M:%S %Z'`\"\n" > $(BUILDINFO)

container: $(DEPENDS)
	docker buildx build -t $(CONTAINER) -t $(CONTAINER_BASE) .

push-container:
	docker push $(CONTAINER)

server: $(DEPENDS) clients clients/test.pem
	poetry run evrec_server --debug

test-private.pem:
	openssl ecparam -genkey -name prime256v1 -noout -out $@

clients:
	mkdir clients

clients/test.pem: test-private.pem
	openssl ec -in $< -pubout -out $@

test: $(DEPENDS)
	poetry run pytest --ruff --ruff-format

lint:
	poetry run ruff check .

reformat:
	poetry run ruff check --select I --fix
	poetry run ruff format .

clean:
	rm -f *.pem
	rm -fr clients
	rm -f $(BUILDINFO)

realclean: clean
	poetry env remove --all
