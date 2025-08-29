FROM alpine:latest

ARG ROOT_HINTS="https://www.internic.net/domain/named.root"
ARG ICANN_CERT="https://data.iana.org/root-anchors/icannbundle.pem"
ARG PUID="1000"
ARG PGID="1000"

WORKDIR /var/unbound/etc
COPY unbound/unbound.conf /var/unbound/etc/unbound.conf

RUN apk update \
    && apk add --no-cache tini drill curl unbound ca-certificates \
    && curl -q -o /var/unbound/etc/root.hints -SL ${ROOT_HINTS} \
    && curl -o /tmp/icannbundle.pem -SL ${ICANN_CERT} \
    && unbound-anchor -a /var/unbound/etc/root.key -c /tmp/icannbundle.pem -r /var/unbound/etc/root.hints || echo "Root Key was updated"  \
    && rm -rf /tmp/* \
    && unbound-checkconf ./unbound.conf 

USER root
EXPOSE 53

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s CMD drill -p 53 @127.0.0.1 a.root-servers.net || exit 1

ENTRYPOINT ["/sbin/tini","--","unbound"]

CMD ["-dd","-c","/var/unbound/etc/unbound.conf"]