.PHONY: installdeps srpm

installdeps:
	dnf -y install git autoconf automake make python3-devel

srpm: installdeps
	# $(eval SUFFIX=$(shell sh -c " echo '.$$(date -u +%Y%m%d%H%M%S).git$$(git rev-parse --short HEAD)'"))
	# changing the spec file as passing -D won't preserve the suffix when rebuilding in mock
	# sed "s:%{?release_suffix}:${SUFFIX}:" -i mom.spec.in
	mkdir -p tmp.repos
	./autogen.sh
	./configure --prefix=/usr --disable-python-syntax-check
	make dist
	rpmbuild \
		-D "_topdir tmp.repos" \
		-ts ./*.tar.gz
	cp tmp.repos/SRPMS/*.src.rpm $(outdir)
