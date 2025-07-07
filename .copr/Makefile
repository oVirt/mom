.PHONY: installdeps git-safe srpm

installdeps:
	dnf -y install git autoconf automake make python3-devel

# Explicity mark the copr generated git repo directory as safe for git
# commands. The directory is created prior to the mock call to the make_srpm
# and will be the current pwd.
git-safe:
	# From git 2.35.2 we need to mark temporary directory, where the
	# project is cloned to, as safe, otherwise git commands won't work
	# because of the fix for CVE-2022-24765
	git config --global --add safe.directory "$(shell pwd)"

srpm: installdeps git-safe
	#$(eval SUFFIX=$(shell sh -c " echo '.$$(date -u +%Y%m%d%H%M%S).git$$(git rev-parse --short HEAD)'"))
	# changing the spec file as passing -D won't preserve the suffix when rebuilding in mock
	#sed "s:%{?release_suffix}:${SUFFIX}:" -i mom.spec.in
	mkdir -p tmp.repos
	./autogen.sh
	./configure --prefix=/usr --disable-python-syntax-check
	make dist
	rpmbuild \
		-D "_topdir tmp.repos" \
		-ts ./*.tar.gz
	cp tmp.repos/SRPMS/*.src.rpm $(outdir)
