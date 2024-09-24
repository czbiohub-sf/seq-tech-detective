NAME=seq-detective
BUILDDIR=build
PREFIXARG=--prefix $(PWD)/seq-detective

.PHONY: $(NAME) profile install test clean lint lint_c lint_py lint_sh fmt

$(NAME): $(BUILDDIR)
	meson compile -C $(BUILDDIR)
	meson install -C $(BUILDDIR)

$(BUILDDIR):
	meson setup $(BUILDDIR) --reconfigure $(PREFIXARG) $(CFGFLAGS)

ext-specs: CFGFLAGS += -Dext_specs=enabled
ext-specs: $(BUILDDIR) $(NAME)

profile: CFGFLAGS += -Dtracy=enabled
profile: $(BUILDDIR) $(NAME)

install: CFGFLAGS += -Dext_specs=enabled PREFIXARG =
install: $(BUILDDIR) $(NAME)

# unit tests:
test: CFGFLAGS += -Dtest=enabled -Db_coverage=true
test: $(BUILDDIR)
	meson test -C $(BUILDDIR) --interactive

# clean:
clean: $(BUILDDIR)
	meson compile -C $(BUILDDIR) --clean
	rm -r $(BUILDDIR)

# linters
lint_c: $(BUILDDIR)
	meson --internal clangtidy . $(BUILDDIR)

lint_py:
	-ruff check

lint_sh:
	-shellcheck --extended-analysis=true -o all -e SC2312 -S style classify-rnaseq

lint: lint_py lint_sh lint_c

# format
fmt:
	meson fmt -r -i
	meson --internal clangformat . $(BUILDDIR)
