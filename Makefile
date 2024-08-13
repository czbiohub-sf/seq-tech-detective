NAME=seq-detective
BUILDDIR=build

.PHONY: $(NAME) profile clean lint lint_c lint_py lint_sh fmt

$(NAME): $(BUILDDIR)
	meson compile -C $(BUILDDIR)

$(BUILDDIR):
	meson setup $(BUILDDIR) --reconfigure

profile:
	meson setup $(BUILDDIR) --reconfigure -Dtracy_enable=enabled
	meson compile -C $(BUILDDIR)

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
	meson fmt -i
	ninja -C $(BUILDDIR) clang-format