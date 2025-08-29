FROM powerdns/dnsdist-18:latest

USER root

RUN apt update

# RUN apt install curl ca-certificates -y
# RUN install -d /usr/share/postgresql-common/pgdg
# RUN curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc

# # Create the repository configuration file:
# RUN sh -c 'echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'

# RUN /bin/sh -c set -ex; export PYTHONDONTWRITEBYTECODE=1; dpkgArch="$(dpkg --print-architecture)"; aptRepo="[ signed-by=/usr/local/share/keyrings/postgres.gpg.asc ] http://apt.postgresql.org/pub/repos/apt/ bookworm-pgdg main $PG_MAJOR"; case "$dpkgArch" in amd64 | arm64 | ppc64el | s390x) echo "deb $aptRepo" > /etc/apt/sources.list.d/pgdg.list; apt-get update; ;; *) echo "deb-src $aptRepo" > /etc/apt/sources.list.d/pgdg.list; savedAptMark="$(apt-mark showmanual)"; tempDir="$(mktemp -d)"; cd "$tempDir"; apt-get update; apt-get install -y --no-install-recommends dpkg-dev; echo "deb [ trusted=yes ] file://$tempDir ./" > /etc/apt/sources.list.d/temp.list; _update_repo() { dpkg-scanpackages . > Packages; apt-get -o Acquire::GzipIndexes=false update; }; _update_repo; nproc="$(nproc)"; export DEB_BUILD_OPTIONS="nocheck parallel=$nproc"; apt-get build-dep -y postgresql-common pgdg-keyring; apt-get source --compile postgresql-common pgdg-keyring; _update_repo; DEBIAN_FRONTEND=noninteractive apt-get build-dep -y "postgresql-$PG_MAJOR=$PG_VERSION"; apt-get source --compile "postgresql-$PG_MAJOR=$PG_VERSION"; apt-mark showmanual | xargs apt-mark auto > /dev/null; apt-mark manual $savedAptMark; ls -lAFh; _update_repo; grep '^Package: ' Packages; cd /; ;; esac; apt-get install -y --no-install-recommends postgresql-common; sed -ri 's/#(create_main_cluster) .*$/\1 = false/' /etc/postgresql-common/createcluster.conf; apt-get install -y --no-install-recommends "postgresql-$PG_MAJOR=$PG_VERSION" ; rm -rf /var/lib/apt/lists/*; if [ -n "$tempDir" ]; then apt-get purge -y --auto-remove; rm -rf "$tempDir" /etc/apt/sources.list.d/temp.list; fi; find /usr -name '*.pyc' -type f -exec bash -c 'for pyc; do dpkg -S "$pyc" &> /dev/null || rm -vf "$pyc"; done' -- '{}' +; # buildkit


# RUN apt update

# RUN apt install postgresql -y
RUN apt install -y postgresql-common

# RUN apt install postgresql-client-16 libpq-dev -y
RUN apt-get install luarocks -y
RUN apt-get install git -y
RUN apt install -y gnupg

RUN bash /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh  -y

RUN apt install postgresql -y
RUN apt install -y libpq-dev

RUN ln -s /usr/include/postgresql/* /usr/local/include/

# ✅ FIX: install Lua dev headers + LuaSQL Postgres module so require "luasql.postgres" works
RUN apt-get update && \
    apt-get install -y liblua5.3-dev lua-sql-postgres && \
    rm -rf /var/lib/apt/lists/*

# RUN luarocks install luasql-postgres